#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON:-python3}"
SOURCE_DATE_EPOCH="${SOURCE_DATE_EPOCH:-$(git -C "$ROOT" show -s --format=%ct HEAD)}"
REFERENCE_DIR="${1:-}"
WORKDIR="$(mktemp -d)"
trap 'rm -rf -- "$WORKDIR"' EXIT

mkdir -p "$WORKDIR/first" "$WORKDIR/second"

build_once() {
  local output="$1"
  SOURCE_DATE_EPOCH="$SOURCE_DATE_EPOCH" \
    "$PYTHON_BIN" -m build --no-isolation --outdir "$output" "$ROOT" >/dev/null
  SOURCE_DATE_EPOCH="$SOURCE_DATE_EPOCH" \
    "$PYTHON_BIN" "$ROOT/scripts/normalize_sdist.py" --epoch "$SOURCE_DATE_EPOCH" \
    "$output"/otoe-*.tar.gz
}

build_once "$WORKDIR/first"
build_once "$WORKDIR/second"

compare_distribution_sets() {
  local expected_dir="$1"
  local actual_dir="$2"
  local name
  local -a expected_names
  local -a actual_names

  mapfile -t expected_names < <(
    find "$expected_dir" -maxdepth 1 -type f \
      \( -name 'otoe-*.whl' -o -name 'otoe-*.tar.gz' \) \
      -printf '%f\n' | LC_ALL=C sort
  )
  mapfile -t actual_names < <(
    find "$actual_dir" -maxdepth 1 -type f \
      \( -name 'otoe-*.whl' -o -name 'otoe-*.tar.gz' \) \
      -printf '%f\n' | LC_ALL=C sort
  )

  if [[ "${#expected_names[@]}" != "2" ]]; then
    echo "reproducible build check: expected one wheel and one sdist in $expected_dir" >&2
    exit 1
  fi
  if [[ "${expected_names[*]}" != "${actual_names[*]}" ]]; then
    echo "reproducible build check: distribution sets differ" >&2
    printf 'expected: %s\n' "${expected_names[*]}" >&2
    printf 'actual:   %s\n' "${actual_names[*]}" >&2
    exit 1
  fi

  for name in "${expected_names[@]}"; do
    cmp -- "$expected_dir/$name" "$actual_dir/$name"
  done
}

compare_distribution_sets "$WORKDIR/first" "$WORKDIR/second"
if [[ -n "$REFERENCE_DIR" ]]; then
  if [[ ! -d "$REFERENCE_DIR" ]]; then
    echo "reproducible build check: reference directory does not exist: $REFERENCE_DIR" >&2
    exit 1
  fi
  compare_distribution_sets "$REFERENCE_DIR" "$WORKDIR/first"
fi

echo "reproducible build check: ok"
