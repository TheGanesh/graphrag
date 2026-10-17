"""Check every AQL query in this repository against ArangoDB's real grammar.

    sh tools/aql-lint/fetch.sh && python tools/aql-lint/build.py   # once
    python tools/aql-lint/check_repo.py

Scans: ```aql blocks in book/*.md, ALL_CAPS string constants and literal
kdb.aql(db, "...") calls in code/*.py, and the AQL column of code/data/benchmark.csv.
Reports syntax errors and unknown function names; exits non-zero on problems.
"""
import ast
import csv
import glob
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
from aqlcheck import check, unknown_functions  # noqa: E402

AQL_HINT = re.compile(r"\b(RETURN|INSERT|UPSERT|UPDATE|REMOVE|REPLACE)\b")


def markdown_blocks(path):
    lines = open(path, encoding="utf-8").read().split("\n")
    inside, start, buf = False, 0, []
    for no, line in enumerate(lines, 1):
        bare = re.sub(r"^\s*>\s?", "", line)          # blocks may sit inside > quotes
        if not inside and bare.strip().startswith("```aql"):
            inside, start, buf = True, no, []
        elif inside and bare.strip().startswith("```"):
            inside = False
            yield start, "\n".join(buf)
        elif inside:
            buf.append(bare)


def python_queries(path):
    tree = ast.parse(open(path, encoding="utf-8").read())
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant) \
                and isinstance(node.value.value, str):
            names = [t.id for t in node.targets if isinstance(t, ast.Name)]
            text = node.value.value
            if names and names[0].isupper() and AQL_HINT.search(text) and \
                    re.match(r"\s*(FOR|LET|RETURN|WITH|UPSERT|INSERT)\b", text):
                yield node.lineno, text
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "aql" \
                and len(node.args) > 1 and isinstance(node.args[1], ast.Constant) \
                and isinstance(node.args[1].value, str):
            yield node.lineno, node.args[1].value


def main() -> int:
    items = []
    for md in sorted(glob.glob(os.path.join(ROOT, "book", "*.md"))) + [os.path.join(ROOT, "README.md")]:
        if os.path.exists(md):
            items += [(os.path.relpath(md, ROOT), n, q) for n, q in markdown_blocks(md)]
    for py in sorted(glob.glob(os.path.join(ROOT, "code", "*.py"))):
        items += [(os.path.relpath(py, ROOT), n, q) for n, q in python_queries(py)]
    bench = os.path.join(ROOT, "code", "data", "benchmark.csv")
    with open(bench, encoding="utf-8") as fh:
        for i, row in enumerate(csv.DictReader(fh, delimiter=";"), 2):
            items.append((os.path.relpath(bench, ROOT), i, row["aql"]))
    problems = 0
    for where, line, query in items:
        ok, msg = check(query)
        bad = unknown_functions(query) if ok else []
        if not ok or bad:
            problems += 1
            print(f"FAIL {where}:{line}: {msg} {('unknown functions: ' + ', '.join(bad)) if bad else ''}")
    print(f"{len(items)} AQL queries checked, {problems} problems")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
