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

test -s preview.html
test -s preview.png
test -f dist/cage/manifest.json
test -f dist/cage/otoe-run.py

echo "wheel smoke: ok"
