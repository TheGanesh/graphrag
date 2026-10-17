"""Run (almost) every AQL query in this guide against a live ArangoDB.

    docker compose up -d
    python selftest.py

No API key needed: embeddings use the offline hashing trick (EMBEDDINGS=hash)
and the LLM steps are replaced by fixed fixture outputs. Needs internet once to
download the Movies script. Uses throw-away databases named selftest_*.
"""
from __future__ import annotations

import datetime
import os
import traceback

os.environ["EMBEDDINGS"] = "hash"           # must be set before kit.llm is imported

import ch02_vector_hybrid as ch02            # noqa: E402
import ch03_advanced_vector as ch03          # noqa: E402
import ch04_text2aql as ch04                 # noqa: E402
import ch05_agentic_rag as ch05              # noqa: E402
import ch06_contract_kg as ch06              # noqa: E402
import ch07_ms_graphrag as ch07              # noqa: E402
import ch08_evaluation as ch08               # noqa: E402
import load_movies                           # noqa: E402
from kit import db as kdb                    # noqa: E402
from kit import llm                          # noqa: E402

RESULTS: list[tuple[str, bool, str]] = []


def check(name: str, condition: bool, detail: object = "") -> None:
    RESULTS.append((name, bool(condition), "" if condition else str(detail)[:300]))
    print(("PASS " if condition else "FAIL ") + name + ("" if condition else f"  -> {detail}"))


def sync_view(db, view: str) -> None:
    """ArangoSearch views refresh asynchronously (about once a second); wait for it."""
    kdb.aql(db, "FOR d IN @@view SEARCH true OPTIONS { waitForSync: true } LIMIT 1 RETURN 1",
            **{"@view": view})


EINSTEIN_NOTES = """Einstein's patents and inventions - study notes.

As a student at ETH Zurich, Einstein spent most of his time in the physics laboratory,
fascinated by direct contact with observation. Later he worked as a technical expert at
the Swiss patent office in Bern, where he examined patent applications for inventions.

1. Introduction
Einstein was a theoretical physicist, yet he also worked on practical inventions as a
diversion. His father's company built electrical equipment, so he grew up among machines.

2. The refrigerator
Together with Leo Szilard, Einstein designed an absorption refrigerator without moving
parts. The refrigerator patent was granted in 1930 and used ammonia, butane and water.

3. Sound reproduction
With Rudolf Goldschmidt, Einstein worked on a sound reproduction device that could help
people with hearing loss. The device used a magnetostrictive element.

4. The automatic camera
With Gustav Bucky, Einstein patented a camera that adjusts the exposure automatically
to the light intensity, using a photoelectric cell to move a shutter.

5. Clothing
Einstein was also named on a design patent for a blouse, granted in 1936, which shows
how varied his interests were.
"""


# ---------------------------------------------------------------- chapter 2
def test_ch02() -> None:
    db = kdb.connect("selftest_ch02", fresh=True)
    n = ch02.setup(db, EINSTEIN_NOTES)
    check("ch02 chunks stored", n > 3, n)
    hits = ch02.vector_search(db, "Szilard refrigerator patent", k=2)
    check("ch02 vector search returns k rows", len(hits) == 2, hits)
    check("ch02 vector search finds the refrigerator", "refrigerator" in hits[0]["text"].lower(), hits[:1])
    sync_view(db, "chunks_view")
    kw = kdb.aql(db, ch02.KEYWORD_SEARCH, question="laboratory observation", k=3)
    check("ch02 BM25 keyword search", kw and "laboratory" in kw[0]["text"].lower(), kw[:1])
    hy = ch02.hybrid_search(db, "Where did Einstein work in the laboratory?", k=3)
    check("ch02 hybrid search top score is 1.0", hy and abs(hy[0]["score"] - 1.0) < 1e-9, hy[:1])
    check("ch02 hybrid search de-duplicates", len({h["index"] for h in hy}) == len(hy), hy)
    rrf = kdb.aql(db, ch02.HYBRID_SEARCH_RRF, question="camera light intensity",
                  question_embedding=llm.embed(["camera light intensity"])[0], k=3)
    check("ch02 RRF hybrid search", rrf and "camera" in rrf[0]["text"].lower(), rrf[:1])
    db2 = kdb.connect("selftest_ch02_upsert", fresh=True)
    kdb.ensure_collection(db2, "chunks")
    texts = ["alpha", "beta"]
    kdb.aql(db2, ch02.STORE_CHUNKS_UPSERT, texts=texts, embeddings=llm.embed(texts))
    kdb.aql(db2, ch02.STORE_CHUNKS_UPSERT, texts=texts, embeddings=llm.embed(texts))
    check("ch02 UPSERT import is idempotent", db2.collection("chunks").count() == 2,
          db2.collection("chunks").count())


# ---------------------------------------------------------------- chapter 3
def test_ch03() -> None:
    db = kdb.connect("selftest_ch03", fresh=True)
    sections = ch03.split_into_sections(EINSTEIN_NOTES)
    check("ch03 section split", len(sections) == 6, [s[:30] for s in sections])
    n_parents, n_children = ch03.build_graph(db, EINSTEIN_NOTES)
    check("ch03 parents and children imported", n_parents >= 6 and n_children >= n_parents,
          (n_parents, n_children))
    check("ch03 has_child edges", db.collection("has_child").count() == n_children,
          db.collection("has_child").count())
    kdb.aql(db, ch03.IMPORT_PARENT, pdf_id=ch03.PDF_ID, title=ch03.PDF_TITLE, parent_key=f"{ch03.PDF_ID}-0",
            parent_text="dup", children=["dup"], embeddings=llm.embed(["dup"]))
    check("ch03 re-import does not duplicate pdfs", db.collection("pdfs").count() == 1,
          db.collection("pdfs").count())
    docs = ch03.parent_retrieval(db, "refrigerator designed with Leo Szilard", k=2)
    check("ch03 parent retrieval returns whole parents", docs and "Szilard" in docs[0], docs[:1])
    rows = kdb.aql(db, ch03.PARENT_RETRIEVAL, question_embedding=llm.embed(["patent"])[0],
                   candidates=12, k=3)
    check("ch03 parents are de-duplicated", len({r["key"] for r in rows}) == len(rows), rows)
    kdb.ensure_graph(db, "einstein_questions", [
        {"edge_collection": "has_question", "from_vertex_collections": ["parents"],
         "to_vertex_collections": ["questions"]}])
    parent_key = kdb.aql(db, "FOR p IN parents FILTER CONTAINS(p.text, 'Bucky') RETURN p._key")[0]
    qs = ["Who invented an automatic camera with Einstein?", "How did the camera adjust exposure?"]
    kdb.aql(db, ch03.IMPORT_QUESTIONS, parent_key=parent_key, questions=qs, embeddings=llm.embed(qs))
    kdb.ensure_vector_index(db.collection("questions"), "embedding", dimension=llm.EMBEDDING_DIM)
    hq = kdb.aql(db, ch03.HYPOTHETICAL_QUESTION_RETRIEVAL,
                 question_embedding=llm.embed(["camera exposure"])[0], candidates=2, k=1)
    check("ch03 hypothetical-question retrieval", hq and hq[0]["key"] == parent_key, hq)


# ---------------------------------------------------------------- chapter 4/5/8 (movies)
def test_movies() -> None:
    db = kdb.connect("selftest_movies", fresh=True)
    counts = load_movies.load(db)
    check("movies loaded", counts.get("movies") == 38 and counts.get("persons") == 133, counts)
    schema = ch04.format_schema(ch04.get_structured_schema(db))
    check("ch04 schema lists edge patterns", "acted_in: persons -> movies" in schema, schema[:400])
    check("ch04 schema lists attributes", "born: number" in schema and "roles: array" in schema, schema[:400])
    ex1 = kdb.aql(db, ch04.EXAMPLES[0][1])
    check("ch04 few-shot example 1 runs", len(ex1) == 1 and ex1[0]["movie_count"] >= 3, ex1)
    ex2 = kdb.aql(db, ch04.EXAMPLES[1][1])
    check("ch04 few-shot example 2 runs", ex2 and abs(ex2[0]["avg_rating"] - 66.5) < 1e-6, ex2)
    ro = ch04.reader_db(db)
    try:
        ro.aql.execute('INSERT { name: "intruder" } INTO persons')
        check("ch04 read-only user cannot write", False, "insert succeeded")
    except Exception:
        check("ch04 read-only user cannot write", True)
    check("ch04 read-only user can read",
          list(ro.aql.execute("RETURN COLLECTION_COUNT('movies')")) == [38])
    naive = kdb.aql(db, "FOR p IN persons FILTER p.born < 1940 RETURN p.name")
    safe = kdb.aql(db, "FOR p IN persons FILTER p.born != null AND p.born < 1940 RETURN p.name")
    check("watch-out: null < 1940 is true in AQL", len(naive) == 15 and len(safe) == 10,
          (len(naive), len(safe)))

    ch05.db = db
    info = ch05.movie_info_by_title("matrix")
    check("ch05 movie_info_by_title", len(info) == 3 and any("Keanu Reeves" in m["cast"] for m in info), info[:1])
    hanks = ch05.movies_info_by_actor("tom hanks")
    check("ch05 movies_info_by_actor", len(hanks) == 12, len(hanks))
    check("ch05 tool schemas", all(t["description"]["type"] == "function" for t in ch05.TOOLS.values()))

    expected = {
        "How many movies are there?": [{"movies": 38}],
        "Who acted in the most movies?": [{"name": "Tom Hanks", "movie_count": 12}],
        "Who has the longest name among all actors?": ["Philip Seymour Hoffman"],
        "Who was born in 1965 and has directed a movie?": {"Lana Wachowski", "Tom Tykwer"},
        "How many movies did Tom Hanks appear in?": [{"movies": 12}],
        "Who directed the most movies?": [{"name": "Lana Wachowski", "movie_count": 5},
                                          {"name": "Lilly Wachowski", "movie_count": 5}],
    }
    for row in ch08.load_benchmark():
        got = kdb.aql(db, row["aql"])
        want = expected.get(row["question"])
        if want is None:
            check(f"ch08 ground truth runs: {row['question']}", got is not None)
        elif isinstance(want, set):
            check(f"ch08 ground truth: {row['question']}", set(got) == want, got)
        else:
            check(f"ch08 ground truth: {row['question']}", got == want, got)


# ---------------------------------------------------------------- chapter 6
CONTRACT_A = {
    "contract_type": "Licensing Agreement", "effective_date": "2025-03-01", "end_date": "2027-02-28",
    "term": "2 years, auto-renews yearly", "contract_scope": "License to use GraphLens",
    "total_amount": 120000.0, "governing_law": {"address": None, "city": None, "state": "Texas", "country": "US"},
    "parties": [
        {"name": "Northwind Analytics, Inc.", "role": "licensor",
         "location": {"address": "500 Congress Avenue", "city": "Austin", "state": "Texas", "country": "US"}},
        {"name": "Acme Data Ltd.", "role": "licensee",
         "location": {"address": "12 Wellington Street", "city": "Leeds", "state": None, "country": "GB"}}]}
CONTRACT_B = {
    "contract_type": "Service Agreement", "effective_date": "2020-01-01", "end_date": "2021-01-01",
    "term": "1 year", "contract_scope": "Data cleaning services", "total_amount": None, "governing_law": None,
    "parties": [
        {"name": "ACME Data Limited", "role": "client",
         "location": {"address": None, "city": "Leeds", "state": None, "country": "GB"}},
        {"name": "Contoso Cleaning LLC", "role": "provider",
         "location": {"address": None, "city": "Seattle", "state": "Washington", "country": "US"}}]}


def test_ch06() -> None:
    db = kdb.connect("selftest_ch06", fresh=True)
    ch06.setup(db)
    doc_a = open(os.path.join(ch06.HERE, "data", "sample_contract.txt"), encoding="utf-8").read()
    rows = ch06.import_contract(db, CONTRACT_A, doc_a)
    check("ch06 import returns one row per party", len(rows) == 2, rows)
    ch06.import_contract(db, CONTRACT_A, doc_a)
    check("ch06 import is idempotent", db.collection("contracts").count() == 1
          and db.collection("has_party").count() == 2, db.collection("contracts").count())
    ch06.import_contract(db, CONTRACT_B, "contract b text")
    check("ch06 two contracts", db.collection("contracts").count() == 2)
    loc = kdb.aql(db, "FOR l IN locations FILTER l.city == 'Leeds' AND l.address == null RETURN l.full_address")
    check("ch06 null address skipped in full_address", loc == ["Leeds, GB"], loc)
    n = ch06.add_chunks(db, doc_a)
    check("ch06 clause chunks", n >= 7, n)
    today = datetime.date(2026, 1, 1).isoformat()
    active = kdb.aql(db, ch06.ACTIVE_CONTRACTS_WITH, party="acme", today=today)
    check("ch06 active contracts (filter + count)", active == [1], active)
    hits = kdb.aql(db, ch06.CONTRACT_SCOPED_SEARCH, party="Northwind",
                   question_embedding=llm.embed(["payment terms invoices"])[0], k=2)
    check("ch06 graph-scoped vector search", hits and "invoice" in hits[0]["text"].lower(), hits[:1])
    dupes = kdb.aql(db, ch06.DUPLICATE_CANDIDATES, noise=ch06.LEGAL_NOISE)
    check("ch06 duplicate candidates", len(dupes) == 1 and dupes[0]["canonical"] == "acme data", dupes)
    fuzzy = kdb.aql(db, ch06.FUZZY_CANDIDATES, max_distance=6)
    check("ch06 fuzzy candidates", any("Acme" in f["a"] + f["b"] for f in fuzzy), fuzzy)
    keys = sorted(o["key"] for o in dupes[0]["organizations"])
    ch06.merge_organizations(db, keys[0], keys[1:])
    parties = kdb.aql(db, "FOR e IN has_party FILTER e._from == CONCAT('organizations/', @k) RETURN e._to", k=keys[0])
    check("ch06 merge re-points edges", len(parties) == 2 and db.collection("organizations").count() == 3,
          parties)


# ---------------------------------------------------------------- chapter 7
EXTRACTIONS = [
    ('("entity"<|>TELEMACHUS<|>PERSON<|>Son of Ulysses who receives a disguised visitor.)##'
     '("entity"<|>MINERVA<|>GOD<|>Goddess who visits Ithaca disguised as Mentes.)##'
     '("entity"<|>ITHACA<|>LOCATION<|>Island home of Ulysses.)##'
     '("relationship"<|>MINERVA<|>TELEMACHUS<|>Minerva advises Telemachus.<|>9)##'
     '("relationship"<|>MINERVA<|>ITHACA<|>Minerva travels to Ithaca.<|>5)<|COMPLETE|>'),
    ('("entity"<|>TELEMACHUS<|>PERSON<|>Telemachus calls an assembly of the Ithacans.)##'
     '("entity"<|>MINERVA<|>GOD<|>Minerva helps Telemachus find a ship.)##'
     '("entity"<|>ORESTES<|>PERSON<|>Son of Agamemnon who killed Aegisthus.)##'
     '("entity"<|>AEGISTHUS<|>PERSON<|>Murderer of Agamemnon.)##'
     '("relationship"<|>MINERVA<|>TELEMACHUS<|>Minerva finds Telemachus a ship.<|>8)##'
     '("relationship"<|>ORESTES<|>AEGISTHUS<|>Orestes killed Aegisthus.<|>10)<|COMPLETE|>'),
    ('("entity"<|>ORESTES<|>PERSON<|>Orestes is praised for avenging his father.)##'
     '("entity"<|>AEGISTHUS<|>PERSON<|>Aegisthus was warned by Mercury.)##'
     '("entity"<|>MERCURY<|>GOD<|>Messenger god who warned Aegisthus.)##'
     '("relationship"<|>MERCURY<|>AEGISTHUS<|>Mercury warned Aegisthus.<|>6)##'
     '("relationship"<|>ORESTES<|>AEGISTHUS<|>Orestes avenged his father on Aegisthus.<|>9)<|COMPLETE|>'),
]


def test_ch07() -> None:
    db = kdb.connect("selftest_ch07", fresh=True)
    ch07.setup(db)
    for i, out in enumerate(EXTRACTIONS):
        nodes, rels = ch07.parse_extraction(out)
        ch07.import_chunk(db, 0, i, f"chunk {i}: " + out[:80], nodes, rels)
    ch07.import_chunk(db, 0, 0, "chunk 0 again", *ch07.parse_extraction(EXTRACTIONS[0]))
    counts = kdb.aql(db, ch07.COUNTS)[0]
    check("ch07 extraction import", counts["entities"] == 6 and counts["relationships"] == 6, counts)
    desc = kdb.aql(db, ch07.ENTITY_DESCRIPTIONS, name="ORESTES")
    check("ch07 descriptions accumulate per entity", desc and len(desc[0]) == 2, desc)
    pair = kdb.aql(db, ch07.BUSIEST_PAIR)
    check("ch07 busiest pair", pair and pair[0]["count"] == 2, pair)

    ch07.summarize_descriptions = lambda name, descs: " ".join(descs)    # no LLM in the self-test
    ch07.summarize_entities_and_relationships(db)
    check("ch07 every entity has a summary",
          kdb.aql(db, "FOR e IN entities FILTER e.summary == null RETURN 1") == [])
    check("ch07 one summarized edge per pair", db.collection("summarized").count() == 4,
          db.collection("summarized").count())
    sizes = ch07.detect_communities(db)
    check("ch07 communities detected", sizes and sum(sizes) <= 6, sizes)

    def fake_report(messages):
        return {"title": "Fixture community", "summary": "A test community.", "rating": 7,
                "rating_explanation": "test", "findings": [{"summary": "s", "explanation": "e"}]}
    real = ch07.llm.chat_json
    ch07.llm.chat_json = fake_report
    try:
        n = ch07.write_community_reports(db)
    finally:
        ch07.llm.chat_json = real
    check("ch07 community reports saved", n == len(sizes), n)
    info = kdb.aql(db, ch07.COMMUNITY_INFO)
    check("ch07 community info has members", all(i["entities"] for i in info), info[:1])
    check("ch07 largest community", kdb.aql(db, ch07.LARGEST_COMMUNITY)[0]["size"] == max(sizes))
    check("ch07 community weights", kdb.aql(db, "FOR c IN communities FILTER c.weight > 0 RETURN 1"))
    glob = kdb.aql(db, ch07.GLOBAL_COMMUNITIES, min_rating=5)
    check("ch07 global search candidates", len(glob) == n, glob[:1])
    ch07.embed_entities(db)
    ctx = ch07.local_context(db, "Who is Telemachus and who helps him?", k=3)
    check("ch07 local search: entities", len(ctx["entities"]) == 3, ctx["entities"])
    check("ch07 local search: sources and reports", ctx["sources"] and ctx["reports"], ctx)
    check("ch07 context tables format", "-----Entities-----" in ch07.format_tables(ctx))


def main() -> None:
    for test in (test_ch02, test_ch03, test_movies, test_ch06, test_ch07):
        try:
            test()
        except Exception as exc:  # report and continue with the next chapter
            traceback.print_exc()
            check(f"{test.__name__} raised", False, repr(exc))
    failed = [r for r in RESULTS if not r[1]]
    print(f"\n{len(RESULTS) - len(failed)}/{len(RESULTS)} checks passed")
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()
