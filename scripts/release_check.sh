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
    echo "release check: refusing to delete empty $label" >&2
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
    echo "release check: refusing to delete unsafe $label: $path" >&2
    exit 1
  fi
  if [[ -n "$home_path" && "$abs_path" == "$home_path" ]]; then
    echo "release check: refusing to delete home directory as $label: $path" >&2
    exit 1
  fi
  if ((depth < 2)) || [[ "${abs_path##*/}" == "tmp" ]]; then
    echo "release check: refusing to delete too-broad $label: $path" >&2
    exit 1
  fi
}

refuse_unexpected_release_cleanup_target() {
  local path="$1"
  local abs_path

  refuse_unsafe_rm_rf "cleanup target" "$path"
  abs_path="$(resolve_path "$path")"
  case "$abs_path" in
    "$ROOT_ABS/build"|"$ROOT_ABS/dist"|"$ROOT_ABS/dist-wheel-smoke"|"$ROOT_ABS"/src/*.egg-info|"$ROOT_ABS"/*.egg-info)
      ;;
    *)
      echo "release check: refusing to delete unexpected cleanup target: $path" >&2
      exit 1
      ;;
  esac
}

require_frozen_source_tree() {
  local current_commit
  local source_status

  if ! current_commit="$(git -C "$ROOT" rev-parse --verify HEAD 2>/dev/null)"; then
    echo "release check: source checkout must have a committed HEAD" >&2
    exit 1
  fi
  if [[ -n "${SOURCE_COMMIT:-}" && "$current_commit" != "$SOURCE_COMMIT" ]]; then
    echo "release check: HEAD changed during the release check" >&2
    exit 1
  fi
  source_status="$(git -C "$ROOT" status --porcelain=v1 --untracked-files=all)"
  if [[ -n "$source_status" ]]; then
    echo "release check: source working tree and index must be clean" >&2
    printf '%s\n' "$source_status" >&2
    exit 1
  fi
}

ROOT_ABS="$(resolve_path "$ROOT")"

cd "$ROOT"
SOURCE_COMMIT="$(git rev-parse --verify HEAD)"
SOURCE_DATE_EPOCH="$(git show -s --format=%ct "$SOURCE_COMMIT")"
export SOURCE_DATE_EPOCH
require_frozen_source_tree

# Release cleanup is destructive and is limited to known generated artifacts.
cleanup_paths=("$ROOT/build" "$ROOT/dist" "$ROOT/dist-wheel-smoke")
shopt -s nullglob
cleanup_paths+=("$ROOT"/src/*.egg-info "$ROOT"/*.egg-info)
shopt -u nullglob
for cleanup_path in "${cleanup_paths[@]}"; do
  refuse_unexpected_release_cleanup_target "$cleanup_path"
done
rm -rf -- "${cleanup_paths[@]}"

"$PYTHON_BIN" -m pip install \
  --constraint "$ROOT/requirements/ci-constraints.txt" \
  build markdown-it-py packaging setuptools twine wheel
"$PYTHON_BIN" -m pip install \
  --no-build-isolation \
  --constraint "$ROOT/requirements/ci-constraints.txt" \
  -e ".[dev,native-text]"
"$PYTHON_BIN" -m pip check
"$PYTHON_BIN" scripts/update_portable_core_docs.py --check
"$PYTHON_BIN" -m compileall -q src examples tests
"$PYTHON_BIN" -m ruff check src tests examples scripts
"$PYTHON_BIN" -m mypy --strict src/otoe
"$PYTHON_BIN" -m mypy --strict \
  scripts/cold_start_evidence.py \
  scripts/runtime_soak.py \
  scripts/verify_release_artifacts.py \
  scripts/verify_release_checks.py
"$PYTHON_BIN" -m mypy.stubtest otoe --allowlist tests/stubtest_allowlist.txt
"$PYTHON_BIN" -m pytest -q --cov=otoe --cov-report=term-missing --cov-fail-under=82
require_frozen_source_tree
"$PYTHON_BIN" -m build --no-isolation
"$PYTHON_BIN" scripts/normalize_sdist.py --epoch "$SOURCE_DATE_EPOCH" dist/*.tar.gz
"$PYTHON_BIN" -I scripts/verify_release_artifacts.py \
  --dist-dir dist \
  --project pyproject.toml
"$PYTHON_BIN" -m twine check dist/*.whl dist/*.tar.gz
bash "$ROOT/scripts/sdist_smoke.sh" "$(find dist -maxdepth 1 -name 'otoe-*.tar.gz' -print -quit)"
bash "$ROOT/scripts/wheel_smoke.sh" "$(find dist -maxdepth 1 -name 'otoe-*.whl' -print -quit)"
PYTHON="$PYTHON_BIN" "$ROOT/scripts/reproducible_build_check.sh" "$ROOT/dist"
"$PYTHON_BIN" scripts/bench_smoke.py --check
require_frozen_source_tree

echo "release check: ok"
