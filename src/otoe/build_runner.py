from __future__ import annotations

from collections.abc import Mapping, Sequence
from pprint import pformat


def build_runner_source(expected_framework_files: Mapping[str, Sequence[str]]) -> str:
    source = '''from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
MANIFEST_PATH = ROOT / "manifest.json"
EXPECTED_SCHEMA_VERSION = 1
EXPECTED_FRAMEWORK_FILES = __EXPECTED_FRAMEWORK_FILES__


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="otoe-run")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="load the bundled target")
    mode.add_argument(
        "--layout-check",
        action="store_true",
        help="layout and paint the bundled target without writing output",
    )
    mode.add_argument("--png", help="render one native PNG frame")
    mode.add_argument("--verify", action="store_true", help="verify bundled files")
    parser.add_argument("--background", default="#ffffff", help="PNG background")
    args = parser.parse_args(argv)

    manifest = _load_manifest()
    _verify_manifest_contract(manifest)
    _verify_framework_policy(manifest)
    _install_pythonpath()
    _verify_artifact_schemas(manifest)
    if args.verify:
        _verify_bundle(manifest)
        print("verified: manifest.json")
        return 0

    mounted = _coerce_target(_load_target(manifest["target"]))
    if args.layout_check:
        from otoe import layout_native, paint_native

        stylesheet = _load_stylesheet(manifest)
        layout = layout_native(mounted, stylesheet=stylesheet)
        paint_native(layout, background=args.background)
        print(f"layout checked: {manifest['target']}")
        return 0

    if args.png:
        from otoe import render_native_png

        output = Path(args.png)
        output.parent.mkdir(parents=True, exist_ok=True)
        stylesheet = _load_stylesheet(manifest)
        render_native_png(
            mounted,
            output,
            stylesheet=stylesheet,
            background=args.background,
        )
        print(f"png: {output}")
        return 0

    print(f"loaded: {manifest['target']}")
    return 0


def _install_pythonpath() -> None:
    for relative in reversed(("app", "framework")):
        sys.path.insert(0, str(ROOT / relative))


def _load_manifest() -> dict[str, Any]:
    payload = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    _verify_schema_version(payload, "manifest.json")
    return payload


def _verify_manifest_contract(manifest: dict[str, Any]) -> None:
    for key in (
        "target",
        "profile",
        "backend",
        "backendCapability",
        "plan",
        "deps",
        "styles",
    ):
        _require_manifest_string(manifest, key)
    if manifest.get("runtimeInstallsAllowed") is not False:
        raise ValueError("manifest.json: runtimeInstallsAllowed must be false")
    status = manifest.get("status")
    if status not in {"ok", "warnings"}:
        raise ValueError("manifest.json: status must be 'ok' or 'warnings'")
    if not isinstance(manifest.get("artifacts"), list):
        raise ValueError("manifest.json: artifacts must be a list")
    if not isinstance(manifest.get("runner"), dict):
        raise ValueError("manifest.json: runner must be an object")
    for group in ("assets", "frameworkFiles", "runtimeFiles"):
        if not isinstance(manifest.get(group), list):
            raise ValueError(f"manifest.json: {group} must be a list")


def _require_manifest_string(manifest: dict[str, Any], key: str) -> str:
    value = manifest.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"manifest.json: {key} must be a non-empty string")
    return value


def _load_stylesheet(manifest: dict[str, Any]):
    styles_path = manifest.get("styles")
    if not styles_path:
        return None
    from otoe.style import stylesheet_from_artifact

    payload = _load_json_bundle_file(styles_path, style_artifact=True)
    return stylesheet_from_artifact(payload)


def _verify_bundle(manifest: dict[str, Any]) -> None:
    _verify_artifact_schemas(manifest)
    _verify_framework_policy(manifest)
    for key in ("plan", "deps", "styles"):
        _require_bundle_file(manifest[key])
        _require_artifact_entry(manifest, manifest[key])
    if "backendCoverage" in manifest:
        _require_artifact_entry(manifest, manifest["backendCoverage"])
    for artifact in manifest.get("artifacts", []):
        _verify_manifest_file(artifact, path_key="path")
    runner = manifest.get("runner")
    if runner:
        _verify_manifest_file(runner, path_key="path")
    for group in ("assets", "frameworkFiles", "runtimeFiles"):
        for entry in manifest.get(group, []):
            _verify_manifest_file(entry, path_key="bundlePath")


def _verify_framework_policy(manifest: dict[str, Any]) -> None:
    backend = manifest.get("backend")
    if not backend:
        raise ValueError("manifest.json: missing backend")
    expected_files = EXPECTED_FRAMEWORK_FILES.get(backend)
    if expected_files is None:
        supported = ", ".join(sorted(EXPECTED_FRAMEWORK_FILES))
        raise ValueError(
            f"manifest.json: unsupported backend {backend!r}; supported: {supported}"
        )

    framework_files = manifest.get("frameworkFiles")
    if not isinstance(framework_files, list):
        raise ValueError("manifest.json: frameworkFiles must be a list")
    listed_files = {
        entry.get("bundlePath")
        for entry in framework_files
        if isinstance(entry, dict)
    }
    for expected in expected_files:
        if expected not in listed_files:
            raise ValueError(
                "manifest.json: frameworkFiles missing required file "
                f"{expected!r} for backend {backend!r}"
            )
        _require_bundle_file(expected)


def _verify_artifact_schemas(manifest: dict[str, Any]) -> None:
    plan = _load_json_bundle_file(manifest["plan"])
    if plan.get("hasErrors") is not False or plan.get("status") == "invalid":
        raise ValueError(f"{manifest['plan']}: plan has errors")
    deps = _load_json_bundle_file(manifest["deps"])
    if deps.get("hasErrors") is not False or deps.get("status") == "invalid":
        raise ValueError(f"{manifest['deps']}: dependency audit has errors")
    styles = _load_json_bundle_file(manifest["styles"], style_artifact=True)
    if styles.get("status") == "invalid":
        raise ValueError(f"{manifest['styles']}: style artifact is invalid")
    backend_coverage = manifest.get("backendCoverage")
    if backend_coverage is not None:
        _verify_backend_coverage(backend_coverage)


def _verify_backend_coverage(relative: Any) -> None:
    if not isinstance(relative, str):
        raise ValueError("manifest.json: backendCoverage must be a string")
    payload = _load_json_bundle_file(relative)
    if payload.get("format") != "backend-coverage-report":
        raise ValueError(f"{relative}: format must be 'backend-coverage-report'")
    if payload.get("passed") is not True:
        blockers = payload.get("blockers", [])
        if isinstance(blockers, list) and blockers:
            details = ", ".join(str(blocker) for blocker in blockers)
        else:
            details = "backend coverage failed"
        raise ValueError(f"{relative}: backend coverage failed: {details}")


def _load_json_bundle_file(
    relative: str,
    *,
    style_artifact: bool = False,
) -> dict[str, Any]:
    payload = json.loads(_require_bundle_file(relative).read_text(encoding="utf-8"))
    _verify_schema_version(payload, relative)
    if style_artifact:
        _verify_style_ops_schema(payload, relative)
    return payload


def _verify_style_ops_schema(payload: dict[str, Any], label: str) -> None:
    from otoe.style_ops import StyleIRError, load_style_ir, validate_style_ops

    try:
        validation = validate_style_ops(load_style_ir(payload))
    except StyleIRError as exc:
        details = str(exc)
        if details.startswith("styleOps:"):
            raise ValueError(f"{label} {details}") from exc
        raise ValueError(f"{label}: {details}") from exc
    if validation.passed:
        return
    details = "; ".join(validation.errors) or "styleOps drift detected"
    raise ValueError(f"{label}: styleOps validation failed: {details}")


def _verify_schema_version(payload: Any, label: str) -> None:
    if not isinstance(payload, dict):
        raise ValueError(f"{label}: expected JSON object")
    if "schemaVersion" not in payload:
        raise ValueError(
            f"{label}: missing schemaVersion; expected {EXPECTED_SCHEMA_VERSION}"
        )
    version = payload["schemaVersion"]
    if version != EXPECTED_SCHEMA_VERSION:
        raise ValueError(
            f"{label}: unsupported schemaVersion {version!r}; "
            f"expected {EXPECTED_SCHEMA_VERSION}"
        )


def _verify_manifest_file(entry: dict[str, Any], *, path_key: str) -> None:
    relative = entry[path_key]
    path = _require_bundle_file(relative)
    data = path.read_bytes()
    expected_size = entry.get("size")
    if expected_size is not None and len(data) != expected_size:
        raise ValueError(
            f"{relative}: expected size {expected_size}, got {len(data)}"
        )
    expected_sha = entry.get("sha256")
    if expected_sha is not None:
        actual_sha = hashlib.sha256(data).hexdigest()
        if actual_sha != expected_sha:
            raise ValueError(f"{relative}: sha256 mismatch")


def _require_artifact_entry(manifest: dict[str, Any], relative: Any) -> None:
    if not isinstance(relative, str):
        raise ValueError("manifest.json: backendCoverage must be a string")
    artifacts = manifest.get("artifacts", [])
    if not isinstance(artifacts, list):
        raise ValueError("manifest.json: artifacts must be a list")
    if any(
        isinstance(artifact, dict) and artifact.get("path") == relative
        for artifact in artifacts
    ):
        return
    raise ValueError(f"manifest.json: artifacts missing {relative!r}")


def _require_bundle_file(relative: str) -> Path:
    path = _bundle_path(relative)
    if not path.is_file():
        raise FileNotFoundError(f"bundle file {relative!r} does not exist")
    return path


def _bundle_path(relative: str) -> Path:
    path = Path(relative)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError(f"bundle path {relative!r} is not safe")
    return ROOT / path


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
    return source.replace(
        "__EXPECTED_FRAMEWORK_FILES__",
        pformat(_normalize_expected_framework_files(expected_framework_files), width=88),
    )


def _normalize_expected_framework_files(
    expected_framework_files: Mapping[str, Sequence[str]],
) -> dict[str, tuple[str, ...]]:
    return {
        backend: tuple(files)
        for backend, files in expected_framework_files.items()
    }
