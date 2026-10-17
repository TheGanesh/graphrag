# Appendix A · The ArangoDB environment

> *Replaces the book's appendix, "The Neo4j environment."*

The book's appendix introduces Neo4j (a native graph database queried with Cypher over Bolt or HTTP), its two plugins (**APOC** for utilities and **GDS** for graph algorithms), three ways to run it (Desktop, Docker, the Aura cloud) and the classic **Movies** dataset. Here is the ArangoDB equivalent of each.

---

## What ArangoDB is

ArangoDB is a **multi-model** database: one engine and one query language (**AQL**) for

* **documents**: JSON documents in *document collections*,
* **graphs**: *edge collections* whose documents carry `_from` and `_to`, plus optional *named graphs* that describe which collections connect,
* **search**: *ArangoSearch views* with analyzers and BM25/TF-IDF ranking,
* **vectors**: *vector indexes* (FAISS-based IVF) queried with `APPROX_NEAR_COSINE`, `APPROX_NEAR_L2` and `APPROX_NEAR_INNER_PRODUCT` (v3.12.4+).

Clients talk to it over HTTP. In Python you use **python-arango** (8.x in this guide).

| Neo4j | ArangoDB |
|---|---|
| Cypher | AQL |
| APOC (utilities, `apoc.meta.data`) | built-in AQL functions; schema by sampling (chapter 4) |
| GDS (Louvain, PageRank, …) | AQL traversals and path search in the database. Community detection in NetworkX / `nx-arangodb` (Pregel was removed in 3.12) |
| Neo4j Browser | ArangoDB web UI (http://localhost:8529): queries, graph viewer, collections, indexes, views |
| Desktop / Docker / Aura | Docker / packages / Arango's managed cloud platform |

## Run it with Docker

`code/docker-compose.yml`:

```yaml
services:
  arangodb:
    image: arangodb:3.12.12
    environment:
      ARANGO_ROOT_PASSWORD: openSesame
    command: ["--vector-index"]
    ports:
      - "8529:8529"
    volumes:
      - arangodb_data:/var/lib/arangodb3
      - arangodb_apps:/var/lib/arangodb3-apps
volumes:
  arangodb_data:
  arangodb_apps:
```

```bash
cd code && docker compose up -d
# web UI: http://localhost:8529   user: root   password: openSesame
```

* Arguments after the image name go straight to `arangod`, which is how `--vector-index` is passed. **Vector indexes don't work without it**, and once a deployment has been started with it, it can't be switched off.
* `ARANGO_ROOT_PASSWORD` sets the root password. (`ARANGO_NO_AUTH=1` disables authentication. Only use that for throwaway tests.)
* Mount the data volume so your databases survive container restarts, as the book recommends for Neo4j.

> [!TIP]
> 😌 **Relax: no plugins to install.** Everything the book needed APOC and GDS for is covered by built-in AQL functions, plus a few lines of NetworkX for community detection.

## Python setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r code/requirements.txt
cp code/.env.example code/.env      # then edit it
```

`.env` holds the ArangoDB connection, your OpenAI-compatible endpoint (`OPENAI_API_KEY`, optional `OPENAI_BASE_URL`), and model names (`LLM_MODEL`, `EMBEDDING_MODEL`, `EMBEDDING_DIM`). Set `EMBEDDINGS=hash` to run the plumbing offline with fake but deterministic vectors.

```python
from kit import db as kdb
db = kdb.connect("movies")                       # creates the database if needed
rows = kdb.aql(db, "FOR m IN movies LIMIT 3 RETURN m.title")
```

## The Movies dataset

The book loads Neo4j's Movies example graph with a long Cypher script (or `:play movies` in Neo4j Browser). `code/load_movies.py` **downloads that public script and parses it**, then loads it into ArangoDB:

```bash
python code/load_movies.py
# {'persons': 133, 'movies': 38, 'acted_in': 172, 'directed': 44, 'produced': 15,
#  'wrote': 10, 'follows': 3, 'reviewed': 9}
```

The mapping:

| Cypher | ArangoDB |
|---|---|
| `(:Person {name, born})` | `persons` document, `_key` derived from the name (`Tom_Hanks`) |
| `(:Movie {title, released, tagline})` | `movies` document, `_key` derived from the title (`Cast_Away`) |
| `[:ACTED_IN {roles}]` | `acted_in` edge with `roles` |
| `[:DIRECTED]`, `[:PRODUCED]`, `[:WROTE]` | `directed`, `produced`, `wrote` edges |
| `[:REVIEWED {summary, rating}]` | `reviewed` edge with `summary`, `rating` |
| `[:FOLLOWS]` | `follows` edge (persons → persons) |
| constraints on `Movie.title`, `Person.name` | unique persistent indexes on `movies.title`, `persons.name` |

…plus a named graph `movies` so the web UI's graph viewer can draw it.

## Users and permissions

Generated queries (chapter 4) should run as a **read-only** user:

```python
sys_db.create_user("aql_reader", "readonly-demo")
sys_db.update_permission("aql_reader", "ro", "movies")                  # database level
sys_db.update_permission("aql_reader", "ro", "movies", collection="*")  # all its collections
```

## Check everything works

```bash
python code/selftest.py
```

`selftest.py` runs (almost) every AQL query in this guide against throwaway `selftest_*` databases, with offline embeddings and no LLM calls. It checks real answers (Tom Hanks acted in 12 movies, the read-only user can't write, the `null < 1940` trap returns 15 rows, …) and prints a pass/fail list.

## Licensing in one paragraph

From v3.12.5, the ArangoDB **Community Edition** includes the features that used to be Enterprise-only. It's licensed under the ArangoDB Community License: free to use, a **100 GiB dataset limit**, and **no commercial use in production**. The source code, except for the formerly Enterprise-only features, is available under the Business Source License 1.1 (BUSL-1.1). The **Enterprise Edition** (commercial license) removes those limits. Read the current terms before you ship.

---
[← Chapter 9](09-the-big-picture.md) · [Contents](../README.md) · [Appendix B →](appendix-b-cypher-to-aql.md)
