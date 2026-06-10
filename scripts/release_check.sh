#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON:-python}"

cd "$ROOT"

rm -rf build dist dist-wheel-smoke src/*.egg-info ./*.egg-info

"$PYTHON_BIN" -m pip install -e ".[dev,release,native-text]" "setuptools>=68" wheel
"$PYTHON_BIN" -m compileall -q src examples tests
"$PYTHON_BIN" -m pytest -q
"$PYTHON_BIN" -m build
"$PYTHON_BIN" -m twine check dist/*
OTOE_SMOKE_NO_BUILD_ISOLATION=1 "$ROOT/scripts/wheel_smoke.sh" "$ROOT/dist-wheel-smoke"

echo "release check: ok"
