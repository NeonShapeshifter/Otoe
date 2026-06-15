#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON:-python3}"
if [[ "$PYTHON_BIN" == */* && "$PYTHON_BIN" != /* ]]; then
  PYTHON_BIN="$(pwd)/$PYTHON_BIN"
fi

cd "$ROOT"

rm -rf build dist dist-wheel-smoke src/*.egg-info ./*.egg-info

"$PYTHON_BIN" -m pip install -e ".[dev,release,native-text]" "setuptools>=68" wheel
"$PYTHON_BIN" scripts/update_portable_core_docs.py --check
"$PYTHON_BIN" -m compileall -q src examples tests
"$PYTHON_BIN" -m ruff check src tests examples scripts
"$PYTHON_BIN" -m mypy src/otoe
"$PYTHON_BIN" -m pytest -q
"$PYTHON_BIN" -m build
"$PYTHON_BIN" -m twine check dist/*.whl dist/*.tar.gz
bash "$ROOT/scripts/sdist_smoke.sh"
OTOE_SMOKE_NO_BUILD_ISOLATION=1 "$ROOT/scripts/wheel_smoke.sh" "$ROOT/dist-wheel-smoke"

echo "release check: ok"
