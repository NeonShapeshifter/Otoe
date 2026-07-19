#!/usr/bin/env bash
set -euo pipefail

SCRIPT_SOURCE="${BASH_SOURCE[0]}"
SCRIPT_DIR="."
if [[ "$SCRIPT_SOURCE" == */* ]]; then
  SCRIPT_DIR="${SCRIPT_SOURCE%/*}"
fi
ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd -P)"
SCRIPT="$ROOT/scripts/cold_start_smoke.sh"
EVIDENCE_HELPER="$ROOT/scripts/cold_start_evidence.py"
FLOW_BUDGET_SECONDS=300
WATCHDOG_BUDGET_SECONDS="$FLOW_BUDGET_SECONDS"
LOG_CAPTURE_GRACE_SECONDS=7
LOG_CAPTURE_LIMIT_BYTES=1048576
TRUSTED_PATH="/usr/bin:/bin"
WORKER_DEV_PID=""
WORKER_TEST_PID=""

select_trusted_binary() {
  local label="$1"
  shift
  local candidate
  for candidate in "$@"; do
    if [[ -f "$candidate" && -x "$candidate" ]]; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done
  printf 'cold-start smoke: required system utility is unavailable: %s\n' "$label" >&2
  return 2
}

BASH_BIN="$(select_trusted_binary bash /bin/bash /usr/bin/bash)"
CAT_BIN="$(select_trusted_binary cat /usr/bin/cat /bin/cat)"
CHMOD_BIN="$(select_trusted_binary chmod /usr/bin/chmod /bin/chmod)"
ENV_BIN="$(select_trusted_binary env /usr/bin/env /bin/env)"
FIND_BIN="$(select_trusted_binary find /usr/bin/find /bin/find)"
MKDIR_BIN="$(select_trusted_binary mkdir /usr/bin/mkdir /bin/mkdir)"
MKTEMP_BIN="$(select_trusted_binary mktemp /usr/bin/mktemp /bin/mktemp)"
TIMEOUT_BIN="$(select_trusted_binary timeout /usr/bin/timeout /bin/timeout)"
TOUCH_BIN="$(select_trusted_binary touch /usr/bin/touch /bin/touch)"

resolve_python_command() {
  local requested="$1"
  local candidate=""
  local directory
  if [[ "$requested" == /* ]]; then
    candidate="$requested"
  elif [[ "$requested" == */* ]]; then
    directory="${requested%/*}"
    candidate="$(cd -- "$directory" && pwd -P)/${requested##*/}"
  else
    candidate="$(PATH="${PATH:-$TRUSTED_PATH}" builtin type -P -- "$requested" || true)"
  fi
  if [[ -z "$candidate" || ! -f "$candidate" || ! -x "$candidate" ]]; then
    printf 'cold-start smoke: Python executable is unavailable: %s\n' "$requested" >&2
    return 2
  fi
  # Preserve a virtual-environment launcher path; resolving its symlink would
  # silently switch dependency lookup back to the base interpreter.
  "$candidate" -I -c 'import os, sys; print(os.path.abspath(sys.executable))'
}

PYTHON_REQUESTED="${PYTHON:-python3}"
if [[ "${1:-}" == "--worker" && -n "${5:-}" ]]; then
  PYTHON_REQUESTED="$5"
elif [[ -z "${PYTHON:-}" && -x "$ROOT/.venv/bin/python" ]]; then
  PYTHON_REQUESTED="$ROOT/.venv/bin/python"
fi
PYTHON_ABS="$(resolve_python_command "$PYTHON_REQUESTED")"

resolve_path() {
  "$PYTHON_ABS" -I - "$1" <<'PY'
from pathlib import Path
import sys

print(Path(sys.argv[1]).expanduser().resolve(strict=False))
PY
}

run_clean() {
  local clean_home="$1"
  shift
  "$ENV_BIN" -i \
    PATH="${PATH:-/usr/bin:/bin}" \
    HOME="$clean_home" \
    XDG_CACHE_HOME="$clean_home/.cache" \
    XDG_CONFIG_HOME="$clean_home/.config" \
    PYTHONNOUSERSITE=1 \
    PIP_CONFIG_FILE=/dev/null \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_INDEX=1 \
    "$@"
}

configure_test_watchdog() {
  local hook="${OTOE_COLD_START_TEST_HOOK:-}"
  local test_budget="${OTOE_COLD_START_TEST_BUDGET_SECONDS:-}"
  if [[ -z "$hook" && -z "$test_budget" ]]; then
    return
  fi
  case "$hook" in
    flood-worker-output-v1|hang-worker-v1|hang-ignore-term-v1) ;;
    *)
      echo "cold-start smoke: invalid test-only watchdog hook" >&2
      return 2
      ;;
  esac
  if [[ ! "$test_budget" =~ ^[1-5]$ ]]; then
    echo "cold-start smoke: test-only watchdog budget must be 1-5 seconds" >&2
    return 2
  fi
  # Every supported hook fails or hangs, so shortening this watchdog can never
  # turn an incomplete release check into passing evidence.
  WATCHDOG_BUDGET_SECONDS="$test_budget"
}

run_worker() {
  local root_abs="$1"
  local wheel="$2"
  local workdir="$3"
  local python_bin="$4"
  local expected_sha256="$5"
  local clean_home="$workdir/home"
  local venv="$workdir/venv"
  local app_dir="$workdir/app"
  local artifact_dir="$workdir/artifact"
  local progress="$workdir/progress"
  local artifact="$artifact_dir/${wheel##*/}"

  cleanup_dev() {
    if [[ -n "$WORKER_DEV_PID" ]]; then
      kill "$WORKER_DEV_PID" 2>/dev/null || true
      wait "$WORKER_DEV_PID" 2>/dev/null || true
      WORKER_DEV_PID=""
    fi
  }
  cleanup_test_child() {
    if [[ -n "$WORKER_TEST_PID" ]]; then
      kill -KILL "$WORKER_TEST_PID" 2>/dev/null || true
      wait "$WORKER_TEST_PID" 2>/dev/null || true
      WORKER_TEST_PID=""
    fi
  }
  cleanup_worker_children() {
    cleanup_dev
    cleanup_test_child
  }
  trap cleanup_worker_children EXIT
  trap 'exit 143' INT TERM
  trap 'echo "cold-start worker: failed at line $LINENO" >&2' ERR

  umask 077
  mkdir -p "$clean_home" "$artifact_dir" "$progress"
  cp -- "$wheel" "$artifact"
  cmp -s -- "$wheel" "$artifact"
  "$CHMOD_BIN" 0400 "$artifact"
  "$CHMOD_BIN" 0500 "$artifact_dir"
  touch "$progress/artifact-copied"
  "$python_bin" -I "$EVIDENCE_HELPER" inspect \
    "$artifact" "$workdir/wheel-identity.json" \
    --expected-sha256 "$expected_sha256"
  touch "$progress/package-readme-commands"

  if [[ -n "${OTOE_COLD_START_TEST_HOOK:-}" ]]; then
    "$python_bin" -I - "$workdir/test-worker-environment.json" <<'PY'
import json
import os
from pathlib import Path
import sys

Path(sys.argv[1]).write_text(
    json.dumps(dict(os.environ), indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
PY
    run_clean "$clean_home" "$python_bin" -I - \
      "$workdir/test-clean-environment.json" <<'PY'
import json
import os
from pathlib import Path
import sys

observed = {
    key: value
    for key, value in os.environ.items()
    if key == "BASH_ENV" or key.startswith("PIP_")
}
Path(sys.argv[1]).write_text(
    json.dumps(observed, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
PY
  fi

  if [[ "${OTOE_COLD_START_TEST_HOOK:-}" == "hang-worker-v1" ]]; then
    sleep "$((FLOW_BUDGET_SECONDS + 60))" &
    WORKER_TEST_PID="$!"
    printf '%s\n' "$WORKER_TEST_PID" > "$workdir/test-hung-child.pid"
    wait "$WORKER_TEST_PID"
  fi

  if [[ "${OTOE_COLD_START_TEST_HOOK:-}" == "hang-ignore-term-v1" ]]; then
    "$python_bin" -I - "$workdir/test-hung-child-ready" <<'PY' &
from pathlib import Path
import signal
import sys
import time

signal.signal(signal.SIGINT, signal.SIG_IGN)
signal.signal(signal.SIGTERM, signal.SIG_IGN)
Path(sys.argv[1]).touch()
while True:
    time.sleep(60)
PY
    WORKER_TEST_PID="$!"
    printf '%s\n' "$WORKER_TEST_PID" > "$workdir/test-hung-child.pid"
    for _ in {1..100}; do
      if [[ -f "$workdir/test-hung-child-ready" ]]; then
        break
      fi
      sleep 0.01
    done
    if [[ ! -f "$workdir/test-hung-child-ready" ]]; then
      echo "cold-start worker: test-only TERM-resistant child did not start" >&2
      return 1
    fi
    trap '' INT TERM
    wait "$WORKER_TEST_PID"
  fi

  if [[ "${OTOE_COLD_START_TEST_HOOK:-}" == "flood-worker-output-v1" ]]; then
    "$python_bin" -I - <<'PY'
import os

chunk = b"hostile-output\n" * 4096
for descriptor in (1, 2):
    remaining = 2 * 1024 * 1024
    while remaining > 0:
        written = os.write(descriptor, chunk[:remaining])
        remaining -= written
raise SystemExit(97)
PY
  fi

  "$python_bin" -I -m venv "$venv"
  touch "$progress/clean-venv"
  "$python_bin" -I "$EVIDENCE_HELPER" verify-sha256 \
    "$artifact" "$expected_sha256"
  touch "$progress/wheel-preinstall-digest"
  run_clean "$clean_home" "$venv/bin/python" -m pip install \
    --no-cache-dir \
    --no-deps \
    --no-index \
    "$artifact"
  "$python_bin" -I "$EVIDENCE_HELPER" verify-sha256 \
    "$artifact" "$expected_sha256"
  touch "$progress/wheel-postinstall-digest"
  touch "$progress/install-no-deps" "$progress/install-no-index"
  run_clean "$clean_home" "$venv/bin/python" -m pip check

  run_clean "$clean_home" "$venv/bin/python" -I - \
    "$root_abs" \
    "$venv" \
    "$workdir/import-probe.json" \
    "$workdir/wheel-identity.json" <<'PY'
from importlib.metadata import version
import json
from pathlib import Path
import sys

import otoe

checkout = Path(sys.argv[1]).resolve()
venv = Path(sys.argv[2]).resolve()
output = Path(sys.argv[3])
wheel_identity = json.loads(Path(sys.argv[4]).read_text(encoding="utf-8"))
module_path = Path(otoe.__file__).resolve()
resolved_sys_path = [Path(entry).resolve() for entry in sys.path if entry]
installed_version = version("otoe")

if not module_path.is_relative_to(venv):
    raise SystemExit(f"otoe imported outside clean venv: {module_path}")
if module_path.is_relative_to(checkout):
    raise SystemExit(f"otoe imported from source checkout: {module_path}")
if any(path == checkout or path.is_relative_to(checkout) for path in resolved_sys_path):
    raise SystemExit(f"source checkout leaked onto sys.path: {resolved_sys_path}")
if installed_version != wheel_identity["version"]:
    raise SystemExit(
        "installed otoe version does not match validated wheel identity: "
        f"{installed_version!r} != {wheel_identity['version']!r}"
    )

output.write_text(
    json.dumps(
        {
            "module_path": str(module_path.relative_to(venv)),
            "source_checkout_on_sys_path": False,
            "version": installed_version,
            "wheel_metadata_version_match": True,
        },
        indent=2,
        sort_keys=True,
    )
    + "\n",
    encoding="utf-8",
)
PY
  touch "$progress/source-checkout-absent" "$progress/wheel-version-match"

  run_clean "$clean_home" "$venv/bin/otoe" new "$app_dir"
  cd "$app_dir"
  test -f app.py
  test -f README.md
  test -f styles.css
  run_clean "$clean_home" "$python_bin" -I "$EVIDENCE_HELPER" \
    inspect-generated-readme "$app_dir/README.md"
  touch "$progress/generated-readme-commands"

  run_clean "$clean_home" "$venv/bin/otoe" check > check.txt
  run_clean "$clean_home" "$venv/bin/otoe" check \
    --target app:app --css styles.css > doctor.txt
  touch "$progress/check"
  run_clean "$clean_home" "$venv/bin/otoe" render \
    app:app --out preview.html --css styles.css --pretty
  test -s preview.html
  touch "$progress/html-render"
  run_clean "$clean_home" "$venv/bin/otoe" render \
    app:app --out preview.png --native --css styles.css
  test -s preview.png
  touch "$progress/native-render"

  run_clean "$clean_home" "$venv/bin/otoe" dev \
    app:app --css styles.css --port 0 > dev.log 2>&1 &
  WORKER_DEV_PID="$!"
  local dev_port=""
  local dev_ready=0
  for _ in $(seq 1 100); do
    dev_port="$(sed -n 's#^Otoe dev: http://127\.0\.0\.1:\([0-9][0-9]*\)$#\1#p' dev.log | tail -n 1)"
    if [[ -n "$dev_port" && "$dev_port" != "0" ]]; then
      if run_clean "$clean_home" "$venv/bin/python" -I -c 'import json, sys, urllib.request; payload = json.load(urllib.request.urlopen(f"http://127.0.0.1:{sys.argv[1]}/health", timeout=0.2)); assert payload["ok"] is True' "$dev_port" >/dev/null 2>&1; then
        dev_ready=1
        break
      fi
    fi
    if ! kill -0 "$WORKER_DEV_PID" 2>/dev/null; then
      cat dev.log >&2
      echo "cold-start worker: otoe dev exited before becoming ready" >&2
      return 1
    fi
    sleep 0.1
  done
  if [[ "$dev_ready" != "1" ]]; then
    cat dev.log >&2
    echo "cold-start worker: otoe dev did not report a healthy bound port" >&2
    return 1
  fi
  run_clean "$clean_home" "$venv/bin/python" -I -c 'import sys, urllib.request; html = urllib.request.urlopen(f"http://127.0.0.1:{sys.argv[1]}/", timeout=1).read().decode(); assert "Count: 0" in html and "Increment" in html' "$dev_port"
  touch "$progress/dev-health"
  cleanup_dev

  run_clean "$clean_home" "$venv/bin/otoe" build \
    app:app --out dist/cage --css styles.css --validate
  test -f dist/cage/manifest.json
  test -f dist/cage/otoe-run.py
  touch "$progress/build-validated"

  run_clean "$clean_home" "$venv/bin/otoe" check --tests > check-tests.txt
  touch "$progress/check-tests"
  run_clean "$clean_home" "$venv/bin/otoe" portable-core > portable-core.txt
  run_clean "$clean_home" "$venv/bin/otoe" portable-core --json > portable-core.json
  run_clean "$clean_home" "$venv/bin/otoe" portable-core \
    --format json > portable-core-format.json
  run_clean "$clean_home" "$venv/bin/python" -I - <<'PY'
import json
from pathlib import Path

legacy = json.loads(Path("portable-core.json").read_text(encoding="utf-8"))
alias = json.loads(Path("portable-core-format.json").read_text(encoding="utf-8"))
if legacy != alias:
    raise SystemExit("portable-core JSON aliases differ structurally")
for name, payload in (("portable-core.canonical.json", legacy), ("portable-core-format.canonical.json", alias)):
    Path(name).write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True) + "\n",
        encoding="utf-8",
    )
PY
  cmp -s portable-core.canonical.json portable-core-format.canonical.json
  touch "$progress/portable-core-json-match"

  run_clean "$clean_home" "$venv/bin/python" -I - <<'PY'
from pathlib import Path
from otoe.style import css
import json

assert "Count: 0" in Path("preview.html").read_text(encoding="utf-8")
assert Path("preview.png").read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
assert "Portable Core UI v0" in Path("portable-core.txt").read_text(encoding="utf-8")
payload = json.loads(Path("portable-core.json").read_text(encoding="utf-8"))
assert payload["format"] == "otoe-portable-core-ui-v0"
assert any(entry["id"] == "button" for entry in payload["entries"])
assert set(css(Path("styles.css").read_text(encoding="utf-8")).rules) == {".app", ".title"}
assert "compile app.py: ok" in Path("check.txt").read_text(encoding="utf-8")
doctor = Path("doctor.txt").read_text(encoding="utf-8")
assert "compile app.py: ok" in doctor
assert "target app:app: ok" in doctor
assert "css styles.css: ok (2 rules)" in doctor
tests = Path("check-tests.txt").read_text(encoding="utf-8")
assert "compile app.py: ok" in tests
assert "pytest: skipped (tests directory missing)" in tests
PY
  touch "$progress/completed"
}

run_controller() {
  local input="${1:-}"
  if [[ -z "$input" ]]; then
    echo "cold-start smoke: pass the exact wheel artifact to test" >&2
    return 2
  fi
  if [[ "$input" != *.whl || ! -f "$input" ]]; then
    echo "cold-start smoke: wheel does not exist: $input" >&2
    return 2
  fi
  local timeout_version
  timeout_version="$("$TIMEOUT_BIN" --version 2>/dev/null || true)"
  if [[ "$timeout_version" != *"GNU coreutils"* ]]; then
    echo "cold-start smoke: GNU coreutils timeout is required" >&2
    return 2
  fi
  configure_test_watchdog
  if ! "$PYTHON_ABS" -I -c 'from importlib.metadata import version; from packaging.version import Version; requirements = {"markdown-it-py": "4.2", "packaging": "26.2"}; raise SystemExit(any(Version(version(name)) < Version(minimum) for name, minimum in requirements.items()))' >/dev/null 2>&1; then
    echo "cold-start smoke: markdown-it-py>=4.2 and packaging>=26.2 are required; install .[release]" >&2
    return 2
  fi

  local root_abs
  local wheel
  local workdir
  local workdir_abs
  local python_abs
  root_abs="$(resolve_path "$ROOT")"
  wheel="$(resolve_path "$input")"
  python_abs="$PYTHON_ABS"
  workdir="${OTOE_COLD_START_WORKDIR:-"$("$MKTEMP_BIN" -d)"}"
  if [[ -z "$workdir" ]]; then
    echo "cold-start smoke: refusing an empty workdir" >&2
    return 2
  fi
  workdir_abs="$(resolve_path "$workdir")"
  case "$workdir_abs" in
    "$root_abs"|"$root_abs"/*)
      echo "cold-start smoke: workdir must be outside the source checkout: $workdir" >&2
      return 2
      ;;
  esac
  if [[ -d "$workdir_abs" && -n "$("$FIND_BIN" "$workdir_abs" -mindepth 1 -maxdepth 1 -print -quit)" ]]; then
    echo "cold-start smoke: workdir must be empty: $workdir" >&2
    return 2
  fi
  if [[ -e "$workdir_abs" && ! -d "$workdir_abs" ]]; then
    echo "cold-start smoke: workdir is not a directory: $workdir" >&2
    return 2
  fi
  "$MKDIR_BIN" -p "$workdir_abs/progress"

  local started_ns
  local expected_sha256=""
  local digest_status
  local pre_worker_elapsed
  local remaining_watchdog_seconds
  local worker_status
  local failure_stage="worker"
  local log_capture_note=""
  local elapsed_seconds
  local deadline_reached
  local outcome
  local final_error="$workdir_abs/final-error.log"
  local -a worker_environment=(
    "PATH=$TRUSTED_PATH"
    "HOME=$workdir_abs/home"
  )
  if [[ -n "${OTOE_COLD_START_TEST_HOOK:-}" ]]; then
    worker_environment+=("OTOE_COLD_START_TEST_HOOK=$OTOE_COLD_START_TEST_HOOK")
  fi
  started_ns="$("$python_abs" -I -c 'import time; print(time.monotonic_ns())')"
  : > "$workdir_abs/worker.stdout.log"
  : > "$workdir_abs/worker.stderr.log"
  set +e
  expected_sha256="$(
    "$TIMEOUT_BIN" --signal=TERM --kill-after=5s "${WATCHDOG_BUDGET_SECONDS}s" \
      "$ENV_BIN" -i \
      PATH="$TRUSTED_PATH" \
      HOME="$workdir_abs/home" \
      "$python_abs" -I "$EVIDENCE_HELPER" sha256 "$wheel" \
      2> "$workdir_abs/worker.stderr.log"
  )"
  digest_status="$?"
  set -e
  if [[ "$digest_status" == "0" && ! "$expected_sha256" =~ ^[0-9a-f]{64}$ ]]; then
    digest_status=1
    expected_sha256=""
    printf 'cold-start controller produced an invalid source wheel digest\n' \
      > "$workdir_abs/worker.stderr.log"
  fi

  pre_worker_elapsed="$("$python_abs" -I - "$started_ns" <<'PY'
import sys
import time

print((time.monotonic_ns() - int(sys.argv[1])) / 1_000_000_000)
PY
)"
  remaining_watchdog_seconds="$("$python_abs" -I - \
    "$pre_worker_elapsed" "$WATCHDOG_BUDGET_SECONDS" <<'PY'
import sys

print(f"{max(0.0, float(sys.argv[2]) - float(sys.argv[1])):.6f}")
PY
)"

  if [[ "$digest_status" != "0" ]]; then
    worker_status="$digest_status"
    failure_stage="controller digest"
  elif [[ "$remaining_watchdog_seconds" == "0.000000" ]]; then
    worker_status=124
    failure_stage="controller digest"
  else
    local stdout_pipe="$workdir_abs/worker.stdout.pipe"
    local stderr_pipe="$workdir_abs/worker.stderr.pipe"
    local stdout_limit_marker="$workdir_abs/worker.stdout.limit"
    local stderr_limit_marker="$workdir_abs/worker.stderr.limit"
    local writer_ready_marker="$workdir_abs/worker.writer-ready"
    local stdout_capture_pid
    local stderr_capture_pid
    local stdout_capture_status
    local stderr_capture_status
    local stdout_guard_fd
    local stderr_guard_fd
    "$python_abs" -I - "$stdout_pipe" "$stderr_pipe" <<'PY'
import os
import sys

for path in sys.argv[1:]:
    os.mkfifo(path, mode=0o600)
PY
    "$ENV_BIN" -i \
      PATH="$TRUSTED_PATH" \
      HOME="$workdir_abs/home" \
      "$python_abs" -I "$EVIDENCE_HELPER" capture-log \
        --source "$stdout_pipe" \
        --output "$workdir_abs/worker.stdout.log" \
        --limit-marker "$stdout_limit_marker" \
        --max-bytes "$LOG_CAPTURE_LIMIT_BYTES" \
        --writer-ready "$writer_ready_marker" \
        --timeout-seconds "$((WATCHDOG_BUDGET_SECONDS + LOG_CAPTURE_GRACE_SECONDS))" &
    stdout_capture_pid="$!"
    "$ENV_BIN" -i \
      PATH="$TRUSTED_PATH" \
      HOME="$workdir_abs/home" \
      "$python_abs" -I "$EVIDENCE_HELPER" capture-log \
        --source "$stderr_pipe" \
        --output "$workdir_abs/worker.stderr.log" \
        --limit-marker "$stderr_limit_marker" \
        --max-bytes "$LOG_CAPTURE_LIMIT_BYTES" \
        --writer-ready "$writer_ready_marker" \
        --timeout-seconds "$((WATCHDOG_BUDGET_SECONDS + LOG_CAPTURE_GRACE_SECONDS))" &
    stderr_capture_pid="$!"
    exec {stdout_guard_fd}<>"$stdout_pipe"
    exec {stderr_guard_fd}<>"$stderr_pipe"
    "$TOUCH_BIN" "$writer_ready_marker"
    set +e
    "$python_abs" -I "$EVIDENCE_HELPER" exec-with-closed-fds \
      --fd "$stdout_guard_fd" \
      --fd "$stderr_guard_fd" \
      -- \
      "$TIMEOUT_BIN" --signal=TERM --kill-after=5s "${remaining_watchdog_seconds}s" \
      "$ENV_BIN" -i "${worker_environment[@]}" \
        "$BASH_BIN" --noprofile --norc \
        "$SCRIPT" --worker "$root_abs" "$wheel" "$workdir_abs" "$python_abs" \
        "$expected_sha256" \
      > "$stdout_pipe" \
      2> "$stderr_pipe"
    worker_status="$?"
    exec {stdout_guard_fd}>&-
    exec {stderr_guard_fd}>&-
    wait "$stdout_capture_pid"
    stdout_capture_status="$?"
    wait "$stderr_capture_pid"
    stderr_capture_status="$?"
    set -e
    "$python_abs" -I - "$stdout_pipe" "$stderr_pipe" <<'PY'
from pathlib import Path
import sys

for path in sys.argv[1:]:
    Path(path).unlink(missing_ok=True)
PY
    if [[ "$stdout_capture_status" == "0" && ! -f "$stdout_limit_marker" ]]; then
      "$TOUCH_BIN" "$workdir_abs/progress/stdout-log-bounded"
    else
      log_capture_note="worker stdout exceeded or escaped bounded capture"
    fi
    if [[ "$stderr_capture_status" == "0" && ! -f "$stderr_limit_marker" ]]; then
      "$TOUCH_BIN" "$workdir_abs/progress/stderr-log-bounded"
    elif [[ -n "$log_capture_note" ]]; then
      log_capture_note="$log_capture_note; worker stderr exceeded or escaped bounded capture"
    else
      log_capture_note="worker stderr exceeded or escaped bounded capture"
    fi
    if [[ -n "$log_capture_note" && "$worker_status" == "0" ]]; then
      worker_status=1
      failure_stage="worker log capture"
    fi
  fi
  elapsed_seconds="$("$python_abs" -I - "$started_ns" <<'PY'
import sys
import time

print(f"{(time.monotonic_ns() - int(sys.argv[1])) / 1_000_000_000:.6f}")
PY
)"
  deadline_reached="$("$python_abs" -I - "$elapsed_seconds" "$WATCHDOG_BUDGET_SECONDS" <<'PY'
import sys

print("yes" if float(sys.argv[1]) >= int(sys.argv[2]) else "no")
PY
)"
  "$CAT_BIN" "$workdir_abs/worker.stdout.log"
  "$CAT_BIN" "$workdir_abs/worker.stderr.log" >&2

  if [[ "$worker_status" == "0" ]]; then
    outcome="passed"
  elif [[ ("$worker_status" == "124" || "$worker_status" == "137") && "$deadline_reached" == "yes" ]]; then
    outcome="timeout"
    if [[ -n "${OTOE_COLD_START_TEST_HOOK:-}" ]]; then
      printf 'cold-start %s exceeded the %ss test-only watchdog deadline\n' \
        "$failure_stage" "$WATCHDOG_BUDGET_SECONDS" > "$final_error"
    else
      printf 'cold-start %s exceeded the %ss hard deadline\n' \
        "$failure_stage" "$FLOW_BUDGET_SECONDS" > "$final_error"
    fi
  else
    outcome="failed"
    printf 'cold-start %s exited with status %s\n' \
      "$failure_stage" "$worker_status" > "$final_error"
  fi
  if [[ "$outcome" != "passed" && -s "$workdir_abs/worker.stderr.log" ]]; then
    "$CAT_BIN" "$workdir_abs/worker.stderr.log" >> "$final_error"
  fi
  if [[ "$outcome" != "passed" && -n "$log_capture_note" ]]; then
    printf '%s (per-stream limit: %s bytes)\n' \
      "$log_capture_note" "$LOG_CAPTURE_LIMIT_BYTES" >> "$final_error"
  fi

  local -a finalize_args=(
    finalize
    --workdir "$workdir_abs"
    --wheel "$wheel"
    --output "$workdir_abs/cold-start-evidence.json"
    --outcome "$outcome"
    --worker-exit-code "$worker_status"
    --elapsed-seconds "$elapsed_seconds"
    --budget-seconds "$FLOW_BUDGET_SECONDS"
  )
  if [[ "$outcome" != "passed" ]]; then
    finalize_args+=(--error-file "$final_error")
  fi
  if [[ -n "$expected_sha256" ]]; then
    finalize_args+=(--expected-sha256 "$expected_sha256")
  fi
  "$python_abs" -I "$EVIDENCE_HELPER" "${finalize_args[@]}"

  local evidence_summary
  evidence_summary="$("$python_abs" -I - "$workdir_abs/cold-start-evidence.json" <<'PY'
import json
from pathlib import Path
import sys

payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
print(payload["outcome"], payload["timing"]["elapsed_seconds"], payload["wheel"]["sha256"])
PY
)"
  local evidence_outcome
  local evidence_elapsed
  local wheel_sha256
  read -r evidence_outcome evidence_elapsed wheel_sha256 <<< "$evidence_summary"
  echo "cold-start smoke: wheel sha256 $wheel_sha256"
  echo "cold-start smoke: elapsed ${evidence_elapsed}s / ${FLOW_BUDGET_SECONDS}s"
  echo "cold-start smoke: evidence $workdir_abs/cold-start-evidence.json"
  if [[ "$evidence_outcome" == "passed" ]]; then
    echo "cold-start smoke: ok"
    return 0
  fi
  echo "cold-start smoke: $evidence_outcome" >&2
  if [[ "$worker_status" == "0" ]]; then
    return 1
  fi
  return "$worker_status"
}

if [[ "${1:-}" == "--worker" ]]; then
  shift
  run_worker "$@"
else
  run_controller "$@"
fi
