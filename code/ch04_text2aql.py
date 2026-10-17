"""Chapter 4 - text2aql: let the LLM write AQL for questions vectors can't answer.

    python load_movies.py                        # once
    python ch04_text2aql.py "Who directed the most movies?"

prompt = instructions + schema + terminology mapping + few-shot examples
         + format instructions + question
LLM -> AQL -> explain (syntax/plan check) -> run as a read-only user -> rows
"""
from __future__ import annotations

import json
import re
import sys

from arango.exceptions import ArangoError

from kit import db as kdb
from kit import llm

DB_NAME = "movies"

# --------------------------------------------------------------------------- AQL
# ArangoDB has no apoc.meta.data(); we sample documents instead (cheap, and the
# same trick Neo4j users apply on large graphs).
DOC_ATTRIBUTES = """
FOR d IN @@collection
  LIMIT @sample
  FOR attribute IN ATTRIBUTES(d, true)
    COLLECT name = attribute AGGREGATE types = UNIQUE(TYPENAME(d[attribute]))
    SORT name
    RETURN { name, types }
"""

EDGE_PATTERNS = """
FOR e IN @@collection
  LIMIT @sample
  COLLECT from_collection = PARSE_IDENTIFIER(e._from).collection,
          to_collection = PARSE_IDENTIFIER(e._to).collection
  RETURN { from_collection, to_collection }
"""

# --------------------------------------------------------------------------- prompt
PROMPT_TEMPLATE = """Task: write one AQL (ArangoDB Query Language) query that retrieves the data needed to answer the user question.

Database schema:
Use only the collections, edge collections and attributes listed here. Do not invent others.
{schema}

Terminology mapping:
This section maps words in the question to the schema.
{terminology}

Examples:
The following examples show useful query patterns for this database.
{examples}

AQL reminders:
- Walk relationships with: FOR v, e IN 1..1 OUTBOUND|INBOUND|ANY start edge_collection
- Return only the attributes you need, never whole documents.
- The query must be read-only: no INSERT, UPDATE, REPLACE, REMOVE or UPSERT.

Format instructions:
Do not include explanations or apologies. Do not answer anything other than with an AQL query.
Respond with the AQL query only - no code fences, no comments.

User question: {question}"""

TERMINOLOGY = """Persons: actors, directors, writers, producers and reviewers are all documents in the `persons` collection; their job is the edge collection that connects them to a movie (acted_in, directed, wrote, produced, reviewed).
Movies: a "film" or "movie" is a document in the `movies` collection."""

EXAMPLES = [
    ("Which two people acted together in the most movies?",
     """FOR p1 IN persons
  FOR m IN 1..1 OUTBOUND p1 acted_in
    FOR p2 IN 1..1 INBOUND m acted_in
      FILTER p1._key < p2._key
      COLLECT actor1 = p1.name, actor2 = p2.name WITH COUNT INTO movie_count
      SORT movie_count DESC
      LIMIT 1
      RETURN { actor1, actor2, movie_count }"""),
    ("What is the average review rating of movies directed by Ron Howard?",
     """FOR d IN persons
  FILTER d.name == "Ron Howard"
  FOR m IN 1..1 OUTBOUND d directed
    FOR reviewer, review IN 1..1 INBOUND m reviewed
      COLLECT AGGREGATE avg_rating = AVERAGE(review.rating)
      RETURN { avg_rating }"""),
]

WRITE_KEYWORDS = re.compile(r"\b(INSERT|UPDATE|REPLACE|REMOVE|UPSERT)\b", re.I)


# --------------------------------------------------------------------------- schema
def get_structured_schema(db, sample: int = 100) -> dict:
    """Collections, attributes (+ observed types) and edge patterns, by sampling."""
    schema = {"collections": {}, "edges": {}, "patterns": []}
    for col in db.collections():
        if col["system"]:
            continue
        name = col["name"]
        attrs = kdb.aql(db, DOC_ATTRIBUTES, **{"@collection": name, "sample": sample})
        if col["type"] == "edge":
            schema["edges"][name] = attrs
            for p in kdb.aql(db, EDGE_PATTERNS, **{"@collection": name, "sample": sample}):
                schema["patterns"].append({"edge": name, **p})
        else:
            schema["collections"][name] = attrs
    return schema


def format_schema(s: dict) -> str:
    def props(attrs):
        hidden = {"embedding"}  # vectors are noise for the LLM
        return ", ".join(f"{a['name']}: {'|'.join(a['types'])}" for a in attrs if a["name"] not in hidden)

    lines = ["Document collections and attributes:"]
    lines += [f"{c} {{{props(a)}}}" for c, a in sorted(s["collections"].items())]
    lines.append("Edge collections and attributes:")
    lines += [f"{e} {{{props(a)}}}" for e, a in sorted(s["edges"].items())]
    lines.append("Relationships (edge collection: from -> to):")
    lines += [f"{p['edge']}: {p['from_collection']} -> {p['to_collection']}" for p in s["patterns"]]
    return "\n".join(lines)


def build_prompt(question: str, schema_text: str) -> str:
    examples = "\n".join(f"Question: {q}\nAQL:\n{a}\n" for q, a in EXAMPLES)
    return PROMPT_TEMPLATE.format(schema=schema_text, terminology=TERMINOLOGY,
                                  examples=examples, question=question)


# --------------------------------------------------------------------------- run
def reader_db(admin_db, password: str = "readonly-demo"):
    """A second connection as a read-only user: the real safety net."""
    from arango import ArangoClient

    sys_db = ArangoClient(hosts=kdb.ARANGO_URL).db(
        "_system", username=kdb.ARANGO_USER, password=kdb.ARANGO_PASSWORD)
    if not sys_db.has_user("aql_reader"):
        sys_db.create_user("aql_reader", password)
    sys_db.update_permission("aql_reader", "ro", admin_db.name)                  # database level
    sys_db.update_permission("aql_reader", "ro", admin_db.name, collection="*")  # all its collections
    return ArangoClient(hosts=kdb.ARANGO_URL).db(admin_db.name, username="aql_reader", password=password)


def clean(query: str) -> str:
    query = query.strip()
    query = re.sub(r"^```(?:aql|sql)?\s*|\s*```$", "", query)  # some models add fences anyway
    return query.strip()


def text2aql(db, question: str, schema_text: str | None = None, attempts: int = 3) -> tuple[str, list]:
    """Generate AQL, check it with EXPLAIN, run it read-only; on error, show the
    LLM the error message and let it fix the query (bonus: not in the book)."""
    schema_text = schema_text or format_schema(get_structured_schema(db))
    ro = reader_db(db)
    messages = [{"role": "user", "content": build_prompt(question, schema_text)}]
    last_error = ""
    for _ in range(attempts):
        query = clean(llm.chat(messages))
        if WRITE_KEYWORDS.search(query):
            last_error = "The query must be read-only."
        else:
            try:
                ro.aql.explain(query)  # parses + plans, does not execute
                rows = list(ro.aql.execute(query, max_runtime=10, memory_limit=256 * 1024 * 1024))
                return query, rows
            except ArangoError as exc:
                last_error = str(exc)
        messages += [{"role": "assistant", "content": query},
                     {"role": "user", "content": f"That query failed: {last_error}\n"
                                                 "Return a corrected AQL query only."}]
    raise RuntimeError(f"could not produce a working query: {last_error}")


def main() -> None:
    question = sys.argv[1] if len(sys.argv) > 1 else "Who directed the most movies?"
    db = kdb.connect(DB_NAME)
    schema_text = format_schema(get_structured_schema(db))
    print(schema_text, "\n")
    query, rows = text2aql(db, question, schema_text)
    print(query, "\n")
    print(json.dumps(rows, indent=2))


if __name__ == "__main__":
    main()
