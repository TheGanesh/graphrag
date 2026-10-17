"""ArangoDB helpers (python-arango 8.x).

Everything here is idempotent: run a chapter script twice and you get the
same collections, indexes and views, not duplicates.
"""
from __future__ import annotations

import math
import os
from typing import Any

from arango import ArangoClient
from arango.database import StandardDatabase

ARANGO_URL = os.getenv("ARANGO_URL", "http://localhost:8529")
ARANGO_DB = os.getenv("ARANGO_DB", "graphrag")
ARANGO_USER = os.getenv("ARANGO_USER", "root")
ARANGO_PASSWORD = os.getenv("ARANGO_PASSWORD", "openSesame")


def connect(db_name: str | None = None, fresh: bool = False) -> StandardDatabase:
    """Return a handle to `db_name` (default $ARANGO_DB), creating it if needed.

    Every chapter uses its own database (ch02, ch03, ...) so the demos never
    step on each other; fresh=True drops and recreates it first.
    """
    name = db_name or ARANGO_DB
    client = ArangoClient(hosts=ARANGO_URL)
    sys_db = client.db("_system", username=ARANGO_USER, password=ARANGO_PASSWORD)
    if fresh and sys_db.has_database(name):
        sys_db.delete_database(name)
    if not sys_db.has_database(name):
        sys_db.create_database(name)
    return client.db(name, username=ARANGO_USER, password=ARANGO_PASSWORD)


def aql(db: StandardDatabase, query: str, **bind_vars: Any) -> list:
    """Run an AQL query and return all results as a list."""
    return list(db.aql.execute(query, bind_vars=bind_vars))


def ensure_collection(db: StandardDatabase, name: str, edge: bool = False):
    if db.has_collection(name):
        return db.collection(name)
    return db.create_collection(name, edge=edge)


def ensure_graph(db: StandardDatabase, name: str, edge_definitions: list[dict]) -> None:
    """Create a named graph, e.g.
    ensure_graph(db, "movies", [{"edge_collection": "acted_in",
        "from_vertex_collections": ["persons"], "to_vertex_collections": ["movies"]}])
    """
    for ed in edge_definitions:
        ensure_collection(db, ed["edge_collection"], edge=True)
        for c in ed["from_vertex_collections"] + ed["to_vertex_collections"]:
            ensure_collection(db, c)
    if not db.has_graph(name):
        db.create_graph(name, edge_definitions=edge_definitions)


def ensure_persistent_index(col, fields: list[str], unique: bool = False, sparse: bool = False):
    return col.add_index({"type": "persistent", "fields": fields, "unique": unique, "sparse": sparse})


def ensure_vector_index(col, field: str = "embedding", dimension: int = 1536,
                        metric: str = "cosine", n_lists: int | None = None,
                        default_n_probe: int | None = None, stored_values: list[str] | None = None,
                        sparse: bool = False):
    """Create a vector (IVF) index on `field`.

    Needs: the server started with --vector-index (see docker-compose.yml).
    Up to ArangoDB 3.12.8 the collection must already contain the vectors,
    because the index *trains* its centroids on existing data; from 3.12.9 the
    index can be created first and trains once enough documents exist.
    nLists may not exceed the number of documents.
    """
    n_docs = col.count()
    if n_lists is None:
        # roughly sqrt(N) Voronoi cells, at least 1, never more than the doc count
        n_lists = max(1, min(n_docs, int(round(math.sqrt(max(n_docs, 1))))))
    if default_n_probe is None:
        # tiny demo collections: probe a good share of the cells so recall stays high
        default_n_probe = max(1, min(n_lists, 8))
    definition: dict[str, Any] = {
        "name": f"vec_{field}",
        "type": "vector",
        "fields": [field],
        "params": {
            "metric": metric,
            "dimension": dimension,
            "nLists": n_lists,
            "defaultNProbe": default_n_probe,
        },
    }
    if stored_values:
        definition["storedValues"] = stored_values  # attributes you can FILTER on inside the index
    if sparse:
        definition["sparse"] = True  # skip documents that have no vector (yet)
    return col.add_index(definition)


def ensure_search_view(db: StandardDatabase, view: str, links: dict[str, dict[str, list[str]]]):
    """Create an ArangoSearch view.

    links = {"chunks": {"text": ["text_en"]}} indexes chunks.text with the
    built-in English analyzer (tokenize, lowercase, stem).
    """
    if any(v["name"] == view for v in db.views()):
        return
    db.create_arangosearch_view(view, properties={
        "links": {
            col: {"fields": {field: {"analyzers": analyzers} for field, analyzers in fields.items()}}
            for col, fields in links.items()
        }
    })
