# How to use this guide

![The road through this guide](../images/roadmap.svg)

This guide retells the **design and architecture** in *Essential GraphRAG* (Tomaž Bratanič & Oskar Hane, Manning 2025) chapter by chapter. Then it rebuilds every example on **ArangoDB**: Neo4j becomes ArangoDB and Cypher becomes **AQL**, the ArangoDB Query Language. It's a study companion, not a substitute. The book has more depth, more context and the authors' own voice, so read it.

## Who this is for

You know some Python and you've called an LLM API. You may never have touched a graph database. Every AQL query is explained the first time it appears, and [Appendix B](appendix-b-cypher-to-aql.md) is a Cypher ⇄ AQL phrasebook if you're arriving from Neo4j.

## Your brain on this guide

Your brain ignores the boring and keeps what surprises it, what it has to work at, and what it sees in pictures. So this guide:

* **Draws the mechanism.** Every diagram shows *where data flows*, not just boxes with names.
* **Talks to you** in a conversational voice, like a colleague at a whiteboard.
* **Makes you do things.** Each chapter has exercises with hidden solutions, and every query runs.
* **Repeats the important ideas in different shapes**: a picture, then code, then a Q&A, then an exercise.

### The recurring boxes

| Box | What it means |
|---|---|
| 🧠 **Brain Bender** | Stop and think before reading on. There's no wrong answer, only a lazy one. |
| ✏️ **Pencil Time** | A hands-on exercise. Solutions hide in a fold-out ▸ below it. |
| 🙋 **No Such Thing as a Dumb Question** | The questions people actually ask, answered. |
| ⚠️ **Watch Out!** | A trap that bites real projects. |
| 😌 **Relax** | Something you can safely skim now. |
| 🔄 **Translation Station** | How a Neo4j/Cypher idea from the book maps to ArangoDB/AQL. |
| 🎙️ **Tonight's Talk** | Two concepts argue it out, so you remember the trade-offs. |
| 📌 **Key Takeaways** | The chapter on one screen. |

## Running the code

Everything lives in [`code/`](../code). Quick start:

```bash
cd code
docker compose up -d                 # ArangoDB 3.12 with vector indexes enabled
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env                 # add your OpenAI-compatible API key
python selftest.py                   # runs (almost) every AQL query in the guide, no API key needed
```

Each chapter tells you which script to run. Every chapter gets its own database (`ch02`, `ch03`, …, `movies`), so you can rerun any chapter without breaking the others.

## How the chapters map to the book

| Guide chapter | Book chapter | You'll build on ArangoDB |
|---|---|---|
| [1 · Why LLMs need help](01-improving-llm-accuracy.md) | 1 Improving LLM accuracy | your mental model: RAG + knowledge graphs, and the ArangoDB data model |
| [2 · Vector & hybrid search](02-vector-and-hybrid-search.md) | 2 Vector similarity search and hybrid search | chunks, a vector index, `APPROX_NEAR_COSINE`, an ArangoSearch view with BM25, hybrid fusion |
| [3 · Smarter vector retrieval](03-advanced-vector-retrieval.md) | 3 Advanced vector retrieval strategies | step-back prompting, a parent/child document graph, hypothetical questions |
| [4 · text2aql](04-text2aql.md) | 4 Generating Cypher queries from natural language | schema sampling, a prompt that writes AQL, safe execution |
| [5 · Agentic RAG](05-agentic-rag.md) | 5 Agentic RAG | a tool router, AQL tools, an answer critic, plus an MCP server bonus |
| [6 · Building KGs with LLMs](06-building-knowledge-graphs.md) | 6 Constructing knowledge graphs with LLMs | Structured Outputs to UPSERT, entity resolution, graph-scoped search |
| [7 · Microsoft GraphRAG](07-microsoft-graphrag.md) | 7 Microsoft's GraphRAG implementation | entity graph, summaries, Louvain communities, global & local search |
| [8 · Evaluation](08-evaluation.md) | 8 RAG application evaluation | an AQL-grounded benchmark and three LLM-as-judge metrics |
| [9 · The big picture](09-the-big-picture.md) | *(new)* | a decision guide and a reference architecture |
| [Appendix A](appendix-a-arangodb-environment.md) | Appendix (Neo4j environment) | ArangoDB setup and the Movies dataset |
| [Appendix B](appendix-b-cypher-to-aql.md) | *(new)* | Cypher ⇄ AQL phrasebook |
| [Appendix C](appendix-c-translation-notes.md) | *(new)* | translation decisions and errata spotted in the book |

---
[Contents](../README.md) · [Chapter 1 →](01-improving-llm-accuracy.md)
