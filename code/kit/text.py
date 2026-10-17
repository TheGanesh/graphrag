"""Text utilities: chunking, token counting and ArangoDB-safe keys."""
from __future__ import annotations

import hashlib
import re
import unicodedata


def chunk_text(text: str, size: int, overlap: int, whitespace_only: bool = True) -> list[str]:
    """Sliding-window chunker measured in characters.

    Each chunk is about `size` characters and starts roughly `overlap`
    characters before the previous chunk ended, so a sentence that straddles
    a boundary appears in both chunks. With whitespace_only=True, chunk edges
    are moved to the nearest space so words are never cut in half.
    """
    chunks: list[str] = []
    pos = 0
    n = len(text)
    while pos < n:
        if whitespace_only:
            start = text.rfind(" ", 0, max(pos - overlap, 0) + 1) if pos else 0
            start = max(start, 0)
            end = text.find(" ", pos + size)
            end = n if end == -1 else end
            piece = text[start:end].strip()
            pos = end + 1
        else:
            start = max(0, pos - overlap)
            end = min(n, pos + size)
            piece = text[start:end].strip()
            pos += size
        if piece:
            chunks.append(piece)
    return chunks


def count_tokens(text: str, model_hint: str = "o200k_base") -> int:
    """Count tokens with tiktoken; falls back to a words*1.3 estimate."""
    try:
        import tiktoken

        try:
            enc = tiktoken.get_encoding(model_hint)
        except Exception:
            enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
    except Exception:
        return int(len(text.split()) * 1.3)


_KEY_OK = re.compile(r"[^A-Za-z0-9_\-:.@()+,=;$!*'%]")


def safe_key(name: str, max_len: int = 200) -> str:
    """Turn any string into a valid, stable ArangoDB _key.

    Allowed key characters are letters, digits and _-:.@()+,=;$!*'% .
    Accents are folded (Bratanič -> Bratanic), everything else becomes '_'.
    Very long names get a short hash suffix.
    """
    folded = unicodedata.normalize("NFKD", name.strip()).encode("ascii", "ignore").decode()
    key = _KEY_OK.sub("_", folded)
    key = re.sub(r"_+", "_", key).strip("_") or "x"
    if len(key) > max_len:
        key = key[: max_len - 9] + "_" + hashlib.sha1(name.encode()).hexdigest()[:8]
    return key


def content_key(text: str) -> str:
    """Deterministic key derived from content (idempotent imports)."""
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:20]
