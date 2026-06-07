from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

from pathlib import Path

from .backend_package import (
    BACKEND_PACKAGE_DESCRIPTOR,
    BackendPackageError,
    copy_backend_package as write_backend_package,
    load_backend_package_manifest,
)
from .build_runner import build_runner_source
from .profile_types import PlanProfileConfig, ProfileAsset, ProfileRuntimeFile


PLAN_ARTIFACT_FILENAME = "otoe-plan.json"
DEPS_ARTIFACT_FILENAME = "otoe-deps.json"
STYLE_ARTIFACT_FILENAME = "otoe-styles.json"
BACKEND_COVERAGE_ARTIFACT_FILENAME = "otoe-backend-coverage.json"
BUILD_MANIFEST_FILENAME = "manifest.json"
RUNNER_FILENAME = "otoe-run.py"
ASSET_OUTPUT_DIR = "assets"
RUNTIME_OUTPUT_DIR = "app"
FRAMEWORK_OUTPUT_DIR = "framework"
BACKEND_PACKAGE_OUTPUT_DIR = "backend"
RUNNER_PYTHON_PATH = ("app", "framework")
OTOE_PACKAGE_DIR = Path(__file__).resolve().parent
CORE_RUNTIME_FILES = (
    "__init__.py",
    "api_status.py",
    "backend_package.py",
    "bundle_backend_coverage.py",
    "bundle_backend_package.py",
    "bundle_deps.py",
    "capabilities.py",
    "component.py",
    "control.py",
    "control.pyi",
    "errors.py",
    "events.py",
    "html.py",
    "html_live.py",
    "mount.py",
    "node.py",
    "owner.py",
    "py.typed",
    "reactive.py",
    "render_ir.py",
    "render_ir_serialize.py",
    "render_ir_target.py",
    "render_ir_types.py",
    "render_ir_validate.py",
    "scheduler.py",
    "snapshot.py",
    "style.py",
    "style_ops.py",
    "style_ops_artifact.py",
    "style_ops_replay.py",
    "style_ops_types.py",
    "style_ops_validation.py",
    "style_ops_values.py",
    "template.py",
    "timing.py",
    "ui.py",
    "ui.pyi",
    "_ui_helpers.py",
    "_ui_keyboard.py",
    "_ui_models.py",
    "utilities.py",
    "widgets.py",
    "widgets.pyi",
    "window.py",
    "_render_identity.py",
)
BACKEND_RUNTIME_FILES = {
    "native": (
        "native.py",
        "_native_backend.py",
        "_native_contracts.py",
        "_native_hit_test.py",
        "_native_layout.py",
        "_native_layout_align.py",
        "_native_paint.py",
        "_native_png.py",
        "_native_shared.py",
        "_native_surface.py",
        "_native_text.py",
    ),
}


class BuildError(ValueError):
    pass


@dataclass(frozen=True)
class BundleFile:
    source: Path
    relative_path: Path


@dataclass(frozen=True)
class BackendPackageArtifacts:
    summary: dict[str, Any]
    artifacts: list[dict[str, Any]]


def build_manifest(
    *,
    target: str,
    plan: dict[str, Any],
    deps: dict[str, Any],
    profile_config: PlanProfileConfig,
    assets: list[dict[str, Any]] | None = None,
    artifacts: list[dict[str, Any]] | None = None,
    backend_coverage: dict[str, Any] | None = None,
    backend_package: dict[str, Any] | None = None,
    framework_files: list[dict[str, Any]] | None = None,
    runner: dict[str, Any] | None = None,
    runtime_files: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if plan["hasErrors"]:
        raise BuildError("plan invalid; refusing to write build manifest")
    if deps["hasErrors"]:
        raise BuildError("dependency audit invalid; refusing to write build manifest")
    if backend_coverage is not None and backend_coverage.get("passed") is not True:
        raise BuildError("backend coverage invalid; refusing to write build manifest")
    manifest = {
        "schemaVersion": 1,
        "target": target,
        "profile": plan["profile"],
        "backend": profile_config.backend_name or "native",
        "backendCapability": plan.get("backend", "native-python"),
        "runtimeInstallsAllowed": profile_config.allow_runtime_installs,
        "plan": PLAN_ARTIFACT_FILENAME,
        "deps": DEPS_ARTIFACT_FILENAME,
        "styles": STYLE_ARTIFACT_FILENAME,
        "artifacts": artifacts or [],
        "assets": assets or [],
        "frameworkFiles": framework_files or [],
        "runner": runner or {},
        "runtimeFiles": runtime_files or [],
        "status": _combined_status(plan["status"], deps["status"]),
    }
    if backend_coverage is not None:
        manifest["backendCoverage"] = BACKEND_COVERAGE_ARTIFACT_FILENAME
    if backend_package is not None:
        manifest["backendPackage"] = backend_package
    return manifest


def copy_assets(
    assets: tuple[ProfileAsset, ...],
    *,
    output_dir: Path,
) -> list[dict[str, Any]]:
    return _copy_manifest_files(
        assets,
        output_dir=output_dir,
        bundle_dir=ASSET_OUTPUT_DIR,
        missing_label="asset file",
    )


def copy_runtime_files(
    runtime_files: tuple[ProfileRuntimeFile, ...],
    *,
    output_dir: Path,
) -> list[dict[str, Any]]:
    return _copy_manifest_files(
        runtime_files,
        output_dir=output_dir,
        bundle_dir=RUNTIME_OUTPUT_DIR,
        missing_label="runtime file",
    )


def copy_framework_files(
    profile_config: PlanProfileConfig,
    *,
    output_dir: Path,
) -> list[dict[str, Any]]:
    return _copy_manifest_files(
        _framework_files(profile_config),
        output_dir=output_dir,
        bundle_dir=FRAMEWORK_OUTPUT_DIR,
        missing_label="framework file",
    )


def copy_backend_package_artifacts(
    profile_config: PlanProfileConfig,
    *,
    output_dir: Path,
) -> BackendPackageArtifacts | None:
    manifest_path = profile_config.backend_package_manifest
    if manifest_path is None:
        return None
    try:
        package_manifest = load_backend_package_manifest(manifest_path)
    except BackendPackageError as exc:
        raise BuildError(str(exc)) from exc

    package_root = _backend_package_bundle_root(package_manifest.name)
    package_output_dir = output_dir / package_root
    descriptor = write_backend_package(
        package_manifest,
        output_dir=package_output_dir,
    )
    descriptor_path = package_output_dir / BACKEND_PACKAGE_DESCRIPTOR
    artifacts = [bundle_artifact(descriptor_path, output_dir=output_dir)]
    for file in package_manifest.files:
        artifacts.append(
            bundle_artifact(package_output_dir / file.bundle_path, output_dir=output_dir)
        )

    descriptor_bundle_path = (package_root / BACKEND_PACKAGE_DESCRIPTOR).as_posix()
    entrypoint_bundle_path = (package_root / package_manifest.entrypoint).as_posix()
    summary = {
        "name": descriptor["name"],
        "label": descriptor["label"],
        "kind": descriptor["kind"],
        "path": descriptor_bundle_path,
        "root": package_root.as_posix(),
        "entrypoint": entrypoint_bundle_path,
        "packageHash": descriptor["packageHash"],
        "files": [
            (package_root / file.bundle_path).as_posix()
            for file in package_manifest.files
        ],
    }
    return BackendPackageArtifacts(summary=summary, artifacts=artifacts)


def write_runner(*, output_dir: Path) -> dict[str, Any]:
    runner_path = output_dir / RUNNER_FILENAME
    runner_path.write_text(
        build_runner_source(_runner_expected_framework_files()),
        encoding="utf-8",
    )
    data = runner_path.read_bytes()
    return {
        "path": RUNNER_FILENAME,
        "pythonPath": list(RUNNER_PYTHON_PATH),
        "modes": ["backend-package-check", "check", "layout-check", "png", "verify"],
        "size": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def bundle_artifact(path: Path, *, output_dir: Path) -> dict[str, Any]:
    if not path.is_file():
        raise BuildError(f"bundle artifact {str(path)!r} does not exist")
    data = path.read_bytes()
    try:
        relative = path.relative_to(output_dir)
    except ValueError as exc:
        raise BuildError(
            f"bundle artifact {str(path)!r} is not inside {str(output_dir)!r}"
        ) from exc
    return {
        "path": relative.as_posix(),
        "size": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def _framework_files(profile_config: PlanProfileConfig) -> tuple[BundleFile, ...]:
    backend_name = profile_config.backend_name or "native"
    if backend_name not in BACKEND_RUNTIME_FILES:
        supported = ", ".join(sorted(BACKEND_RUNTIME_FILES))
        raise BuildError(
            f"unsupported build backend {backend_name!r}; supported: {supported}"
        )
    paths = _unique_paths(CORE_RUNTIME_FILES + BACKEND_RUNTIME_FILES[backend_name])
    return tuple(
        BundleFile(
            source=OTOE_PACKAGE_DIR / path,
            relative_path=Path("otoe") / path,
        )
        for path in paths
    )


def _backend_package_bundle_root(name: str) -> Path:
    path = Path(name)
    if (
        path.is_absolute()
        or path.as_posix() != name
        or len(path.parts) != 1
        or any(part in {"", ".", ".."} for part in path.parts)
    ):
        raise BuildError("backend package name must be a safe bundle directory name")
    return Path(BACKEND_PACKAGE_OUTPUT_DIR) / path


def _unique_paths(paths: tuple[str, ...]) -> tuple[str, ...]:
    seen = set()
    ordered = []
    for path in paths:
        if path in seen:
            continue
        seen.add(path)
        ordered.append(path)
    return tuple(ordered)


def _runner_expected_framework_files() -> dict[str, tuple[str, ...]]:
    return {
        backend: tuple(
            (Path(FRAMEWORK_OUTPUT_DIR) / "otoe" / path).as_posix()
            for path in _unique_paths(CORE_RUNTIME_FILES + files)
        )
        for backend, files in BACKEND_RUNTIME_FILES.items()
    }


def _combined_status(plan_status: str, deps_status: str) -> str:
    if plan_status == "invalid" or deps_status == "invalid":
        return "invalid"
    if plan_status == "warnings" or deps_status == "warnings":
        return "warnings"
    return "ok"


def _copy_manifest_files(
    files,
    *,
    output_dir: Path,
    bundle_dir: str,
    missing_label: str,
) -> list[dict[str, Any]]:
    copied = []
    for file in files:
        if not file.source.exists():
            raise BuildError(f"{missing_label} {str(file.source)!r} does not exist")
        if not file.source.is_file():
            raise BuildError(f"{missing_label} path {str(file.source)!r} is not a file")
        bundle_path = Path(bundle_dir) / file.relative_path
        destination = output_dir / bundle_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        data = file.source.read_bytes()
        destination.write_bytes(data)
        copied.append(
            {
                "source": file.relative_path.as_posix(),
                "bundlePath": bundle_path.as_posix(),
                "size": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
            }
        )
    return copied
