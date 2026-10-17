#!/usr/bin/env sh
# Download the AQL grammar, lexer and function registry of a pinned ArangoDB release.
# These files are ArangoDB source code (BUSL-1.1); they are fetched, not redistributed.
set -eu
TAG="${ARANGO_TAG:-v3.12.12}"
BASE="https://raw.githubusercontent.com/arangodb/arangodb/${TAG}/arangod/Aql"
DIR="$(cd "$(dirname "$0")" && pwd)/vendor"
mkdir -p "$DIR"
curl -fsSL -o "$DIR/grammar.y" "$BASE/Parser/grammar.y"
curl -fsSL -o "$DIR/tokens.ll" "$BASE/Parser/tokens.ll"
curl -fsSL -o "$DIR/AqlFunctionFeature.cpp" "$BASE/AqlFunctionFeature.cpp"
echo "fetched ArangoDB $TAG AQL sources into $DIR"
