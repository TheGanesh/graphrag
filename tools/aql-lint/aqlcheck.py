"""Syntax-check AQL with ArangoDB's own grammar (semantic actions stripped).

    from aqlcheck import check, unknown_functions
    ok, msg = check("FOR d IN docs RETURN d")

The lexer is a Python port of arangod/Aql/Parser/tokens.ll; the parser is
bison-generated from grammar.y by build.py. It checks *syntax only* - not
collection existence, and not the checks ArangoDB performs inside grammar
actions (e.g. that an identifier in keyword position really is SEARCH, PRUNE,
OPTIONS, KEEP or COUNT). unknown_functions() adds a function-name check.
"""
import ctypes
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.join(HERE, "build")
TOKENS_LL = os.environ.get("AQL_TOKENS_LL", os.path.join(HERE, "vendor", "tokens.ll"))

_lib = ctypes.CDLL(os.path.join(BUILD, "libaql.so"))
_lib.aql_parse.argtypes = [ctypes.POINTER(ctypes.c_int), ctypes.c_int, ctypes.c_char_p,
                           ctypes.c_int, ctypes.POINTER(ctypes.c_int)]

# token ids from the generated header
TOK = {}
for m in re.finditer(r"^\s+(T_\w+)\s*=\s*(\d+)", open(os.path.join(BUILD, "aql_min.h")).read(), re.M):
    TOK[m.group(1)] = int(m.group(2))

# keyword map from tokens.ll: (?i:WORD) { ... return T_X;
KEYWORDS = {}
_ll = open(TOKENS_LL, encoding="utf-8").read()
for m in re.finditer(r"^\(\?i:([A-Z_]+)\)\s*\{(.*?)\n\}", _ll, re.M | re.S):
    r = re.search(r"return (T_\w+);", m.group(2))
    if r:
        KEYWORDS[m.group(1)] = r.group(1)

OPS = [
    ("=~", "T_REGEX_MATCH"), ("!~", "T_REGEX_NON_MATCH"), ("==", "T_EQ"), ("!=", "T_NE"),
    (">=", "T_GE"), ("<=", "T_LE"), ("&&", "T_AND"), ("||", "T_OR"), ("::", "T_SCOPE"),
    ("..", "T_RANGE"), (">", "T_GT"), ("<", "T_LT"), ("=", "T_ASSIGN"), ("!", "T_NOT"),
    ("+", "T_PLUS"), ("-", "T_MINUS"), ("*", "T_TIMES"), ("/", "T_DIV"), ("%", "T_MOD"),
    ("?", "T_QUESTION"), (":", "T_COLON"), (",", "T_COMMA"), ("(", "T_OPEN"), (")", "T_CLOSE"),
    ("{", "T_OBJECT_OPEN"), ("}", "T_OBJECT_CLOSE"), ("[", "T_ARRAY_OPEN"), ("]", "T_ARRAY_CLOSE"),
]

RE_IDENT = re.compile(r"(\$?|_+)[a-zA-Z]+[_a-zA-Z0-9]*")
RE_INT = re.compile(r"0[bB][01]+|0[xX][0-9a-fA-F]+|0|[1-9][0-9]*")
RE_DOUBLE = re.compile(r"((0|[1-9][0-9]*)(\.[0-9]+)?|\.[0-9]+)([eE][\-\+]?[0-9]+)?")
RE_NOT_IN = re.compile(r"(?i:NOT[ \t\r\n]+IN)(?=[^_a-zA-Z0-9]|$)")
RE_BANG_IN = re.compile(r"(?i:![ \t\r\n]*IN)(?=[^_a-zA-Z0-9]|$)")
RE_AT_LEAST = re.compile(r"(?i:AT[ \t\r\n]+LEAST)")
RE_PARAM = re.compile(r"@@?(_+[a-zA-Z0-9]+[a-zA-Z0-9_]*|[a-zA-Z0-9][a-zA-Z0-9_]*)")


def lex(q: str):
    toks = []  # (token_id, offset, text)
    i, n = 0, len(q)
    while i < n:
        c = q[i]
        if c in " \t\r\n":
            i += 1
            continue
        if q.startswith("//", i):
            j = q.find("\n", i)
            i = n if j < 0 else j
            continue
        if q.startswith("/*", i):
            j = q.find("*/", i + 2)
            if j < 0:
                raise SyntaxError(f"unterminated comment at {i}")
            i = j + 2
            continue
        if c in "\"'`´":
            j = i + 1
            while j < n and q[j] != c:
                j += 2 if q[j] == "\\" else 1
            if j >= n:
                raise SyntaxError(f"unterminated string at {i}")
            kind = "T_QUOTED_STRING" if c in "\"'" else "T_STRING"
            toks.append((TOK[kind], i, q[i:j + 1]))
            i = j + 1
            continue
        if c == "@":
            m = RE_PARAM.match(q, i)
            if not m:
                raise SyntaxError(f"bad bind parameter at {i}")
            kind = "T_DATA_SOURCE_PARAMETER" if q.startswith("@@", i) else "T_PARAMETER"
            toks.append((TOK[kind], i, m.group(0)))
            i = m.end()
            continue
        # candidates for longest match (ties -> earlier rule; keywords precede identifiers,
        # integers precede doubles)
        cands = []
        m = RE_NOT_IN.match(q, i)
        if m:
            cands.append((m.end() - i, 0, "T_NOT_IN"))
        m = RE_AT_LEAST.match(q, i)
        if m:
            cands.append((m.end() - i, 1, "T_AT_LEAST"))
        m = RE_IDENT.match(q, i)
        if m:
            word = m.group(0)
            kw = KEYWORDS.get(word.upper())
            # keyword rules only match the exact keyword; an identifier that merely starts
            # with a keyword is longer and wins as T_STRING
            if kw:
                cands.append((len(word), 2, kw))
            cands.append((len(word), 5, "T_STRING"))
        m = RE_BANG_IN.match(q, i)
        if m:
            cands.append((m.end() - i, 3, "T_NOT_IN"))
        for op, name in OPS:
            if q.startswith(op, i):
                cands.append((len(op), 4, name))
                break
        m = RE_INT.match(q, i)
        if m and m.end() > i:
            cands.append((m.end() - i, 6, "T_INTEGER"))
        m = RE_DOUBLE.match(q, i)
        if m and m.end() > i:
            cands.append((m.end() - i, 7, "T_DOUBLE"))
        if cands:
            cands.sort(key=lambda t: (-t[0], t[1]))
            length, _, name = cands[0]
            toks.append((TOK[name], i, q[i:i + length]))
            i += length
            continue
        # catch-all: single character token (e.g. '.')
        toks.append((ord(c), i, c))
        i += 1
    return toks


def check(q: str):
    try:
        toks = lex(q)
    except SyntaxError as e:
        return False, f"lex error: {e}"
    ids = (ctypes.c_int * len(toks))(*[t[0] for t in toks])
    err = ctypes.create_string_buffer(512)
    pos = ctypes.c_int(-1)
    rc = _lib.aql_parse(ids, len(toks), err, 512, ctypes.byref(pos))
    if rc == 0:
        return True, "ok"
    p = pos.value - 1
    where = ""
    if 0 <= p < len(toks):
        off = toks[p][1]
        line = q.count("\n", 0, off) + 1
        col = off - (q.rfind("\n", 0, off) + 1) + 1
        where = f" near {toks[p][2]!r} (line {line}, col {col})"
    else:
        where = " at end of query"
    return False, err.value.decode() + where


if __name__ == "__main__":
    import sys
    data = sys.stdin.read()
    ok, msg = check(data)
    print("OK" if ok else "FAIL", msg)


FUNCTIONS = {line.strip().upper() for line in open(os.path.join(BUILD, "functions.txt")) if line.strip()}


def unknown_functions(q: str):
    """Names used in call position (identifier followed by '(') that are not AQL functions."""
    toks = lex(q)
    bad = []
    for k in range(len(toks) - 1):
        tid, _, text = toks[k]
        if tid == TOK["T_STRING"] and toks[k + 1][0] == TOK["T_OPEN"]:
            prev = toks[k - 1][2] if k else ""
            if prev in (".", "::") or "::" in text:
                continue
            if text.upper() not in FUNCTIONS:
                bad.append(text)
    return bad
