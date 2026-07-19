#!/usr/bin/env python3
"""Verify that release archives have one exact, internally consistent identity."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from dataclasses import dataclass
from email.message import Message
from email.parser import BytesParser
from email.policy import default as default_email_policy
from pathlib import Path
import stat
import sys
import tarfile
import tomllib
from typing import Final, cast
import zipfile

from packaging.utils import (
    InvalidName,
    InvalidSdistFilename,
    InvalidWheelFilename,
    canonicalize_name,
    parse_sdist_filename,
    parse_wheel_filename,
)
from packaging.version import InvalidVersion, Version


EXPECTED_DISTRIBUTION: Final = "otoe"
_MAX_PROJECT_BYTES: Final = 1024 * 1024
_MAX_ARCHIVE_BYTES: Final = 128 * 1024 * 1024
_MAX_ARCHIVE_MEMBERS: Final = 20_000
_MAX_MEMBER_BYTES: Final = 64 * 1024 * 1024
_MAX_EXPANDED_BYTES: Final = 256 * 1024 * 1024
_MAX_METADATA_BYTES: Final = 1024 * 1024
_READ_CHUNK_BYTES: Final = 64 * 1024


class ArtifactVerificationError(RuntimeError):
    """A release artifact is absent, ambiguous, unsafe, or inconsistent."""


@dataclass(frozen=True)
class ProjectIdentity:
    distribution: str
    version: Version
    version_text: str


@dataclass(frozen=True)
class VerifiedArtifacts:
    identity: ProjectIdentity
    wheel: Path
    sdist: Path


def _require_bounded_regular_file(path: Path, *, label: str, maximum: int) -> int:
    try:
        file_stat = path.lstat()
    except OSError as exc:
        raise ArtifactVerificationError(f"cannot inspect {label} {path}: {exc}") from exc
    if not stat.S_ISREG(file_stat.st_mode):
        raise ArtifactVerificationError(f"{label} must be a regular file, not a link or directory: {path}")
    if file_stat.st_size <= 0:
        raise ArtifactVerificationError(f"{label} is empty: {path}")
    if file_stat.st_size > maximum:
        raise ArtifactVerificationError(
            f"{label} is {file_stat.st_size} bytes; the limit is {maximum} bytes: {path}"
        )
    return file_stat.st_size


def load_project_identity(project_path: Path) -> ProjectIdentity:
    """Load and validate the static PEP 621 release identity."""

    _require_bounded_regular_file(
        project_path,
        label="project file",
        maximum=_MAX_PROJECT_BYTES,
    )
    try:
        document = tomllib.loads(project_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        raise ArtifactVerificationError(f"cannot parse project TOML {project_path}: {exc}") from exc

    raw_project: object = document.get("project")
    if not isinstance(raw_project, dict):
        raise ArtifactVerificationError("project TOML has no [project] table")
    project = cast(dict[str, object], raw_project)

    raw_name = project.get("name")
    if not isinstance(raw_name, str):
        raise ArtifactVerificationError("project.name must be a string")
    try:
        distribution = str(canonicalize_name(raw_name, validate=True))
    except InvalidName as exc:
        raise ArtifactVerificationError(f"project.name is not a valid distribution name: {raw_name!r}") from exc
    if distribution != EXPECTED_DISTRIBUTION:
        raise ArtifactVerificationError(
            f"project distribution is {distribution!r}; expected {EXPECTED_DISTRIBUTION!r}"
        )

    raw_version = project.get("version")
    if not isinstance(raw_version, str):
        raise ArtifactVerificationError("project.version must be a static string")
    try:
        version = Version(raw_version)
    except InvalidVersion as exc:
        raise ArtifactVerificationError(
            f"project.version is not a valid PEP 440 version: {raw_version!r}"
        ) from exc
    version_text = str(version)
    if raw_version != version_text:
        raise ArtifactVerificationError(
            f"project.version must use canonical PEP 440 spelling {version_text!r}, got {raw_version!r}"
        )
    return ProjectIdentity(
        distribution=EXPECTED_DISTRIBUTION,
        version=version,
        version_text=version_text,
    )


def verify_tag(tag: str, identity: ProjectIdentity) -> None:
    """Require the conventional tag to encode the exact project version."""

    if not tag.startswith("v") or len(tag) == 1:
        raise ArtifactVerificationError(
            f"release tag must have the form v{identity.version_text}, got {tag!r}"
        )
    raw_version = tag[1:]
    try:
        tag_version = Version(raw_version)
    except InvalidVersion as exc:
        raise ArtifactVerificationError(f"release tag has an invalid PEP 440 version: {tag!r}") from exc
    expected_tag = f"v{identity.version_text}"
    if tag_version != identity.version or tag != expected_tag:
        raise ArtifactVerificationError(
            f"release tag version mismatch: expected {expected_tag!r}, got {tag!r}"
        )


def select_release_artifacts(dist_dir: Path) -> tuple[Path, Path]:
    """Select exactly one wheel and one gzip sdist, with no extra entries."""

    try:
        directory_stat = dist_dir.stat()
    except OSError as exc:
        raise ArtifactVerificationError(f"cannot inspect distribution directory {dist_dir}: {exc}") from exc
    if not stat.S_ISDIR(directory_stat.st_mode):
        raise ArtifactVerificationError(f"distribution path is not a directory: {dist_dir}")
    try:
        entries = tuple(sorted(dist_dir.iterdir(), key=lambda path: path.name))
    except OSError as exc:
        raise ArtifactVerificationError(f"cannot list distribution directory {dist_dir}: {exc}") from exc

    wheels = tuple(path for path in entries if path.name.endswith(".whl"))
    sdists = tuple(path for path in entries if path.name.endswith(".tar.gz"))
    recognized = set(wheels) | set(sdists)
    unexpected = tuple(path.name for path in entries if path not in recognized)
    if unexpected:
        raise ArtifactVerificationError(
            "distribution directory contains unexpected entries: " + ", ".join(unexpected)
        )
    if len(wheels) != 1:
        raise ArtifactVerificationError(
            f"distribution directory must contain exactly one wheel; found {len(wheels)}"
        )
    if len(sdists) != 1:
        raise ArtifactVerificationError(
            f"distribution directory must contain exactly one .tar.gz sdist; found {len(sdists)}"
        )

    wheel = wheels[0]
    sdist = sdists[0]
    _require_bounded_regular_file(wheel, label="wheel", maximum=_MAX_ARCHIVE_BYTES)
    _require_bounded_regular_file(sdist, label="sdist", maximum=_MAX_ARCHIVE_BYTES)
    return wheel, sdist


def _safe_archive_parts(member_name: str, *, archive_label: str) -> tuple[str, ...]:
    if not member_name or "\x00" in member_name or "\\" in member_name:
        raise ArtifactVerificationError(
            f"{archive_label} contains an unsafe member path: {member_name!r}"
        )
    trimmed = member_name[:-1] if member_name.endswith("/") else member_name
    if not trimmed or trimmed.startswith("/"):
        raise ArtifactVerificationError(
            f"{archive_label} contains an unsafe member path: {member_name!r}"
        )
    parts = tuple(trimmed.split("/"))
    if any(part in {"", ".", ".."} for part in parts) or parts[0].endswith(":"):
        raise ArtifactVerificationError(
            f"{archive_label} contains an unsafe member path: {member_name!r}"
        )
    return parts


def _single_metadata_header(message: Message, field: str, *, context: str) -> str:
    values = message.get_all(field)
    if values is None or len(values) != 1:
        count = 0 if values is None else len(values)
        raise ArtifactVerificationError(
            f"{context} must contain exactly one {field} header; found {count}"
        )
    value = values[0]
    if not value or value != value.strip():
        raise ArtifactVerificationError(f"{context} has an invalid {field} header")
    return value


def _verify_metadata(
    payload: bytes,
    *,
    identity: ProjectIdentity,
    context: str,
) -> None:
    if len(payload) > _MAX_METADATA_BYTES:
        raise ArtifactVerificationError(
            f"{context} is {len(payload)} bytes; the metadata limit is {_MAX_METADATA_BYTES} bytes"
        )
    try:
        message = BytesParser(policy=default_email_policy).parsebytes(payload)
    except (UnicodeDecodeError, ValueError) as exc:
        raise ArtifactVerificationError(f"cannot parse {context}: {exc}") from exc
    if message.defects:
        raise ArtifactVerificationError(f"{context} is malformed: {message.defects[0]}")

    _single_metadata_header(message, "Metadata-Version", context=context)
    metadata_name = _single_metadata_header(message, "Name", context=context)
    try:
        canonical_name = str(canonicalize_name(metadata_name, validate=True))
    except InvalidName as exc:
        raise ArtifactVerificationError(
            f"{context} has an invalid Name header: {metadata_name!r}"
        ) from exc
    if canonical_name != identity.distribution:
        raise ArtifactVerificationError(
            f"{context} Name mismatch: expected {identity.distribution!r}, got {metadata_name!r}"
        )

    metadata_version = _single_metadata_header(message, "Version", context=context)
    try:
        parsed_version = Version(metadata_version)
    except InvalidVersion as exc:
        raise ArtifactVerificationError(
            f"{context} has an invalid PEP 440 Version header: {metadata_version!r}"
        ) from exc
    if parsed_version != identity.version or metadata_version != identity.version_text:
        raise ArtifactVerificationError(
            f"{context} Version mismatch: expected {identity.version_text!r}, got {metadata_version!r}"
        )


def _read_zip_member(
    archive: zipfile.ZipFile,
    member: zipfile.ZipInfo,
    *,
    limit: int,
    capture: bool,
) -> bytes:
    captured = bytearray()
    actual_size = 0
    with archive.open(member, "r") as source:
        while True:
            chunk = source.read(_READ_CHUNK_BYTES)
            if not chunk:
                break
            actual_size += len(chunk)
            if actual_size > limit:
                raise ArtifactVerificationError(
                    f"wheel member {member.filename!r} exceeded its {limit}-byte read limit"
                )
            if capture:
                captured.extend(chunk)
    if actual_size != member.file_size:
        raise ArtifactVerificationError(
            f"wheel member {member.filename!r} size does not match its archive header"
        )
    return bytes(captured)


def verify_wheel(wheel_path: Path, identity: ProjectIdentity) -> None:
    """Verify wheel filename, archive shape, and core metadata identity."""

    _require_bounded_regular_file(wheel_path, label="wheel", maximum=_MAX_ARCHIVE_BYTES)
    try:
        parsed_name, parsed_version, _build, _tags = parse_wheel_filename(wheel_path.name)
    except InvalidWheelFilename as exc:
        raise ArtifactVerificationError(f"invalid wheel filename: {wheel_path.name!r}") from exc
    expected_prefix = f"{identity.distribution}-{identity.version_text}-"
    if str(parsed_name) != identity.distribution or not wheel_path.name.startswith(expected_prefix):
        raise ArtifactVerificationError(
            f"wheel filename distribution/version mismatch: {wheel_path.name!r}"
        )
    if parsed_version != identity.version:
        raise ArtifactVerificationError(
            f"wheel filename version mismatch: expected {identity.version_text!r}, "
            f"got {str(parsed_version)!r}"
        )

    metadata_path = (
        f"{identity.distribution}-{identity.version_text}.dist-info/METADATA"
    )
    metadata_payload: bytes | None = None
    try:
        with zipfile.ZipFile(wheel_path, mode="r") as archive:
            members = archive.infolist()
            if len(members) > _MAX_ARCHIVE_MEMBERS:
                raise ArtifactVerificationError(
                    f"wheel has {len(members)} members; the limit is {_MAX_ARCHIVE_MEMBERS}"
                )
            seen_paths: set[str] = set()
            expanded_size = 0
            metadata_candidates = 0
            for member in members:
                parts = _safe_archive_parts(member.filename, archive_label="wheel")
                normalized_path = "/".join(parts).casefold()
                if normalized_path in seen_paths:
                    raise ArtifactVerificationError(
                        f"wheel contains a duplicate member path: {member.filename!r}"
                    )
                seen_paths.add(normalized_path)

                mode = (member.external_attr >> 16) & 0xFFFF
                file_type = stat.S_IFMT(mode)
                if member.is_dir():
                    if member.file_size != 0 or file_type not in {0, stat.S_IFDIR}:
                        raise ArtifactVerificationError(
                            f"wheel has an invalid directory member: {member.filename!r}"
                        )
                    continue
                if file_type not in {0, stat.S_IFREG}:
                    raise ArtifactVerificationError(
                        f"wheel contains a link or special member: {member.filename!r}"
                    )
                if member.flag_bits & 0x1:
                    raise ArtifactVerificationError(
                        f"wheel contains an encrypted member: {member.filename!r}"
                    )
                if member.file_size < 0 or member.file_size > _MAX_MEMBER_BYTES:
                    raise ArtifactVerificationError(
                        f"wheel member {member.filename!r} has unsafe size {member.file_size}"
                    )
                expanded_size += member.file_size
                if expanded_size > _MAX_EXPANDED_BYTES:
                    raise ArtifactVerificationError(
                        f"wheel expanded size exceeds {_MAX_EXPANDED_BYTES} bytes"
                    )

                is_metadata = member.filename.casefold().endswith(".dist-info/metadata")
                if is_metadata:
                    metadata_candidates += 1
                capture = member.filename == metadata_path
                read_limit = _MAX_METADATA_BYTES if capture else _MAX_MEMBER_BYTES
                payload = _read_zip_member(
                    archive,
                    member,
                    limit=read_limit,
                    capture=capture,
                )
                if capture:
                    metadata_payload = payload
            if metadata_candidates != 1 or metadata_payload is None:
                raise ArtifactVerificationError(
                    f"wheel must contain exactly one metadata file at {metadata_path!r}; "
                    f"found {metadata_candidates} .dist-info/METADATA entries"
                )
    except ArtifactVerificationError:
        raise
    except (OSError, RuntimeError, NotImplementedError, zipfile.BadZipFile) as exc:
        raise ArtifactVerificationError(f"cannot verify wheel archive {wheel_path}: {exc}") from exc

    _verify_metadata(
        metadata_payload,
        identity=identity,
        context=f"wheel {metadata_path}",
    )


def verify_sdist(sdist_path: Path, identity: ProjectIdentity) -> None:
    """Verify sdist filename, safe tar shape, top directory, and PKG-INFO."""

    _require_bounded_regular_file(sdist_path, label="sdist", maximum=_MAX_ARCHIVE_BYTES)
    try:
        parsed_name, parsed_version = parse_sdist_filename(sdist_path.name)
    except InvalidSdistFilename as exc:
        raise ArtifactVerificationError(f"invalid sdist filename: {sdist_path.name!r}") from exc
    expected_filename = f"{identity.distribution}-{identity.version_text}.tar.gz"
    if sdist_path.name != expected_filename or str(parsed_name) != identity.distribution:
        raise ArtifactVerificationError(
            f"sdist filename distribution/version mismatch: expected {expected_filename!r}, "
            f"got {sdist_path.name!r}"
        )
    if parsed_version != identity.version:
        raise ArtifactVerificationError(
            f"sdist filename version mismatch: expected {identity.version_text!r}, "
            f"got {str(parsed_version)!r}"
        )

    top_directory = f"{identity.distribution}-{identity.version_text}"
    metadata_path = f"{top_directory}/PKG-INFO"
    metadata_payload: bytes | None = None
    top_directory_entry = False
    member_count = 0
    expanded_size = 0
    seen_paths: set[str] = set()
    try:
        with tarfile.open(sdist_path, mode="r:gz") as archive:
            for member in archive:
                member_count += 1
                if member_count > _MAX_ARCHIVE_MEMBERS:
                    raise ArtifactVerificationError(
                        f"sdist has more than {_MAX_ARCHIVE_MEMBERS} members"
                    )
                parts = _safe_archive_parts(member.name, archive_label="sdist")
                normalized_path = "/".join(parts).casefold()
                if normalized_path in seen_paths:
                    raise ArtifactVerificationError(
                        f"sdist contains a duplicate member path: {member.name!r}"
                    )
                seen_paths.add(normalized_path)
                if parts[0] != top_directory:
                    raise ArtifactVerificationError(
                        f"sdist member is outside the required top directory "
                        f"{top_directory!r}: {member.name!r}"
                    )

                if member.isdir():
                    if member.size != 0:
                        raise ArtifactVerificationError(
                            f"sdist directory member has non-zero size: {member.name!r}"
                        )
                    if len(parts) == 1:
                        top_directory_entry = True
                    continue
                if not member.isfile():
                    raise ArtifactVerificationError(
                        f"sdist contains a link or special member: {member.name!r}"
                    )
                if member.size < 0 or member.size > _MAX_MEMBER_BYTES:
                    raise ArtifactVerificationError(
                        f"sdist member {member.name!r} has unsafe size {member.size}"
                    )
                expanded_size += member.size
                if expanded_size > _MAX_EXPANDED_BYTES:
                    raise ArtifactVerificationError(
                        f"sdist expanded size exceeds {_MAX_EXPANDED_BYTES} bytes"
                    )

                if member.name == metadata_path:
                    if member.size > _MAX_METADATA_BYTES:
                        raise ArtifactVerificationError(
                            f"sdist {metadata_path} exceeds the metadata size limit"
                        )
                    extracted = archive.extractfile(member)
                    if extracted is None:
                        raise ArtifactVerificationError(
                            f"cannot read sdist metadata file {metadata_path!r}"
                        )
                    payload = extracted.read(_MAX_METADATA_BYTES + 1)
                    if len(payload) != member.size:
                        raise ArtifactVerificationError(
                            f"sdist metadata size does not match its archive header: {metadata_path!r}"
                        )
                    metadata_payload = payload
    except ArtifactVerificationError:
        raise
    except (OSError, EOFError, tarfile.TarError) as exc:
        raise ArtifactVerificationError(f"cannot verify sdist archive {sdist_path}: {exc}") from exc

    if not top_directory_entry:
        raise ArtifactVerificationError(
            f"sdist has no explicit top directory entry {top_directory!r}"
        )
    if metadata_payload is None:
        raise ArtifactVerificationError(
            f"sdist must contain exactly one metadata file at {metadata_path!r}"
        )
    _verify_metadata(
        metadata_payload,
        identity=identity,
        context=f"sdist {metadata_path}",
    )


def verify_release_artifacts(
    *,
    dist_dir: Path,
    project_path: Path,
    tag: str | None = None,
) -> VerifiedArtifacts:
    """Verify every identity surface of the exact release artifact pair."""

    identity = load_project_identity(project_path)
    if tag is not None:
        verify_tag(tag, identity)
    wheel, sdist = select_release_artifacts(dist_dir)
    verify_wheel(wheel, identity)
    verify_sdist(sdist, identity)
    return VerifiedArtifacts(identity=identity, wheel=wheel, sdist=sdist)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Fail closed unless a wheel and sdist have the exact project release identity."
    )
    parser.add_argument("--dist-dir", required=True, type=Path)
    parser.add_argument("--project", required=True, type=Path)
    parser.add_argument("--tag")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        verified = verify_release_artifacts(
            dist_dir=args.dist_dir,
            project_path=args.project,
            tag=args.tag,
        )
    except ArtifactVerificationError as exc:
        print(f"artifact verification failed: {exc}", file=sys.stderr)
        return 1
    print(
        f"verified {verified.identity.distribution} {verified.identity.version_text}: "
        f"{verified.wheel.name}, {verified.sdist.name}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
