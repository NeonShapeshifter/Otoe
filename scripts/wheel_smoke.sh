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
"$WORKDIR/venv/bin/otoe" check --tests > check.txt
"$WORKDIR/venv/bin/otoe" build app:app --out dist/cage --css styles.css --validate
"$WORKDIR/venv/bin/otoe" portable-core > portable-core.txt
"$WORKDIR/venv/bin/otoe" portable-core --json > portable-core.json
"$WORKDIR/venv/bin/otoe" portable-core --format json > portable-core-format.json

DEV_PORT="$("$WORKDIR/venv/bin/python" -c 'import socket; sock = socket.socket(); sock.bind(("127.0.0.1", 0)); print(sock.getsockname()[1]); sock.close()')"
"$WORKDIR/venv/bin/otoe" dev app:app --css styles.css --port "$DEV_PORT" > dev.log 2>&1 &
DEV_PID="$!"
trap 'kill "$DEV_PID" 2>/dev/null || true' EXIT
DEV_READY=0
for _ in $(seq 1 50); do
  if "$WORKDIR/venv/bin/python" -c 'import json, sys, urllib.request; payload = json.load(urllib.request.urlopen(f"http://127.0.0.1:{sys.argv[1]}/health", timeout=0.2)); assert payload["ok"] is True' "$DEV_PORT" >/dev/null 2>&1; then
    DEV_READY=1
    break
  fi
  sleep 0.1
done
if [[ "$DEV_READY" != "1" ]]; then
  cat dev.log >&2
  kill "$DEV_PID" 2>/dev/null || true
  exit 1
fi
"$WORKDIR/venv/bin/python" -c 'import sys, urllib.request; html = urllib.request.urlopen(f"http://127.0.0.1:{sys.argv[1]}/", timeout=1).read().decode(); assert "Count: 0" in html and "Increment" in html' "$DEV_PORT"
kill "$DEV_PID"
wait "$DEV_PID" 2>/dev/null || true
trap - EXIT

test -s preview.html
test -s preview.png
test -s check.txt
test -f dist/cage/manifest.json
test -f dist/cage/otoe-run.py
test -s portable-core.txt
test -s portable-core.json
test -s portable-core-format.json
"$WORKDIR/venv/bin/python" -c 'from pathlib import Path; import sys; text = Path(sys.argv[1]).read_text(encoding="utf-8"); assert "Portable Core UI v0" in text and "`Button`" in text' portable-core.txt
"$WORKDIR/venv/bin/python" -c 'import json, sys; payload = json.load(open(sys.argv[1], encoding="utf-8")); assert payload["format"] == "otoe-portable-core-ui-v0"; assert any(entry["id"] == "button" for entry in payload["entries"])' portable-core.json
"$WORKDIR/venv/bin/python" -c 'import json, sys; payload = json.load(open(sys.argv[1], encoding="utf-8")); assert payload["format"] == "otoe-portable-core-ui-v0"; assert any(entry["id"] == "button" for entry in payload["entries"])' portable-core-format.json
"$WORKDIR/venv/bin/python" -c 'from pathlib import Path; text = Path("check.txt").read_text(encoding="utf-8"); assert "compile app.py: ok" in text and "pytest: skipped (tests directory missing)" in text'

echo "wheel smoke: ok"
