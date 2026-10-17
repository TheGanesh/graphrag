"""LLM + embedding helpers for any OpenAI-compatible endpoint.

Environment variables
  OPENAI_API_KEY      key for api.openai.com (or your gateway)
  OPENAI_BASE_URL     optional: point at Ollama, vLLM, LM Studio, Azure, ...
  LLM_MODEL           chat model id              (default: gpt-5.4-mini)
  EMBEDDING_MODEL     embedding model id         (default: text-embedding-3-small)
  EMBEDDING_DIM       its vector length          (default: 1536)
  EMBEDDINGS=hash     offline mode: deterministic hashing-trick vectors, no API
  LLM_TEMPERATURE     optional; only sent if set (some reasoning models reject it)
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
from typing import Any

LLM_MODEL = os.getenv("LLM_MODEL", "gpt-5.4-mini")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIM", "1536"))
EMBEDDINGS = os.getenv("EMBEDDINGS", "openai")
_TEMPERATURE = os.getenv("LLM_TEMPERATURE")

_client = None


def client():
    global _client
    if _client is None:
        from openai import OpenAI

        _client = OpenAI()  # reads OPENAI_API_KEY and OPENAI_BASE_URL
    return _client


def _extra() -> dict[str, Any]:
    return {"temperature": float(_TEMPERATURE)} if _TEMPERATURE else {}


def chat(messages: list[dict], model: str | None = None, json_mode: bool = False) -> str:
    """Plain chat completion; returns the assistant text."""
    kwargs: dict[str, Any] = {"model": model or LLM_MODEL, "messages": messages, **_extra()}
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    resp = client().chat.completions.create(**kwargs)
    return resp.choices[0].message.content or ""


def chat_json(messages: list[dict], model: str | None = None) -> dict:
    """Chat completion that must return a JSON object."""
    raw = chat(messages, model=model, json_mode=True)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", raw, re.S)  # tolerate stray prose around the JSON
        return json.loads(m.group(0)) if m else {}


def chat_tools(messages: list[dict], tools: list[dict], model: str | None = None):
    """Chat completion with tool (function) calling; returns the message object."""
    resp = client().chat.completions.create(
        model=model or LLM_MODEL, messages=messages, tools=tools, **_extra()
    )
    return resp.choices[0].message


def parse(messages: list[dict], schema, model: str | None = None):
    """Structured Outputs: the reply is validated against a Pydantic model."""
    resp = client().chat.completions.parse(
        model=model or LLM_MODEL, messages=messages, response_format=schema, **_extra()
    )
    return resp.choices[0].message.parsed


# ------------------------------------------------------------------ embeddings
def hash_embed(text: str, dim: int = EMBEDDING_DIM) -> list[float]:
    """Offline stand-in for a real embedding model (the 'hashing trick').

    Each lowercase word (and word pair) is hashed to a few dimensions; texts
    that share words end up with a high cosine similarity. It knows nothing
    about synonyms, but it is deterministic, free and good enough to test the
    plumbing (vector index + AQL) without an API key.
    """
    vec = [0.0] * dim
    words = re.findall(r"[a-z0-9]+", text.lower())
    feats = words + [a + "_" + b for a, b in zip(words, words[1:])]
    for w in feats:
        h = hashlib.md5(w.encode()).digest()
        for i in range(0, 6, 3):
            idx = int.from_bytes(h[i:i + 2], "little") % dim
            vec[idx] += 1.0 if h[i + 2] % 2 else -1.0
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def embed(texts: list[str], batch_size: int = 128) -> list[list[float]]:
    """Embed a list of texts (same model for documents and questions!)."""
    if EMBEDDINGS == "hash":
        return [hash_embed(t) for t in texts]
    out: list[list[float]] = []
    for i in range(0, len(texts), batch_size):
        resp = client().embeddings.create(model=EMBEDDING_MODEL, input=texts[i:i + batch_size])
        out.extend(d.embedding for d in resp.data)
    return out
