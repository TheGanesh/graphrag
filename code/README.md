# Code for *GraphRAG, Illustrated*

Runnable Python + AQL for every chapter, on ArangoDB 3.12.

## Setup

```bash
docker compose up -d                       # ArangoDB 3.12.12 with --vector-index, UI on :8529
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env                       # OPENAI_API_KEY, LLM_MODEL, EMBEDDING_MODEL, ...
python selftest.py                         # runs the guide's AQL against ArangoDB, no API key needed
```

Any **OpenAI-compatible** endpoint works (OpenAI, Azure, Ollama, vLLM, LM Studio, gateways): set `OPENAI_BASE_URL`, `LLM_MODEL`, `EMBEDDING_MODEL` and `EMBEDDING_DIM`. With `EMBEDDINGS=hash` the scripts use deterministic offline vectors. That's useful for testing the plumbing, but not for real answers.

## Scripts

| Chapter | Command | Database |
|---|---|---|
| 2 · vector & hybrid search | `python ch02_vector_hybrid.py "At what time was Einstein really interested in experimental works?"` | `ch02` |
| 3 · step-back + parent documents | `python ch03_advanced_vector.py "When was Einstein granted the patent for his blouse design?"` | `ch03` |
| 4 · text2aql | `python load_movies.py` then `python ch04_text2aql.py "Who directed the most movies?"` | `movies` |
| 5 · agentic RAG | `python ch05_agentic_rag.py "Who directed The Matrix, and which other movies did they direct?"` | `movies` |
| 5 · bonus MCP server | `python ch05_mcp_server.py` (stdio) | `movies` |
| 6 · contract knowledge graph | `python ch06_contract_kg.py [path/to/contract.txt]` | `ch06` |
| 7 · Microsoft-style GraphRAG | `python ch07_ms_graphrag.py index --books 1` · `… global "What is this story about?"` · `… local "Who is Ulysses?"` · `… inspect` | `ch07` |
| 8 · evaluation | `python ch08_evaluation.py` → `results/benchmark_results.csv` | `movies` |

Each chapter uses its own database, so you can rerun chapters independently. Chapters 2 and 3 recreate theirs on every run, and chapter 7's `index` command recreates `ch07`.

## Layout

```text
kit/db.py      connect, collections, graphs, persistent/vector indexes, ArangoSearch views
kit/llm.py     chat, JSON chat, tool calling, structured outputs, embeddings (+ offline hash vectors)
kit/text.py    sliding-window chunking, token counting, safe _keys, content hashes
load_movies.py parses Neo4j's public Movies Cypher script into persons/movies + 6 edge collections
selftest.py    end-to-end checks of the guide's queries (offline embeddings, fixture LLM outputs)
data/          benchmark.csv (AQL ground truth), sample_contract.txt (fictional)
```

## Costs and data

* Chapter 7 makes **many LLM calls**: one extraction call per chunk (plus gleanings), one summary per entity or pair with several descriptions, and one report per community. Start with `--books 1`.
* Downloads at run time: the Einstein paper (arXiv 1709.00666), *The Odyssey* (Project Gutenberg #1727) and Neo4j's Movies script. For real contracts, try CUAD (CC BY 4.0).

## Using the MCP server

Point any MCP host at the stdio server, for example:

```json
{"mcpServers": {"movies-graph": {"command": "python", "args": ["/abs/path/to/code/ch05_mcp_server.py"]}}}
```

It exposes `movie_info_by_title`, `movies_info_by_actor` and `ask_movie_database` (read-only text2aql).
