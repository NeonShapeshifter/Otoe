import json
import subprocess
import sys
from pathlib import Path

import pytest

import scripts.runtime_soak as runtime_soak
from scripts.runtime_soak import main


ROOT = Path(__file__).resolve().parents[1]
SOAK_SCRIPT = ROOT / "scripts" / "runtime_soak.py"


def test_runtime_soak_restarts_without_lost_work_or_leaks():
    completed, result = _run_soak_subprocess(25, host_cycles=5)

    assert completed.returncode == 0, completed.stderr
    assert result["cycles"] == 25
    assert result["cycles_completed"] == 25
    assert result["failing_cycle"] is None
    assert result["callbacks_posted"] == 25 * 9
    assert result["callbacks_run"] == result["callbacks_posted"]
    assert result["host_cycles"] == 5
    assert result["worker_threads_joined"] == (25 * 4) + 5
    assert result["owners_observed"] == 25 * 9
    assert result["resources_acquired"] == 25 * 13
    assert result["resources_released"] == result["resources_acquired"]
    assert result["http_host_starts"] == 5
    assert result["http_host_restarts"] == 4
    assert result["http_requests"] == 20
    assert result["native_host_pumps"] == 5
    assert result["elapsed_seconds"] > 0
    assert result["counters_complete"] is True
    assert result["counter_scope"] == "complete"
    assert result["python"]
    assert result["platform"]
    assert result["failures"] == []


def test_runtime_soak_cli_emits_machine_readable_evidence_in_subprocess():
    completed, payload = _run_soak_subprocess(2, host_cycles=2)

    assert completed.returncode == 0, completed.stderr
    assert payload["format"] == "otoe-runtime-soak"
    assert payload["cycles"] == 2
    assert payload["host_cycles"] == 2
    assert payload["cycles_completed"] == 2
    assert payload["failing_cycle"] is None
    assert payload["callbacks_posted"] == 18
    assert payload["callbacks_run"] == 18
    assert payload["resources_acquired"] == payload["resources_released"] == 26
    assert payload["http_host_starts"] == 2
    assert payload["http_host_restarts"] == 1
    assert payload["native_host_pumps"] == 2
    assert payload["elapsed_seconds"] > 0
    assert payload["counters_complete"] is True
    assert payload["counter_scope"] == "complete"
    assert payload["python"]
    assert payload["platform"]
    assert payload["failures"] == []


def test_runtime_soak_long_gate_runs_1000_cycles_in_isolated_process():
    completed, payload = _run_soak_subprocess(1_000, timeout=180)

    assert completed.returncode == 0, completed.stderr
    assert payload["cycles"] == 1_000
    assert payload["host_cycles"] == 100
    assert payload["cycles_completed"] == 1_000
    assert payload["failing_cycle"] is None
    assert payload["callbacks_posted"] == payload["callbacks_run"] == 9_000
    assert payload["owners_observed"] == 9_000
    assert payload["resources_acquired"] == payload["resources_released"] == 13_000
    assert payload["worker_threads_joined"] == 4_100
    assert payload["http_host_starts"] == 100
    assert payload["http_host_restarts"] == 99
    assert payload["http_requests"] == 400
    assert payload["native_host_pumps"] == 100
    assert payload["counters_complete"] is True
    assert payload["counter_scope"] == "complete"
    assert payload["failures"] == []


def test_runtime_soak_cli_reports_progress_for_unexpected_base_exception(
    monkeypatch,
    capsys,
):
    class UnexpectedAbort(BaseException):
        pass

    def fail(*, cycles, host_cycles, _progress):
        assert cycles == 7
        assert host_cycles == 3
        _progress.cycles_completed = 3
        _progress.failing_cycle = 3
        _progress.callbacks_posted = 27
        _progress.callbacks_run = 27
        raise UnexpectedAbort("unexpected abort")

    monkeypatch.setattr(runtime_soak, "run_runtime_soak", fail)

    assert main(["--_worker", "--cycles", "7", "--host-cycles", "3"]) == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["cycles"] == 7
    assert payload["cycles_completed"] == 3
    assert payload["failing_cycle"] == 3
    assert payload["callbacks_posted"] == payload["callbacks_run"] == 27
    assert payload["failures"] == ["UnexpectedAbort: unexpected abort"]


@pytest.mark.parametrize("error", [KeyboardInterrupt(), SystemExit(7)])
def test_runtime_soak_cli_reports_but_does_not_swallow_process_control(
    monkeypatch,
    capsys,
    error,
):
    def fail(*, cycles, host_cycles, _progress):
        raise error

    monkeypatch.setattr(runtime_soak, "run_runtime_soak", fail)

    with pytest.raises(type(error)):
        main(["--_worker", "--cycles", "4", "--host-cycles", "2"])

    payload = json.loads(capsys.readouterr().out)
    assert payload["cycles_completed"] == 0
    assert payload["failures"][0].startswith(type(error).__name__)


def test_runtime_soak_supervisor_terminates_hung_child_and_emits_json():
    completed = subprocess.run(
        [
            sys.executable,
            str(SOAK_SCRIPT),
            "--cycles",
            "1000",
            "--host-cycles",
            "100",
            "--timeout-seconds",
            "0.001",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )

    payload = json.loads(completed.stdout)
    assert completed.returncode == 1
    assert payload["cycles_completed"] < payload["cycles"]
    assert payload["counters_complete"] is False
    assert payload["counter_scope"] == "last-persisted-checkpoint"
    assert payload["failures"]
    assert payload["failures"][-1].startswith("TimeoutError:")


def _run_soak_subprocess(
    cycles: int,
    *,
    host_cycles: int | None = None,
    timeout: int = 60,
) -> tuple[subprocess.CompletedProcess[str], dict]:
    command = [sys.executable, str(SOAK_SCRIPT), "--cycles", str(cycles)]
    if host_cycles is not None:
        command.extend(("--host-cycles", str(host_cycles)))
    completed = subprocess.run(
        command,
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return completed, json.loads(completed.stdout)
