# aql-lint: check AQL without running ArangoDB

A small tool that syntax-checks every AQL query in this repo using **ArangoDB's own grammar**:

1. `fetch.sh` downloads `grammar.y`, `tokens.ll` and `AqlFunctionFeature.cpp` from a pinned ArangoDB release (default `v3.12.12`; override with `ARANGO_TAG`).
2. `build.py` strips the C++ semantic actions from the bison grammar, keeps the tokens, precedence and rules, and compiles a tiny parser (`bison` + a C compiler). It also extracts the list of AQL function names.
3. `aqlcheck.py` is a Python port of the lexer that feeds tokens to that parser through `ctypes`.
4. `check_repo.py` scans the fenced `aql` code blocks in `README.md` and `book/*.md`, `code/*.py` (AQL constants and literal `kdb.aql(...)` calls) and `code/data/benchmark.csv`.

```bash
sh tools/aql-lint/fetch.sh
python tools/aql-lint/build.py
python tools/aql-lint/check_repo.py      # -> "122 AQL queries checked, 0 problems"
```

**What it catches:** syntax errors (missing `RETURN`, a misplaced `LIMIT`, unbalanced brackets, wrong `COLLECT` forms, …) and unknown function names.
**What it doesn't:** whether collections and attributes exist, bind-parameter values, or semantic rules such as "don't read a collection after writing it". `code/selftest.py` covers those against a real server.

The downloaded ArangoDB sources (BUSL-1.1) go into `vendor/` and the generated parser into `build/`. Both are git-ignored and never committed.
