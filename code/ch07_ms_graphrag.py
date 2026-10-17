"""Chapter 7 - Microsoft-style GraphRAG on ArangoDB (The Odyssey).

    python ch07_ms_graphrag.py index --books 1        # build the graph index for book I
    python ch07_ms_graphrag.py global "What is this story about?"
    python ch07_ms_graphrag.py local  "Who is Ulysses?"

Indexing:  books -> chunks -> LLM extracts entities + relationships (with descriptions)
           -> LLM merges descriptions per entity / per entity pair
           -> Louvain communities -> LLM writes one report per community
Querying:  global = map-reduce over community reports
           local  = vector search for entities -> expand to chunks, reports, relationships

Collections (database "ch07"):
  chunks --has_entity--> entities --related--> entities        (raw, many per pair)
                         entities --summarized--> entities     (one per pair, with summary)
                         entities --in_community--> communities
"""
from __future__ import annotations

import argparse
import json
import random
import re

import networkx as nx
import requests

from kit import db as kdb
from kit import llm
from kit.text import chunk_text, content_key, count_tokens, safe_key

DB_NAME = "ch07"
ODYSSEY_URL = "https://www.gutenberg.org/cache/epub/1727/pg1727.txt"
ENTITY_TYPES = ["PERSON", "ORGANIZATION", "LOCATION", "GOD", "EVENT", "CREATURE", "WEAPON_OR_TOOL"]
TUPLE, RECORD, DONE = "<|>", "##", "<|COMPLETE|>"

# =========================================================================== prompts
EXTRACTION_PROMPT = """-Goal-
Given a text and a list of entity types, find every entity of those types in the
text and every relationship between the entities you found.

-Steps-
1. For each entity, record:
   - entity_name: the name, in UPPER CASE
   - entity_type: one of [{entity_types}]
   - entity_description: everything the text says about the entity's attributes and actions
   Format: ("entity"{t}<entity_name>{t}<entity_type>{t}<entity_description>)
2. For each pair of entities from step 1 that are clearly related, record:
   - source_entity, target_entity: the names exactly as in step 1
   - relationship_description: why they are related
   - relationship_strength: an integer from 1 (weak) to 10 (strong)
   Format: ("relationship"{t}<source_entity>{t}<target_entity>{t}<relationship_description>{t}<relationship_strength>)
3. Output all entities and relationships as a single list in English, separated by {r}.
4. When finished, output {done}

-Example-
Entity types: PERSON, LOCATION
Text: Ada sailed from Lisbon to meet her brother Tomas, who had taught her to navigate.
Output:
("entity"{t}ADA{t}PERSON{t}Ada is a sailor who travels from Lisbon to meet her brother Tomas.)
{r}
("entity"{t}TOMAS{t}PERSON{t}Tomas is Ada's brother; he taught her to navigate.)
{r}
("entity"{t}LISBON{t}LOCATION{t}Lisbon is the city Ada sails from.)
{r}
("relationship"{t}ADA{t}TOMAS{t}Tomas is Ada's brother and taught her to navigate.{t}9)
{r}
("relationship"{t}ADA{t}LISBON{t}Ada sets sail from Lisbon.{t}4)
{done}

-Real data-
Entity types: {entity_types}
Text: {text}
Output:"""

# "Gleaning": ask again for what was missed (more passes -> more entities, fig. 7.2)
GLEAN_CONTINUE = ("Many entities and relationships were missed in the last extraction. "
                  "Add them below using the same format:")
GLEAN_CHECK = ("Some entities or relationships may still be missing. Answer Y if there are "
               "still entities or relationships to add, or N if there are none. Answer Y or N only.")

SUMMARIZE_PROMPT = """You turn several partial descriptions into one comprehensive description.
Below are one or two entities and a list of descriptions of them, collected from
different parts of a text. Merge them into a single, coherent description that keeps
every distinct fact and resolves contradictions. Write in the third person and
mention the entity names so the description stands on its own.

Entities: {name}
Descriptions:
{descriptions}

Description:"""

COMMUNITY_REPORT_PROMPT = """You help an analyst understand a community: a group of closely connected
entities from a knowledge graph. Write a report about the community below using only
the entities and relationships given.

Return JSON with exactly these keys:
{{
  "title": "a short, specific name that mentions the key entities",
  "summary": "an executive summary of who or what is in the community and how they relate",
  "rating": "a number from 0 to 10: how important this community is for understanding the text",
  "rating_explanation": "one sentence that justifies the rating",
  "findings": [{{"summary": "insight headline", "explanation": "a paragraph grounded in the data"}}]
}}
Give 5 to 10 findings.

Entities (name | type | description):
{entities}

Relationships (source | target | description):
{relationships}"""

MAP_SYSTEM_PROMPT = """You answer questions about a dataset using the community reports below.

Return JSON: {{"points": [{{"description": "...", "score": 0}}]}}
- Each point answers part of the user's question and ends with its evidence,
  e.g. "Minerva guides Telemachus [Data: Reports (3)]".
- score: how important the point is for answering the question, 0-100.
- If the reports do not help, return a single point saying so with score 0.
- Use only the reports. Do not make anything up.

----- Reports -----
{context}"""

REDUCE_SYSTEM_PROMPT = """You combine findings from several analysts, each of whom read a different
part of a dataset, into one answer to the user's question. The findings are listed
from most to least important.
- Drop what is irrelevant; merge the rest into a well-structured markdown answer.
- Keep the data references such as [Data: Reports (2, 7)]; list at most 5 ids per
  reference, then "+more". Never mention the analysts.
- If the findings do not answer the question, say so. Do not make anything up.
Target length and format: {response_type}

----- Findings -----
{findings}"""

LOCAL_SYSTEM_PROMPT = """You answer the user's question from the data tables below: entities,
relationships, community reports and source text taken from a knowledge graph.
- Support statements with references such as
  [Data: Entities (5, 7); Relationships (23); Reports (2); Sources (4)];
  at most 5 ids per table, then "+more".
- If the tables do not contain the answer, say you don't know. Do not make anything up.
Target length and format: {response_type}

----- Data tables -----
{context}"""

# =========================================================================== AQL
IMPORT_CHUNK_ENTITIES = """
LET chunk = FIRST(
  INSERT { _key: @chunk_key, book: @book, chunk: @chunk, text: @text }
  INTO chunks OPTIONS { overwriteMode: "replace" }
  RETURN NEW
)
LET found = (
  FOR e IN @entities
    UPSERT { _key: e.key }
    INSERT { _key: e.key, name: e.name, type: e.type, descriptions: e.descriptions }
    UPDATE { descriptions: UNION_DISTINCT(OLD.descriptions, e.descriptions) }
    IN entities
    RETURN NEW._id
)
FOR id IN found
  INSERT { _key: CONCAT(chunk._key, "-", PARSE_IDENTIFIER(id).key), _from: chunk._id, _to: id }
  INTO has_entity OPTIONS { overwriteMode: "ignore" }
"""

IMPORT_RELATIONSHIPS = """
FOR r IN @relationships
  LET source = CONCAT("entities/", r.source)
  LET target = CONCAT("entities/", r.target)
  FILTER DOCUMENT(source) != null AND DOCUMENT(target) != null
  INSERT { _key: r.key, _from: source, _to: target, description: r.description,
           strength: r.strength, chunk: @chunk_key }
  INTO related OPTIONS { overwriteMode: "ignore" }
"""

COUNTS = """
RETURN {
  entities: COLLECTION_COUNT("entities"),
  relationships: COLLECTION_COUNT("related"),
  chunks: COLLECTION_COUNT("chunks")
}
"""

ENTITY_DESCRIPTIONS = """
FOR e IN entities
  FILTER e.name == @name
  RETURN e.descriptions
"""

# the entity pair with the most raw relationships (direction ignored)
BUSIEST_PAIR = """
FOR r IN related
  LET pair = r._from < r._to ? [r._from, r._to] : [r._to, r._from]
  COLLECT p = pair INTO descriptions = r.description
  SORT LENGTH(descriptions) DESC
  LIMIT 1
  RETURN { source: DOCUMENT(p[0]).name, target: DOCUMENT(p[1]).name,
           count: LENGTH(descriptions), descriptions }
"""

ENTITIES_TO_SUMMARIZE = """
FOR e IN entities
  FILTER LENGTH(e.descriptions) > 1
  RETURN { key: e._key, name: e.name, descriptions: e.descriptions }
"""

KEEP_SINGLE_DESCRIPTIONS = """
FOR e IN entities
  FILTER LENGTH(e.descriptions) == 1
  UPDATE e WITH { summary: e.descriptions[0] } IN entities
"""

SAVE_ENTITY_SUMMARIES = """
FOR s IN @summaries
  UPDATE { _key: s.key } WITH { summary: s.summary } IN entities
"""

# group raw relationships per (unordered) entity pair
RELATIONSHIP_PAIRS = """
FOR r IN related
  LET pair = r._from < r._to ? [r._from, r._to] : [r._to, r._from]
  COLLECT p = pair INTO rels = { description: r.description, strength: r.strength }
  RETURN { source: p[0], target: p[1], names: [DOCUMENT(p[0]).name, DOCUMENT(p[1]).name],
           descriptions: UNIQUE(rels[*].description), weight: SUM(rels[*].strength),
           count: LENGTH(rels) }
"""

SAVE_SUMMARIZED = """
FOR s IN @rows
  INSERT { _key: s.key, _from: s.source, _to: s.target, summary: s.summary,
           weight: s.weight, count: s.count }
  INTO summarized OPTIONS { overwriteMode: "replace" }
"""

# rank relationships like MS GraphRAG: combined degree of both endpoints
ENTITY_DEGREE = """
FOR e IN entities
  LET degree = LENGTH(FOR s IN summarized FILTER s._from == e._id OR s._to == e._id RETURN 1)
  UPDATE e WITH { degree } IN entities
"""
RELATIONSHIP_RANK = """
FOR s IN summarized
  UPDATE s WITH { rank: DOCUMENT(s._from).degree + DOCUMENT(s._to).degree } IN summarized
"""

GRAPH_EDGES = """
FOR s IN summarized
  RETURN { source: s._from, target: s._to, weight: s.weight }
"""

SAVE_COMMUNITIES = """
LET created = (
  FOR c IN @communities
    INSERT { _key: c.key, level: 0, size: LENGTH(c.members) }
    INTO communities OPTIONS { overwriteMode: "replace" }
    RETURN NEW._key
)
FOR c IN @communities
  FOR member IN c.members
    INSERT { _key: CONCAT(c.key, "-", PARSE_IDENTIFIER(member).key),
             _from: member, _to: CONCAT("communities/", c.key) }
    INTO in_community OPTIONS { overwriteMode: "ignore" }
"""

COMMUNITY_INFO = """
WITH entities
FOR c IN communities
  LET members = (FOR e IN 1..1 INBOUND c in_community RETURN e)
  LET member_ids = members[*]._id
  LET rels = (
    FOR m IN members
      FOR other, r IN 1..1 OUTBOUND m summarized
        FILTER other._id IN member_ids
        SORT r.rank DESC
        RETURN { source: m.name, target: other.name, description: r.summary }
  )
  RETURN {
    community: c._key,
    entities: members[* RETURN { name: CURRENT.name, type: CURRENT.type, description: CURRENT.summary }],
    relationships: rels
  }
"""

SAVE_REPORTS = """
FOR r IN @reports
  UPDATE { _key: r.community } WITH {
    title: r.title, summary: r.summary, rating: r.rating,
    rating_explanation: r.rating_explanation, findings: r.findings, full_content: r.full_content
  } IN communities
"""

# community weight = how many distinct chunks mention its members
COMMUNITY_WEIGHT = """
WITH entities, chunks
FOR c IN communities
  LET weight = LENGTH(
    FOR e IN 1..1 INBOUND c in_community
      FOR ch IN 1..1 INBOUND e has_entity
        RETURN DISTINCT ch._key
  )
  UPDATE c WITH { weight } IN communities
"""

LARGEST_COMMUNITY = """
FOR c IN communities
  SORT c.size DESC
  LIMIT 1
  RETURN { title: c.title, summary: c.summary, size: c.size }
"""

GLOBAL_COMMUNITIES = """
FOR c IN communities
  FILTER c.rating >= @min_rating
  SORT c.rating DESC
  RETURN { id: c._key, title: c.title, content: c.full_content }
"""

ENTITIES_TO_EMBED = """
FOR e IN entities
  FILTER e.summary != null
  RETURN { key: e._key, text: CONCAT(e.name, ": ", e.summary) }
"""

SAVE_EMBEDDINGS = """
FOR row IN @rows
  UPDATE { _key: row.key } WITH { embedding: row.embedding } IN entities
"""

# Book listing 7.20 in AQL: vector search for entry entities, then expand.
LOCAL_SEARCH = """
WITH entities, chunks, communities
LET nodes = (
  FOR e IN entities
    LET score = APPROX_NEAR_COSINE(e.embedding, @question_embedding)
    SORT score DESC
    LIMIT @k
    RETURN { id: e._id, key: e._key, name: e.name, type: e.type, summary: e.summary }
)
LET node_ids = nodes[*].id
LET sources = (
  FOR n IN nodes
    FOR ch IN 1..1 INBOUND n.id has_entity
      COLLECT chunk_id = ch._id WITH COUNT INTO mentions
      SORT mentions DESC
      LIMIT @top_chunks
      RETURN { id: PARSE_IDENTIFIER(chunk_id).key, text: DOCUMENT(chunk_id).text, mentions }
)
LET reports = (
  FOR n IN nodes
    FOR c IN 1..1 OUTBOUND n.id in_community
      COLLECT community_id = c._id WITH COUNT INTO matched
      LET community = DOCUMENT(community_id)
      SORT matched DESC, community.rating DESC, community.weight DESC
      LIMIT @top_communities
      RETURN { id: community._key, title: community.title, summary: community.summary }
)
LET relationships = (
  FOR n IN nodes
    FOR other, r IN 1..1 OUTBOUND n.id summarized
      FILTER other._id IN node_ids
      SORT r.rank DESC, r.weight DESC
      LIMIT @top_inside_rels
      RETURN { id: r._key, source: n.name, target: other.name, description: r.summary }
)
RETURN {
  entities: nodes[* RETURN { id: CURRENT.key, entity: CURRENT.name, type: CURRENT.type,
                             description: CURRENT.summary }],
  relationships,
  reports,
  sources
}
"""


# =========================================================================== indexing
def load_books() -> list[str]:
    raw = requests.get(ODYSSEY_URL, timeout=60).text
    return split_into_books(raw)


def split_into_books(raw: str) -> list[str]:
    """Cut the Gutenberg header/footer, then split on body headings 'BOOK I' ... 'BOOK XXIV'
    (contents entries look like ' BOOK I.' and are not matched)."""
    start = raw.find("*** START OF")
    end = raw.find("*** END OF")
    text = raw[max(start, 0): end if end > 0 else None]
    headings = list(re.finditer(r"^BOOK [IVXL]+\s*$", text, flags=re.M))
    if not headings:
        return []
    footnotes = text.rfind("\nFOOTNOTES")
    if footnotes > headings[-1].start():
        text = text[:footnotes]
    parts = re.split(r"^BOOK [IVXL]+\s*$", text, flags=re.M)
    return [p.strip() for p in parts[1:] if p.strip()]


def parse_extraction(output: str) -> tuple[dict, list]:
    """Parse ("entity"<|>NAME<|>TYPE<|>desc) ## ("relationship"<|>A<|>B<|>desc<|>7) records."""
    nodes: dict[str, dict] = {}
    rels: list[dict] = []
    for record in output.replace(DONE, "").split(RECORD):
        record = record.strip()
        if record.startswith("(") and record.endswith(")"):
            record = record[1:-1]
        fields = [f.strip().strip('"').strip() for f in record.split(TUPLE)]
        if fields[0].lower() == "entity" and len(fields) >= 4:
            name = fields[1].upper()
            node = nodes.setdefault(name, {"name": name, "type": fields[2].upper(), "descriptions": []})
            if fields[3] not in node["descriptions"]:
                node["descriptions"].append(fields[3])
        elif fields[0].lower() == "relationship" and len(fields) >= 5:
            try:
                strength = float(re.findall(r"[\d.]+", fields[4])[0])
            except (IndexError, ValueError):
                strength = 1.0
            rels.append({"source": fields[1].upper(), "target": fields[2].upper(),
                         "description": fields[3], "strength": strength})
    return nodes, rels


def extract_entities(text: str, gleanings: int = 0) -> tuple[dict, list]:
    prompt = EXTRACTION_PROMPT.format(entity_types=", ".join(ENTITY_TYPES), text=text,
                                      t=TUPLE, r=RECORD, done=DONE)
    messages = [{"role": "user", "content": prompt}]
    output = llm.chat(messages)
    messages.append({"role": "assistant", "content": output})
    for i in range(gleanings):                      # optional self-reflection passes
        messages.append({"role": "user", "content": GLEAN_CONTINUE})
        more = llm.chat(messages)
        messages.append({"role": "assistant", "content": more})
        output += RECORD + more
        if i == gleanings - 1:
            break
        verdict = llm.chat(messages + [{"role": "user", "content": GLEAN_CHECK}])
        if verdict.strip().upper()[:1] != "Y":
            break
    return parse_extraction(output)


def setup(db) -> None:
    kdb.ensure_graph(db, "odyssey", [
        {"edge_collection": "has_entity", "from_vertex_collections": ["chunks"],
         "to_vertex_collections": ["entities"]},
        {"edge_collection": "related", "from_vertex_collections": ["entities"],
         "to_vertex_collections": ["entities"]},
        {"edge_collection": "summarized", "from_vertex_collections": ["entities"],
         "to_vertex_collections": ["entities"]},
        {"edge_collection": "in_community", "from_vertex_collections": ["entities"],
         "to_vertex_collections": ["communities"]},
    ])


def import_chunk(db, book: int, chunk: int, text: str, nodes: dict, rels: list) -> None:
    chunk_key = f"b{book}-c{chunk}"
    entities = [{"key": safe_key(n["name"]), **n} for n in nodes.values()]
    kdb.aql(db, IMPORT_CHUNK_ENTITIES, chunk_key=chunk_key, book=book, chunk=chunk, text=text,
            entities=entities)
    relationships = [{**r, "source": safe_key(r["source"]), "target": safe_key(r["target"]),
                      "key": content_key(chunk_key + r["source"] + r["target"] + r["description"])}
                     for r in rels]
    kdb.aql(db, IMPORT_RELATIONSHIPS, relationships=relationships, chunk_key=chunk_key)


def summarize_descriptions(name: str, descriptions: list[str]) -> str:
    return llm.chat([{"role": "user", "content": SUMMARIZE_PROMPT.format(
        name=name, descriptions="\n".join(f"- {d}" for d in descriptions))}]).strip()


def summarize_entities_and_relationships(db) -> None:
    rows = kdb.aql(db, ENTITIES_TO_SUMMARIZE)
    summaries = [{"key": r["key"], "summary": summarize_descriptions(r["name"], r["descriptions"])}
                 for r in rows]
    kdb.aql(db, SAVE_ENTITY_SUMMARIES, summaries=summaries)
    kdb.aql(db, KEEP_SINGLE_DESCRIPTIONS)
    out = []
    for p in kdb.aql(db, RELATIONSHIP_PAIRS):
        if len(p["descriptions"]) > 1:
            summary = summarize_descriptions(" relationship to ".join(p["names"]), p["descriptions"])
        else:
            summary = p["descriptions"][0]
        out.append({"key": content_key(p["source"] + p["target"]), "source": p["source"],
                    "target": p["target"], "summary": summary, "weight": p["weight"],
                    "count": p["count"]})
    kdb.aql(db, SAVE_SUMMARIZED, rows=out)
    kdb.aql(db, ENTITY_DEGREE)
    kdb.aql(db, RELATIONSHIP_RANK)


def detect_communities(db, seed: int = 42) -> list[int]:
    """Louvain on the summarized graph (NetworkX). Returns community sizes."""
    graph = nx.Graph()
    for e in kdb.aql(db, GRAPH_EDGES):
        graph.add_edge(e["source"], e["target"], weight=e["weight"] or 1.0)
    found = nx.community.louvain_communities(graph, weight="weight", seed=seed)
    communities = [{"key": f"c{i}", "members": sorted(c)} for i, c in enumerate(found) if len(c) > 1]
    db.collection("in_community").truncate()
    db.collection("communities").truncate()
    kdb.aql(db, SAVE_COMMUNITIES, communities=communities)
    return sorted((len(c["members"]) for c in communities), reverse=True)


def write_community_reports(db) -> int:
    reports = []
    for info in kdb.aql(db, COMMUNITY_INFO):
        entities = "\n".join(f"{e['name']} | {e['type']} | {e['description']}" for e in info["entities"])
        relationships = "\n".join(f"{r['source']} | {r['target']} | {r['description']}"
                                  for r in info["relationships"])
        report = llm.chat_json([{"role": "user", "content": COMMUNITY_REPORT_PROMPT.format(
            entities=entities, relationships=relationships)}])
        try:
            rating = float(report.get("rating", 0))
        except (TypeError, ValueError):
            rating = 0.0
        findings = report.get("findings", [])
        full = "\n\n".join([f"# {report.get('title', '')}", report.get("summary", "")] +
                           [f"## {f.get('summary', '')}\n{f.get('explanation', '')}" for f in findings])
        reports.append({"community": info["community"], "title": report.get("title", ""),
                        "summary": report.get("summary", ""), "rating": rating,
                        "rating_explanation": report.get("rating_explanation", ""),
                        "findings": findings, "full_content": full})
    kdb.aql(db, SAVE_REPORTS, reports=reports)
    kdb.aql(db, COMMUNITY_WEIGHT)
    return len(reports)


def embed_entities(db) -> None:
    rows = kdb.aql(db, ENTITIES_TO_EMBED)
    vectors = llm.embed([r["text"] for r in rows])
    kdb.aql(db, SAVE_EMBEDDINGS, rows=[{"key": r["key"], "embedding": v} for r, v in zip(rows, vectors)])
    kdb.ensure_vector_index(db.collection("entities"), "embedding", dimension=len(vectors[0]), sparse=True)


def index(db, n_books: int = 1, chunk_chars: int = 1000, gleanings: int = 0) -> None:
    setup(db)
    books = load_books()
    if not books:
        raise RuntimeError("could not split the text into books")
    sizes = [count_tokens(b) for b in books]
    print(f"{len(books)} books; tokens avg {sum(sizes) // len(sizes)}, min {min(sizes)}, max {max(sizes)}")
    for b, book in enumerate(books[:n_books]):
        for c, chunk in enumerate(chunk_text(book, chunk_chars, 40)):
            nodes, rels = extract_entities(chunk, gleanings)
            import_chunk(db, b, c, chunk, nodes, rels)
    print("after extraction:", kdb.aql(db, COUNTS)[0])
    summarize_entities_and_relationships(db)
    print("community sizes:", detect_communities(db))
    print("reports:", write_community_reports(db))
    embed_entities(db)


# =========================================================================== retrieval
def _score(point: dict) -> float:
    try:
        return float(point.get("score", 0) or 0)
    except (TypeError, ValueError):
        return 0.0


def global_search(db, query: str, min_rating: float = 5, batch_tokens: int = 6000,
                  response_type: str = "multiple paragraphs") -> str:
    reports = kdb.aql(db, GLOBAL_COMMUNITIES, min_rating=min_rating)
    random.Random(7).shuffle(reports)                # spread themes across batches
    batches, cur, size = [], [], 0
    for r in reports:                                # pack reports into a token budget
        t = count_tokens(r["content"])
        if cur and size + t > batch_tokens:
            batches.append(cur)
            cur, size = [], 0
        cur.append(r)
        size += t
    if cur:
        batches.append(cur)
    points = []
    for batch in batches:                            # MAP: one LLM call per batch
        context = "\n\n".join(f"id: {r['id']}\n{r['content']}" for r in batch)
        out = llm.chat_json([{"role": "system", "content": MAP_SYSTEM_PROMPT.format(context=context)},
                             {"role": "user", "content": query}])
        points += [p for p in out.get("points", []) if _score(p) > 0]
    if not points:
        return "I don't know - no community report was relevant to the question."
    points.sort(key=_score, reverse=True)            # REDUCE: best points first
    findings = "\n".join(f"(importance {p['score']}) {p['description']}" for p in points[:40])
    return llm.chat([{"role": "system", "content": REDUCE_SYSTEM_PROMPT.format(
        response_type=response_type, findings=findings)}, {"role": "user", "content": query}])


def local_context(db, query: str, k: int = 5, top_chunks: int = 3, top_communities: int = 3,
                  top_inside_rels: int = 10) -> dict:
    return kdb.aql(db, LOCAL_SEARCH, question_embedding=llm.embed([query])[0], k=k,
                   top_chunks=top_chunks, top_communities=top_communities,
                   top_inside_rels=top_inside_rels)[0]


def format_tables(ctx: dict) -> str:
    def table(name, rows, cols):
        lines = [f"-----{name}-----", "|".join(cols)]
        lines += ["|".join(str(r.get(c, "")).replace("\n", " ") for c in cols) for r in rows]
        return "\n".join(lines)

    return "\n\n".join([
        table("Entities", ctx["entities"], ["id", "entity", "type", "description"]),
        table("Relationships", ctx["relationships"], ["id", "source", "target", "description"]),
        table("Reports", ctx["reports"], ["id", "title", "summary"]),
        table("Sources", ctx["sources"], ["id", "text"]),
    ])


def local_search(db, query: str, response_type: str = "multiple paragraphs") -> str:
    context = format_tables(local_context(db, query))
    return llm.chat([{"role": "system", "content": LOCAL_SYSTEM_PROMPT.format(
        response_type=response_type, context=context)}, {"role": "user", "content": query}])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["index", "global", "local", "inspect"])
    ap.add_argument("query", nargs="?", default="What is this story about?")
    ap.add_argument("--books", type=int, default=1)
    ap.add_argument("--gleanings", type=int, default=0)
    args = ap.parse_args()
    db = kdb.connect(DB_NAME, fresh=(args.mode == "index"))
    if args.mode == "index":
        index(db, args.books, gleanings=args.gleanings)
    elif args.mode == "inspect":
        print(kdb.aql(db, COUNTS))
        print(kdb.aql(db, ENTITY_DESCRIPTIONS, name="ORESTES"))
        print(json.dumps(kdb.aql(db, BUSIEST_PAIR), indent=2))
        print(kdb.aql(db, LARGEST_COMMUNITY))
    elif args.mode == "global":
        print(global_search(db, args.query))
    else:
        print(local_search(db, args.query))


if __name__ == "__main__":
    main()
