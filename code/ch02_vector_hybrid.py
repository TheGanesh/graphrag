"""Chapter 2 - vector similarity search and hybrid search, on ArangoDB.

    python ch02_vector_hybrid.py "At what time was Einstein really interested in experimental works?"

Data setup:  paper -> 500-char chunks -> embeddings -> `chunks` collection
             -> vector index (cosine) + ArangoSearch view (BM25)
Query time:  question -> embedding -> vector / hybrid search -> LLM answer
"""
from __future__ import annotations

import io
import sys

import requests

from kit import db as kdb
from kit import llm
from kit.text import chunk_text

DB_NAME = "ch02"
PAPER_URL = "https://arxiv.org/pdf/1709.00666"  # Chaudhuri, "Einstein's Patents and Inventions"

# --------------------------------------------------------------------------- AQL
# Book listing 2.4 used UNWIND + MERGE + SET. The direct AQL translation is
# UPSERT; the idiomatic (and index-free) version keys each chunk by its number.
STORE_CHUNKS = """
FOR i IN 0..LENGTH(@texts) - 1
  INSERT { _key: TO_STRING(i), index: i, text: @texts[i], embedding: @embeddings[i] }
  INTO chunks
  OPTIONS { overwriteMode: "replace" }
"""

STORE_CHUNKS_UPSERT = """
FOR i IN 0..LENGTH(@texts) - 1
  UPSERT { index: i }
  INSERT { index: i, text: @texts[i], embedding: @embeddings[i] }
  UPDATE { text: @texts[i], embedding: @embeddings[i] }
  IN chunks
"""

VECTOR_SEARCH = """
FOR c IN chunks
  LET score = APPROX_NEAR_COSINE(c.embedding, @question_embedding)
  SORT score DESC
  LIMIT @k
  RETURN { text: c.text, index: c.index, score }
"""

KEYWORD_SEARCH = """
FOR c IN chunks_view
  SEARCH ANALYZER(c.text IN TOKENS(@question, "text_en"), "text_en")
  LET score = BM25(c)
  SORT score DESC
  LIMIT @k
  RETURN { text: c.text, index: c.index, score }
"""

# Book listing 2.13: run both searches, divide each score by the best score of
# its own search (so both lists top out at 1.0), merge, keep each chunk once.
HYBRID_SEARCH = """
LET vector_hits = (
  FOR c IN chunks
    LET score = APPROX_NEAR_COSINE(c.embedding, @question_embedding)
    SORT score DESC
    LIMIT @k
    RETURN { doc: KEEP(c, "_key", "text", "index"), score }
)
LET keyword_hits = (
  FOR c IN chunks_view
    SEARCH ANALYZER(c.text IN TOKENS(@question, "text_en"), "text_en")
    LET score = BM25(c)
    SORT score DESC
    LIMIT @k
    RETURN { doc: KEEP(c, "_key", "text", "index"), score }
)
LET vector_max = MAX(vector_hits[*].score)
LET keyword_max = MAX(keyword_hits[*].score)
FOR hit IN UNION(
    (FOR h IN vector_hits RETURN { doc: h.doc, score: h.score / vector_max }),
    (FOR h IN keyword_hits RETURN { doc: h.doc, score: h.score / keyword_max })
  )
  COLLECT key = hit.doc._key, text = hit.doc.text, index = hit.doc.index
    AGGREGATE score = MAX(hit.score)
  SORT score DESC
  LIMIT @k
  RETURN { text, index, score }
"""

# Bonus (not in the book): Reciprocal Rank Fusion ignores raw score scales and
# only uses each chunk's rank in each list: score = sum(1 / (60 + rank)).
HYBRID_SEARCH_RRF = """
LET vector_hits = (
  FOR c IN chunks
    SORT APPROX_NEAR_COSINE(c.embedding, @question_embedding) DESC
    LIMIT @k
    RETURN c._key
)
LET keyword_hits = (
  FOR c IN chunks_view
    SEARCH ANALYZER(c.text IN TOKENS(@question, "text_en"), "text_en")
    SORT BM25(c) DESC
    LIMIT @k
    RETURN c._key
)
FOR hit IN UNION(
    (FOR key IN vector_hits RETURN { key, rrf: 1 / (60 + POSITION(vector_hits, key, true) + 1) }),
    (FOR key IN keyword_hits RETURN { key, rrf: 1 / (60 + POSITION(keyword_hits, key, true) + 1) })
  )
  COLLECT key = hit.key AGGREGATE score = SUM(hit.rrf)
  SORT score DESC
  LIMIT @k
  LET c = DOCUMENT("chunks", key)
  RETURN { text: c.text, index: c.index, score }
"""

SYSTEM_MESSAGE = (
    "You are an expert on Albert Einstein. Answer only from the documents provided "
    "by the user; if they do not contain the answer, say you don't know."
)


def load_paper() -> str:
    from pypdf import PdfReader

    pdf = PdfReader(io.BytesIO(requests.get(PAPER_URL, timeout=60).content))
    return "\n".join(page.extract_text() or "" for page in pdf.pages)


def setup(db, text: str) -> int:
    """Data setup: chunk, embed, store, index."""
    chunks = kdb.ensure_collection(db, "chunks")
    texts = chunk_text(text, 500, 40)
    embeddings = llm.embed(texts)
    kdb.aql(db, STORE_CHUNKS, texts=texts, embeddings=embeddings)
    # vector index AFTER the data is in (IVF needs vectors to train its centroids)
    kdb.ensure_vector_index(chunks, "embedding", dimension=len(embeddings[0]), metric="cosine")
    # keyword side of hybrid search: ArangoSearch view with the English analyzer
    kdb.ensure_search_view(db, "chunks_view", {"chunks": {"text": ["text_en"]}})
    return len(texts)


def vector_search(db, question: str, k: int = 4) -> list[dict]:
    return kdb.aql(db, VECTOR_SEARCH, question_embedding=llm.embed([question])[0], k=k)


def hybrid_search(db, question: str, k: int = 4) -> list[dict]:
    return kdb.aql(db, HYBRID_SEARCH, question_embedding=llm.embed([question])[0],
                   question=question, k=k)


def answer(question: str, documents: list[str]) -> str:
    user_message = (
        "Use the following documents to answer the question that follows.\n"
        + "\n---\n".join(documents)
        + f"\n\n---\nQuestion (answer only from the documents above): {question}"
    )
    return llm.chat([{"role": "system", "content": SYSTEM_MESSAGE},
                     {"role": "user", "content": user_message}])


def main() -> None:
    question = sys.argv[1] if len(sys.argv) > 1 else \
        "At what time was Einstein really interested in experimental works?"
    db = kdb.connect(DB_NAME, fresh=True)
    n = setup(db, load_paper())
    print(f"stored {n} chunks")

    print("\n== vector search ==")
    hits = vector_search(db, question, k=2)
    for h in hits:
        print(f"[{h['index']}] {h['score']:.3f}  {h['text'][:90]}...")

    print("\n== hybrid search ==")
    hybrid = hybrid_search(db, question, k=4)
    for h in hybrid:
        print(f"[{h['index']}] {h['score']:.3f}  {h['text'][:90]}...")

    print("\n== answer ==")
    print(answer(question, [h["text"] for h in hybrid]))


if __name__ == "__main__":
    main()
