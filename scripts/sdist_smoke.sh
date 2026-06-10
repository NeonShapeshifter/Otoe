#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON:-python}"
SDIST="${1:-}"
WORKDIR="${OTOE_SDIST_SMOKE_WORKDIR:-"$(mktemp -d)"}"

if [[ -z "$SDIST" ]]; then
  SDIST="$(find "$ROOT/dist" -maxdepth 1 -name 'otoe-*.tar.gz' -print | sort | tail -n 1)"
fi
if [[ -z "$SDIST" || ! -f "$SDIST" ]]; then
  echo "sdist smoke: no otoe sdist found" >&2
  exit 1
fi

rm -rf "$WORKDIR"
mkdir -p "$WORKDIR"
tar -xzf "$SDIST" -C "$WORKDIR"
SOURCE_DIR="$(find "$WORKDIR" -mindepth 1 -maxdepth 1 -type d -name 'otoe-*' -print | sort | tail -n 1)"
if [[ -z "$SOURCE_DIR" || ! -d "$SOURCE_DIR" ]]; then
  echo "sdist smoke: could not find extracted otoe source directory" >&2
  exit 1
fi

test -d "$SOURCE_DIR/src/otoe"
test -d "$SOURCE_DIR/tests"
test -d "$SOURCE_DIR/examples"
test -d "$SOURCE_DIR/docs"
test -f "$SOURCE_DIR/MANIFEST.in"

cd "$SOURCE_DIR"
"$PYTHON_BIN" -m compileall -q src examples tests
PYTHONPATH=src:. "$PYTHON_BIN" -m pytest -q \
  tests/test_html.py \
  tests/test_backend_package.py::test_backend_package_manifest_describes_path0_external_backend \
  tests/test_cli.py::test_cli_portable_core_accepts_format_json_alias
PYTHONPATH=src:. "$PYTHON_BIN" -m otoe portable-core --format json > portable-core.json
test -s portable-core.json

echo "sdist smoke: ok"
