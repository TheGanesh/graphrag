"""Chapter 3 - step-back prompting + the parent document retriever, on ArangoDB.

    python ch03_advanced_vector.py "When was Einstein granted the patent for his blouse design?"

Graph:  pdfs --has_parent--> parents (<= 2000 chars) --has_child--> children (500 chars + embedding)
Search: embed the (step-back) question -> nearest *children* -> walk up to their
        parents -> keep each parent once -> hand whole parents to the LLM.
"""
from __future__ import annotations

import re
import sys

from ch02_vector_hybrid import load_paper
from kit import db as kdb
from kit import llm
from kit.text import chunk_text, count_tokens

DB_NAME = "ch03"
PDF_ID = "1709.00666"
PDF_TITLE = "Einstein's Patents and Inventions"

# --------------------------------------------------------------------------- AQL
# Book listing 3.7 (MERGE PDF, MERGE Parent, UNWIND children, MERGE Child) in AQL.
# Each data-modification runs against a different collection, which AQL allows
# once per collection per query.
IMPORT_PARENT = """
LET pdf = FIRST(
  UPSERT { _key: @pdf_id }
  INSERT { _key: @pdf_id, title: @title }
  UPDATE {}
  IN pdfs
  RETURN NEW
)
LET parent = FIRST(
  INSERT { _key: @parent_key, text: @parent_text }
  INTO parents OPTIONS { overwriteMode: "replace" }
  RETURN NEW
)
LET pdf_link = (
  INSERT { _key: @parent_key, _from: pdf._id, _to: parent._id }
  INTO has_parent OPTIONS { overwriteMode: "ignore" }
)
LET kids = (
  FOR i IN 0..LENGTH(@children) - 1
    INSERT { _key: CONCAT(@parent_key, "-", i), text: @children[i], embedding: @embeddings[i] }
    INTO children OPTIONS { overwriteMode: "replace" }
    RETURN NEW._id
)
FOR kid IN kids
  INSERT { _key: PARSE_IDENTIFIER(kid).key, _from: parent._id, _to: kid }
  INTO has_child OPTIONS { overwriteMode: "ignore" }
"""

# Book listing 3.11: fetch k*4 children, walk to the parents, de-duplicate.
PARENT_RETRIEVAL = """
WITH parents
LET hits = (
  FOR child IN children
    LET score = APPROX_NEAR_COSINE(child.embedding, @question_embedding)
    SORT score DESC
    LIMIT @candidates
    RETURN { id: child._id, score }
)
FOR hit IN hits
  FOR parent IN 1..1 INBOUND hit.id has_child
    COLLECT key = parent._key, text = parent.text AGGREGATE score = MAX(hit.score)
    SORT score DESC
    LIMIT @k
    RETURN { key, text, score }
"""

# Same idea for the *hypothetical question* strategy (figure 3.2, left side):
# questions --(embedded)--> nearest question -> the document it came from.
HYPOTHETICAL_QUESTION_RETRIEVAL = """
WITH parents
LET hits = (
  FOR q IN questions
    LET score = APPROX_NEAR_COSINE(q.embedding, @question_embedding)
    SORT score DESC
    LIMIT @candidates
    RETURN { id: q._id, score }
)
FOR hit IN hits
  FOR doc IN 1..1 INBOUND hit.id has_question
    COLLECT key = doc._key, text = doc.text AGGREGATE score = MAX(hit.score)
    SORT score DESC
    LIMIT @k
    RETURN { key, text, score }
"""

STEPBACK_SYSTEM = """You rewrite questions for a search engine.
Step back from the specifics and paraphrase the question into a more generic
question whose answer would contain the original answer. Reply with the
rewritten question only.

Examples
input:  Which company did Satya Nadella work for in 1995?
output: What is Satya Nadella's employment history?
input:  Did Marie Curie win a Nobel Prize in 1911?
output: Which awards did Marie Curie receive during her career?"""

ANSWER_SYSTEM = (
    "You are an expert on Albert Einstein. Answer only from the provided documents; "
    "if they do not contain the answer, say so."
)


def split_into_sections(text: str) -> list[str]:
    """Split on numbered headings like '\\n3A. The refrigerator\\n' (keep the heading)."""
    heading = re.compile(r"\n(\d+[A-Z]?\. {1,3}.{0,60})\n")
    parts = heading.split(text)
    sections = [parts[0].strip()]
    for title, body in zip(parts[1::2], parts[2::2]):
        sections.append(title.strip() + "\n" + body.strip())
    return [s for s in sections if s]


def build_graph(db, text: str) -> tuple[int, int]:
    kdb.ensure_graph(db, "einstein", [
        {"edge_collection": "has_parent", "from_vertex_collections": ["pdfs"],
         "to_vertex_collections": ["parents"]},
        {"edge_collection": "has_child", "from_vertex_collections": ["parents"],
         "to_vertex_collections": ["children"]},
    ])
    sections = split_into_sections(text)
    print("section token counts:", [count_tokens(s) for s in sections])
    parents = [p for s in sections for p in chunk_text(s, 2000, 40)]
    n_children, dim = 0, llm.EMBEDDING_DIM
    for i, parent in enumerate(parents):
        kids = chunk_text(parent, 500, 20)
        embeddings = llm.embed(kids)
        dim = len(embeddings[0])
        kdb.aql(db, IMPORT_PARENT, pdf_id=PDF_ID, title=PDF_TITLE, parent_key=f"{PDF_ID}-{i}",
                parent_text=parent, children=kids, embeddings=embeddings)
        n_children += len(kids)
    kdb.ensure_vector_index(db.collection("children"), "embedding", dimension=dim)
    return len(parents), n_children


QUESTIONS_SYSTEM = """Write 3 short questions that the given text answers.
Return JSON: {"questions": ["...", "...", "..."]}"""

IMPORT_QUESTIONS = """
LET qs = (
  FOR i IN 0..LENGTH(@questions) - 1
    INSERT { _key: CONCAT(@parent_key, "-q", i), text: @questions[i], embedding: @embeddings[i] }
    INTO questions OPTIONS { overwriteMode: "replace" }
    RETURN NEW._id
)
FOR q IN qs
  INSERT { _key: PARSE_IDENTIFIER(q).key, _from: CONCAT("parents/", @parent_key), _to: q }
  INTO has_question OPTIONS { overwriteMode: "ignore" }
"""


def add_hypothetical_questions(db) -> int:
    """Figure 3.2 (left): embed questions a parent can answer instead of the parent."""
    kdb.ensure_graph(db, "einstein_questions", [
        {"edge_collection": "has_question", "from_vertex_collections": ["parents"],
         "to_vertex_collections": ["questions"]}])
    total, dim = 0, llm.EMBEDDING_DIM
    for p in kdb.aql(db, "FOR p IN parents RETURN { key: p._key, text: p.text }"):
        qs = llm.chat_json([{"role": "system", "content": QUESTIONS_SYSTEM},
                            {"role": "user", "content": p["text"]}]).get("questions", [])
        if not qs:
            continue
        embeddings = llm.embed(qs)
        dim = len(embeddings[0])
        kdb.aql(db, IMPORT_QUESTIONS, parent_key=p["key"], questions=qs, embeddings=embeddings)
        total += len(qs)
    kdb.ensure_vector_index(db.collection("questions"), "embedding", dimension=dim)
    return total


def stepback(question: str) -> str:
    return llm.chat([{"role": "system", "content": STEPBACK_SYSTEM},
                     {"role": "user", "content": question}]).strip()


def parent_retrieval(db, question: str, k: int = 4) -> list[str]:
    rows = kdb.aql(db, PARENT_RETRIEVAL, question_embedding=llm.embed([question])[0],
                   candidates=k * 4, k=k)
    return [r["text"] for r in rows]


def generate_answer(question: str, documents: list[str]) -> str:
    user = ("Use the following documents to answer the question that follows.\n"
            + "\n---\n".join(documents)
            + f"\n\n---\nQuestion (answer only from the documents above): {question}")
    return llm.chat([{"role": "system", "content": ANSWER_SYSTEM},
                     {"role": "user", "content": user}])


def rag_pipeline(db, question: str) -> str:
    broader = stepback(question)
    print("step-back question:", broader)
    documents = parent_retrieval(db, broader)        # search with the broad question...
    return generate_answer(question, documents)       # ...but answer the original one


def main() -> None:
    question = sys.argv[1] if len(sys.argv) > 1 else \
        "When was Einstein granted the patent for his blouse design?"
    db = kdb.connect(DB_NAME, fresh=True)
    n_parents, n_children = build_graph(db, load_paper())
    print(f"{n_parents} parents, {n_children} children")
    print(rag_pipeline(db, question))


if __name__ == "__main__":
    main()
