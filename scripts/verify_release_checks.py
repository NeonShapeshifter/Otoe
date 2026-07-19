#!/usr/bin/env python3
"""Fail closed unless exact GitHub workflow runs passed for the release commit."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
import os
import re
import sys
from typing import Final, cast
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urlsplit
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class WorkflowRequirement:
    file: str
    name: str
    path: str
    jobs: tuple[str, ...]


WORKFLOW_REQUIREMENTS: Final[tuple[WorkflowRequirement, ...]] = (
    WorkflowRequirement(
        file="ci.yml",
        name="CI",
        path=".github/workflows/ci.yml",
        jobs=("tests (3.11)", "tests (3.12)", "tests (3.13)", "tests (3.14)"),
    ),
    WorkflowRequirement(
        file="codeql.yml",
        name="CodeQL",
        path=".github/workflows/codeql.yml",
        jobs=("Analyze Python",),
    ),
)
REQUIRED_CHECKS: Final[tuple[str, ...]] = tuple(
    job for requirement in WORKFLOW_REQUIREMENTS for job in requirement.jobs
)
_API_VERSION: Final = "2022-11-28"
_MAX_RESULTS: Final = 1_000
_MAX_PAGE_BYTES: Final = 4 * 1024 * 1024
_PER_PAGE: Final = 100
_REQUEST_TIMEOUT_SECONDS: Final = 30.0
_RELEASE_BRANCH: Final = "main"
_RELEASE_EVENT: Final = "push"
_SHA_PATTERN: Final = re.compile(r"[0-9a-fA-F]{40}(?:[0-9a-fA-F]{24})?")


class CheckGateError(RuntimeError):
    """The remote workflow evidence is absent, unsuccessful, or untrustworthy."""


@dataclass(frozen=True)
class WorkflowRun:
    identifier: int
    attempt: int
    status: str
    conclusion: str | None
    started_at: datetime


@dataclass(frozen=True)
class WorkflowJob:
    identifier: int
    name: str
    status: str
    conclusion: str | None


def _require_environment(name: str) -> str:
    value = os.environ.get(name, "")
    if not value:
        raise CheckGateError(f"required environment variable {name} is missing")
    return value


def _validate_inputs(repository: str, commit_sha: str, token: str, api_url: str) -> tuple[str, str]:
    repository_parts = repository.split("/")
    if len(repository_parts) != 2 or not all(repository_parts):
        raise CheckGateError("release repository must have the form owner/repository")
    if _SHA_PATTERN.fullmatch(commit_sha) is None:
        raise CheckGateError("release SHA must be a full 40- or 64-character hexadecimal commit SHA")
    if not token or any(character.isspace() for character in token):
        raise CheckGateError("release token is empty or contains whitespace")

    parsed_api_url = urlsplit(api_url)
    if (
        parsed_api_url.scheme != "https"
        or not parsed_api_url.netloc
        or parsed_api_url.query
        or parsed_api_url.fragment
    ):
        raise CheckGateError("release API URL must be HTTPS and have no query or fragment")
    return repository_parts[0], repository_parts[1]


def _parse_timestamp(value: object, *, context: str, field: str) -> datetime:
    if not isinstance(value, str):
        raise CheckGateError(
            f"malformed GitHub Actions response: {context}.{field} is not a string"
        )
    normalized = f"{value[:-1]}+00:00" if value.endswith("Z") else value
    try:
        timestamp = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise CheckGateError(
            f"malformed GitHub Actions response: {context}.{field} is not ISO 8601"
        ) from exc
    if timestamp.tzinfo is None:
        raise CheckGateError(
            f"malformed GitHub Actions response: {context}.{field} has no timezone"
        )
    return timestamp


def _parse_collection(payload: object, *, key: str) -> tuple[int, list[object]]:
    if not isinstance(payload, dict):
        raise CheckGateError("malformed GitHub Actions response: top-level value is not an object")
    data = cast(dict[str, object], payload)
    total_count = data.get("total_count")
    if isinstance(total_count, bool) or not isinstance(total_count, int) or total_count < 0:
        raise CheckGateError(
            "malformed GitHub Actions response: total_count is not a non-negative integer"
        )
    if total_count > _MAX_RESULTS:
        raise CheckGateError(
            f"GitHub Actions response has {total_count} entries; refusing to inspect more than "
            f"{_MAX_RESULTS}"
        )
    raw_items = data.get(key)
    if not isinstance(raw_items, list):
        raise CheckGateError(f"malformed GitHub Actions response: {key} is not an array")
    if len(raw_items) > total_count:
        raise CheckGateError("malformed GitHub Actions response: page exceeds total_count")
    return total_count, raw_items


def _positive_integer(value: object, *, context: str, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise CheckGateError(
            f"malformed GitHub Actions response: {context}.{field} is not a positive integer"
        )
    return value


def _status_and_conclusion(data: dict[str, object], *, context: str) -> tuple[str, str | None]:
    status = data.get("status")
    if not isinstance(status, str) or not status:
        raise CheckGateError(
            f"malformed GitHub Actions response: {context}.status is not a non-empty string"
        )
    conclusion = data.get("conclusion")
    if conclusion is not None and not isinstance(conclusion, str):
        raise CheckGateError(
            f"malformed GitHub Actions response: {context}.conclusion is invalid"
        )
    if status == "completed" and not isinstance(conclusion, str):
        raise CheckGateError(
            f"malformed GitHub Actions response: completed {context} has no conclusion"
        )
    return status, conclusion


def _parse_workflow_page(
    payload: object,
    *,
    requirement: WorkflowRequirement,
    expected_sha: str,
) -> tuple[int, int, tuple[int, ...], tuple[WorkflowRun, ...]]:
    total_count, raw_runs = _parse_collection(payload, key="workflow_runs")
    identifiers: list[int] = []
    runs: list[WorkflowRun] = []
    for index, raw_run in enumerate(raw_runs):
        context = f"workflow_runs[{index}]"
        if not isinstance(raw_run, dict):
            raise CheckGateError(
                f"malformed GitHub Actions response: {context} is not an object"
            )
        run = cast(dict[str, object], raw_run)
        identifier = _positive_integer(run.get("id"), context=context, field="id")
        identifiers.append(identifier)
        if run.get("name") != requirement.name or run.get("path") != requirement.path:
            raise CheckGateError(
                f"workflow endpoint for {requirement.file!r} returned an unexpected workflow"
            )
        if run.get("head_branch") != _RELEASE_BRANCH or run.get("event") != _RELEASE_EVENT:
            raise CheckGateError(
                f"workflow {requirement.name!r} is not a {_RELEASE_EVENT} run on "
                f"{_RELEASE_BRANCH!r}"
            )
        head_sha = run.get("head_sha")
        if not isinstance(head_sha, str) or head_sha.lower() != expected_sha.lower():
            raise CheckGateError(
                f"workflow {requirement.name!r} does not target the requested commit"
            )
        attempt = _positive_integer(run.get("run_attempt"), context=context, field="run_attempt")
        status, conclusion = _status_and_conclusion(run, context=context)
        runs.append(
            WorkflowRun(
                identifier=identifier,
                attempt=attempt,
                status=status,
                conclusion=conclusion,
                started_at=_parse_timestamp(
                    run.get("run_started_at"), context=context, field="run_started_at"
                ),
            )
        )
    return total_count, len(raw_runs), tuple(identifiers), tuple(runs)


def _parse_jobs_page(
    payload: object,
    *,
    requirement: WorkflowRequirement,
    workflow_run: WorkflowRun,
    expected_sha: str,
) -> tuple[int, int, tuple[int, ...], tuple[WorkflowJob, ...]]:
    total_count, raw_jobs = _parse_collection(payload, key="jobs")
    identifiers: list[int] = []
    jobs: list[WorkflowJob] = []
    for index, raw_job in enumerate(raw_jobs):
        context = f"jobs[{index}]"
        if not isinstance(raw_job, dict):
            raise CheckGateError(
                f"malformed GitHub Actions response: {context} is not an object"
            )
        job = cast(dict[str, object], raw_job)
        identifier = _positive_integer(job.get("id"), context=context, field="id")
        identifiers.append(identifier)
        name = job.get("name")
        if not isinstance(name, str):
            raise CheckGateError(
                f"malformed GitHub Actions response: {context}.name is not a string"
            )
        if name not in requirement.jobs:
            continue
        if (
            job.get("run_id") != workflow_run.identifier
            or job.get("run_attempt") != workflow_run.attempt
        ):
            raise CheckGateError(f"required job {name!r} is bound to another workflow attempt")
        if job.get("workflow_name") != requirement.name:
            raise CheckGateError(f"required job {name!r} has an unexpected workflow name")
        if job.get("head_branch") != _RELEASE_BRANCH:
            raise CheckGateError(f"required job {name!r} is not bound to {_RELEASE_BRANCH!r}")
        head_sha = job.get("head_sha")
        if not isinstance(head_sha, str) or head_sha.lower() != expected_sha.lower():
            raise CheckGateError(f"required job {name!r} does not target the requested commit")
        status, conclusion = _status_and_conclusion(job, context=context)
        jobs.append(
            WorkflowJob(
                identifier=identifier,
                name=name,
                status=status,
                conclusion=conclusion,
            )
        )
    return total_count, len(raw_jobs), tuple(identifiers), tuple(jobs)


def _request_json(*, endpoint: str, token: str) -> object:
    request = Request(
        endpoint,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": _API_VERSION,
        },
    )
    try:
        with urlopen(request, timeout=_REQUEST_TIMEOUT_SECONDS) as response:
            body: bytes = response.read(_MAX_PAGE_BYTES + 1)
    except HTTPError as exc:
        raise CheckGateError(f"GitHub Actions API returned HTTP {exc.code}") from exc
    except (URLError, TimeoutError, OSError, ValueError) as exc:
        raise CheckGateError(f"could not query the GitHub Actions API: {exc}") from exc
    if len(body) > _MAX_PAGE_BYTES:
        raise CheckGateError("GitHub Actions API response exceeded the bounded page size")
    try:
        payload: object = json.loads(body)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CheckGateError("GitHub Actions API returned malformed JSON") from exc
    return payload


def _workflow_endpoint(
    *,
    api_url: str,
    owner: str,
    repository: str,
    requirement: WorkflowRequirement,
    commit_sha: str,
    page: int,
) -> str:
    query = urlencode(
        {
            "branch": _RELEASE_BRANCH,
            "event": _RELEASE_EVENT,
            "head_sha": commit_sha,
            "per_page": _PER_PAGE,
            "page": page,
        }
    )
    return (
        f"{api_url.rstrip('/')}/repos/{quote(owner, safe='')}/{quote(repository, safe='')}/"
        f"actions/workflows/{quote(requirement.file, safe='')}/runs?{query}"
    )


def _jobs_endpoint(
    *,
    api_url: str,
    owner: str,
    repository: str,
    workflow_run: WorkflowRun,
    page: int,
) -> str:
    query = urlencode({"filter": "latest", "per_page": _PER_PAGE, "page": page})
    return (
        f"{api_url.rstrip('/')}/repos/{quote(owner, safe='')}/{quote(repository, safe='')}/"
        f"actions/runs/{workflow_run.identifier}/attempts/{workflow_run.attempt}/jobs?{query}"
    )


def _fetch_workflow_runs(
    *,
    api_url: str,
    owner: str,
    repository: str,
    requirement: WorkflowRequirement,
    commit_sha: str,
    token: str,
) -> tuple[WorkflowRun, ...]:
    expected_total: int | None = None
    fetched_count = 0
    seen_ids: set[int] = set()
    runs: list[WorkflowRun] = []
    page = 1
    while True:
        payload = _request_json(
            endpoint=_workflow_endpoint(
                api_url=api_url,
                owner=owner,
                repository=repository,
                requirement=requirement,
                commit_sha=commit_sha,
                page=page,
            ),
            token=token,
        )
        total_count, page_count, identifiers, parsed_runs = _parse_workflow_page(
            payload, requirement=requirement, expected_sha=commit_sha
        )
        if expected_total is None:
            expected_total = total_count
        elif total_count != expected_total:
            raise CheckGateError("workflow total_count changed while the response was paginated")
        if seen_ids.intersection(identifiers) or len(set(identifiers)) != len(identifiers):
            raise CheckGateError("workflow pagination returned a duplicate run id")
        seen_ids.update(identifiers)
        fetched_count += page_count
        if fetched_count > total_count:
            raise CheckGateError("malformed GitHub Actions response: pages exceed total_count")
        runs.extend(parsed_runs)
        if fetched_count == total_count:
            return tuple(runs)
        if page_count == 0:
            raise CheckGateError("workflow pagination ended before total_count")
        page += 1


def _fetch_workflow_jobs(
    *,
    api_url: str,
    owner: str,
    repository: str,
    requirement: WorkflowRequirement,
    workflow_run: WorkflowRun,
    commit_sha: str,
    token: str,
) -> tuple[WorkflowJob, ...]:
    expected_total: int | None = None
    fetched_count = 0
    seen_ids: set[int] = set()
    jobs: list[WorkflowJob] = []
    page = 1
    while True:
        payload = _request_json(
            endpoint=_jobs_endpoint(
                api_url=api_url,
                owner=owner,
                repository=repository,
                workflow_run=workflow_run,
                page=page,
            ),
            token=token,
        )
        total_count, page_count, identifiers, parsed_jobs = _parse_jobs_page(
            payload,
            requirement=requirement,
            workflow_run=workflow_run,
            expected_sha=commit_sha,
        )
        if expected_total is None:
            expected_total = total_count
        elif total_count != expected_total:
            raise CheckGateError("job total_count changed while the response was paginated")
        if seen_ids.intersection(identifiers) or len(set(identifiers)) != len(identifiers):
            raise CheckGateError("job pagination returned a duplicate job id")
        seen_ids.update(identifiers)
        fetched_count += page_count
        if fetched_count > total_count:
            raise CheckGateError("malformed GitHub Actions response: pages exceed total_count")
        jobs.extend(parsed_jobs)
        if fetched_count == total_count:
            return tuple(jobs)
        if page_count == 0:
            raise CheckGateError("job pagination ended before total_count")
        page += 1


def _latest_workflow_run(
    requirement: WorkflowRequirement,
    runs: tuple[WorkflowRun, ...],
) -> WorkflowRun:
    if not runs:
        raise CheckGateError(
            f"missing required {_RELEASE_EVENT} workflow on {_RELEASE_BRANCH}: {requirement.name}"
        )
    latest_started_at = max(run.started_at for run in runs)
    latest_runs = tuple(run for run in runs if run.started_at == latest_started_at)
    if len(latest_runs) != 1:
        raise CheckGateError(
            f"ambiguous latest workflow evidence for {requirement.name!r}"
        )
    return latest_runs[0]


def _require_successful_run(requirement: WorkflowRequirement, run: WorkflowRun) -> None:
    if run.status != "completed":
        raise CheckGateError(f"pending workflow: {requirement.name}={run.status}")
    if run.conclusion != "success":
        raise CheckGateError(
            f"unsuccessful workflow: {requirement.name}={run.conclusion}"
        )


def _require_successful_jobs(
    requirement: WorkflowRequirement,
    jobs: tuple[WorkflowJob, ...],
) -> None:
    by_name: dict[str, WorkflowJob] = {}
    duplicates: list[str] = []
    for job in jobs:
        if job.name in by_name:
            duplicates.append(job.name)
        else:
            by_name[job.name] = job
    if duplicates:
        raise CheckGateError(
            f"duplicate required jobs in {requirement.name}: {', '.join(sorted(set(duplicates)))}"
        )
    missing = [name for name in requirement.jobs if name not in by_name]
    pending = [
        f"{name}={by_name[name].status}"
        for name in requirement.jobs
        if name in by_name and by_name[name].status != "completed"
    ]
    failed = [
        f"{name}={by_name[name].conclusion}"
        for name in requirement.jobs
        if name in by_name
        and by_name[name].status == "completed"
        and by_name[name].conclusion != "success"
    ]
    problems: list[str] = []
    if missing:
        problems.append(f"missing required jobs: {', '.join(missing)}")
    if pending:
        problems.append(f"pending jobs: {', '.join(pending)}")
    if failed:
        problems.append(f"unsuccessful jobs: {', '.join(failed)}")
    if problems:
        raise CheckGateError(f"{requirement.name}: {'; '.join(problems)}")


def verify_commit_checks(
    *,
    repository: str,
    commit_sha: str,
    token: str,
    api_url: str = "https://api.github.com",
) -> None:
    owner, repository_name = _validate_inputs(repository, commit_sha, token, api_url)
    for requirement in WORKFLOW_REQUIREMENTS:
        runs = _fetch_workflow_runs(
            api_url=api_url,
            owner=owner,
            repository=repository_name,
            requirement=requirement,
            commit_sha=commit_sha,
            token=token,
        )
        latest_run = _latest_workflow_run(requirement, runs)
        _require_successful_run(requirement, latest_run)
        jobs = _fetch_workflow_jobs(
            api_url=api_url,
            owner=owner,
            repository=repository_name,
            requirement=requirement,
            workflow_run=latest_run,
            commit_sha=commit_sha,
            token=token,
        )
        _require_successful_jobs(requirement, jobs)
        confirmed_runs = _fetch_workflow_runs(
            api_url=api_url,
            owner=owner,
            repository=repository_name,
            requirement=requirement,
            commit_sha=commit_sha,
            token=token,
        )
        confirmed_run = _latest_workflow_run(requirement, confirmed_runs)
        if confirmed_run != latest_run:
            raise CheckGateError(
                f"workflow {requirement.name!r} changed while its jobs were verified"
            )


def main() -> int:
    try:
        repository = _require_environment("RELEASE_CHECK_REPOSITORY")
        commit_sha = _require_environment("RELEASE_CHECK_SHA")
        token = _require_environment("RELEASE_CHECK_TOKEN")
        api_url = os.environ.get("RELEASE_CHECK_API_URL", "https://api.github.com")
        verify_commit_checks(
            repository=repository,
            commit_sha=commit_sha,
            token=token,
            api_url=api_url,
        )
    except CheckGateError as exc:
        print(f"release check gate: {exc}", file=sys.stderr)
        return 1
    print(f"release check gate: required workflows passed for {repository}@{commit_sha}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
