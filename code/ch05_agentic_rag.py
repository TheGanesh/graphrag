"""Chapter 5 - agentic RAG: a retriever router, retriever tools and an answer critic.

    python load_movies.py     # once
    python ch05_agentic_rag.py "Who directed The Matrix, and which other movies did they direct?"

question -> query updater -> router (LLM picks a tool + arguments) -> tool runs AQL
         -> answers so far -> critic (anything missing? -> one more round) -> final answer
"""
from __future__ import annotations

import json
import sys

from ch04_text2aql import format_schema, get_structured_schema, text2aql
from kit import db as kdb
from kit import llm

DB_NAME = "movies"
db = None          # set in init()
_schema_text = None

# --------------------------------------------------------------------------- AQL tools
MOVIE_INFO_BY_TITLE = """
WITH persons
FOR m IN movies
  FILTER CONTAINS(LOWER(m.title), LOWER(@title))
  LET cast = (FOR p IN 1..1 INBOUND m acted_in RETURN p.name)
  LET directors = (FOR p IN 1..1 INBOUND m directed RETURN p.name)
  RETURN { title: m.title, released: m.released, tagline: m.tagline, cast, directors }
"""

MOVIES_BY_ACTOR = """
WITH movies
FOR p IN persons
  FILTER CONTAINS(LOWER(p.name), LOWER(@actor))
  FOR m IN 1..1 OUTBOUND p acted_in
    LET cast = (FOR c IN 1..1 INBOUND m acted_in RETURN c.name)
    LET directors = (FOR d IN 1..1 INBOUND m directed RETURN d.name)
    RETURN { actor: p.name, title: m.title, released: m.released, cast, directors }
"""


def movie_info_by_title(title: str):
    """Return movie information (cast, directors) for titles containing `title`."""
    return kdb.aql(db, MOVIE_INFO_BY_TITLE, title=title)


def movies_info_by_actor(actor: str):
    """Return the movies an actor appeared in, with cast and directors."""
    return kdb.aql(db, MOVIES_BY_ACTOR, actor=actor)


def text2aql_tool(question: str):
    """Catch-all: let the LLM write AQL for the question."""
    _, rows = text2aql(db, question, _schema_text)
    return rows


def answer_given(answer: str):
    """The answer is already in the conversation; just pass it through."""
    return answer


def _tool(name: str, description: str, param: str, param_description: str) -> dict:
    return {"type": "function", "function": {
        "name": name, "description": description,
        "parameters": {"type": "object",
                       "properties": {param: {"type": "string", "description": param_description}},
                       "required": [param]}}}


TOOLS = {
    "movie_info_by_title": {
        "description": _tool("movie_info_by_title", "Get information about a movie by its title.",
                             "title", "The movie title"),
        "function": movie_info_by_title},
    "movies_info_by_actor": {
        "description": _tool("movies_info_by_actor", "Get the movies an actor has acted in.",
                             "actor", "The actor's name"),
        "function": movies_info_by_actor},
    "text2aql": {
        "description": _tool("text2aql", "Query the movie database with a natural-language question. "
                             "Use this when no other tool fits (counts, rankings, filters, ...).",
                             "question", "The question to answer from the database"),
        "function": text2aql_tool},
    "answer_given": {
        "description": _tool("answer_given", "Use when the conversation already contains the "
                             "complete answer to the question.", "answer", "The answer"),
        "function": answer_given},
}

# --------------------------------------------------------------------------- prompts
QUERY_UPDATE_PROMPT = """You make questions atomic, specific and easy to look up.
Fill in missing details of the user's question using the answers given earlier in
this conversation. Change the question only if needed; never ask for more than the
original question did. Reply in JSON: {"question": "<updated question>"}"""

TOOL_PICKER_PROMPT = """Choose the right tool(s) to answer the user's question.
The tools are provided with the request. Pass complete, correct arguments."""

CRITIC_PROMPT = """You check whether a question has been fully answered by the information
in this conversation. If something is missing, list new questions that would gather
the missing information; each must be complete, atomic and specific.
If nothing is missing, return an empty list.
Reply in JSON: {"questions": ["...", "..."]}"""

MAIN_PROMPT = """You answer the user's question using only the information in this
conversation. If part of the answer is missing, say which part is missing.
Never make anything up and never use outside knowledge."""


# --------------------------------------------------------------------------- the loop
def handle_tool_calls(tool_calls) -> list:
    """The LLM only *chooses* tools; executing them is our job."""
    results = []
    for call in tool_calls or []:
        fn = TOOLS[call.function.name]["function"]
        args = json.loads(call.function.arguments or "{}")
        results.append({"tool": call.function.name, "args": args, "result": fn(**args)})
    return results


def query_update(question: str, answers: list[dict]) -> str:
    out = llm.chat_json([{"role": "system", "content": QUERY_UPDATE_PROMPT}, *answers,
                         {"role": "user", "content": f"The user question to rewrite: '{question}'"}])
    return out.get("question", question)


def route_question(question: str, answers: list[dict]) -> list:
    message = llm.chat_tools(
        [{"role": "system", "content": TOOL_PICKER_PROMPT}, *answers,
         {"role": "user", "content": f"The user question to find a tool to answer: '{question}'"}],
        tools=[t["description"] for t in TOOLS.values()])
    return handle_tool_calls(message.tool_calls)


def handle_user_input(question: str, answers: list[dict] | None = None) -> list[dict]:
    answers = [] if answers is None else answers
    updated = query_update(question, answers)
    results = route_question(updated, answers)
    answers.append({"role": "assistant", "content":
                    f"For the question '{updated}', we have the answer: {json.dumps(results, default=str)}"})
    return answers


def critique_answers(question: str, answers: list[dict]) -> list[str]:
    out = llm.chat_json([{"role": "system", "content": CRITIC_PROMPT}, *answers,
                         {"role": "user", "content": f"The original user question to answer: {question}"}])
    return out.get("questions", [])


def get_answer(question: str) -> tuple[str, list[dict]]:
    """Run the agent; returns (answer, context messages) - used by chapter 8."""
    answers = handle_user_input(question)
    missing = critique_answers(question, answers)
    if missing:                                   # exit criterion: critique only once
        answers = handle_user_input(" ".join(missing), answers)
    final = llm.chat([{"role": "system", "content": MAIN_PROMPT}, *answers,
                      {"role": "user", "content": f"The user question to answer: {question}"}])
    return final, answers


def init(db_name: str = DB_NAME) -> None:
    global db, _schema_text
    db = kdb.connect(db_name)
    _schema_text = format_schema(get_structured_schema(db))


def main() -> None:
    question = sys.argv[1] if len(sys.argv) > 1 else \
        "Who directed The Matrix, and which other movies did they direct?"
    init()
    answer, context = get_answer(question)
    for c in context:
        print("-", c["content"][:300])
    print("\n", answer)


if __name__ == "__main__":
    main()
