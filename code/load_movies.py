"""Load the classic "Movies" example graph (used in chapters 4, 5 and 8) into ArangoDB.

    python load_movies.py                 # downloads Neo4j's public movies.cypher and imports it
    python load_movies.py path/to.cypher  # or parse a local copy

The source script is plain Cypher (MERGE ... ON CREATE SET ...). Rather than
re-typing the data, we parse it and map it onto ArangoDB:

    (:Person)               -> document collection  persons   (_key from the name)
    (:Movie)                -> document collection  movies    (_key from the title)
    [:ACTED_IN {roles}]     -> edge collection      acted_in  (persons -> movies)
    [:DIRECTED|PRODUCED|WROTE|REVIEWED] -> directed / produced / wrote / reviewed
    [:FOLLOWS]              -> edge collection      follows   (persons -> persons)
plus a named graph "movies" that ties them together.
"""
from __future__ import annotations

import re
import sys

import requests

from kit import db as kdb
from kit.text import safe_key

SCRIPT_URL = "https://raw.githubusercontent.com/neo4j-graph-examples/movies/main/scripts/movies.cypher"
DB_NAME = "movies"
LABEL_TO_COLLECTION = {"Person": "persons", "Movie": "movies"}
IDENTITY = {"Person": "name", "Movie": "title"}

EDGE_DEFINITIONS = [
    {"edge_collection": e, "from_vertex_collections": ["persons"], "to_vertex_collections": ["movies"]}
    for e in ("acted_in", "directed", "produced", "wrote", "reviewed")
] + [{"edge_collection": "follows", "from_vertex_collections": ["persons"],
      "to_vertex_collections": ["persons"]}]


# ------------------------------------------------------------ tiny Cypher reader
def _skip_ws(s: str, i: int) -> int:
    while i < len(s) and s[i] in " \t\r\n":
        i += 1
    return i


def parse_literal(s: str, i: int):
    """Parse a Cypher literal (string, number, bool, null, list, map) at s[i]."""
    i = _skip_ws(s, i)
    c = s[i]
    if c in "'\"":
        out, j = [], i + 1
        while s[j] != c:
            if s[j] == "\\":
                out.append(s[j + 1])
                j += 2
            else:
                out.append(s[j])
                j += 1
        return "".join(out), j + 1
    if c == "[":
        items, j = [], _skip_ws(s, i + 1)
        while s[j] != "]":
            v, j = parse_literal(s, j)
            items.append(v)
            j = _skip_ws(s, j)
            if s[j] == ",":
                j = _skip_ws(s, j + 1)
        return items, j + 1
    if c == "{":
        obj, j = {}, _skip_ws(s, i + 1)
        while s[j] != "}":
            m = re.compile(r"(\w+)\s*:").match(s, j)
            v, j = parse_literal(s, m.end())
            obj[m.group(1)] = v
            j = _skip_ws(s, j)
            if s[j] == ",":
                j = _skip_ws(s, j + 1)
        return obj, j + 1
    m = re.compile(r"-?\d+(\.\d+)?").match(s, i)
    if m:
        txt = m.group(0)
        return (float(txt) if "." in txt else int(txt)), m.end()
    for word, val in (("true", True), ("false", False), ("null", None)):
        if s.startswith(word, i):
            return val, i + len(word)
    raise ValueError(f"cannot parse literal at {s[i:i + 30]!r}")


def split_statements(script: str) -> list[str]:
    out, buf, quote, i = [], [], None, 0
    while i < len(script):
        c = script[i]
        if quote:
            buf.append(c)
            if c == "\\":
                buf.append(script[i + 1])
                i += 1
            elif c == quote:
                quote = None
        elif c in "'\"":
            quote = c
            buf.append(c)
        elif c == ";":
            out.append("".join(buf))
            buf = []
        else:
            buf.append(c)
        i += 1
    out.append("".join(buf))
    return [s for s in out if s.strip()]


NODE = re.compile(r"\((\w+):(\w+)\s*")
REL = re.compile(r"\((\w+)\)-\[:(\w+)\s*")
ASSIGN = re.compile(r"(\w+)\.(\w+)\s*=\s*")


def parse_cypher(script: str):
    nodes: dict[tuple[str, str], dict] = {}
    rels: list[tuple[str, tuple, tuple, dict]] = []
    for stmt in split_statements(script):
        if "CONSTRAINT" in stmt:
            continue
        var: dict[str, tuple[str, str]] = {}
        i = 0
        while i < len(stmt):
            m = NODE.match(stmt, i)
            if m and stmt[m.end():m.end() + 1] == "{":
                props, j = parse_literal(stmt, m.end())
                label = m.group(2)
                ident = (label, props[IDENTITY[label]])
                nodes.setdefault(ident, {}).update(props)
                var[m.group(1)] = ident
                i = stmt.index(")", j) + 1
                continue
            m = REL.match(stmt, i)
            if m:
                j = m.end()
                props = {}
                if stmt[j] == "{":
                    props, j = parse_literal(stmt, j)
                end = re.compile(r"\s*\]->\((\w+)\)").match(stmt, j)
                rels.append((m.group(2), var[m.group(1)], var[end.group(1)], props))
                i = end.end()
                continue
            m = ASSIGN.match(stmt, i)
            if m and m.group(1) in var:
                val, j = parse_literal(stmt, m.end())
                nodes[var[m.group(1)]][m.group(2)] = val
                i = j
                continue
            i += 1
    return nodes, rels


def to_arango(nodes, rels):
    docs = {c: [] for c in LABEL_TO_COLLECTION.values()}
    keys = {}
    for (label, ident), props in nodes.items():
        key = safe_key(ident)
        keys[(label, ident)] = f"{LABEL_TO_COLLECTION[label]}/{key}"
        docs[LABEL_TO_COLLECTION[label]].append({"_key": key, **props})
    edges: dict[str, list[dict]] = {}
    for rtype, a, b, props in rels:
        frm, to = keys[a], keys[b]
        edges.setdefault(rtype.lower(), []).append({
            "_key": safe_key(frm.split("/")[1] + "__" + to.split("/")[1]),
            "_from": frm, "_to": to, **props})
    return docs, edges


def load(db, script: str | None = None) -> dict[str, int]:
    if script is None:
        script = requests.get(SCRIPT_URL, timeout=60).text
    docs, edges = to_arango(*parse_cypher(script))
    kdb.ensure_graph(db, "movies", EDGE_DEFINITIONS)
    counts = {}
    for name, rows in list(docs.items()) + list(edges.items()):
        db.collection(name).insert_many(rows, overwrite_mode="replace")
        counts[name] = len(rows)
    kdb.ensure_persistent_index(db.collection("persons"), ["name"], unique=True)
    kdb.ensure_persistent_index(db.collection("movies"), ["title"], unique=True)
    return counts


if __name__ == "__main__":
    text = open(sys.argv[1], encoding="utf-8").read() if len(sys.argv) > 1 else None
    print(load(kdb.connect(DB_NAME), text))
