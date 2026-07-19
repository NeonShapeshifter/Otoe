from __future__ import annotations

import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import time
from zipfile import ZIP_DEFLATED, ZipFile

import pytest

from scripts.cold_start_evidence import (
    CHECK_MARKERS,
    GENERATED_README_COMMANDS,
    ISOLATION_MARKERS,
    ColdStartEvidenceError,
    build_evidence,
    capture_bounded_log,
    file_sha256,
    inspect_generated_readme,
    inspect_wheel,
    validate_evidence,
    write_evidence,
)


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "cold_start_smoke.sh"
BASH = Path(shutil.which("bash") or "/bin/bash").resolve()
PACKAGE_README_COMMANDS = (
    "python -m pip install otoe",
    "otoe new hello_otoe",
    "cd hello_otoe",
    "otoe check",
    "otoe render app:app --out preview.html --css styles.css --pretty",
    "otoe render app:app --out preview.png --native --css styles.css",
    "otoe dev app:app --css styles.css",
    "otoe build app:app --out dist/cage --css styles.css --validate",
)


def _fixed_gnu_timeout() -> Path | None:
    for candidate in (Path("/usr/bin/timeout"), Path("/bin/timeout")):
        if not candidate.is_file() or not os.access(candidate, os.X_OK):
            continue
        result = subprocess.run(
            [str(candidate), "--version"],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0 and "GNU coreutils" in result.stdout:
            return candidate
    return None


GNU_TIMEOUT = _fixed_gnu_timeout()
requires_cold_start_host = pytest.mark.skipif(
    GNU_TIMEOUT is None,
    reason="cold-start integration requires GNU timeout in /usr/bin or /bin",
)


def _package_readme(*blocks: tuple[str, ...]) -> str:
    rendered_blocks = []
    for block in blocks:
        body = "\n".join(block)
        rendered_blocks.append(f"```bash\n{body}\n```")
    return "\n\n".join(("# Otoe", "## Quickstart", *rendered_blocks))


def _run(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    command_env = os.environ.copy()
    command_env["PYTHON"] = sys.executable
    if env is not None:
        command_env.update(env)
    return subprocess.run(
        [str(BASH), str(SCRIPT), *args],
        cwd=ROOT,
        env=command_env,
        check=False,
        capture_output=True,
        text=True,
    )


def _wheel(
    path: Path,
    *,
    metadata_version: str = "0.2.0",
    dist_info_version: str = "0.2.0",
    duplicate_version: bool = False,
    package_readme: str | None = None,
) -> Path:
    readme = package_readme or _package_readme(
        PACKAGE_README_COMMANDS,
        ("echo unrelated-documentation-example",),
    )
    metadata = (
        "Metadata-Version: 2.4\n"
        "Name: otoe\n"
        f"Version: {metadata_version}\n"
        f"{'Version: ' + metadata_version + chr(10) if duplicate_version else ''}"
        "Description-Content-Type: text/markdown\n"
        "\n"
        f"{readme}\n"
    )
    with ZipFile(path, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr(
            f"otoe-{dist_info_version}.dist-info/METADATA",
            metadata,
        )
    return path


@requires_cold_start_host
def test_cold_start_smoke_requires_an_exact_wheel() -> None:
    result = _run()

    assert result.returncode == 2
    assert "pass the exact wheel artifact" in result.stderr


@requires_cold_start_host
def test_cold_start_smoke_rejects_missing_wheel(tmp_path: Path) -> None:
    result = _run(str(tmp_path / "missing.whl"))

    assert result.returncode == 2
    assert "wheel does not exist" in result.stderr


@requires_cold_start_host
def test_cold_start_smoke_rejects_checkout_workdir(tmp_path: Path) -> None:
    wheel = tmp_path / "otoe-0-py3-none-any.whl"
    wheel.write_bytes(b"not reached")

    result = _run(
        str(wheel),
        env={"OTOE_COLD_START_WORKDIR": str(ROOT / ".cold-start-test")},
    )

    assert result.returncode == 2
    assert "workdir must be outside the source checkout" in result.stderr
    assert not (ROOT / ".cold-start-test").exists()


@requires_cold_start_host
def test_cold_start_smoke_rejects_nonempty_workdir(tmp_path: Path) -> None:
    wheel = tmp_path / "otoe-0-py3-none-any.whl"
    wheel.write_bytes(b"not reached")
    workdir = tmp_path / "work"
    workdir.mkdir()
    sentinel = workdir / "keep.txt"
    sentinel.write_text("keep\n", encoding="utf-8")

    result = _run(
        str(wheel),
        env={"OTOE_COLD_START_WORKDIR": str(workdir)},
    )

    assert result.returncode == 2
    assert "workdir must be empty" in result.stderr
    assert sentinel.read_text(encoding="utf-8") == "keep\n"


@pytest.mark.skipif(GNU_TIMEOUT is not None, reason="host provides the required GNU timeout")
def test_cold_start_smoke_fails_clearly_without_fixed_gnu_timeout(tmp_path: Path) -> None:
    wheel = tmp_path / "otoe-0-py3-none-any.whl"
    wheel.write_bytes(b"not reached")

    result = _run(str(wheel))

    assert result.returncode == 2
    assert (
        "required system utility is unavailable: timeout" in result.stderr
        or "GNU coreutils timeout is required" in result.stderr
    )


def test_installed_wheel_release_gates_delegate_to_cold_start() -> None:
    cold_start = SCRIPT.read_text(encoding="utf-8")
    wheel_smoke = (ROOT / "scripts" / "wheel_smoke.sh").read_text(encoding="utf-8")
    release_check = (ROOT / "scripts" / "release_check.sh").read_text(encoding="utf-8")
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    publish = (ROOT / ".github" / "workflows" / "publish.yml").read_text(encoding="utf-8")

    assert '"$ROOT/scripts/cold_start_smoke.sh" "$WHEEL"' in wheel_smoke
    assert "scripts/wheel_smoke.sh" in release_check
    assert "scripts/verify_release_artifacts.py" in release_check
    assert "scripts/verify_release_artifacts.py" in ci
    assert "scripts/verify_release_artifacts.py" in publish
    assert '--tag "$GITHUB_REF_NAME"' in publish
    assert "scripts/wheel_smoke.sh" in ci
    assert "scripts/wheel_smoke.sh" in publish
    assert "PIP_NO_INDEX=1" in cold_start
    assert '"$ENV_BIN" -i' in cold_start
    assert cold_start.count('"$ENV_BIN" -i') >= 2
    assert "--no-deps" in cold_start
    assert "source checkout leaked onto sys.path" in cold_start
    assert "wheel_metadata_version_match" in cold_start
    assert 'inspect-generated-readme "$app_dir/README.md"' in cold_start
    assert cold_start.count('--expected-sha256 "$expected_sha256"') == 2
    assert cold_start.count("verify-sha256") == 2
    assert '"$CHMOD_BIN" 0400 "$artifact"' in cold_start
    assert '"$CHMOD_BIN" 0500 "$artifact_dir"' in cold_start
    assert "LOG_CAPTURE_LIMIT_BYTES=1048576" in cold_start
    assert "capture-log" in cold_start
    assert "FLOW_BUDGET_SECONDS=300" in cold_start
    assert "time.monotonic_ns()" in cold_start
    assert "--signal=TERM --kill-after=5s" in cold_start
    assert "--port 0" in cold_start
    assert "portable-core.canonical.json" in cold_start
    for workflow in (ci, publish):
        assert "OTOE_SMOKE_WORKDIR: ${{ runner.temp }}/otoe-cold-start" in workflow
        assert "Record cold-start evidence digest" in workflow
        assert "Upload cold-start evidence" in workflow
        assert "cold-start-evidence.json" in workflow
        assert "if: always()" in workflow
        assert "if-no-files-found: error" in workflow
    assert (
        "name: cold-start-evidence-py${{ matrix.python-version }}-"
        "attempt${{ github.run_attempt }}"
    ) in ci
    assert "name: cold-start-evidence-publish-attempt${{ github.run_attempt }}" in publish
    assert publish.count("name: python-package-distributions") == 2
    assert "overwrite: true" in publish
    assert "packages-dir: release/packages" in publish


def test_wheel_identity_requires_filename_dist_info_and_metadata_version_match(
    tmp_path: Path,
) -> None:
    wheel = _wheel(
        tmp_path / "otoe-0.2.0-py3-none-any.whl",
        metadata_version="9.9.9",
    )

    with pytest.raises(ColdStartEvidenceError, match="versions must match"):
        inspect_wheel(wheel)


def test_wheel_identity_rejects_duplicate_identity_headers(tmp_path: Path) -> None:
    wheel = _wheel(
        tmp_path / "otoe-0.2.0-py3-none-any.whl",
        duplicate_version=True,
    )

    with pytest.raises(ColdStartEvidenceError, match="exactly one Name and one Version"):
        inspect_wheel(wheel)


@pytest.mark.parametrize(
    "package_readme",
    (
        "\n".join(("# Otoe", *PACKAGE_README_COMMANDS)),
        _package_readme(tuple(f"# {command}" for command in PACKAGE_README_COMMANDS)),
        _package_readme(
            (
                PACKAGE_README_COMMANDS[0],
                PACKAGE_README_COMMANDS[0],
                *PACKAGE_README_COMMANDS[1:],
            )
        ),
        _package_readme((*PACKAGE_README_COMMANDS, "echo unexpected")),
        _package_readme(
            (
                PACKAGE_README_COMMANDS[1],
                PACKAGE_README_COMMANDS[0],
                *PACKAGE_README_COMMANDS[2:],
            )
        ),
        _package_readme(PACKAGE_README_COMMANDS, PACKAGE_README_COMMANDS),
    ),
    ids=("prose", "comments", "duplicate-command", "extra", "order", "duplicate-block"),
)
def test_wheel_identity_requires_one_exact_contiguous_bash_quickstart(
    tmp_path: Path,
    package_readme: str,
) -> None:
    wheel = _wheel(
        tmp_path / "otoe-0.2.0-py3-none-any.whl",
        package_readme=package_readme,
    )

    with pytest.raises(ColdStartEvidenceError, match="exactly one contiguous bash"):
        inspect_wheel(wheel)


def test_wheel_identity_rejects_backticks_nested_in_a_larger_literal_fence(
    tmp_path: Path,
) -> None:
    commands = "\n".join(PACKAGE_README_COMMANDS)
    package_readme = "\n".join(
        (
            "# Otoe",
            "## Quickstart",
            "````text",
            "```bash",
            commands,
            "```",
            "````",
        )
    )
    wheel = _wheel(
        tmp_path / "otoe-0.2.0-py3-none-any.whl",
        package_readme=package_readme,
    )

    with pytest.raises(ColdStartEvidenceError, match="exactly one contiguous bash"):
        inspect_wheel(wheel)


def test_generated_readme_requires_one_real_top_level_commonmark_fence(
    tmp_path: Path,
) -> None:
    commands = "\n".join(GENERATED_README_COMMANDS)
    readme = tmp_path / "README.md"
    readme.write_text(
        "\n".join(
            (
                "# App",
                "````text",
                "```bash",
                commands,
                "```",
                "````",
            )
        ),
        encoding="utf-8",
    )

    with pytest.raises(ColdStartEvidenceError, match="one top-level bash block"):
        inspect_generated_readme(readme)


def test_generated_readme_rejects_additional_bash_blocks(tmp_path: Path) -> None:
    readme = tmp_path / "README.md"
    readme.write_text(
        _package_readme(GENERATED_README_COMMANDS, ("echo unexpected",)),
        encoding="utf-8",
    )

    with pytest.raises(ColdStartEvidenceError, match="one top-level bash block"):
        inspect_generated_readme(readme)


def test_generated_readme_accepts_the_single_canonical_bash_block(tmp_path: Path) -> None:
    readme = tmp_path / "README.md"
    readme.write_text(_package_readme(GENERATED_README_COMMANDS), encoding="utf-8")

    inspect_generated_readme(readme)


@requires_cold_start_host
def test_watchdog_test_hook_is_fail_closed(tmp_path: Path) -> None:
    wheel = _wheel(tmp_path / "otoe-0.2.0-py3-none-any.whl")

    result = _run(
        str(wheel),
        env={
            "OTOE_COLD_START_TEST_BUDGET_SECONDS": "1",
            "OTOE_COLD_START_TEST_HOOK": "not-a-supported-hook",
            "OTOE_COLD_START_WORKDIR": str(tmp_path / "work"),
        },
    )

    assert result.returncode == 2
    assert "invalid test-only watchdog hook" in result.stderr


@requires_cold_start_host
def test_identity_failure_still_writes_failure_evidence(tmp_path: Path) -> None:
    wheel = _wheel(
        tmp_path / "otoe-0.2.0-py3-none-any.whl",
        metadata_version="9.9.9",
    )
    workdir = tmp_path / "work"

    result = _run(
        str(wheel),
        env={"OTOE_COLD_START_WORKDIR": str(workdir)},
    )

    assert result.returncode != 0
    evidence = json.loads((workdir / "cold-start-evidence.json").read_text(encoding="utf-8"))
    assert evidence["outcome"] == "failed"
    assert evidence["wheel"]["identity_valid"] is False
    assert evidence["wheel"]["sha256"] == file_sha256(wheel)
    assert "versions must match" in evidence["error"]


@requires_cold_start_host
def test_invalid_controller_digest_still_writes_failure_evidence(tmp_path: Path) -> None:
    wheel = _wheel(tmp_path / "otoe-0.2.0-py3-none-any.whl")
    workdir = tmp_path / "work"
    python_wrapper = tmp_path / "python-wrapper"
    python_wrapper.write_text(
        "#!/bin/sh\n"
        "case \"${3:-}\" in\n"
        "  *'os.path.abspath(sys.executable)'*) printf '%s\\n' \"$0\"; exit 0 ;;\n"
        "esac\n"
        "for arg in \"$@\"; do\n"
        "  if [ \"$arg\" = sha256 ]; then printf 'not-a-digest\\n'; exit 0; fi\n"
        "done\n"
        f"exec {shlex.quote(sys.executable)} \"$@\"\n",
        encoding="utf-8",
    )
    python_wrapper.chmod(0o755)

    result = _run(
        str(wheel),
        env={
            "OTOE_COLD_START_WORKDIR": str(workdir),
            "PYTHON": str(python_wrapper),
        },
    )

    assert result.returncode == 1
    evidence = json.loads((workdir / "cold-start-evidence.json").read_text(encoding="utf-8"))
    assert evidence["outcome"] == "failed"
    assert evidence["wheel"]["expected_sha256"] is None
    assert evidence["checks"]["wheel_expected_copy_match"] is False
    assert "invalid source wheel digest" in evidence["error"]


@requires_cold_start_host
def test_bounded_log_capture_truncates_without_unbounded_memory(tmp_path: Path) -> None:
    source = tmp_path / "source.log"
    output = tmp_path / "captured.log"
    limit_marker = tmp_path / "captured.limit"
    source.write_bytes(b"0123456789abcdef" * (128 * 1024))

    capture_bounded_log(
        source=source,
        output=output,
        limit_marker=limit_marker,
        max_bytes=4096,
        timeout_seconds=2,
    )

    assert output.stat().st_size == 4096
    assert output.read_bytes().endswith(b"[cold-start log truncated at 4096 bytes]\n")
    assert limit_marker.read_text(encoding="utf-8") == "size-limit\n"


@requires_cold_start_host
def test_bounded_log_capture_times_out_while_fifo_has_no_writer(tmp_path: Path) -> None:
    source = tmp_path / "source.pipe"
    output = tmp_path / "captured.log"
    limit_marker = tmp_path / "captured.limit"
    os.mkfifo(source)

    started = time.monotonic()
    capture_bounded_log(
        source=source,
        output=output,
        limit_marker=limit_marker,
        max_bytes=4096,
        timeout_seconds=0.2,
    )

    assert time.monotonic() - started < 2
    assert output.read_bytes().endswith(b"[cold-start log capture timed out]\n")
    assert limit_marker.read_text(encoding="utf-8") == "capture-timeout\n"


@requires_cold_start_host
def test_hostile_worker_output_is_bounded_and_still_emits_evidence(tmp_path: Path) -> None:
    wheel = _wheel(tmp_path / "otoe-0.2.0-py3-none-any.whl")
    workdir = tmp_path / "work"

    started = time.monotonic()
    result = _run(
        str(wheel),
        env={
            "OTOE_COLD_START_TEST_BUDGET_SECONDS": "5",
            "OTOE_COLD_START_TEST_HOOK": "flood-worker-output-v1",
            "OTOE_COLD_START_WORKDIR": str(workdir),
        },
    )

    assert result.returncode != 0
    assert time.monotonic() - started < 10
    assert (workdir / "worker.stdout.log").stat().st_size == 1024 * 1024
    assert (workdir / "worker.stderr.log").stat().st_size == 1024 * 1024
    assert (workdir / "worker.stdout.limit").read_text(encoding="utf-8") == "size-limit\n"
    assert (workdir / "worker.stderr.limit").read_text(encoding="utf-8") == "size-limit\n"
    evidence = json.loads((workdir / "cold-start-evidence.json").read_text(encoding="utf-8"))
    assert evidence["outcome"] == "failed"
    assert evidence["checks"]["stdout_log_bounded"] is False
    assert evidence["checks"]["stderr_log_bounded"] is False
    assert "per-stream limit: 1048576 bytes" in evidence["error"]
    artifact = workdir / "artifact" / wheel.name
    assert artifact.stat().st_mode & 0o777 == 0o400
    assert artifact.parent.stat().st_mode & 0o777 == 0o500


def test_success_evidence_schema_and_hashes(tmp_path: Path) -> None:
    wheel = _wheel(tmp_path / "otoe-0.2.0-py3-none-any.whl")
    workdir = tmp_path / "work"
    copied_wheel = workdir / "artifact" / wheel.name
    copied_wheel.parent.mkdir(parents=True)
    copied_wheel.write_bytes(wheel.read_bytes())
    progress = workdir / "progress"
    progress.mkdir()
    for check_marker in (*CHECK_MARKERS.values(), "source-checkout-absent", "completed"):
        (progress / check_marker).touch()
    for isolation_marker in ISOLATION_MARKERS.values():
        if isolation_marker is not None:
            (progress / isolation_marker).touch()
    app = workdir / "app"
    app.mkdir()
    (app / "preview.html").write_text("<p>Count: 0</p>\n", encoding="utf-8")
    (app / "preview.png").write_bytes(b"\x89PNG\r\n\x1a\nfixture")

    evidence = build_evidence(
        workdir=workdir,
        wheel=wheel,
        outcome="passed",
        worker_exit_code=0,
        elapsed_seconds=5.25,
        budget_seconds=300,
        expected_sha256=file_sha256(wheel),
        error=None,
    )
    output = workdir / "cold-start-evidence.json"
    write_evidence(output, evidence)
    loaded = json.loads(output.read_text(encoding="utf-8"))

    validate_evidence(loaded)
    assert loaded["outcome"] == "passed"
    assert loaded["wheel"] == {
        "distribution": "otoe",
        "expected_copy_match": True,
        "expected_sha256": file_sha256(wheel),
        "expected_source_match": True,
        "filename": wheel.name,
        "identity_valid": True,
        "sha256": file_sha256(wheel),
        "source_copy_match": True,
        "source_sha256": file_sha256(wheel),
        "version": "0.2.0",
    }
    assert loaded["artifacts"]["preview.html"]["sha256"] == file_sha256(app / "preview.html")
    assert loaded["timing"] == {
        "budget_seconds": 300,
        "elapsed_seconds": 5.25,
        "scope": "controller-digest-through-generated-app-validation",
        "within_budget": True,
    }


def test_timeout_evidence_preserves_partial_results(tmp_path: Path) -> None:
    wheel = _wheel(tmp_path / "otoe-0.2.0-py3-none-any.whl")
    workdir = tmp_path / "work"
    (workdir / "progress").mkdir(parents=True)
    (workdir / "progress" / "package-readme-commands").touch()

    evidence = build_evidence(
        workdir=workdir,
        wheel=wheel,
        outcome="timeout",
        worker_exit_code=124,
        elapsed_seconds=300.01,
        budget_seconds=300,
        expected_sha256=file_sha256(wheel),
        error="hard deadline exceeded",
    )

    validate_evidence(evidence)
    assert evidence["outcome"] == "timeout"
    assert evidence["timing"]["within_budget"] is False
    assert evidence["checks"]["package_readme_commands"] is True
    assert evidence["checks"]["dev_health"] is False
    assert evidence["checks"]["wheel_source_copy_match"] is False
    assert evidence["error"] == "hard deadline exceeded"


def test_evidence_rejects_non_finite_elapsed_time(tmp_path: Path) -> None:
    wheel = _wheel(tmp_path / "otoe-0.2.0-py3-none-any.whl")
    workdir = tmp_path / "work"
    (workdir / "progress").mkdir(parents=True)

    with pytest.raises(ColdStartEvidenceError, match="invalid elapsed time"):
        build_evidence(
            workdir=workdir,
            wheel=wheel,
            outcome="timeout",
            worker_exit_code=124,
            elapsed_seconds=float("nan"),
            budget_seconds=300,
            expected_sha256=file_sha256(wheel),
            error="hard deadline exceeded",
        )


@requires_cold_start_host
def test_watchdog_terminates_worker_process_group_without_child_leak(
    tmp_path: Path,
) -> None:
    wheel = _wheel(tmp_path / "otoe-0.2.0-py3-none-any.whl")
    workdir = tmp_path / "work"
    bash_env = tmp_path / "hostile-bash-env.sh"
    bash_env_sentinel = tmp_path / "bash-env-read-by-worker"
    bash_env.write_text(
        'if [[ "${1:-}" == "--worker" ]]; then\n'
        '  : > "${OTOE_COLD_START_TEST_BASH_ENV_SENTINEL:?}"\n'
        "  exit 97\n"
        "fi\n",
        encoding="utf-8",
    )
    hostile_path = tmp_path / "hostile-path"
    hostile_path.mkdir()
    hostile_sentinel = tmp_path / "hostile-command-ran"
    intercepted_commands = (
            "bash",
            "cat",
            "chmod",
            "cmp",
        "cp",
        "dirname",
        "env",
        "find",
        "mkdir",
        "mktemp",
        "sleep",
        "timeout",
        "touch",
    )
    for command in intercepted_commands:
        executable = hostile_path / command
        executable.write_text(
            "#!/bin/sh\n"
            'printf intercepted > "${OTOE_COLD_START_HOSTILE_SENTINEL:?}"\n'
            "exit 98\n",
            encoding="utf-8",
        )
        executable.chmod(0o755)
    hostile_function = (
        '() { printf intercepted > "${OTOE_COLD_START_HOSTILE_SENTINEL:?}"; return 98; }'
    )
    started = time.monotonic()
    hostile_environment = {
        f"BASH_FUNC_{command}%%": hostile_function for command in intercepted_commands
    }
    result = _run(
        str(wheel),
        env={
            **hostile_environment,
            "BASH_ENV": str(bash_env),
            "BASHOPTS": "checkwinsize:cmdhist:complete_fullquote:extquote:force_fignore:globasciiranges:globskipdots:hostcomplete:interactive_comments:patsub_replacement:progcomp:promptvars:sourcepath",
            "ENV": str(bash_env),
            "OTOE_COLD_START_TEST_BASH_ENV_SENTINEL": str(bash_env_sentinel),
            "OTOE_COLD_START_TEST_BUDGET_SECONDS": "1",
            "OTOE_COLD_START_HOSTILE_SENTINEL": str(hostile_sentinel),
            "OTOE_COLD_START_TEST_HOOK": "hang-worker-v1",
            "OTOE_COLD_START_WORKDIR": str(workdir),
            "PATH": str(hostile_path),
            "PIP_CONFIG_FILE": str(tmp_path / "poison-pip.conf"),
            "PIP_CONSTRAINT": str(tmp_path / "poison-constraints.txt"),
            "PIP_EXTRA_INDEX_URL": "https://invalid.example/extra",
            "PIP_INDEX_URL": "https://invalid.example/simple",
            "PIP_NO_INDEX": "0",
            "PIP_REQUIREMENT": str(tmp_path / "poison-requirements.txt"),
            "PIP_TARGET": str(tmp_path / "poison-target"),
            "PIP_USER": "1",
            "SHELLOPTS": "braceexpand:hashall:interactive-comments",
        },
    )

    assert result.returncode == 124
    assert time.monotonic() - started < 8
    evidence = json.loads((workdir / "cold-start-evidence.json").read_text(encoding="utf-8"))
    assert evidence["outcome"] == "timeout"
    assert evidence["worker_exit_code"] == 124
    assert "test-only watchdog deadline" in evidence["error"]
    assert not bash_env_sentinel.exists()
    assert not hostile_sentinel.exists()
    worker_environment = json.loads(
        (workdir / "test-worker-environment.json").read_text(encoding="utf-8")
    )
    assert worker_environment["HOME"] == str(workdir / "home")
    assert worker_environment["PATH"] == "/usr/bin:/bin"
    assert not any(name.startswith("BASH_FUNC_") for name in worker_environment)
    for forbidden in (
        "BASHOPTS",
        "BASH_ENV",
        "ENV",
        "PIP_CONFIG_FILE",
        "PIP_INDEX_URL",
        "PIP_NO_INDEX",
        "SHELLOPTS",
    ):
        assert forbidden not in worker_environment
    clean_environment = json.loads(
        (workdir / "test-clean-environment.json").read_text(encoding="utf-8")
    )
    assert clean_environment == {
        "PIP_CONFIG_FILE": "/dev/null",
        "PIP_DISABLE_PIP_VERSION_CHECK": "1",
        "PIP_NO_INDEX": "1",
    }
    child_pid = int((workdir / "test-hung-child.pid").read_text(encoding="utf-8"))
    process_status = Path(f"/proc/{child_pid}/stat")
    deadline = time.monotonic() + 1
    while process_status.exists() and time.monotonic() < deadline:
        time.sleep(0.01)
    assert not process_status.exists()


@requires_cold_start_host
def test_watchdog_escalates_to_kill_for_term_resistant_process_group(
    tmp_path: Path,
) -> None:
    wheel = _wheel(tmp_path / "otoe-0.2.0-py3-none-any.whl")
    workdir = tmp_path / "work"

    started = time.monotonic()
    result = _run(
        str(wheel),
        env={
            "OTOE_COLD_START_TEST_BUDGET_SECONDS": "1",
            "OTOE_COLD_START_TEST_HOOK": "hang-ignore-term-v1",
            "OTOE_COLD_START_WORKDIR": str(workdir),
        },
    )
    elapsed = time.monotonic() - started

    assert result.returncode in {124, 137}
    assert 5.5 <= elapsed < 10
    evidence = json.loads((workdir / "cold-start-evidence.json").read_text(encoding="utf-8"))
    assert evidence["outcome"] == "timeout"
    assert evidence["worker_exit_code"] in {124, 137}
    assert "test-only watchdog deadline" in evidence["error"]
    child_pid = int((workdir / "test-hung-child.pid").read_text(encoding="utf-8"))
    process_status = Path(f"/proc/{child_pid}/stat")
    deadline = time.monotonic() + 2
    while process_status.exists() and time.monotonic() < deadline:
        time.sleep(0.01)
    assert not process_status.exists()


def test_passing_evidence_rejects_source_wheel_changed_after_copy(tmp_path: Path) -> None:
    wheel = _wheel(tmp_path / "otoe-0.2.0-py3-none-any.whl")
    workdir = tmp_path / "work"
    copied_wheel = workdir / "artifact" / wheel.name
    copied_wheel.parent.mkdir(parents=True)
    copied_wheel.write_bytes(wheel.read_bytes())
    progress = workdir / "progress"
    progress.mkdir()
    for check_marker in (*CHECK_MARKERS.values(), "source-checkout-absent", "completed"):
        (progress / check_marker).touch()
    for isolation_marker in ISOLATION_MARKERS.values():
        if isolation_marker is not None:
            (progress / isolation_marker).touch()
    app = workdir / "app"
    app.mkdir()
    (app / "preview.html").write_text("ok\n", encoding="utf-8")
    (app / "preview.png").write_bytes(b"png")
    wheel.write_bytes(wheel.read_bytes() + b"changed")

    evidence = build_evidence(
        workdir=workdir,
        wheel=wheel,
        outcome="passed",
        worker_exit_code=0,
        elapsed_seconds=1.0,
        budget_seconds=300,
        expected_sha256=file_sha256(copied_wheel),
        error=None,
    )

    assert evidence["outcome"] == "failed"
    assert evidence["checks"]["wheel_source_copy_match"] is False
    assert evidence["wheel"]["source_copy_match"] is False


def test_passing_evidence_rejects_source_and_copy_replaced_after_test(
    tmp_path: Path,
) -> None:
    wheel = _wheel(tmp_path / "otoe-0.2.0-py3-none-any.whl")
    workdir = tmp_path / "work"
    copied_wheel = workdir / "artifact" / wheel.name
    copied_wheel.parent.mkdir(parents=True)
    copied_wheel.write_bytes(wheel.read_bytes())
    expected_sha256 = file_sha256(copied_wheel)
    progress = workdir / "progress"
    progress.mkdir()
    for check_marker in (*CHECK_MARKERS.values(), "source-checkout-absent", "completed"):
        (progress / check_marker).touch()
    for isolation_marker in ISOLATION_MARKERS.values():
        if isolation_marker is not None:
            (progress / isolation_marker).touch()
    app = workdir / "app"
    app.mkdir()
    (app / "preview.html").write_text("ok\n", encoding="utf-8")
    (app / "preview.png").write_bytes(b"png")

    with ZipFile(wheel, "a", compression=ZIP_DEFLATED) as archive:
        archive.writestr("otoe/replaced-after-test.txt", "different valid wheel bytes\n")
    copied_wheel.write_bytes(wheel.read_bytes())

    evidence = build_evidence(
        workdir=workdir,
        wheel=wheel,
        outcome="passed",
        worker_exit_code=0,
        elapsed_seconds=1.0,
        budget_seconds=300,
        expected_sha256=expected_sha256,
        error=None,
    )

    assert evidence["outcome"] == "failed"
    assert evidence["checks"]["wheel_source_copy_match"] is True
    assert evidence["checks"]["wheel_expected_copy_match"] is False
    assert evidence["checks"]["wheel_expected_source_match"] is False
    assert evidence["wheel"]["expected_sha256"] == expected_sha256
