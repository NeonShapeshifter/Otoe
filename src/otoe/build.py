from __future__ import annotations

import ast
import hashlib
from dataclasses import dataclass
from typing import Any, Iterable, Mapping

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
RENDER_TREE_ARTIFACT_FILENAME = "otoe-render-tree.json"
PATH0_EXTERNAL_BACKEND_ARTIFACT_FILENAME = "otoe-path0-external-backend.json"
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
    "experimental/__init__.py",
    "experimental/backend.py",
    "experimental/native.py",
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
    "_style_schema.py",
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
    "_widget_contracts.py",
    "_ui_commands.py",
    "_ui_data.py",
    "_ui_helpers.py",
    "_ui_keyboard.py",
    "_ui_layout.py",
    "_ui_models.py",
    "_ui_navigation.py",
    "_ui_overlays.py",
    "_ui_surfaces.py",
    "_ui_theme.py",
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
        "_native_pillow.py",
        "_native_png.py",
        "_native_shared.py",
        "_native_surface.py",
        "_native_surface_focus.py",
        "_native_surface_input.py",
        "_native_surface_scroll.py",
        "_native_text.py",
    ),
}
# Keep this empty unless an imported local module is intentionally excluded
# from frameworkFiles and the reason is documented near the test.
FRAMEWORK_IMPORT_DEPENDENCY_ALLOWLIST: Mapping[str, frozenset[str]] = {}


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
    external_backend_report: dict[str, Any] | None = None,
    framework_files: list[dict[str, Any]] | None = None,
    native_text: dict[str, Any] | None = None,
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
        "renderTree": RENDER_TREE_ARTIFACT_FILENAME,
        "artifacts": artifacts or [],
        "assets": assets or [],
        "frameworkFiles": framework_files or [],
        "runner": runner or {},
        "runtimeFiles": runtime_files or [],
        "status": _combined_status(plan["status"], deps["status"]),
    }
    if native_text is not None:
        manifest["nativeText"] = native_text
    if backend_coverage is not None:
        manifest["backendCoverage"] = BACKEND_COVERAGE_ARTIFACT_FILENAME
    if backend_package is not None:
        manifest["backendPackage"] = backend_package
    if external_backend_report is not None:
        manifest["externalBackendReport"] = PATH0_EXTERNAL_BACKEND_ARTIFACT_FILENAME
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


def copy_native_text_font(
    profile_config: PlanProfileConfig,
    *,
    output_dir: Path,
) -> dict[str, Any] | None:
    if profile_config.native_text.renderer == "marker":
        return None
    font = profile_config.native_text.font
    relative_path = profile_config.native_text.font_relative_path
    if font is None or relative_path is None:
        raise BuildError("native text renderer 'pillow' requires a font file")
    copied = _copy_manifest_files(
        (ProfileAsset(source=font, relative_path=relative_path),),
        output_dir=output_dir,
        bundle_dir=ASSET_OUTPUT_DIR,
        missing_label="native text font file",
    )
    return {
        "renderer": profile_config.native_text.renderer,
        "font": copied[0],
    }


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
        "modes": [
            "backend-package-check",
            "check",
            "external-backend-check",
            "layout-check",
            "png",
            "verify",
        ],
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
    paths = _framework_runtime_paths(backend_name)
    return tuple(
        BundleFile(
            source=OTOE_PACKAGE_DIR / path,
            relative_path=Path("otoe") / path,
        )
        for path in paths
    )


def _framework_runtime_paths(backend_name: str) -> tuple[str, ...]:
    if backend_name not in BACKEND_RUNTIME_FILES:
        supported = ", ".join(sorted(BACKEND_RUNTIME_FILES))
        raise BuildError(
            f"unsupported build backend {backend_name!r}; supported: {supported}"
        )
    return _unique_paths(CORE_RUNTIME_FILES + BACKEND_RUNTIME_FILES[backend_name])


def _framework_import_dependency_errors(
    backend_name: str,
    *,
    included_paths: Iterable[str] | None = None,
    allowlist: Mapping[str, Iterable[str]] | None = None,
) -> tuple[str, ...]:
    paths = (
        tuple(included_paths)
        if included_paths is not None
        else _framework_runtime_paths(backend_name)
    )
    included = set(paths)
    allowed = _normalize_framework_dependency_allowlist(
        allowlist or FRAMEWORK_IMPORT_DEPENDENCY_ALLOWLIST
    )
    errors: list[str] = []
    for source_path in sorted(path for path in included if path.endswith(".py")):
        for dependency_path in _local_runtime_imports(source_path):
            if dependency_path in included:
                continue
            if dependency_path in allowed.get(source_path, frozenset()):
                continue
            if dependency_path in allowed.get("*", frozenset()):
                continue
            errors.append(
                f"{source_path} imports {dependency_path}, but {dependency_path} "
                f"is not included in frameworkFiles for backend {backend_name!r}"
            )
    return tuple(errors)


def _normalize_framework_dependency_allowlist(
    allowlist: Mapping[str, Iterable[str]],
) -> dict[str, frozenset[str]]:
    return {source: frozenset(dependencies) for source, dependencies in allowlist.items()}


def _local_runtime_imports(runtime_path: str) -> tuple[str, ...]:
    source_path = OTOE_PACKAGE_DIR / runtime_path
    if source_path.suffix != ".py" or not source_path.is_file():
        return ()

    tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
    dependencies: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            dependencies.update(_import_from_local_runtime_files(runtime_path, node))
        elif isinstance(node, ast.Import):
            for alias in node.names:
                dependency = _absolute_otoe_module_runtime_file(alias.name)
                if dependency is not None:
                    dependencies.add(dependency)
    dependencies.discard(runtime_path)
    return tuple(sorted(dependencies))


def _import_from_local_runtime_files(
    runtime_path: str,
    node: ast.ImportFrom,
) -> tuple[str, ...]:
    dependencies: set[str] = set()
    if node.level:
        base_parts = _relative_import_base_parts(runtime_path, node.level)
        if node.module is None:
            for alias in node.names:
                dependency = _module_runtime_file((*base_parts, *alias.name.split(".")))
                if dependency is not None:
                    dependencies.add(dependency)
            return tuple(sorted(dependencies))

        module_parts = (*base_parts, *node.module.split("."))
        dependency = _module_runtime_file(module_parts)
        if dependency is not None:
            dependencies.add(dependency)
        if _is_runtime_package(module_parts):
            for alias in node.names:
                dependency = _module_runtime_file((*module_parts, *alias.name.split(".")))
                if dependency is not None:
                    dependencies.add(dependency)
        return tuple(sorted(dependencies))

    if node.module is None:
        return ()
    if node.module == "otoe":
        for alias in node.names:
            dependency = _module_runtime_file(tuple(alias.name.split(".")))
            if dependency is not None:
                dependencies.add(dependency)
        return tuple(sorted(dependencies))
    if node.module.startswith("otoe."):
        module_parts = tuple(node.module.split(".")[1:])
        dependency = _module_runtime_file(module_parts)
        if dependency is not None:
            dependencies.add(dependency)
        if _is_runtime_package(module_parts):
            for alias in node.names:
                dependency = _module_runtime_file((*module_parts, *alias.name.split(".")))
                if dependency is not None:
                    dependencies.add(dependency)
    return tuple(sorted(dependencies))


def _relative_import_base_parts(runtime_path: str, level: int) -> tuple[str, ...]:
    package_parts = Path(runtime_path).parent.parts
    parent_levels = level - 1
    if parent_levels > len(package_parts):
        return ()
    if parent_levels == 0:
        return package_parts
    return package_parts[:-parent_levels]


def _absolute_otoe_module_runtime_file(module_name: str) -> str | None:
    if module_name == "otoe":
        return "__init__.py"
    if not module_name.startswith("otoe."):
        return None
    return _module_runtime_file(tuple(module_name.split(".")[1:]))


def _module_runtime_file(module_parts: tuple[str, ...]) -> str | None:
    if not module_parts:
        return "__init__.py"
    module_file = Path(*module_parts).with_suffix(".py")
    if (OTOE_PACKAGE_DIR / module_file).is_file():
        return module_file.as_posix()
    package_file = Path(*module_parts) / "__init__.py"
    if (OTOE_PACKAGE_DIR / package_file).is_file():
        return package_file.as_posix()
    return None


def _is_runtime_package(module_parts: tuple[str, ...]) -> bool:
    if not module_parts:
        return True
    package_file = Path(*module_parts) / "__init__.py"
    return (OTOE_PACKAGE_DIR / package_file).is_file()


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
    files: Iterable[BundleFile | ProfileAsset | ProfileRuntimeFile],
    *,
    output_dir: Path,
    bundle_dir: str,
    missing_label: str,
) -> list[dict[str, Any]]:
    copied: list[dict[str, Any]] = []
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
