#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ -n "${PYTHON:-}" ]]; then
  PYTHON_BIN="$PYTHON"
elif [[ -x "$ROOT/.venv/bin/python" ]]; then
  PYTHON_BIN="$ROOT/.venv/bin/python"
else
  PYTHON_BIN="python3"
fi
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
    echo "wheel smoke: refusing to delete empty $label" >&2
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
    echo "wheel smoke: refusing to delete unsafe $label: $path" >&2
    exit 1
  fi
  if [[ -n "$home_path" && "$abs_path" == "$home_path" ]]; then
    echo "wheel smoke: refusing to delete home directory as $label: $path" >&2
    exit 1
  fi
  if ((depth < 2)) || [[ "${abs_path##*/}" == "tmp" ]]; then
    echo "wheel smoke: refusing to delete too-broad $label: $path" >&2
    exit 1
  fi
}

ROOT_ABS="$(resolve_path "$ROOT")"
INPUT="${1:-}"
WHEEL=""
if [[ -n "$INPUT" && "$INPUT" == *.whl ]]; then
  if [[ ! -f "$INPUT" ]]; then
    echo "wheel smoke: wheel does not exist: $INPUT" >&2
    exit 1
  fi
  WHEEL="$(resolve_path "$INPUT")"
  WHEELHOUSE=""
else
  WHEELHOUSE="${INPUT:-"$ROOT/dist-wheel-smoke"}"
fi
WORKDIR="${OTOE_SMOKE_WORKDIR:-"$(mktemp -d)"}"
BUILD_ARGS=()
if [[ "${OTOE_SMOKE_NO_BUILD_ISOLATION:-0}" == "1" ]]; then
  BUILD_ARGS+=(--no-build-isolation)
  "$PYTHON_BIN" - <<'PY'
from importlib.metadata import PackageNotFoundError, version
import re
import sys


def version_tuple(distribution: str) -> tuple[int, ...]:
    try:
        raw = version(distribution)
    except PackageNotFoundError:
        print(
            f"wheel smoke: --no-build-isolation requires {distribution} to be installed.",
            file=sys.stderr,
        )
        raise SystemExit(1)
    parts = tuple(int(part) for part in re.findall(r"\d+", raw)[:3])
    return parts or (0,)


requirements = {
    "packaging": (26, 2),
    "setuptools": (77,),
    "wheel": (0, 43),
}
for distribution, minimum in requirements.items():
    current = version_tuple(distribution)
    if current < minimum:
        floor = ".".join(str(part) for part in minimum)
        installed = ".".join(str(part) for part in current)
        print(
            "wheel smoke: --no-build-isolation requires "
            f"{distribution}>={floor}; found {installed}.",
            file=sys.stderr,
        )
        raise SystemExit(1)
PY
fi

if [[ -z "$WHEEL" ]]; then
  # A wheelhouse argument is destructive: this directory is deleted before rebuilding.
  refuse_unsafe_rm_rf "wheelhouse" "$WHEELHOUSE"
  WHEELHOUSE_ABS="$(resolve_path "$WHEELHOUSE")"
  if [[ "$WHEELHOUSE_ABS" == "$ROOT_ABS"/* && "$WHEELHOUSE_ABS" != "$ROOT_ABS/dist-wheel-smoke" ]]; then
    echo "wheel smoke: refusing to delete wheelhouse inside repo: $WHEELHOUSE" >&2
    exit 1
  fi
  rm -rf -- "$WHEELHOUSE"
  mkdir -p "$WHEELHOUSE"

  "$PYTHON_BIN" -m pip wheel "$ROOT" --no-deps "${BUILD_ARGS[@]}" -w "$WHEELHOUSE"
  WHEEL="$(find "$WHEELHOUSE" -maxdepth 1 -name 'otoe-*.whl' -print | sort | tail -n 1)"
  if [[ -z "$WHEEL" ]]; then
    echo "wheel smoke: no otoe wheel produced in $WHEELHOUSE" >&2
    exit 1
  fi
fi

PYTHON="$PYTHON_BIN" \
  OTOE_COLD_START_WORKDIR="$WORKDIR" \
  "$ROOT/scripts/cold_start_smoke.sh" "$WHEEL"

echo "wheel smoke: ok"
