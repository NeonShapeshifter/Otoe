#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON:-python3}"
if [[ "$PYTHON_BIN" == */* && "$PYTHON_BIN" != /* ]]; then
  PYTHON_BIN="$(pwd)/$PYTHON_BIN"
fi

resolve_path() {
  "$PYTHON_BIN" - "$1" <<'PY'
from pathlib import Path
import sys

print(Path(sys.argv[1]).expanduser().resolve(strict=False))
PY
}

refuse_unsafe_rm_rf() {
  local label="$1"
  local path="${2:-}"
  local abs_path
  local current_path
  local home_path=""
  local part
  local depth=0
  local -a path_parts

  if [[ -z "$path" ]]; then
    echo "sdist smoke: refusing to delete empty $label" >&2
    exit 1
  fi

  abs_path="$(resolve_path "$path")"
  current_path="$(resolve_path "$PWD")"
  if [[ -n "${HOME:-}" ]]; then
    home_path="$(resolve_path "$HOME")"
  fi

  IFS='/' read -r -a path_parts <<< "${abs_path#/}"
  for part in "${path_parts[@]}"; do
    if [[ -n "$part" ]]; then
      depth=$((depth + 1))
    fi
  done

  if [[ "$abs_path" == "/" || "$abs_path" == "$current_path" || "$abs_path" == "$ROOT_ABS" ]]; then
    echo "sdist smoke: refusing to delete unsafe $label: $path" >&2
    exit 1
  fi
  if [[ -n "$home_path" && "$abs_path" == "$home_path" ]]; then
    echo "sdist smoke: refusing to delete home directory as $label: $path" >&2
    exit 1
  fi
  if ((depth < 2)) || [[ "${abs_path##*/}" == "tmp" ]]; then
    echo "sdist smoke: refusing to delete too-broad $label: $path" >&2
    exit 1
  fi
}

ROOT_ABS="$(resolve_path "$ROOT")"
SDIST="${1:-}"
WORKDIR="${OTOE_SDIST_SMOKE_WORKDIR:-"$(mktemp -d)"}"

if [[ -z "$SDIST" ]]; then
  SDIST="$(find "$ROOT/dist" -maxdepth 1 -name 'otoe-*.tar.gz' -print | sort | tail -n 1)"
fi
if [[ -z "$SDIST" || ! -f "$SDIST" ]]; then
  echo "sdist smoke: no otoe sdist found" >&2
  exit 1
fi

# OTOE_SDIST_SMOKE_WORKDIR is destructive: this directory is deleted before extraction.
refuse_unsafe_rm_rf "workdir" "$WORKDIR"
WORKDIR_ABS="$(resolve_path "$WORKDIR")"
if [[ "$WORKDIR_ABS" == "$ROOT_ABS"/* ]]; then
  echo "sdist smoke: refusing to delete workdir inside repo: $WORKDIR" >&2
  exit 1
fi
rm -rf -- "$WORKDIR"
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
  tests/test_cli_dev_new_portable.py::test_cli_portable_core_accepts_format_json_alias
PYTHONPATH=src:. "$PYTHON_BIN" -m otoe portable-core --format json > portable-core.json
test -s portable-core.json

echo "sdist smoke: ok"
