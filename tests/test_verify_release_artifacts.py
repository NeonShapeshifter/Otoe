from __future__ import annotations

from collections.abc import Iterable
from io import BytesIO
from pathlib import Path
import tarfile
from typing import TypedDict
import zipfile

import pytest

from scripts import verify_release_artifacts
from scripts.verify_release_artifacts import ArtifactVerificationError


class WheelOptions(TypedDict, total=False):
    metadata_version: str
    metadata_path_version: str | None
    extra_entries: Iterable[tuple[str, bytes]]


def _metadata(*, name: str = "otoe", version: str = "0.2.0") -> bytes:
    return (
        "Metadata-Version: 2.4\n"
        f"Name: {name}\n"
        f"Version: {version}\n"
        "Summary: Test artifact\n"
        "\n"
    ).encode("utf-8")


def _write_project(path: Path, *, name: str = "otoe", version: str = "0.2.0") -> Path:
    path.write_text(
        f'[project]\nname = "{name}"\nversion = "{version}"\n',
        encoding="utf-8",
    )
    return path


def _write_wheel(
    dist_dir: Path,
    *,
    filename_version: str = "0.2.0",
    metadata_version: str = "0.2.0",
    metadata_path_version: str | None = None,
    extra_entries: Iterable[tuple[str, bytes]] = (),
) -> Path:
    wheel = dist_dir / f"otoe-{filename_version}-py3-none-any.whl"
    dist_info_version = metadata_path_version or filename_version
    with zipfile.ZipFile(wheel, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("otoe/__init__.py", b"")
        archive.writestr(
            f"otoe-{dist_info_version}.dist-info/METADATA",
            _metadata(version=metadata_version),
        )
        for member_name, payload in extra_entries:
            archive.writestr(member_name, payload)
    return wheel


def _tar_entry(name: str, payload: bytes | None) -> tuple[tarfile.TarInfo, BytesIO | None]:
    member = tarfile.TarInfo(name)
    if payload is None:
        member.type = tarfile.DIRTYPE
        member.size = 0
        return member, None
    member.size = len(payload)
    return member, BytesIO(payload)


def _write_sdist(
    dist_dir: Path,
    *,
    filename_version: str = "0.2.0",
    topdir_version: str | None = None,
    metadata_version: str = "0.2.0",
    extra_entries: Iterable[tuple[str, bytes | None]] = (),
) -> Path:
    sdist = dist_dir / f"otoe-{filename_version}.tar.gz"
    top = f"otoe-{topdir_version or filename_version}"
    entries: list[tuple[str, bytes | None]] = [
        (top, None),
        (f"{top}/PKG-INFO", _metadata(version=metadata_version)),
        (f"{top}/src/otoe/__init__.py", b""),
    ]
    entries.extend(extra_entries)
    with tarfile.open(sdist, mode="w:gz") as archive:
        for member_name, payload in entries:
            member, source = _tar_entry(member_name, payload)
            archive.addfile(member, source)
    return sdist


def _release_tree(tmp_path: Path) -> tuple[Path, Path]:
    project = _write_project(tmp_path / "pyproject.toml")
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    _write_wheel(dist_dir)
    _write_sdist(dist_dir)
    return project, dist_dir


def test_release_artifact_identity_passes_api_and_cli(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    project, dist_dir = _release_tree(tmp_path)

    verified = verify_release_artifacts.verify_release_artifacts(
        dist_dir=dist_dir,
        project_path=project,
        tag="v0.2.0",
    )

    assert verified.identity.distribution == "otoe"
    assert verified.identity.version_text == "0.2.0"
    assert verify_release_artifacts.main(
        ["--dist-dir", str(dist_dir), "--project", str(project), "--tag", "v0.2.0"]
    ) == 0
    assert "verified otoe 0.2.0" in capsys.readouterr().out


def test_artifact_filename_version_mismatch_fails_closed(tmp_path: Path) -> None:
    project = _write_project(tmp_path / "pyproject.toml")
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    _write_wheel(dist_dir, filename_version="9.9.9", metadata_version="9.9.9")
    _write_sdist(dist_dir, filename_version="9.9.9", metadata_version="9.9.9")

    with pytest.raises(ArtifactVerificationError, match="wheel filename"):
        verify_release_artifacts.verify_release_artifacts(
            dist_dir=dist_dir,
            project_path=project,
        )


def test_release_tag_version_mismatch_fails_closed(tmp_path: Path) -> None:
    project, dist_dir = _release_tree(tmp_path)

    with pytest.raises(ArtifactVerificationError, match="release tag version mismatch"):
        verify_release_artifacts.verify_release_artifacts(
            dist_dir=dist_dir,
            project_path=project,
            tag="v9.9.9",
        )


@pytest.mark.parametrize("extra_name", ["SHA256SUMS", "otoe-0.2.0.zip"])
def test_distribution_directory_rejects_extra_entries(
    tmp_path: Path,
    extra_name: str,
) -> None:
    project, dist_dir = _release_tree(tmp_path)
    (dist_dir / extra_name).write_bytes(b"extra")

    with pytest.raises(ArtifactVerificationError, match="unexpected entries"):
        verify_release_artifacts.verify_release_artifacts(
            dist_dir=dist_dir,
            project_path=project,
        )


def test_distribution_directory_rejects_duplicate_archive_kind(tmp_path: Path) -> None:
    project, dist_dir = _release_tree(tmp_path)
    original_wheel = dist_dir / "otoe-0.2.0-py3-none-any.whl"
    (dist_dir / "otoe-0.2.0-1-py3-none-any.whl").write_bytes(original_wheel.read_bytes())

    with pytest.raises(ArtifactVerificationError, match="exactly one wheel; found 2"):
        verify_release_artifacts.verify_release_artifacts(
            dist_dir=dist_dir,
            project_path=project,
        )


@pytest.mark.parametrize(
    ("wheel_options", "message"),
    [
        ({"metadata_version": "9.9.9"}, "wheel .* Version mismatch"),
        ({"metadata_path_version": "9.9.9"}, "exactly one metadata file"),
        (
            {
                "extra_entries": [
                    ("other-0.2.0.dist-info/METADATA", _metadata(name="other"))
                ]
            },
            "found 2 .dist-info/METADATA entries",
        ),
    ],
)
def test_wheel_internal_metadata_mismatch_fails_closed(
    tmp_path: Path,
    wheel_options: WheelOptions,
    message: str,
) -> None:
    project = _write_project(tmp_path / "pyproject.toml")
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    _write_wheel(dist_dir, **wheel_options)
    _write_sdist(dist_dir)

    with pytest.raises(ArtifactVerificationError, match=message):
        verify_release_artifacts.verify_release_artifacts(
            dist_dir=dist_dir,
            project_path=project,
        )


def test_sdist_internal_metadata_version_mismatch_fails_closed(tmp_path: Path) -> None:
    project = _write_project(tmp_path / "pyproject.toml")
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    _write_wheel(dist_dir)
    _write_sdist(dist_dir, metadata_version="9.9.9")

    with pytest.raises(ArtifactVerificationError, match="sdist .* Version mismatch"):
        verify_release_artifacts.verify_release_artifacts(
            dist_dir=dist_dir,
            project_path=project,
        )


def test_sdist_top_directory_version_mismatch_fails_closed(tmp_path: Path) -> None:
    project = _write_project(tmp_path / "pyproject.toml")
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    _write_wheel(dist_dir)
    _write_sdist(dist_dir, topdir_version="9.9.9")

    with pytest.raises(ArtifactVerificationError, match="outside the required top directory"):
        verify_release_artifacts.verify_release_artifacts(
            dist_dir=dist_dir,
            project_path=project,
        )


def test_duplicate_core_metadata_header_fails_closed(tmp_path: Path) -> None:
    project = _write_project(tmp_path / "pyproject.toml")
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    duplicate_header = b"Metadata-Version: 2.4\n" + _metadata()
    wheel = dist_dir / "otoe-0.2.0-py3-none-any.whl"
    with zipfile.ZipFile(wheel, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("otoe/__init__.py", b"")
        archive.writestr("otoe-0.2.0.dist-info/METADATA", duplicate_header)
    _write_sdist(dist_dir)

    with pytest.raises(
        ArtifactVerificationError,
        match="exactly one Metadata-Version header; found 2",
    ):
        verify_release_artifacts.verify_release_artifacts(
            dist_dir=dist_dir,
            project_path=project,
        )


@pytest.mark.parametrize(
    "dangerous_path",
    [
        "../escape",
        "/absolute",
        "otoe-0.2.0/../escape",
        "C:/escape",
        "otoe-0.2.0\\escape",
    ],
)
def test_sdist_rejects_dangerous_member_paths(
    tmp_path: Path,
    dangerous_path: str,
) -> None:
    project = _write_project(tmp_path / "pyproject.toml")
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    _write_wheel(dist_dir)
    _write_sdist(dist_dir, extra_entries=[(dangerous_path, b"escape")])

    with pytest.raises(ArtifactVerificationError, match="unsafe member path"):
        verify_release_artifacts.verify_release_artifacts(
            dist_dir=dist_dir,
            project_path=project,
        )


def test_sdist_rejects_duplicate_root_metadata(tmp_path: Path) -> None:
    project = _write_project(tmp_path / "pyproject.toml")
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    _write_wheel(dist_dir)
    _write_sdist(
        dist_dir,
        extra_entries=[("otoe-0.2.0/PKG-INFO", _metadata())],
    )

    with pytest.raises(ArtifactVerificationError, match="duplicate member path"):
        verify_release_artifacts.verify_release_artifacts(
            dist_dir=dist_dir,
            project_path=project,
        )


def test_sdist_rejects_links(tmp_path: Path) -> None:
    project, dist_dir = _release_tree(tmp_path)
    sdist = dist_dir / "otoe-0.2.0.tar.gz"
    replacement = tmp_path / "unsafe.tar.gz"
    with tarfile.open(sdist, mode="r:gz") as source, tarfile.open(replacement, mode="w:gz") as target:
        for member in source:
            extracted = source.extractfile(member) if member.isfile() else None
            target.addfile(member, extracted)
        link = tarfile.TarInfo("otoe-0.2.0/link")
        link.type = tarfile.SYMTYPE
        link.linkname = "../../escape"
        target.addfile(link)
    replacement.replace(sdist)

    with pytest.raises(ArtifactVerificationError, match="link or special member"):
        verify_release_artifacts.verify_release_artifacts(
            dist_dir=dist_dir,
            project_path=project,
        )
