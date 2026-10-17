# Appendix C · Translation notes and errata

> *New in this guide. Every place where moving from Neo4j/Cypher to ArangoDB/AQL took a decision, plus small issues we noticed in the book while translating.*

## Translation decisions

| Topic | Book (Neo4j) | This guide (ArangoDB) | Why |
|---|---|---|---|
| Data model | labels, relationship types | document collections per label, edge collections per relationship type | Mirrors Cypher's types one-to-one, so traversals read like the book's patterns. |
| Multi-labels | `:__Entity__:PERSON` | one `entities` collection with a `type` attribute | ArangoDB documents live in exactly one collection. A type attribute is simpler than one collection per entity type. |
| Uniqueness | `CREATE CONSTRAINT … IS UNIQUE` | `_key` or a unique persistent index | Native equivalents. |
| Upserts | `MERGE` | `UPSERT`, or `INSERT … OPTIONS { overwriteMode }` with a chosen `_key` | Choosing keys makes imports idempotent and needs no lookup index. |
| IDs | `randomUUID()` for contracts | hash of the document text | Re-importing a contract updates it instead of duplicating it. |
| Vector search | `CREATE VECTOR INDEX`, `db.index.vector.queryNodes` | `type: "vector"` index (IVF), `SORT APPROX_NEAR_COSINE(...) DESC LIMIT k` | Requires `--vector-index`. Created after loading data (mandatory up to 3.12.8). |
| Full-text | full-text index | ArangoSearch view + `text_en` analyzer + `BM25()` | The legacy full-text index type has been deprecated since 3.10. |
| Hybrid fusion | max-normalization in Cypher `UNION` | same math in AQL with `UNION()` + `COLLECT … AGGREGATE MAX`; RRF variant added | Faithful translation, plus a more robust alternative. |
| Schema for text2aql | `apoc.meta.data()` | sampling queries with `ATTRIBUTES`, `TYPENAME`, `PARSE_IDENTIFIER` | No APOC in ArangoDB. Sampling is cheap and good enough. |
| Prompt | Cypher-specific | adds a two-line "AQL reminders" block | Models have seen less AQL than Cypher. |
| Safety | (not covered) | read-only user, EXPLAIN, runtime/memory limits, retry with error feedback | Generated queries need guard rails before users see them. |
| Community detection | GDS Louvain (Leiden in the paper) | NetworkX Louvain on edges exported with AQL | ArangoDB 3.12 removed Pregel. NetworkX is simple and deterministic with a seed. |
| Relationship ranking | `rank`/`weight` properties | `rank` = degree(source) + degree(target), `weight` = sum of strengths | Follows Microsoft GraphRAG's heuristics. |
| Local search report ranking | community rank, weight | matched-entity count, then rating, then weight | MS GraphRAG's heuristic. Same spirit as the book. |
| Global search | one MAP call per community | reports packed into ~6k-token batches | Fewer LLM calls, as in Microsoft's implementation. |
| Extraction gleaning | described (paper figure) | implemented (`--gleanings N`) | Lets you reproduce the "more passes → more entities" effect. |
| Evaluation | RAGAS | built-in LLM judge (same three metrics) + optional RAGAS 0.4 | RAGAS' API and dependencies change often. The built-in judge is transparent. |
| Models | `gpt-4o`, `gpt-4` | configurable (`LLM_MODEL`, default `gpt-5.4-mini`), any OpenAI-compatible endpoint | The book's models were retired or deprecated by late 2026. Temperature is optional because some reasoning models reject it. |
| MCP | (not in the book) | `ch05_mcp_server.py` with MCP Python SDK v2 (`MCPServer`) | Ties chapter 5 to the "agent + tools" world. SDK v2 renamed `FastMCP` to `MCPServer`. |
| Data | Neo4j Movies script, arXiv PDF, Gutenberg text, a CUAD contract | same public sources, downloaded at run time. Contract example is a fictional sample. | The guide doesn't redistribute third-party data. |

## Errata spotted in the book

These are small issues that don't affect the ideas. They're listed so they don't trip you up if you also run the book's own code.

| Where | What | Fix used here |
|---|---|---|
| Ch. 1, §1.3.1 | The LLM training stages are attributed to "Andrew Karpathy" | Andrej Karpathy |
| Ch. 2, listings 2.12–2.13 | The full-text index is created as `PdfChunkFulltext` but queried as `ftPdfChunk` | One view name, `chunks_view`, everywhere |
| Ch. 3, listing 3.8 | Missing comma after `pdf_id='1709.00666'` in the `execute_query(...)` call | n/a (different code) |
| Ch. 3, listing 3.9 | Captioned "Create a vector index on child nodes" but shows a visualization query (the caption of listing 3.10) | n/a |
| Ch. 4, listing 4.1 | Averages `r.score`, but the schema's `REVIEWED` property is `rating` | `review.rating` |
| Ch. 4, few-shot example | `WHERE p1 <> p2` counts every co-actor pair twice | `FILTER p1._key < p2._key` |
| Ch. 5, listing 5.1 (`movies_info_by_actor`) | The `WHERE` comes after the `OPTIONAL MATCH`es and reuses the variable `a`, so the actor filter applies to the optional match instead of the actor | Filter the actor first, then traverse |
| Ch. 6, fig. 6.3 vs listing 6.13 | Figure says `HAS_LOCATION`, the import query creates `LOCATED_AT` | `located_at` |
| Ch. 6, listing 6.13 | `fullAddress` is built with `+`, which yields `null` when any part is missing (and `MERGE` on a null property fails) | `CONCAT_SEPARATOR`, which skips nulls |
| Ch. 7, §7.2.1 | Text says "1,000-word limit", but `chunk_text` counts characters | 1,000 characters, stated as such |
| Ch. 7, listing 7.12 | Passes `summaries` (entity summaries) instead of `rel_summaries` to the relationship import | Relationship summaries saved to `summarized` |
| Ch. 7, §7.3.2 | The printed "Who is Ulysses?" local-search response repeats the global-search response word for word | n/a: run `local` yourself to see a real one |
| Ch. 8, table 8.2 | Ground truths printed as `RETURN "MATCH …"` (a query inside a string) | Plain AQL ground truths |
| Ch. 8, companion CSV | Includes a question about `votes`, a property the Movies data doesn't have | Replaced with a year-range question; added a ties question |

## Verification used for this guide

ArangoDB couldn't be run in the environment where this guide was written, so the AQL was checked in three other ways. Run the fourth yourself.

1. **Syntax**: every AQL query in `code/` and every `aql` block in `book/` was parsed with a parser generated from **ArangoDB 3.12.12's own grammar** (`arangod/Aql/Parser/grammar.y`, with semantic actions stripped). Function names were checked against the 3.12.12 function registry. See `tools/aql-lint/`.
2. **Bind parameters and control flow**: every chapter script was dry-run end to end against a fake database that rejects missing *and* unused bind parameters. A fake LLM was used for that run.
3. **Semantics**: each feature was checked against the official ArangoDB 3.12 documentation (vector index parameters and versions, `FILTER` placement with vector search, `COLLECT` variants, `UPSERT` and `INSERT` options, `CONCAT_SEPARATOR` null handling, mutable `_from`/`_to`, view consistency, Pregel removal).
4. **Run it**: `python code/selftest.py` executes the queries against a real ArangoDB and checks known answers. If anything fails on your version, please open an issue in this repo.

---
[← Appendix B](appendix-b-cypher-to-aql.md) · [Contents](../README.md)
