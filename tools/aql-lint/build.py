"""Build a syntax-only AQL parser from ArangoDB's real bison grammar.

    sh fetch.sh          # downloads vendor/grammar.y, tokens.ll, AqlFunctionFeature.cpp
    python build.py      # needs bison and a C compiler; writes build/

Strips the C++ semantic actions, prologue and epilogue from grammar.y and keeps
tokens, precedence and rules. Adds a tiny C driver whose yylex() replays token
ids handed in from Python (see aqlcheck.py), then runs bison + cc. Also writes
build/functions.txt, the list of AQL function names of that release.
"""
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
VENDOR = os.path.join(HERE, "vendor")
BUILD = os.path.join(HERE, "build")

# ArangoSearch functions are registered outside AqlFunctionFeature.cpp
ARANGOSEARCH_FUNCTIONS = """ANALYZER BOOST BM25 TFIDF EXISTS IN_RANGE MIN_MATCH NGRAM_MATCH PHRASE STARTS_WITH
LEVENSHTEIN_MATCH LIKE TOKENS GEO_CONTAINS GEO_DISTANCE GEO_IN_RANGE GEO_INTERSECTS OFFSET_INFO
MINHASH_MATCH""".split()


def strip_block(text: str, start: int) -> int:
    """text[start] == '{' -> index just past the matching '}' (skips strings/comments)."""
    depth, i, n = 0, start, len(text)
    while i < n:
        c = text[i]
        if text.startswith("//", i):
            i = text.index("\n", i)
            continue
        if text.startswith("/*", i):
            i = text.index("*/", i) + 2
            continue
        if c in "\"'":
            i += 1
            while text[i] != c:
                i += 2 if text[i] == "\\" else 1
            i += 1
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    raise ValueError("unbalanced braces")


def strip_rules(rules: str) -> str:
    out, i, n = [], 0, len(rules)
    while i < n:
        c = rules[i]
        if rules.startswith("/*", i):
            i = rules.index("*/", i) + 2
            continue
        if rules.startswith("//", i):
            i = rules.index("\n", i)
            continue
        if c == "'":                       # character-literal token such as '.'
            j = i + 2 if rules[i + 1] != "\\" else i + 3
            out.append(rules[i:j + 1])
            i = j + 1
            continue
        if c == '"':
            j = i + 1
            while rules[j] != '"':
                j += 2 if rules[j] == "\\" else 1
            out.append(rules[i:j + 1])
            i = j + 1
            continue
        if c == "{":
            i = strip_block(rules, i)
            out.append(" ")
            continue
        out.append(c)
        i += 1
    return "".join(out)


EPILOGUE = r"""
static const int *g_ids; static int g_n; static int g_pos;
static char g_err[512]; static int g_err_pos;
int yylex(void) { return g_pos < g_n ? g_ids[g_pos++] : 0; }
void yyerror(const char *s) { strncpy(g_err, s, sizeof(g_err) - 1); g_err_pos = g_pos; }
int aql_parse(const int *ids, int n, char *err, int errlen, int *errpos) {
  g_ids = ids; g_n = n; g_pos = 0; g_err[0] = 0; g_err_pos = -1;
  int rc = yyparse();
  if (rc != 0) { strncpy(err, g_err, errlen - 1); err[errlen - 1] = 0; *errpos = g_err_pos; }
  return rc;
}
"""


def main() -> None:
    os.makedirs(BUILD, exist_ok=True)
    text = open(os.path.join(VENDOR, "grammar.y"), encoding="utf-8").read()
    decls, rules = re.split(r"^%%\s*$", text, flags=re.M)[:2]
    keep = [s.strip().rstrip(";") for s in decls.splitlines()
            if s.strip().startswith(("%token", "%left", "%right", "%nonassoc", "%precedence", "%start"))]
    prologue = ("%{\n#include <stdio.h>\n#include <string.h>\n"
                "int yylex(void);\nvoid yyerror(const char *s);\n%}\n%define parse.error verbose\n")
    grammar = prologue + "\n".join(keep) + "\n%%\n" + strip_rules(rules) + "\n%%\n" + EPILOGUE
    y, c, h = (os.path.join(BUILD, f) for f in ("aql_min.y", "aql_min.c", "aql_min.h"))
    open(y, "w").write(grammar)
    subprocess.run(["bison", "-Wno-other", f"--defines={h}", "-o", c, y], check=True)
    cc = os.environ.get("CC", "cc")
    subprocess.run([cc, "-shared", "-fPIC", "-O1", "-o", os.path.join(BUILD, "libaql.so"), c], check=True)

    src = open(os.path.join(VENDOR, "AqlFunctionFeature.cpp"), encoding="utf-8").read()
    names = set(re.findall(r'add\(\{"([A-Z0-9_]+)"', src)) | set(re.findall(r'addAlias\("([A-Z0-9_]+)"', src))
    names |= set(ARANGOSEARCH_FUNCTIONS)
    with open(os.path.join(BUILD, "functions.txt"), "w") as fh:
        fh.write("\n".join(sorted(names)) + "\n")
    print(f"built parser and {len(names)} function names into {BUILD}")


if __name__ == "__main__":
    sys.exit(main())
