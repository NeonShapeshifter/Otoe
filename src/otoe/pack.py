from __future__ import annotations

import gzip
import hashlib
import io
import json
import os
import subprocess
import sys
import tarfile
from dataclasses import dataclass
from pathlib import Path

from .build import (
    ASSET_OUTPUT_DIR,
    BACKEND_COVERAGE_ARTIFACT_FILENAME,
    BUILD_MANIFEST_FILENAME,
    DEPS_ARTIFACT_FILENAME,
    FRAMEWORK_OUTPUT_DIR,
    PLAN_ARTIFACT_FILENAME,
    RUNTIME_OUTPUT_DIR,
    RUNNER_FILENAME,
    STYLE_ARTIFACT_FILENAME,
)
from .style_ops import StyleIRError, load_style_ir, validate_style_ops


CACHE_DIR_NAMES = frozenset({"__pycache__", ".pytest_cache"})
CACHE_SUFFIXES = (".pyc", ".pyo")
PACK_TOP_LEVEL_FILES = frozenset(
    {
        BUILD_MANIFEST_FILENAME,
        BACKEND_COVERAGE_ARTIFACT_FILENAME,
        PLAN_ARTIFACT_FILENAME,
        DEPS_ARTIFACT_FILENAME,
        STYLE_ARTIFACT_FILENAME,
        RUNNER_FILENAME,
    }
)
PACK_DIRECTORIES = frozenset({ASSET_OUTPUT_DIR, FRAMEWORK_OUTPUT_DIR, RUNTIME_OUTPUT_DIR})


class PackError(ValueError):
    pass


@dataclass(frozen=True)
class PackResult:
    path: Path
    files: int
    size: int
    sha256: str


def pack_bundle(bundle_dir: Path, output_path: Path) -> PackResult:
    bundle_dir = bundle_dir.resolve()
    output_path = output_path.resolve()
    _verify_bundle_input(bundle_dir)

    manifest = _load_manifest(bundle_dir)
    entries = tuple(_bundle_entries(bundle_dir, output_path=output_path))
    _reject_unmanifested_entries(entries, manifest, bundle_dir=bundle_dir)
    _run_bundle_verify(bundle_dir)
    _run_style_ir_strict_verify(bundle_dir)
    if not entries:
        raise PackError(f"bundle {str(bundle_dir)!r} does not contain packable files")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("wb") as raw:
        with gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as gz:
            with tarfile.open(fileobj=gz, mode="w", format=tarfile.PAX_FORMAT) as tar:
                for path in entries:
                    _add_tar_entry(tar, path, bundle_dir=bundle_dir)

    data = output_path.read_bytes()
    return PackResult(
        path=output_path,
        files=len(entries),
        size=len(data),
        sha256=hashlib.sha256(data).hexdigest(),
    )


def _verify_bundle_input(bundle_dir: Path) -> None:
    if not bundle_dir.exists():
        raise PackError(f"bundle directory {str(bundle_dir)!r} does not exist")
    if not bundle_dir.is_dir():
        raise PackError(f"bundle path {str(bundle_dir)!r} is not a directory")
    manifest = bundle_dir / BUILD_MANIFEST_FILENAME
    if not manifest.is_file():
        raise PackError(f"bundle is missing {BUILD_MANIFEST_FILENAME}")
    runner = bundle_dir / RUNNER_FILENAME
    if not runner.is_file():
        raise PackError(f"bundle is missing {RUNNER_FILENAME}")


def _run_bundle_verify(bundle_dir: Path) -> None:
    command = [sys.executable, str(bundle_dir / RUNNER_FILENAME), "--verify"]
    result = subprocess.run(
        command,
        capture_output=True,
        cwd=bundle_dir,
        env={**os.environ, "PYTHONPATH": ""},
        text=True,
    )
    if result.returncode == 0:
        return
    details = result.stderr.strip() or result.stdout.strip()
    if not details:
        details = f"runner exited with status {result.returncode}"
    raise PackError(f"runner verification failed: {details}")


def _run_style_ir_strict_verify(bundle_dir: Path) -> None:
    manifest = _load_manifest(bundle_dir)
    styles_relative = manifest.get("styles", STYLE_ARTIFACT_FILENAME)
    if not isinstance(styles_relative, str):
        raise PackError(f"{BUILD_MANIFEST_FILENAME}: styles must be a string")
    styles_path = _safe_bundle_path(bundle_dir, styles_relative)
    if not styles_path.is_file():
        raise PackError(f"bundle is missing {styles_relative}")

    try:
        payload = json.loads(styles_path.read_text(encoding="utf-8"))
        validation = validate_style_ops(load_style_ir(payload))
    except json.JSONDecodeError as exc:
        raise PackError(f"{styles_relative} is not valid JSON: {exc}") from exc
    except StyleIRError as exc:
        raise PackError(f"style-ir strict verification failed: {exc}") from exc
    if validation.passed:
        return
    details = "; ".join(validation.errors) or "styleOps drift detected"
    raise PackError(f"style-ir strict verification failed: {details}")


def _load_manifest(bundle_dir: Path) -> dict:
    manifest_path = bundle_dir / BUILD_MANIFEST_FILENAME
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise PackError(f"{BUILD_MANIFEST_FILENAME} is not valid JSON: {exc}") from exc
    if not isinstance(manifest, dict):
        raise PackError(f"{BUILD_MANIFEST_FILENAME} must contain a JSON object")
    return manifest


def _safe_bundle_path(bundle_dir: Path, relative: str) -> Path:
    if relative in {"", "."}:
        raise PackError(f"bundle path {relative!r} is not safe")
    path = Path(relative)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise PackError(f"bundle path {relative!r} is not safe")
    return bundle_dir / path


def _bundle_entries(bundle_dir: Path, *, output_path: Path) -> list[Path]:
    entries: list[Path] = []
    for path in bundle_dir.rglob("*"):
        if not path.is_file():
            continue
        if path.resolve() == output_path:
            continue
        relative = path.relative_to(bundle_dir)
        if not _is_pack_path(relative):
            continue
        if _is_cache_path(relative):
            continue
        entries.append(path)
    return sorted(entries, key=lambda path: path.relative_to(bundle_dir).as_posix())


def _reject_unmanifested_entries(
    entries: tuple[Path, ...],
    manifest: dict,
    *,
    bundle_dir: Path,
) -> None:
    allowed = _manifest_pack_paths(manifest, bundle_dir=bundle_dir)
    for path in entries:
        relative = path.relative_to(bundle_dir).as_posix()
        if relative not in allowed:
            raise PackError(f"unmanifested bundle file {relative!r}")


def _manifest_pack_paths(manifest: dict, *, bundle_dir: Path) -> set[str]:
    paths = {BUILD_MANIFEST_FILENAME}
    for key in ("plan", "deps", "styles", "backendCoverage"):
        value = manifest.get(key)
        _add_manifest_pack_path(paths, value, bundle_dir=bundle_dir)
    runner = manifest.get("runner")
    if isinstance(runner, dict):
        _add_manifest_pack_path(paths, runner.get("path"), bundle_dir=bundle_dir)
    for artifact in manifest.get("artifacts", []):
        if isinstance(artifact, dict):
            _add_manifest_pack_path(
                paths,
                artifact.get("path"),
                bundle_dir=bundle_dir,
            )
    for group in ("assets", "frameworkFiles", "runtimeFiles"):
        for entry in manifest.get(group, []):
            if not isinstance(entry, dict):
                continue
            _add_manifest_pack_path(
                paths,
                entry.get("bundlePath"),
                bundle_dir=bundle_dir,
            )
    return paths


def _add_manifest_pack_path(
    paths: set[str],
    relative: object,
    *,
    bundle_dir: Path,
) -> None:
    if not isinstance(relative, str):
        return
    _safe_bundle_path(bundle_dir, relative)
    paths.add(relative)


def _is_cache_path(relative: Path) -> bool:
    if any(part in CACHE_DIR_NAMES for part in relative.parts):
        return True
    return relative.suffix in CACHE_SUFFIXES


def _is_pack_path(relative: Path) -> bool:
    if len(relative.parts) == 1:
        return relative.name in PACK_TOP_LEVEL_FILES
    return relative.parts[0] in PACK_DIRECTORIES


def _add_tar_entry(tar: tarfile.TarFile, path: Path, *, bundle_dir: Path) -> None:
    relative = path.relative_to(bundle_dir).as_posix()
    data = path.read_bytes()
    info = tarfile.TarInfo(relative)
    info.size = len(data)
    info.mtime = 0
    info.uid = 0
    info.gid = 0
    info.uname = ""
    info.gname = ""
    info.mode = 0o644
    tar.addfile(info, io.BytesIO(data))
