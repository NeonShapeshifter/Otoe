#!/usr/bin/env python3
from __future__ import annotations

import argparse
from dataclasses import dataclass
from email.parser import BytesParser
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import platform
import re
import select
import stat
import time
from typing import Any, cast
from zipfile import BadZipFile, ZipFile

try:
    from markdown_it import MarkdownIt
    from packaging.utils import canonicalize_name, parse_wheel_filename
    from packaging.version import InvalidVersion, Version
except ModuleNotFoundError as exc:  # pragma: no cover - exercised by release hosts
    raise SystemExit(
        "cold-start evidence requires the 'markdown-it-py' and 'packaging' "
        "release dependencies"
    ) from exc


EVIDENCE_FORMAT = "otoe-cold-start-v1"
SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
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
GENERATED_README_COMMANDS = (
    "otoe check",
    "otoe check --target app:app --css styles.css",
    "otoe render app:app --out preview.html --css styles.css --pretty",
    "otoe render app:app --out preview.png --native --css styles.css",
    "otoe dev app:app --css styles.css",
    "otoe build app:app --out dist/cage --css styles.css --validate",
)
CHECK_MARKERS = {
    "build_validated": "build-validated",
    "check": "check",
    "check_tests": "check-tests",
    "dev_health": "dev-health",
    "html_render": "html-render",
    "native_render": "native-render",
    "package_readme_commands": "package-readme-commands",
    "portable_core_json_match": "portable-core-json-match",
    "readme_commands": "generated-readme-commands",
    "stderr_log_bounded": "stderr-log-bounded",
    "stdout_log_bounded": "stdout-log-bounded",
    "wheel_postinstall_digest": "wheel-postinstall-digest",
    "wheel_preinstall_digest": "wheel-preinstall-digest",
}
ISOLATION_MARKERS = {
    "install_no_deps": "install-no-deps",
    "install_no_index": "install-no-index",
    "source_checkout_on_sys_path": None,
    "wheel_metadata_version_match": "wheel-version-match",
}


class ColdStartEvidenceError(ValueError):
    pass


@dataclass(frozen=True)
class WheelIdentity:
    distribution: str
    filename: str
    sha256: str
    version: str


def file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_sha256(path: Path, expected_sha256: str) -> None:
    if not SHA256_PATTERN.fullmatch(expected_sha256):
        raise ColdStartEvidenceError("expected wheel digest must be lowercase SHA-256")
    observed_sha256 = file_sha256(path)
    if observed_sha256 != expected_sha256:
        raise ColdStartEvidenceError(
            "wheel digest changed: " f"{observed_sha256} != {expected_sha256}"
        )


def capture_bounded_log(
    *,
    source: Path,
    output: Path,
    limit_marker: Path,
    max_bytes: int,
    timeout_seconds: float,
    writer_ready: Path | None = None,
) -> None:
    if max_bytes < 256:
        raise ColdStartEvidenceError("bounded log limit must be at least 256 bytes")
    if not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
        raise ColdStartEvidenceError("bounded log timeout must be positive and finite")

    output.parent.mkdir(parents=True, exist_ok=True)
    limit_marker.unlink(missing_ok=True)
    deadline = time.monotonic() + timeout_seconds
    written = 0
    truncated = False
    timed_out = False
    try:
        source_mode = source.stat().st_mode
        descriptor = os.open(
            source,
            os.O_RDONLY | (os.O_NONBLOCK if stat.S_ISFIFO(source_mode) else 0),
        )
    except OSError as exc:
        raise ColdStartEvidenceError(f"could not open bounded log source: {exc}") from exc
    source_is_fifo = stat.S_ISFIFO(source_mode)
    writer_confirmed = not source_is_fifo
    with os.fdopen(descriptor, "rb", buffering=0) as input_stream, output.open(
        "w+b", buffering=0
    ) as log:
        descriptor = input_stream.fileno()
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                timed_out = True
                break
            readable, _, _ = select.select((descriptor,), (), (), remaining)
            if not readable:
                timed_out = True
                break
            try:
                chunk = os.read(descriptor, 64 * 1024)
            except BlockingIOError:
                continue
            if not chunk:
                if writer_ready is not None and writer_ready.is_file():
                    writer_confirmed = True
                if writer_confirmed:
                    break
                time.sleep(min(0.01, max(0.0, remaining)))
                continue
            writer_confirmed = True
            available = max_bytes - written
            if available > 0:
                retained = chunk[:available]
                log.write(retained)
                written += len(retained)
            if len(chunk) > available:
                truncated = True

        if truncated or timed_out:
            if timed_out:
                notice = b"\n[cold-start log capture timed out]\n"
                reason = "capture-timeout\n"
            else:
                notice = f"\n[cold-start log truncated at {max_bytes} bytes]\n".encode()
                reason = "size-limit\n"
            notice = notice[-max_bytes:]
            notice_start = max(0, min(written, max_bytes) - len(notice))
            log.seek(notice_start)
            log.write(notice)
            log.truncate(min(max_bytes, max(written, notice_start + len(notice))))
            limit_marker.write_text(reason, encoding="utf-8")


def _read_text_tail(path: Path, *, max_bytes: int) -> str | None:
    with path.open("rb") as stream:
        size = stream.seek(0, os.SEEK_END)
        stream.seek(max(0, size - max_bytes))
        content = stream.read(max_bytes)
    return content.decode("utf-8", errors="replace").strip() or None


def _package_readme_bash_blocks(description: str) -> tuple[tuple[str, ...], ...]:
    tokens = MarkdownIt("commonmark").parse(description)
    return tuple(
        tuple(token.content.splitlines())
        for token in tokens
        if token.type == "fence" and token.level == 0 and token.info.strip() == "bash"
    )


def inspect_generated_readme(path: Path) -> None:
    try:
        readme = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise ColdStartEvidenceError(f"could not read generated README: {exc}") from exc
    bash_blocks = _package_readme_bash_blocks(readme)
    if bash_blocks != (GENERATED_README_COMMANDS,):
        raise ColdStartEvidenceError(
            "generated README must contain exactly one top-level bash block "
            "with the canonical commands"
        )
    if "examples." in readme or "PYTHONPATH" in readme:
        raise ColdStartEvidenceError("generated README depends on source-checkout paths")


def inspect_wheel(path: Path) -> WheelIdentity:
    try:
        filename_name, filename_version, _build, _tags = parse_wheel_filename(path.name)
    except (InvalidVersion, ValueError) as exc:
        raise ColdStartEvidenceError(f"invalid wheel filename {path.name!r}: {exc}") from exc

    try:
        with ZipFile(path) as archive:
            dist_info_dirs = {
                name.split("/", 1)[0] for name in archive.namelist() if ".dist-info/" in name
            }
            metadata_members = [
                name for name in archive.namelist() if name.endswith(".dist-info/METADATA")
            ]
            if len(dist_info_dirs) != 1 or len(metadata_members) != 1:
                raise ColdStartEvidenceError(
                    "wheel must contain exactly one dist-info directory and METADATA"
                )
            dist_info_dir = next(iter(dist_info_dirs))
            metadata_member = metadata_members[0]
            if metadata_member != f"{dist_info_dir}/METADATA":
                raise ColdStartEvidenceError(
                    "wheel METADATA is not in its unique dist-info directory"
                )
            metadata = BytesParser().parsebytes(archive.read(metadata_member))
    except (BadZipFile, KeyError, OSError) as exc:
        raise ColdStartEvidenceError(f"could not inspect wheel {path.name!r}: {exc}") from exc

    dist_info_stem = dist_info_dir.removesuffix(".dist-info")
    dist_info_name, separator, dist_info_version_text = dist_info_stem.rpartition("-")
    if not separator or not dist_info_name or not dist_info_version_text:
        raise ColdStartEvidenceError(f"invalid dist-info directory {dist_info_dir!r}")

    metadata_names = metadata.get_all("Name", [])
    metadata_versions = metadata.get_all("Version", [])
    if len(metadata_names) != 1 or len(metadata_versions) != 1:
        raise ColdStartEvidenceError("wheel METADATA must contain exactly one Name and one Version")
    metadata_name = metadata_names[0]
    metadata_version_text = metadata_versions[0]
    if not metadata_name or not metadata_version_text:
        raise ColdStartEvidenceError("wheel METADATA Name and Version cannot be empty")
    try:
        metadata_version = Version(metadata_version_text)
        dist_info_version = Version(dist_info_version_text)
    except InvalidVersion as exc:
        raise ColdStartEvidenceError(f"invalid wheel identity version: {exc}") from exc

    names = {
        canonicalize_name(filename_name),
        canonicalize_name(dist_info_name),
        canonicalize_name(metadata_name),
    }
    if names != {"otoe"}:
        raise ColdStartEvidenceError(
            "wheel filename, dist-info and METADATA names must all identify otoe"
        )
    if not (filename_version == dist_info_version == metadata_version):
        raise ColdStartEvidenceError(
            "wheel filename, dist-info and METADATA versions must match: "
            f"{filename_version}, {dist_info_version}, {metadata_version}"
        )

    description = metadata.get_payload()
    if not isinstance(description, str):
        raise ColdStartEvidenceError("wheel METADATA description must be text")
    bash_blocks = _package_readme_bash_blocks(description)
    if bash_blocks.count(PACKAGE_README_COMMANDS) != 1:
        raise ColdStartEvidenceError(
            "wheel package README must contain exactly one contiguous bash quickstart "
            "block with the canonical cold-start commands"
        )

    return WheelIdentity(
        distribution="otoe",
        filename=path.name,
        sha256=file_sha256(path),
        version=str(filename_version),
    )


def build_evidence(
    *,
    workdir: Path,
    wheel: Path,
    outcome: str,
    worker_exit_code: int,
    elapsed_seconds: float,
    budget_seconds: int,
    expected_sha256: str | None,
    error: str | None,
) -> dict[str, Any]:
    progress = workdir / "progress"
    copied_wheel = workdir / "artifact" / wheel.name
    identity_path = copied_wheel if copied_wheel.is_file() else wheel
    source_sha256 = file_sha256(wheel) if wheel.is_file() else None
    tested_sha256 = file_sha256(copied_wheel) if copied_wheel.is_file() else None
    source_copy_match = (
        source_sha256 is not None and tested_sha256 is not None and source_sha256 == tested_sha256
    )
    expected_copy_match = expected_sha256 is not None and expected_sha256 == tested_sha256
    expected_source_match = expected_sha256 is not None and expected_sha256 == source_sha256
    identity_error: str | None = None
    try:
        identity = inspect_wheel(identity_path)
        wheel_payload: dict[str, Any] = {
            "distribution": identity.distribution,
            "filename": identity.filename,
            "expected_copy_match": expected_copy_match,
            "expected_sha256": expected_sha256,
            "expected_source_match": expected_source_match,
            "identity_valid": True,
            "sha256": identity.sha256,
            "source_copy_match": source_copy_match,
            "source_sha256": source_sha256,
            "version": identity.version,
        }
    except ColdStartEvidenceError as exc:
        identity_error = str(exc)
        wheel_payload = {
            "filename": identity_path.name,
            "expected_copy_match": expected_copy_match,
            "expected_sha256": expected_sha256,
            "expected_source_match": expected_source_match,
            "identity_valid": False,
            "sha256": file_sha256(identity_path) if identity_path.is_file() else None,
            "source_copy_match": source_copy_match,
            "source_sha256": source_sha256,
            "version": None,
        }

    checks = {name: (progress / marker).is_file() for name, marker in CHECK_MARKERS.items()}
    checks["wheel_expected_copy_match"] = expected_copy_match
    checks["wheel_expected_source_match"] = expected_source_match
    checks["wheel_source_copy_match"] = source_copy_match
    isolation = {
        name: False if marker is None else (progress / marker).is_file()
        for name, marker in ISOLATION_MARKERS.items()
    }
    isolation["source_checkout_on_sys_path"] = not (progress / "source-checkout-absent").is_file()

    recorded_elapsed_seconds = round(elapsed_seconds, 3)
    within_budget = recorded_elapsed_seconds < budget_seconds
    required_passed = (
        all(checks.values())
        and isolation
        == {
            "install_no_deps": True,
            "install_no_index": True,
            "source_checkout_on_sys_path": False,
            "wheel_metadata_version_match": True,
        }
        and wheel_payload["identity_valid"] is True
        and expected_copy_match
        and expected_source_match
        and wheel_payload["sha256"] == expected_sha256
        and (progress / "completed").is_file()
        and within_budget
    )
    if outcome == "passed" and not required_passed:
        outcome = "failed"
        error = error or "worker exited successfully without complete cold-start evidence"

    artifacts: dict[str, dict[str, int | str]] = {}
    for name in ("preview.html", "preview.png"):
        path = workdir / "app" / name
        if path.is_file():
            artifacts[name] = {"bytes": path.stat().st_size, "sha256": file_sha256(path)}

    combined_error = error
    if identity_error is not None:
        combined_error = f"{combined_error}; {identity_error}" if combined_error else identity_error
    payload: dict[str, Any] = {
        "artifacts": artifacts,
        "checks": checks,
        "error": combined_error,
        "format": EVIDENCE_FORMAT,
        "isolation": isolation,
        "outcome": outcome,
        "python": platform.python_version(),
        "timing": {
            "budget_seconds": budget_seconds,
            "elapsed_seconds": recorded_elapsed_seconds,
            "scope": "controller-digest-through-generated-app-validation",
            "within_budget": within_budget,
        },
        "wheel": wheel_payload,
        "worker_exit_code": worker_exit_code,
    }
    validate_evidence(payload)
    return payload


def validate_evidence(payload: dict[str, Any]) -> None:
    if payload.get("format") != EVIDENCE_FORMAT:
        raise ColdStartEvidenceError("invalid cold-start evidence format")
    if payload.get("outcome") not in {"passed", "failed", "timeout"}:
        raise ColdStartEvidenceError("invalid cold-start outcome")
    if not isinstance(payload.get("python"), str) or not payload["python"]:
        raise ColdStartEvidenceError("cold-start evidence has no Python version")
    worker_exit_code = payload.get("worker_exit_code")
    if not isinstance(worker_exit_code, int) or isinstance(worker_exit_code, bool):
        raise ColdStartEvidenceError("cold-start evidence has an invalid worker exit status")
    if payload.get("error") is not None and not isinstance(payload["error"], str):
        raise ColdStartEvidenceError("cold-start evidence error must be text or null")
    if payload["outcome"] != "passed" and not payload.get("error"):
        raise ColdStartEvidenceError("non-passing evidence requires an error report")
    if payload["outcome"] == "timeout" and worker_exit_code not in {124, 137}:
        raise ColdStartEvidenceError("timeout evidence has an invalid worker exit status")
    timing = payload.get("timing")
    if not isinstance(timing, dict) or timing.get("budget_seconds") != 300:
        raise ColdStartEvidenceError("cold-start evidence must enforce a 300-second budget")
    elapsed = timing.get("elapsed_seconds")
    if (
        not isinstance(elapsed, (int, float))
        or isinstance(elapsed, bool)
        or not math.isfinite(elapsed)
        or elapsed < 0
    ):
        raise ColdStartEvidenceError("cold-start evidence has invalid elapsed time")
    if timing.get("within_budget") is not (elapsed < 300):
        raise ColdStartEvidenceError("cold-start evidence has inconsistent budget status")
    if timing.get("scope") != "controller-digest-through-generated-app-validation":
        raise ColdStartEvidenceError("cold-start evidence has an invalid timing scope")
    wheel = payload.get("wheel")
    if not isinstance(wheel, dict):
        raise ColdStartEvidenceError("cold-start evidence has no wheel identity")
    if not isinstance(wheel.get("filename"), str) or not wheel["filename"].endswith(".whl"):
        raise ColdStartEvidenceError("cold-start evidence has an invalid wheel filename")
    if not isinstance(wheel.get("identity_valid"), bool):
        raise ColdStartEvidenceError("cold-start evidence has an invalid identity result")
    if not isinstance(wheel.get("source_copy_match"), bool):
        raise ColdStartEvidenceError("cold-start evidence has an invalid source-copy result")
    if not isinstance(wheel.get("expected_copy_match"), bool):
        raise ColdStartEvidenceError("cold-start evidence has an invalid expected-copy result")
    if not isinstance(wheel.get("expected_source_match"), bool):
        raise ColdStartEvidenceError("cold-start evidence has an invalid expected-source result")
    digest = wheel.get("sha256")
    if digest is not None and (not isinstance(digest, str) or not SHA256_PATTERN.fullmatch(digest)):
        raise ColdStartEvidenceError("cold-start evidence has an invalid wheel digest")
    source_digest = wheel.get("source_sha256")
    if source_digest is not None and (
        not isinstance(source_digest, str) or not SHA256_PATTERN.fullmatch(source_digest)
    ):
        raise ColdStartEvidenceError("cold-start evidence has an invalid source wheel digest")
    expected_digest = wheel.get("expected_sha256")
    if expected_digest is not None and (
        not isinstance(expected_digest, str) or not SHA256_PATTERN.fullmatch(expected_digest)
    ):
        raise ColdStartEvidenceError("cold-start evidence has an invalid expected wheel digest")
    checks = payload.get("checks")
    expected_checks = {
        *CHECK_MARKERS,
        "wheel_expected_copy_match",
        "wheel_expected_source_match",
        "wheel_source_copy_match",
    }
    if not isinstance(checks, dict) or set(checks) != expected_checks:
        raise ColdStartEvidenceError("cold-start evidence has an invalid check set")
    if any(not isinstance(value, bool) for value in checks.values()):
        raise ColdStartEvidenceError("cold-start evidence checks must be booleans")
    isolation = payload.get("isolation")
    if not isinstance(isolation, dict) or set(isolation) != set(ISOLATION_MARKERS):
        raise ColdStartEvidenceError("cold-start evidence has an invalid isolation set")
    if any(not isinstance(value, bool) for value in isolation.values()):
        raise ColdStartEvidenceError("cold-start isolation assertions must be booleans")
    artifacts = payload.get("artifacts")
    if not isinstance(artifacts, dict):
        raise ColdStartEvidenceError("cold-start artifacts must be an object")
    if not set(artifacts).issubset({"preview.html", "preview.png"}):
        raise ColdStartEvidenceError("cold-start evidence has an unknown render artifact")
    for artifact in artifacts.values():
        if not isinstance(artifact, dict):
            raise ColdStartEvidenceError("cold-start artifact evidence must be an object")
        size = artifact.get("bytes")
        artifact_digest = artifact.get("sha256")
        if not isinstance(size, int) or isinstance(size, bool) or size <= 0:
            raise ColdStartEvidenceError("cold-start artifact size must be positive")
        if not isinstance(artifact_digest, str) or not SHA256_PATTERN.fullmatch(artifact_digest):
            raise ColdStartEvidenceError("cold-start artifact digest is invalid")
    if payload["outcome"] == "passed":
        if payload.get("error") is not None:
            raise ColdStartEvidenceError("passing evidence cannot contain an error")
        if not timing.get("within_budget"):
            raise ColdStartEvidenceError("passing evidence exceeded its budget")
        if payload.get("worker_exit_code") != 0:
            raise ColdStartEvidenceError("passing evidence requires worker exit status zero")
        if wheel.get("identity_valid") is not True:
            raise ColdStartEvidenceError("passing evidence requires a valid wheel identity")
        if (
            wheel.get("distribution") != "otoe"
            or not isinstance(wheel.get("version"), str)
            or not wheel["version"]
        ):
            raise ColdStartEvidenceError("passing evidence requires canonical wheel identity")
        if (
            wheel.get("source_copy_match") is not True
            or wheel.get("expected_copy_match") is not True
            or wheel.get("expected_source_match") is not True
            or expected_digest != digest
            or expected_digest != source_digest
        ):
            raise ColdStartEvidenceError(
                "passing evidence requires the controller-bound wheel digest to remain unchanged"
            )
        if isolation != {
            "install_no_deps": True,
            "install_no_index": True,
            "source_checkout_on_sys_path": False,
            "wheel_metadata_version_match": True,
        }:
            raise ColdStartEvidenceError("passing evidence requires exact isolation assertions")
        if set(artifacts) != {"preview.html", "preview.png"}:
            raise ColdStartEvidenceError("passing evidence requires both render artifacts")
        if not all(checks.values()):
            raise ColdStartEvidenceError("passing evidence has incomplete checks")


def write_evidence(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    subcommands = parser.add_subparsers(dest="command", required=True)
    inspect = subcommands.add_parser("inspect")
    inspect.add_argument("wheel", type=Path)
    inspect.add_argument("output", type=Path)
    inspect.add_argument("--expected-sha256")
    generated_readme = subcommands.add_parser("inspect-generated-readme")
    generated_readme.add_argument("readme", type=Path)
    digest = subcommands.add_parser("sha256")
    digest.add_argument("path", type=Path)
    verify_digest = subcommands.add_parser("verify-sha256")
    verify_digest.add_argument("path", type=Path)
    verify_digest.add_argument("expected_sha256")
    capture_log = subcommands.add_parser("capture-log")
    capture_log.add_argument("--source", required=True, type=Path)
    capture_log.add_argument("--output", required=True, type=Path)
    capture_log.add_argument("--limit-marker", required=True, type=Path)
    capture_log.add_argument("--max-bytes", required=True, type=int)
    capture_log.add_argument("--timeout-seconds", required=True, type=float)
    capture_log.add_argument("--writer-ready", type=Path)
    close_fds_exec = subcommands.add_parser("exec-with-closed-fds")
    close_fds_exec.add_argument("--fd", action="append", required=True, type=int)
    close_fds_exec.add_argument("exec_command", nargs=argparse.REMAINDER)
    finalize = subcommands.add_parser("finalize")
    finalize.add_argument("--workdir", required=True, type=Path)
    finalize.add_argument("--wheel", required=True, type=Path)
    finalize.add_argument("--output", required=True, type=Path)
    finalize.add_argument("--outcome", required=True, choices=("passed", "failed", "timeout"))
    finalize.add_argument("--worker-exit-code", required=True, type=int)
    finalize.add_argument("--elapsed-seconds", required=True, type=float)
    finalize.add_argument("--budget-seconds", required=True, type=int)
    finalize.add_argument("--expected-sha256")
    finalize.add_argument("--error-file", type=Path)
    return parser


def main() -> int:
    args = _parser().parse_args()
    if args.command == "inspect":
        identity = inspect_wheel(args.wheel)
        if args.expected_sha256 is not None and identity.sha256 != args.expected_sha256:
            raise ColdStartEvidenceError(
                "copied wheel digest does not match the controller-bound source digest"
            )
        write_evidence(
            args.output,
            {
                "distribution": identity.distribution,
                "filename": identity.filename,
                "package_readme_commands": True,
                "sha256": identity.sha256,
                "version": identity.version,
            },
        )
        return 0
    if args.command == "inspect-generated-readme":
        inspect_generated_readme(args.readme)
        return 0
    if args.command == "sha256":
        print(file_sha256(args.path))
        return 0
    if args.command == "verify-sha256":
        verify_sha256(args.path, args.expected_sha256)
        return 0
    if args.command == "capture-log":
        capture_bounded_log(
            source=args.source,
            output=args.output,
            limit_marker=args.limit_marker,
            max_bytes=args.max_bytes,
            timeout_seconds=args.timeout_seconds,
            writer_ready=args.writer_ready,
        )
        return 0
    if args.command == "exec-with-closed-fds":
        descriptors = cast(list[int], args.fd)
        if any(descriptor < 3 for descriptor in descriptors):
            raise ColdStartEvidenceError("refusing to close a standard stream descriptor")
        command = cast(list[str], args.exec_command)
        if command and command[0] == "--":
            command = command[1:]
        if not command or not Path(command[0]).is_absolute():
            raise ColdStartEvidenceError("exec command must start with an absolute executable")
        for descriptor in set(descriptors):
            os.close(descriptor)
        os.execv(command[0], command)

    error = None
    if args.error_file is not None and args.error_file.is_file():
        error = _read_text_tail(args.error_file, max_bytes=4000)
    payload = build_evidence(
        workdir=args.workdir,
        wheel=args.wheel,
        outcome=args.outcome,
        worker_exit_code=args.worker_exit_code,
        elapsed_seconds=args.elapsed_seconds,
        budget_seconds=args.budget_seconds,
        expected_sha256=args.expected_sha256,
        error=error,
    )
    write_evidence(args.output, payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
