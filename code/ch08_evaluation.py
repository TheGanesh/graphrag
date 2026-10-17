"""Chapter 8 - evaluate the chapter-5 agent with a benchmark whose ground truth is AQL.

    python load_movies.py        # once
    python ch08_evaluation.py    # writes results/benchmark_results.csv

For every benchmark row we
  1. run the row's AQL to get today's ground truth (stays valid when data changes),
  2. run the agent and record its answer, the context it retrieved and the latency,
  3. score it with three LLM-as-judge metrics (the same ideas RAGAS uses):
       context recall      - share of ground-truth statements supported by the context
       faithfulness        - share of answer statements supported by the context
       answer correctness  - F1 of answer statements vs ground-truth statements
"""
from __future__ import annotations

import csv
import json
import os
import statistics
import time

import ch05_agentic_rag as agent
from kit import db as kdb
from kit import llm

HERE = os.path.dirname(os.path.abspath(__file__))

# --------------------------------------------------------------------- judge prompts
STATEMENTS_PROMPT = """Break the answer into short, self-contained factual statements.
Replace pronouns with the names they refer to. Return JSON: {"statements": ["...", "..."]}"""

SUPPORTED_PROMPT = """For each statement, decide whether it can be directly inferred from the context.
Return JSON: {"verdicts": [{"statement": "...", "verdict": 1}]} with verdict 1 (supported) or 0 (not)."""

CORRECTNESS_PROMPT = """Compare the answer statements with the ground-truth statements.
Classify every statement exactly once:
  TP - in the answer and supported by the ground truth
  FP - in the answer but not supported by the ground truth
  FN - in the ground truth but missing from the answer
Return JSON: {"TP": ["..."], "FP": ["..."], "FN": ["..."]}"""


def statements(question: str, text: str) -> list[str]:
    out = llm.chat_json([{"role": "system", "content": STATEMENTS_PROMPT},
                         {"role": "user", "content": f"Question: {question}\nAnswer: {text}"}])
    return out.get("statements", []) or [text]


def supported_share(stmts: list[str], context: str) -> float:
    if not stmts:
        return 0.0
    out = llm.chat_json([{"role": "system", "content": SUPPORTED_PROMPT},
                         {"role": "user", "content": f"Context:\n{context}\n\nStatements:\n"
                                                     + json.dumps(stmts)}])
    verdicts = [int(v.get("verdict", 0)) for v in out.get("verdicts", [])]
    return sum(verdicts) / len(verdicts) if verdicts else 0.0


def context_recall(question: str, reference: str, contexts: list[str]) -> float:
    return supported_share(statements(question, reference), "\n".join(contexts))


def faithfulness(question: str, answer: str, contexts: list[str]) -> float:
    return supported_share(statements(question, answer), "\n".join(contexts))


def answer_correctness(question: str, answer: str, reference: str) -> float:
    out = llm.chat_json([{"role": "system", "content": CORRECTNESS_PROMPT},
                         {"role": "user", "content": json.dumps({
                             "question": question,
                             "answer_statements": statements(question, answer),
                             "ground_truth_statements": statements(question, reference)})}])
    tp, fp, fn = (len(out.get(k, [])) for k in ("TP", "FP", "FN"))
    return tp / (tp + 0.5 * (fp + fn)) if tp else 0.0


# --------------------------------------------------------------------- benchmark
def load_benchmark(path: str | None = None) -> list[dict]:
    path = path or os.path.join(HERE, "data", "benchmark.csv")
    with open(path, encoding="utf-8") as fh:
        return list(csv.DictReader(fh, delimiter=";"))


def run(rows: list[dict]) -> list[dict]:
    db = kdb.connect(agent.DB_NAME)
    agent.init()
    results = []
    for row in rows:
        reference = json.dumps(kdb.aql(db, row["aql"]), default=str)   # live ground truth
        start = time.perf_counter()
        try:
            answer, context = agent.get_answer(row["question"])
            contexts = [m["content"] for m in context]
        except Exception as exc:                                      # keep going, score as a miss
            answer, contexts = f"I don't know ({type(exc).__name__})", []
        latency = time.perf_counter() - start
        q = row["question"]
        results.append({
            "question": q, "ground_truth": reference, "answer": answer, "latency_s": round(latency, 2),
            "context_recall": context_recall(q, reference, contexts) if contexts else 0.0,
            "faithfulness": faithfulness(q, answer, contexts) if contexts else 0.0,
            "answer_correctness": answer_correctness(q, answer, reference),
        })
        print(f"{latency:5.1f}s  {q}")
    return results


def summarize(results: list[dict]) -> dict:
    keys = ["answer_correctness", "context_recall", "faithfulness", "latency_s"]
    return {k: round(statistics.mean(r[k] for r in results), 4) for k in keys}


def evaluate_with_ragas(results: list[dict], contexts: list[list[str]]):
    """Optional: the same three metrics computed by RAGAS (pip install ragas==0.4.3
    'langchain-community<0.4' langchain-openai). Kept separate because RAGAS'
    dependencies move fast."""
    from langchain_openai import ChatOpenAI, OpenAIEmbeddings
    from ragas import EvaluationDataset, evaluate
    from ragas.embeddings import LangchainEmbeddingsWrapper
    from ragas.llms import LangchainLLMWrapper
    from ragas.metrics import answer_correctness as rc, context_recall as rr, faithfulness as rf

    dataset = EvaluationDataset.from_list([
        {"user_input": r["question"], "response": r["answer"], "reference": r["ground_truth"],
         "retrieved_contexts": ctx or ["I don't know"]} for r, ctx in zip(results, contexts)])
    return evaluate(dataset, metrics=[rc, rr, rf],
                    llm=LangchainLLMWrapper(ChatOpenAI(model=llm.LLM_MODEL)),
                    embeddings=LangchainEmbeddingsWrapper(OpenAIEmbeddings(model=llm.EMBEDDING_MODEL)))


def main() -> None:
    results = run(load_benchmark())
    os.makedirs(os.path.join(HERE, "results"), exist_ok=True)
    out = os.path.join(HERE, "results", "benchmark_results.csv")
    with open(out, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(results[0]), delimiter=";")
        writer.writeheader()
        writer.writerows(results)
    print(json.dumps(summarize(results), indent=2))
    print("details:", out)


if __name__ == "__main__":
    main()
