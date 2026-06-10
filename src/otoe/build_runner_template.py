from __future__ import annotations

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
EXPECTED_FRAMEWORK_FILES = "__OTOE_EXPECTED_FRAMEWORK_FILES__"
CACHE_DIR_NAMES = frozenset({"__pycache__", ".pytest_cache"})
CACHE_SUFFIXES = (".pyc", ".pyo")
PACK_TOP_LEVEL_FILES = frozenset(
    {
        "manifest.json",
        "otoe-backend-coverage.json",
        "otoe-path0-external-backend.json",
        "otoe-plan.json",
        "otoe-deps.json",
        "otoe-render-tree.json",
        "otoe-styles.json",
        "otoe-run.py",
    }
)
PACK_DIRECTORIES = frozenset({"app", "assets", "backend", "framework"})


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
    mode.add_argument(
        "--backend-package-check",
        action="store_true",
        help="run the bundled backend package smoke check",
    )
    mode.add_argument(
        "--external-backend-check",
        action="store_true",
        help="run the bundled backend package against bundled app artifacts",
    )
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
    if args.backend_package_check:
        _verify_backend_package_smoke(manifest)
        package = manifest.get("backendPackage")
        if isinstance(package, dict):
            print(f"backend package checked: {package['path']}")
        else:
            print("backend package checked: none")
        return 0
    if args.external_backend_check:
        _verify_backend_package_render_tree(manifest)
        package = manifest.get("backendPackage")
        if isinstance(package, dict):
            print(f"external backend checked: {package['path']}")
        else:
            print("external backend checked: none")
        return 0

    mounted = _coerce_target(_load_target(manifest["target"]))
    if args.layout_check:
        stylesheet = _load_stylesheet(manifest)
        renderer_backend = _native_renderer_backend(manifest)
        if renderer_backend is None:
            from otoe import layout_native, paint_native

            layout = layout_native(mounted, stylesheet=stylesheet)
            paint_native(layout, background=args.background)
        else:
            layout = renderer_backend.layout(mounted, stylesheet=stylesheet)
            renderer_backend.paint(layout, background=args.background)
        print(f"layout checked: {manifest['target']}")
        return 0

    if args.png:
        from otoe import render_native_png

        output = Path(args.png)
        output.parent.mkdir(parents=True, exist_ok=True)
        stylesheet = _load_stylesheet(manifest)
        renderer_backend = _native_renderer_backend(manifest)
        render_native_png(
            mounted,
            output,
            stylesheet=stylesheet,
            background=args.background,
            renderer_backend=renderer_backend,
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
        "renderTree",
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
    backend_package = manifest.get("backendPackage")
    if backend_package is not None:
        _verify_manifest_backend_package_contract(backend_package)
    native_text = manifest.get("nativeText")
    if native_text is not None:
        _verify_manifest_native_text_contract(native_text)
    for group in ("assets", "frameworkFiles", "runtimeFiles"):
        if not isinstance(manifest.get(group), list):
            raise ValueError(f"manifest.json: {group} must be a list")
    _verify_manifest_file_entry_contracts(manifest)
    _verify_manifest_artifact_references(manifest)


def _require_manifest_string(manifest: dict[str, Any], key: str) -> str:
    value = manifest.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"manifest.json: {key} must be a non-empty string")
    return value


def _load_stylesheet(manifest: dict[str, Any]):
    styles_path = manifest.get("styles")
    if not styles_path:
        return None
    from otoe.style import stylesheet_from_style_ops_artifact

    payload = _load_json_bundle_file(styles_path, style_artifact=True)
    return stylesheet_from_style_ops_artifact(payload)


def _verify_bundle(manifest: dict[str, Any]) -> None:
    _verify_artifact_schemas(manifest)
    _verify_framework_policy(manifest)
    for key in ("plan", "deps", "styles", "renderTree"):
        _require_bundle_file(manifest[key])
    for index, artifact in enumerate(manifest.get("artifacts", [])):
        _verify_manifest_file(
            artifact,
            path_key="path",
            label=f"artifacts[{index}]",
        )
    runner = manifest.get("runner")
    _verify_manifest_file(runner, path_key="path", label="runner")
    for group in ("assets", "frameworkFiles", "runtimeFiles"):
        for index, entry in enumerate(manifest.get(group, [])):
            _verify_manifest_file(
                entry,
                path_key="bundlePath",
                label=f"{group}[{index}]",
            )
    native_text = manifest.get("nativeText")
    if isinstance(native_text, dict) and native_text.get("renderer") == "pillow":
        _verify_manifest_file(
            native_text.get("font"),
            path_key="bundlePath",
            label="nativeText.font",
        )
    _reject_unmanifested_bundle_files(manifest)
    _verify_backend_package_smoke(manifest)
    _verify_backend_package_render_tree(manifest)


def _verify_manifest_file_entry_contracts(manifest: dict[str, Any]) -> None:
    for key in ("plan", "deps", "styles", "renderTree"):
        _bundle_path(_require_manifest_string(manifest, key))
    if "backendCoverage" in manifest:
        backend_coverage = manifest.get("backendCoverage")
        if not isinstance(backend_coverage, str) or not backend_coverage:
            raise ValueError("manifest.json: backendCoverage must be a non-empty string")
        _bundle_path(backend_coverage)
    if "externalBackendReport" in manifest:
        external_backend_report = manifest.get("externalBackendReport")
        if (
            not isinstance(external_backend_report, str)
            or not external_backend_report
        ):
            raise ValueError(
                "manifest.json: externalBackendReport must be a non-empty string"
            )
        _bundle_path(external_backend_report)
    backend_package = manifest.get("backendPackage")
    if isinstance(backend_package, dict):
        path = backend_package.get("path")
        if isinstance(path, str):
            _bundle_path(path)

    declared: dict[str, str] = {}
    runner = manifest.get("runner")
    runner_path = _verify_manifest_file_entry(
        runner,
        path_key="path",
        label="runner",
    )
    _record_manifest_bundle_path(declared, runner_path, "runner.path")
    native_text = manifest.get("nativeText")
    if isinstance(native_text, dict) and native_text.get("renderer") == "pillow":
        relative = _verify_manifest_file_entry(
            native_text.get("font"),
            path_key="bundlePath",
            label="nativeText.font",
        )
        _record_manifest_bundle_path(
            declared,
            relative,
            "nativeText.font.bundlePath",
        )
    for index, artifact in enumerate(manifest.get("artifacts", [])):
        relative = _verify_manifest_file_entry(
            artifact,
            path_key="path",
            label=f"artifacts[{index}]",
        )
        _record_manifest_bundle_path(
            declared,
            relative,
            f"artifacts[{index}].path",
        )
    for group in ("assets", "frameworkFiles", "runtimeFiles"):
        for index, entry in enumerate(manifest.get(group, [])):
            relative = _verify_manifest_file_entry(
                entry,
                path_key="bundlePath",
                label=f"{group}[{index}]",
            )
            _record_manifest_bundle_path(
                declared,
                relative,
                f"{group}[{index}].bundlePath",
            )


def _record_manifest_bundle_path(
    declared: dict[str, str],
    relative: str,
    label: str,
) -> None:
    previous = declared.get(relative)
    if previous is not None:
        raise ValueError(
            "manifest.json: duplicate bundle path "
            f"{relative!r} in {label}; already declared by {previous}"
        )
    declared[relative] = label


def _verify_manifest_artifact_references(manifest: dict[str, Any]) -> None:
    for key in ("plan", "deps", "styles", "renderTree"):
        _require_artifact_entry(manifest, manifest[key])
    if "backendCoverage" in manifest:
        _require_artifact_entry(manifest, manifest["backendCoverage"])
    if "externalBackendReport" in manifest:
        _require_artifact_entry(manifest, manifest["externalBackendReport"])
    backend_package = manifest.get("backendPackage")
    if isinstance(backend_package, dict):
        _require_artifact_entry(manifest, backend_package.get("path"))


def _reject_unmanifested_bundle_files(manifest: dict[str, Any]) -> None:
    allowed = _manifest_pack_paths(manifest)
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        relative_path = path.relative_to(ROOT)
        if not _is_pack_path(relative_path):
            continue
        if _is_cache_path(relative_path):
            continue
        relative = relative_path.as_posix()
        if relative not in allowed:
            raise ValueError(f"unmanifested bundle file {relative!r}")


def _manifest_pack_paths(manifest: dict[str, Any]) -> set[str]:
    paths = {"manifest.json"}
    for key in (
        "plan",
        "deps",
        "styles",
        "renderTree",
        "backendCoverage",
        "externalBackendReport",
    ):
        value = manifest.get(key)
        if isinstance(value, str):
            paths.add(value)
    runner = manifest.get("runner")
    if isinstance(runner, dict):
        value = runner.get("path")
        if isinstance(value, str):
            paths.add(value)
    for artifact in manifest.get("artifacts", []):
        if isinstance(artifact, dict):
            value = artifact.get("path")
            if isinstance(value, str):
                paths.add(value)
    for group in ("assets", "frameworkFiles", "runtimeFiles"):
        for entry in manifest.get(group, []):
            if isinstance(entry, dict):
                value = entry.get("bundlePath")
                if isinstance(value, str):
                    paths.add(value)
    native_text = manifest.get("nativeText")
    if isinstance(native_text, dict):
        font = native_text.get("font")
        if isinstance(font, dict):
            value = font.get("bundlePath")
            if isinstance(value, str):
                paths.add(value)
    return paths


def _is_pack_path(relative: Path) -> bool:
    if len(relative.parts) == 1:
        return relative.name in PACK_TOP_LEVEL_FILES
    return relative.parts[0] in PACK_DIRECTORIES


def _is_cache_path(relative: Path) -> bool:
    if any(part in CACHE_DIR_NAMES for part in relative.parts):
        return True
    return relative.suffix in CACHE_SUFFIXES


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
    _verify_dependency_audit_contract(deps, manifest["deps"])
    styles = _load_json_bundle_file(manifest["styles"], style_artifact=True)
    if styles.get("status") == "invalid":
        raise ValueError(f"{manifest['styles']}: style artifact is invalid")
    render_tree = _load_json_bundle_file(manifest["renderTree"])
    _verify_render_tree_schema(render_tree, manifest["renderTree"])
    backend_coverage = manifest.get("backendCoverage")
    if backend_coverage is not None:
        _verify_backend_coverage(backend_coverage)
    if manifest.get("backendPackage") is not None:
        _verify_backend_package(manifest)
    if manifest.get("externalBackendReport") is not None:
        _verify_backend_package_report(manifest)


def _verify_manifest_backend_package_contract(package: Any) -> None:
    if not isinstance(package, dict):
        raise ValueError("manifest.json: backendPackage must be an object")
    for key in ("name", "label", "kind", "path", "root", "entrypoint", "packageHash"):
        _require_non_empty_string(package, key, "manifest.json.backendPackage")
    _bundle_path(package["path"])
    _bundle_path(package["entrypoint"])
    _bundle_path(package["root"] + "/backend-package.json")
    if not _is_sha256_uri(package.get("packageHash")):
        raise ValueError(
            "manifest.json.backendPackage.packageHash must be a sha256 string"
        )
    files = package.get("files")
    if not isinstance(files, list) or not files:
        raise ValueError("manifest.json.backendPackage.files must be a non-empty list")
    for index, relative in enumerate(files):
        if not isinstance(relative, str) or not relative:
            raise ValueError(
                f"manifest.json.backendPackage.files[{index}] "
                "must be a non-empty string"
            )
        _bundle_path(relative)


def _verify_manifest_native_text_contract(native_text: Any) -> None:
    if not isinstance(native_text, dict):
        raise ValueError("manifest.json: nativeText must be an object")
    renderer = native_text.get("renderer")
    if renderer not in {"marker", "pillow"}:
        raise ValueError(
            "manifest.json.nativeText.renderer must be one of 'marker', 'pillow'"
        )
    font = native_text.get("font")
    if renderer == "marker":
        if font is not None:
            raise ValueError("manifest.json.nativeText.font requires renderer 'pillow'")
        return
    _verify_manifest_file_entry(
        font,
        path_key="bundlePath",
        label="nativeText.font",
    )


def _native_renderer_backend(manifest: dict[str, Any]):
    native_text = manifest.get("nativeText")
    if not isinstance(native_text, dict):
        return None
    renderer = native_text.get("renderer")
    if renderer == "marker":
        return None
    if renderer != "pillow":
        raise ValueError(
            "manifest.json.nativeText.renderer must be one of 'marker', 'pillow'"
        )
    font = native_text.get("font")
    if not isinstance(font, dict):
        raise ValueError("manifest.json: nativeText.font must be an object")
    bundle_path = font.get("bundlePath")
    if not isinstance(bundle_path, str) or not bundle_path:
        raise ValueError(
            "manifest.json: nativeText.font.bundlePath must be a non-empty string"
        )
    font_path = _require_bundle_file(bundle_path)
    from otoe import PillowNativeRendererBackend

    return PillowNativeRendererBackend(font_path=font_path)


def _verify_backend_package(manifest: dict[str, Any]) -> None:
    from otoe.bundle_backend_package import verify_backend_package

    verify_backend_package(manifest, root=ROOT)


def _verify_backend_package_smoke(manifest: dict[str, Any]) -> None:
    from otoe.bundle_backend_package import verify_backend_package_smoke

    verify_backend_package_smoke(manifest, root=ROOT, executable=sys.executable)


def _verify_backend_package_render_tree(manifest: dict[str, Any]) -> None:
    from otoe.bundle_backend_package import verify_backend_package_render_tree

    verify_backend_package_render_tree(manifest, root=ROOT, executable=sys.executable)


def _verify_backend_package_report(manifest: dict[str, Any]) -> None:
    from otoe.bundle_backend_package import verify_backend_package_report

    verify_backend_package_report(manifest, root=ROOT)


def _verify_dependency_audit_contract(payload: dict[str, Any], label: str) -> None:
    from otoe.bundle_deps import verify_dependency_audit_contract

    verify_dependency_audit_contract(payload, label)


def _verify_backend_coverage(relative: Any) -> None:
    if not isinstance(relative, str):
        raise ValueError("manifest.json: backendCoverage must be a string")
    payload = _load_json_bundle_file(relative)
    from otoe.bundle_backend_coverage import verify_backend_coverage_contract

    verify_backend_coverage_contract(payload, relative)


def _is_sha256_uri(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    prefix = "sha256:"
    if len(value) != len(prefix) + 64 or not value.startswith(prefix):
        return False
    digest = value[len(prefix) :]
    return all(char in "0123456789abcdef" for char in digest)


def _require_non_empty_string(payload: dict[str, Any], key: str, label: str) -> None:
    if not isinstance(payload.get(key), str) or not payload.get(key):
        raise ValueError(f"{label}.{key} must be a non-empty string")


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


def _verify_render_tree_schema(payload: dict[str, Any], label: str) -> None:
    from otoe.render_ir import RenderIRError, render_tree_from_dict

    try:
        render_tree_from_dict(payload)
    except RenderIRError as exc:
        raise ValueError(f"{label}: {exc}") from exc


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


def _verify_manifest_file(entry: Any, *, path_key: str, label: str) -> None:
    relative = _verify_manifest_file_entry(
        entry,
        path_key=path_key,
        label=label,
    )
    path = _require_bundle_file(relative)
    data = path.read_bytes()
    expected_size = entry["size"]
    if len(data) != expected_size:
        raise ValueError(
            f"{relative}: expected size {expected_size}, got {len(data)}"
        )
    expected_sha = entry["sha256"]
    actual_sha = hashlib.sha256(data).hexdigest()
    if actual_sha != expected_sha:
        raise ValueError(f"{relative}: sha256 mismatch")


def _verify_manifest_file_entry(entry: Any, *, path_key: str, label: str) -> str:
    if not isinstance(entry, dict):
        raise ValueError(f"manifest.json: {label} must be an object")
    relative = entry.get(path_key)
    if not isinstance(relative, str) or not relative:
        raise ValueError(
            f"manifest.json: {label}.{path_key} must be a non-empty string"
        )
    _bundle_path(relative)
    size = entry.get("size")
    if type(size) is not int or size < 0:
        raise ValueError(f"manifest.json: {label}.size must be a non-negative integer")
    sha256 = entry.get("sha256")
    if not _is_sha256_hexdigest(sha256):
        raise ValueError(
            f"manifest.json: {label}.sha256 must be a lowercase sha256 hex digest"
        )
    return relative


def _is_sha256_hexdigest(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    return all(char in "0123456789abcdef" for char in value)


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
