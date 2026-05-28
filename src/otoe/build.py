from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

from pathlib import Path

from .profile import PlanProfileConfig, ProfileAsset, ProfileRuntimeFile


PLAN_ARTIFACT_FILENAME = "otoe-plan.json"
DEPS_ARTIFACT_FILENAME = "otoe-deps.json"
BUILD_MANIFEST_FILENAME = "manifest.json"
RUNNER_FILENAME = "otoe-run.py"
ASSET_OUTPUT_DIR = "assets"
RUNTIME_OUTPUT_DIR = "app"
FRAMEWORK_OUTPUT_DIR = "framework"
RUNNER_PYTHON_PATH = ("app", "framework")
OTOE_PACKAGE_DIR = Path(__file__).resolve().parent
CORE_RUNTIME_FILES = (
    "__init__.py",
    "api_status.py",
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
    "scheduler.py",
    "snapshot.py",
    "style.py",
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
)
BACKEND_RUNTIME_FILES = {
    "native": (
        "native.py",
        "_native_contracts.py",
        "_native_hit_test.py",
        "_native_layout.py",
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


def build_manifest(
    *,
    target: str,
    plan: dict[str, Any],
    deps: dict[str, Any],
    profile_config: PlanProfileConfig,
    assets: list[dict[str, Any]] | None = None,
    framework_files: list[dict[str, Any]] | None = None,
    runner: dict[str, Any] | None = None,
    runtime_files: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if plan["hasErrors"]:
        raise BuildError("plan invalid; refusing to write build manifest")
    if deps["hasErrors"]:
        raise BuildError("dependency audit invalid; refusing to write build manifest")
    return {
        "schemaVersion": 1,
        "target": target,
        "profile": plan["profile"],
        "backend": profile_config.backend_name or "native",
        "runtimeInstallsAllowed": profile_config.allow_runtime_installs,
        "plan": PLAN_ARTIFACT_FILENAME,
        "deps": DEPS_ARTIFACT_FILENAME,
        "assets": assets or [],
        "frameworkFiles": framework_files or [],
        "runner": runner or {},
        "runtimeFiles": runtime_files or [],
        "status": _combined_status(plan["status"], deps["status"]),
    }


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


def write_runner(*, output_dir: Path) -> dict[str, Any]:
    runner_path = output_dir / RUNNER_FILENAME
    runner_path.write_text(_runner_source(), encoding="utf-8")
    data = runner_path.read_bytes()
    return {
        "path": RUNNER_FILENAME,
        "pythonPath": list(RUNNER_PYTHON_PATH),
        "modes": ["check", "png"],
        "size": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def _framework_files(profile_config: PlanProfileConfig) -> tuple[BundleFile, ...]:
    backend_name = profile_config.backend_name or "native"
    if backend_name not in BACKEND_RUNTIME_FILES:
        supported = ", ".join(sorted(BACKEND_RUNTIME_FILES))
        raise BuildError(f"unsupported build backend {backend_name!r}; supported: {supported}")
    paths = _unique_paths(CORE_RUNTIME_FILES + BACKEND_RUNTIME_FILES[backend_name])
    return tuple(
        BundleFile(
            source=OTOE_PACKAGE_DIR / path,
            relative_path=Path("otoe") / path,
        )
        for path in paths
    )


def _unique_paths(paths: tuple[str, ...]) -> tuple[str, ...]:
    seen = set()
    ordered = []
    for path in paths:
        if path in seen:
            continue
        seen.add(path)
        ordered.append(path)
    return tuple(ordered)


def _runner_source() -> str:
    return '''from __future__ import annotations

import argparse
import importlib
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
MANIFEST_PATH = ROOT / "manifest.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="otoe-run")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="load the bundled target")
    mode.add_argument("--png", help="render one native PNG frame")
    parser.add_argument("--background", default="#ffffff", help="PNG background")
    args = parser.parse_args(argv)

    _install_pythonpath()
    manifest = _load_manifest()
    mounted = _coerce_target(_load_target(manifest["target"]))
    if args.png:
        from otoe import render_native_png

        output = Path(args.png)
        output.parent.mkdir(parents=True, exist_ok=True)
        render_native_png(mounted, output, background=args.background)
        print(f"png: {output}")
        return 0

    print(f"loaded: {manifest['target']}")
    return 0


def _install_pythonpath() -> None:
    for relative in reversed(("app", "framework")):
        sys.path.insert(0, str(ROOT / relative))


def _load_manifest() -> dict[str, Any]:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def _load_target(spec: str) -> Any:
    module_name, separator, object_path = spec.partition(":")
    if not separator or not module_name or not object_path:
        raise ValueError("manifest target must use MODULE:OBJECT syntax")
    value = importlib.import_module(module_name)
    for part in object_path.split("."):
        value = getattr(value, part)
    return value


def _coerce_target(target: Any):
    from otoe import MountedNode, Node, mount

    if isinstance(target, MountedNode):
        return target
    if isinstance(target, Node):
        return mount(target)
    if callable(target):
        return _coerce_target(target())
    raise TypeError(
        "bundled target must be a Node, MountedNode, or zero-argument callable"
    )


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"otoe-run: {exc}", file=sys.stderr)
        raise SystemExit(1)
'''


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
