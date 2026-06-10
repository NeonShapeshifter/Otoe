#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ -n "${PYTHON:-}" ]]; then
  PYTHON_BIN="$PYTHON"
elif [[ -x "$ROOT/.venv/bin/python" ]]; then
  PYTHON_BIN="$ROOT/.venv/bin/python"
else
  PYTHON_BIN="python"
fi
WHEELHOUSE="${1:-"$ROOT/dist-wheel-smoke"}"
WORKDIR="${OTOE_SMOKE_WORKDIR:-"$(mktemp -d)"}"
BUILD_ARGS=()
if [[ "${OTOE_SMOKE_NO_BUILD_ISOLATION:-0}" == "1" ]]; then
  BUILD_ARGS+=(--no-build-isolation)
fi

rm -rf "$WHEELHOUSE"
mkdir -p "$WHEELHOUSE"

"$PYTHON_BIN" -m pip wheel "$ROOT" --no-deps "${BUILD_ARGS[@]}" -w "$WHEELHOUSE"
WHEEL="$(find "$WHEELHOUSE" -maxdepth 1 -name 'otoe-*.whl' -print | sort | tail -n 1)"
if [[ -z "$WHEEL" ]]; then
  echo "wheel smoke: no otoe wheel produced in $WHEELHOUSE" >&2
  exit 1
fi

"$PYTHON_BIN" -m venv "$WORKDIR/venv"
"$WORKDIR/venv/bin/python" -m pip install "$WHEEL"
"$WORKDIR/venv/bin/otoe" new "$WORKDIR/app"

cd "$WORKDIR/app"
"$WORKDIR/venv/bin/otoe" render app:app --out preview.html --css styles.css --pretty
"$WORKDIR/venv/bin/otoe" render app:app --out preview.png --native --css styles.css
"$WORKDIR/venv/bin/otoe" build app:app --out dist/cage --css styles.css --validate
"$WORKDIR/venv/bin/otoe" portable-core > portable-core.txt
"$WORKDIR/venv/bin/otoe" portable-core --json > portable-core.json

test -s preview.html
test -s preview.png
test -f dist/cage/manifest.json
test -f dist/cage/otoe-run.py
test -s portable-core.txt
test -s portable-core.json
"$WORKDIR/venv/bin/python" -c 'from pathlib import Path; import sys; text = Path(sys.argv[1]).read_text(encoding="utf-8"); assert "Portable Core UI v0" in text and "`Button`" in text' portable-core.txt
"$WORKDIR/venv/bin/python" -c 'import json, sys; payload = json.load(open(sys.argv[1], encoding="utf-8")); assert payload["format"] == "otoe-portable-core-ui-v0"; assert any(entry["id"] == "button" for entry in payload["entries"])' portable-core.json

echo "wheel smoke: ok"
