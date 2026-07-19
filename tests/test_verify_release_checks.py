from __future__ import annotations

import json
from typing import Any
from urllib.request import Request

import pytest

from scripts import verify_release_checks
from scripts.verify_release_checks import CheckGateError, WORKFLOW_REQUIREMENTS


SHA = "a" * 40


def _workflow_run(
    requirement_index: int,
    *,
    identifier: int | None = None,
    attempt: int = 1,
    status: str = "completed",
    conclusion: str | None = "success",
    started_at: str = "2026-07-17T12:00:00Z",
) -> dict[str, object]:
    requirement = WORKFLOW_REQUIREMENTS[requirement_index]
    return {
        "id": identifier or 100 + requirement_index,
        "name": requirement.name,
        "path": requirement.path,
        "head_branch": "main",
        "head_sha": SHA,
        "event": "push",
        "run_attempt": attempt,
        "status": status,
        "conclusion": conclusion,
        "run_started_at": started_at,
    }


def _job(
    requirement_index: int,
    name: str,
    *,
    identifier: int,
    run_id: int | None = None,
    attempt: int = 1,
    status: str = "completed",
    conclusion: str | None = "success",
) -> dict[str, object]:
    requirement = WORKFLOW_REQUIREMENTS[requirement_index]
    return {
        "id": identifier,
        "run_id": run_id or 100 + requirement_index,
        "run_attempt": attempt,
        "workflow_name": requirement.name,
        "head_branch": "main",
        "head_sha": SHA,
        "name": name,
        "status": status,
        "conclusion": conclusion,
    }


def _payload(key: str, items: list[object], *, total_count: int | None = None) -> dict[str, object]:
    return {"total_count": len(items) if total_count is None else total_count, key: items}


def _successful_jobs(requirement_index: int) -> list[object]:
    return [
        _job(requirement_index, name, identifier=1_000 * (requirement_index + 1) + index)
        for index, name in enumerate(WORKFLOW_REQUIREMENTS[requirement_index].jobs, 1)
    ]


def _install_api(
    monkeypatch: pytest.MonkeyPatch,
    *,
    ci_runs: list[object] | None = None,
    codeql_runs: list[object] | None = None,
    ci_jobs: list[object] | None = None,
    codeql_jobs: list[object] | None = None,
) -> list[str]:
    payloads = {
        "/actions/workflows/ci.yml/runs?": _payload(
            "workflow_runs", [_workflow_run(0)] if ci_runs is None else ci_runs
        ),
        "/actions/workflows/codeql.yml/runs?": _payload(
            "workflow_runs", [_workflow_run(1)] if codeql_runs is None else codeql_runs
        ),
        "/actions/runs/100/attempts/1/jobs?": _payload(
            "jobs", _successful_jobs(0) if ci_jobs is None else ci_jobs
        ),
        "/actions/runs/101/attempts/1/jobs?": _payload(
            "jobs", _successful_jobs(1) if codeql_jobs is None else codeql_jobs
        ),
    }
    captured_urls: list[str] = []

    class Response:
        def __init__(self, payload: object) -> None:
            self.payload = payload

        def __enter__(self) -> Response:
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def read(self, limit: int) -> bytes:
            assert limit == verify_release_checks._MAX_PAGE_BYTES + 1
            return json.dumps(self.payload).encode("utf-8")

    def fake_urlopen(request: Request, *, timeout: float) -> Response:
        captured_urls.append(request.full_url)
        assert request.get_header("Authorization") == "Bearer test-token"
        assert timeout == verify_release_checks._REQUEST_TIMEOUT_SECONDS
        for marker, payload in payloads.items():
            if marker in request.full_url:
                return Response(payload)
        raise AssertionError(f"unexpected endpoint: {request.full_url}")

    monkeypatch.setattr(verify_release_checks, "urlopen", fake_urlopen)
    return captured_urls


def test_exact_ci_and_codeql_workflow_attempts_succeed(monkeypatch: pytest.MonkeyPatch) -> None:
    captured_urls = _install_api(monkeypatch)

    verify_release_checks.verify_commit_checks(
        repository="NeonShapeshifter/Otoe",
        commit_sha=SHA,
        token="test-token",
    )

    assert len(captured_urls) == 6
    workflow_urls = [url for url in captured_urls if "/actions/workflows/" in url]
    assert all(f"head_sha={SHA}" in url for url in workflow_urls)
    assert all("branch=main" in url and "event=push" in url for url in workflow_urls)
    assert all("status=" not in url for url in captured_urls)
    assert all("test-token" not in url for url in captured_urls)


def test_newer_pending_ci_run_cannot_reuse_old_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_api(
        monkeypatch,
        ci_runs=[
            _workflow_run(0, identifier=99, started_at="2026-07-17T11:00:00Z"),
            _workflow_run(
                0,
                identifier=100,
                status="in_progress",
                conclusion=None,
                started_at="2026-07-17T13:00:00Z",
            ),
        ],
    )

    with pytest.raises(CheckGateError, match="pending workflow: CI=in_progress"):
        verify_release_checks.verify_commit_checks(
            repository="NeonShapeshifter/Otoe", commit_sha=SHA, token="test-token"
        )


def test_workflow_rerun_started_while_jobs_are_read_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ci_workflow_reads = 0

    class Response:
        def __init__(self, payload: object) -> None:
            self.payload = payload

        def __enter__(self) -> Response:
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def read(self, limit: int) -> bytes:
            del limit
            return json.dumps(self.payload).encode("utf-8")

    def fake_urlopen(request: Request, *, timeout: float) -> Response:
        nonlocal ci_workflow_reads
        del timeout
        if "/actions/workflows/ci.yml/runs?" in request.full_url:
            ci_workflow_reads += 1
            if ci_workflow_reads == 1:
                return Response(_payload("workflow_runs", [_workflow_run(0)]))
            return Response(
                _payload(
                    "workflow_runs",
                    [
                        _workflow_run(
                            0,
                            attempt=2,
                            status="queued",
                            conclusion=None,
                            started_at="2026-07-17T13:00:00Z",
                        )
                    ],
                )
            )
        if "/actions/runs/100/attempts/1/jobs?" in request.full_url:
            return Response(_payload("jobs", _successful_jobs(0)))
        raise AssertionError(f"unexpected endpoint: {request.full_url}")

    monkeypatch.setattr(verify_release_checks, "urlopen", fake_urlopen)

    with pytest.raises(CheckGateError, match="workflow 'CI' changed while its jobs were verified"):
        verify_release_checks.verify_commit_checks(
            repository="NeonShapeshifter/Otoe", commit_sha=SHA, token="test-token"
        )

    assert ci_workflow_reads == 2


def test_missing_ci_workflow_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_api(monkeypatch, ci_runs=[])

    with pytest.raises(CheckGateError, match="missing required push workflow on main: CI"):
        verify_release_checks.verify_commit_checks(
            repository="NeonShapeshifter/Otoe", commit_sha=SHA, token="test-token"
        )


def test_failed_latest_ci_run_cannot_mix_jobs_from_old_suite(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_api(
        monkeypatch,
        ci_runs=[
            _workflow_run(0, identifier=99, started_at="2026-07-17T11:00:00Z"),
            _workflow_run(
                0,
                identifier=100,
                conclusion="failure",
                started_at="2026-07-17T13:00:00Z",
            ),
        ],
    )

    with pytest.raises(CheckGateError, match="unsuccessful workflow: CI=failure"):
        verify_release_checks.verify_commit_checks(
            repository="NeonShapeshifter/Otoe", commit_sha=SHA, token="test-token"
        )


def test_ci_matrix_must_be_complete_in_one_workflow_attempt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_api(monkeypatch, ci_jobs=_successful_jobs(0)[:2])

    with pytest.raises(CheckGateError, match=r"missing required jobs: tests \(3\.13\), tests \(3\.14\)"):
        verify_release_checks.verify_commit_checks(
            repository="NeonShapeshifter/Otoe", commit_sha=SHA, token="test-token"
        )


def test_required_job_must_match_exact_run_attempt_and_sha(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    jobs = _successful_jobs(0)
    assert isinstance(jobs[0], dict)
    jobs[0] = {**jobs[0], "run_attempt": 2}
    _install_api(monkeypatch, ci_jobs=jobs)

    with pytest.raises(CheckGateError, match="bound to another workflow attempt"):
        verify_release_checks.verify_commit_checks(
            repository="NeonShapeshifter/Otoe", commit_sha=SHA, token="test-token"
        )


def test_required_job_pending_or_failed_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    jobs = _successful_jobs(0)
    assert isinstance(jobs[0], dict) and isinstance(jobs[1], dict)
    jobs[0] = {**jobs[0], "status": "queued", "conclusion": None}
    jobs[1] = {**jobs[1], "conclusion": "timed_out"}
    _install_api(monkeypatch, ci_jobs=jobs)

    with pytest.raises(CheckGateError) as caught:
        verify_release_checks.verify_commit_checks(
            repository="NeonShapeshifter/Otoe", commit_sha=SHA, token="test-token"
        )

    assert "pending jobs: tests (3.11)=queued" in str(caught.value)
    assert "unsuccessful jobs: tests (3.12)=timed_out" in str(caught.value)


def test_duplicate_required_job_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    jobs = _successful_jobs(0)
    duplicate = _job(0, "tests (3.11)", identifier=9_999)
    _install_api(monkeypatch, ci_jobs=[*jobs, duplicate])

    with pytest.raises(CheckGateError, match=r"duplicate required jobs.*tests \(3\.11\)"):
        verify_release_checks.verify_commit_checks(
            repository="NeonShapeshifter/Otoe", commit_sha=SHA, token="test-token"
        )


def test_ambiguous_latest_workflow_timestamp_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_api(
        monkeypatch,
        ci_runs=[_workflow_run(0, identifier=100), _workflow_run(0, identifier=200)],
    )

    with pytest.raises(CheckGateError, match="ambiguous latest workflow evidence"):
        verify_release_checks.verify_commit_checks(
            repository="NeonShapeshifter/Otoe", commit_sha=SHA, token="test-token"
        )


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ({"path": ".github/workflows/other.yml"}, "unexpected workflow"),
        ({"head_branch": "feature"}, "not a push run on 'main'"),
        ({"event": "schedule"}, "not a push run on 'main'"),
        ({"head_sha": "b" * 40}, "does not target the requested commit"),
        ({"run_started_at": "yesterday"}, "run_started_at is not ISO 8601"),
        ({"status": "completed", "conclusion": None}, "has no conclusion"),
    ],
)
def test_malformed_or_wrong_workflow_evidence_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
    mutation: dict[str, object],
    message: str,
) -> None:
    _install_api(monkeypatch, ci_runs=[{**_workflow_run(0), **mutation}])

    with pytest.raises(CheckGateError, match=message):
        verify_release_checks.verify_commit_checks(
            repository="NeonShapeshifter/Otoe", commit_sha=SHA, token="test-token"
        )


def test_job_pagination_rejects_duplicate_ids(monkeypatch: pytest.MonkeyPatch) -> None:
    requirement = WORKFLOW_REQUIREMENTS[0]
    run_payload = _payload("workflow_runs", [_workflow_run(0)])
    first_jobs = [_job(0, f"unrelated-{index}", identifier=index + 1) for index in range(100)]
    second_jobs = [_job(0, name, identifier=1) for name in requirement.jobs]
    calls: list[str] = []

    class Response:
        def __init__(self, payload: object) -> None:
            self.payload = payload

        def __enter__(self) -> Response:
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def read(self, limit: int) -> bytes:
            return json.dumps(self.payload).encode("utf-8")

    def fake_urlopen(request: Request, *, timeout: float) -> Response:
        del timeout
        calls.append(request.full_url)
        if "/actions/workflows/ci.yml/runs?" in request.full_url:
            return Response(run_payload)
        if "page=1" in request.full_url:
            return Response(_payload("jobs", first_jobs, total_count=104))
        return Response(_payload("jobs", second_jobs, total_count=104))

    monkeypatch.setattr(verify_release_checks, "urlopen", fake_urlopen)

    with pytest.raises(CheckGateError, match="duplicate job id"):
        verify_release_checks.verify_commit_checks(
            repository="NeonShapeshifter/Otoe", commit_sha=SHA, token="test-token"
        )

    assert any("page=2" in url for url in calls)


def test_invalid_repository_sha_token_and_api_url_fail_before_network() -> None:
    cases: tuple[dict[str, Any], ...] = (
        {"repository": "invalid", "commit_sha": SHA, "token": "token"},
        {"repository": "owner/repo", "commit_sha": "short", "token": "token"},
        {"repository": "owner/repo", "commit_sha": SHA, "token": "bad token"},
        {
            "repository": "owner/repo",
            "commit_sha": SHA,
            "token": "token",
            "api_url": "http://api.github.com",
        },
    )
    for case in cases:
        with pytest.raises(CheckGateError):
            verify_release_checks.verify_commit_checks(**case)
