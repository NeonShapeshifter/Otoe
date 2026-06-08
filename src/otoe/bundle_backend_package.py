from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from .backend_package import backend_package_payload_errors


EXPECTED_SCHEMA_VERSION = 1


def verify_backend_package(manifest: dict[str, Any], *, root: str | Path) -> None:
    package = manifest.get("backendPackage")
    if package is None:
        return
    if not isinstance(package, dict):
        raise ValueError("manifest.json: backendPackage must be an object")

    descriptor_path = package["path"]
    descriptor = _load_json_bundle_file(root, descriptor_path)
    errors = backend_package_payload_errors(descriptor)
    if errors:
        raise ValueError(f"{descriptor_path}: {'; '.join(errors)}")
    for key in ("name", "label", "kind", "packageHash"):
        if descriptor.get(key) != package.get(key):
            raise ValueError(
                f"manifest.json.backendPackage.{key} must match {descriptor_path}"
            )

    package_root = Path(descriptor_path).parent
    expected_entrypoint = (package_root / descriptor["entrypoint"]).as_posix()
    if package.get("entrypoint") != expected_entrypoint:
        raise ValueError(
            "manifest.json.backendPackage.entrypoint must match backend package"
        )

    declared_files = set(package.get("files", []))
    descriptor_files = descriptor.get("files", [])
    for file_payload in descriptor_files:
        relative = (package_root / file_payload["path"]).as_posix()
        if relative not in declared_files:
            raise ValueError(
                "manifest.json.backendPackage.files missing "
                f"{relative!r} from {descriptor_path}"
            )
        _require_artifact_entry(manifest, relative)
        path = _require_bundle_file(root, relative)
        data = path.read_bytes()
        if len(data) != file_payload["size"]:
            raise ValueError(f"{descriptor_path}: file {relative!r} size mismatch")
        if hashlib.sha256(data).hexdigest() != file_payload["sha256"]:
            raise ValueError(f"{descriptor_path}: file {relative!r} sha256 mismatch")


def verify_backend_package_smoke(
    manifest: dict[str, Any],
    *,
    root: str | Path,
    executable: str | None = None,
    timeout: int = 10,
) -> None:
    package = manifest.get("backendPackage")
    if package is None:
        return
    if not isinstance(package, dict):
        raise ValueError("manifest.json: backendPackage must be an object")

    verify_backend_package(manifest, root=root)
    descriptor = _load_json_bundle_file(root, package["path"])
    if descriptor.get("kind") != "path0-external-json":
        raise ValueError(
            "manifest.json.backendPackage.kind must be 'path0-external-json' "
            "for bundled smoke verification"
        )
    runtime = descriptor.get("runtime")
    if not isinstance(runtime, dict) or runtime.get("language") != "python":
        raise ValueError(f"{package['path']}: runtime.language must be 'python'")

    package_root = _require_bundle_file(root, package["path"]).parent
    entrypoint = _require_bundle_file(root, package["entrypoint"])
    with tempfile.TemporaryDirectory(prefix="otoe-backend-package-") as directory:
        tempdir = Path(directory)
        render_tree_path = tempdir / "render-tree.json"
        layout_path = tempdir / "layout.json"
        paint_path = tempdir / "paint.json"
        report_path = tempdir / "report.json"
        render_tree_payload = _backend_package_smoke_render_tree()
        _write_json_file(render_tree_path, render_tree_payload)
        _run_backend_package_command(
            package=package,
            entrypoint=entrypoint,
            package_root=package_root,
            render_tree_path=render_tree_path,
            layout_path=layout_path,
            paint_path=paint_path,
            report_path=report_path,
            source="bundle-backend-package-smoke",
            executable=executable,
            timeout=timeout,
            error_label="backend package smoke",
        )
        layout = _load_json_file(layout_path, label="backend package layout output")
        paint = _load_json_file(paint_path, label="backend package paint output")
        report = _load_json_file(report_path, label="backend package report")
        _verify_path0_external_smoke_output(
            package=package,
            layout=layout,
            paint=paint,
            report=report,
            expected_source="bundle-backend-package-smoke",
            expected_render_tree=render_tree_payload,
            expected_styles=None,
        )


def verify_backend_package_render_tree(
    manifest: dict[str, Any],
    *,
    root: str | Path,
    executable: str | None = None,
    timeout: int = 10,
) -> None:
    package = manifest.get("backendPackage")
    if package is None:
        return
    if not isinstance(package, dict):
        raise ValueError("manifest.json: backendPackage must be an object")

    verify_backend_package(manifest, root=root)
    descriptor = _load_json_bundle_file(root, package["path"])
    if descriptor.get("kind") != "path0-external-json":
        raise ValueError(
            "manifest.json.backendPackage.kind must be 'path0-external-json' "
            "for bundled render-tree verification"
        )
    runtime = descriptor.get("runtime")
    if not isinstance(runtime, dict) or runtime.get("language") != "python":
        raise ValueError(f"{package['path']}: runtime.language must be 'python'")

    render_tree_relative = manifest.get("renderTree")
    if not isinstance(render_tree_relative, str) or not render_tree_relative:
        raise ValueError("manifest.json: renderTree must be a non-empty string")
    styles_relative = manifest.get("styles")
    if not isinstance(styles_relative, str) or not styles_relative:
        raise ValueError("manifest.json: styles must be a non-empty string")
    render_tree_payload = _load_json_bundle_file(root, render_tree_relative)
    styles_payload = _load_json_bundle_file(root, styles_relative)
    render_tree_path = _require_bundle_file(root, render_tree_relative)
    styles_path = _require_bundle_file(root, styles_relative)
    package_root = _require_bundle_file(root, package["path"]).parent
    entrypoint = _require_bundle_file(root, package["entrypoint"])
    with tempfile.TemporaryDirectory(prefix="otoe-backend-render-tree-") as directory:
        tempdir = Path(directory)
        layout_path = tempdir / "layout.json"
        paint_path = tempdir / "paint.json"
        report_path = tempdir / "report.json"
        _run_backend_package_command(
            package=package,
            entrypoint=entrypoint,
            package_root=package_root,
            render_tree_path=render_tree_path,
            styles_path=styles_path,
            layout_path=layout_path,
            paint_path=paint_path,
            report_path=report_path,
            source=f"bundle:{render_tree_relative}",
            executable=executable,
            timeout=timeout,
            error_label="backend package render-tree check",
        )
        layout = _load_json_file(layout_path, label="backend package layout output")
        paint = _load_json_file(paint_path, label="backend package paint output")
        report = _load_json_file(report_path, label="backend package report")
        _verify_path0_external_smoke_output(
            package=package,
            layout=layout,
            paint=paint,
            report=report,
            expected_source=f"bundle:{render_tree_relative}",
            expected_render_tree=render_tree_payload,
            expected_styles=styles_payload,
        )


def _run_backend_package_command(
    *,
    package: dict[str, Any],
    entrypoint: Path,
    package_root: Path,
    render_tree_path: Path,
    layout_path: Path,
    paint_path: Path,
    report_path: Path,
    source: str,
    executable: str | None,
    timeout: int,
    error_label: str,
    styles_path: Path | None = None,
) -> None:
    command = [
        executable or sys.executable,
        str(entrypoint),
        "--render-tree",
        str(render_tree_path),
        "--layout-out",
        str(layout_path),
        "--paint-out",
        str(paint_path),
        "--contract-out",
        str(report_path),
        "--source",
        source,
    ]
    if styles_path is not None:
        command.extend(["--styles", str(styles_path)])
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            cwd=package_root,
            env={**os.environ, "PYTHONPATH": ""},
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        raise ValueError(f"{package['path']}: {error_label} timed out") from exc
    if result.returncode != 0:
        details = result.stderr.strip() or result.stdout.strip()
        if not details:
            details = f"backend package exited with status {result.returncode}"
        raise ValueError(f"{package['path']}: {error_label} failed: {details}")


def _backend_package_smoke_render_tree() -> dict[str, Any]:
    return {
        "schemaVersion": 1,
        "format": "otoe-render-tree",
        "nodeCount": 1,
        "root": {
            "id": "smoke-root",
            "path": [],
            "name": "Text",
            "widgetId": "smoke-text",
            "key": None,
            "className": None,
            "props": {"content": "Backend package smoke"},
            "events": [],
            "state": [],
            "context": "backend-package-smoke",
            "style": {},
            "children": [],
        },
    }


def _verify_path0_external_smoke_output(
    *,
    package: dict[str, Any],
    layout: dict[str, Any],
    paint: dict[str, Any],
    report: dict[str, Any],
    expected_source: str,
    expected_render_tree: dict[str, Any],
    expected_styles: dict[str, Any] | None,
) -> None:
    if layout.get("format") != "path0-layout-output":
        raise ValueError("backend package layout output format mismatch")
    if not _positive_number(layout.get("boxCount")):
        raise ValueError("backend package layout output must contain boxes")
    if not _is_sha256_uri(layout.get("outputHash")):
        raise ValueError("backend package layout outputHash must be a sha256 string")
    if paint.get("format") != "path0-paint-output":
        raise ValueError("backend package paint output format mismatch")
    if not _positive_number(paint.get("commandCount")):
        raise ValueError("backend package paint output must contain commands")
    if not _is_sha256_uri(paint.get("outputHash")):
        raise ValueError("backend package paint outputHash must be a sha256 string")
    if report.get("format") != "path0-external-backend-report":
        raise ValueError("backend package report format mismatch")
    if report.get("backend") != package["name"]:
        raise ValueError("backend package report backend must match manifest package")
    if report.get("source") != expected_source:
        raise ValueError("backend package report source mismatch")
    output = report.get("output")
    if not isinstance(output, dict):
        raise ValueError("backend package report output must be an object")
    report_input = report.get("input")
    if not isinstance(report_input, dict):
        raise ValueError("backend package report input must be an object")
    expected_render_tree_hash = _contract_hash(expected_render_tree)
    if report_input.get("renderTreeHash") != expected_render_tree_hash:
        raise ValueError("backend package report render tree hash mismatch")
    if report_input.get("nodeCount") != expected_render_tree.get("nodeCount"):
        raise ValueError("backend package report node count mismatch")
    if layout.get("boxCount") != expected_render_tree.get("nodeCount"):
        raise ValueError("backend package layout boxCount must match render tree")
    _verify_report_style_ops_input(
        report_input.get("styleOps"),
        expected_styles=expected_styles,
    )
    report_layout = output.get("layout")
    report_paint = output.get("paint")
    if not isinstance(report_layout, dict) or not isinstance(report_paint, dict):
        raise ValueError("backend package report must include layout and paint output")
    if report_layout.get("outputHash") != layout["outputHash"]:
        raise ValueError("backend package report layout hash mismatch")
    if report_paint.get("outputHash") != paint["outputHash"]:
        raise ValueError("backend package report paint hash mismatch")


def _verify_report_style_ops_input(
    style_ops: Any,
    *,
    expected_styles: dict[str, Any] | None,
) -> None:
    if not isinstance(style_ops, dict):
        raise ValueError("backend package report input.styleOps must be an object")
    if expected_styles is None:
        if style_ops.get("present") is not False:
            raise ValueError(
                "backend package report input.styleOps.present must be false"
            )
        return
    if style_ops.get("present") is not True:
        raise ValueError("backend package report input.styleOps.present must be true")
    if style_ops.get("artifactHash") != _contract_hash(expected_styles):
        raise ValueError("backend package report style artifact hash mismatch")


def _require_artifact_entry(manifest: dict[str, Any], relative: str) -> None:
    artifacts = manifest.get("artifacts", [])
    if not isinstance(artifacts, list):
        raise ValueError("manifest.json: artifacts must be a list")
    if any(
        isinstance(artifact, dict) and artifact.get("path") == relative
        for artifact in artifacts
    ):
        return
    raise ValueError(f"manifest.json: artifacts missing {relative!r}")


def _load_json_bundle_file(root: str | Path, relative: str) -> dict[str, Any]:
    payload = json.loads(_require_bundle_file(root, relative).read_text(encoding="utf-8"))
    _verify_schema_version(payload, relative)
    return payload


def _load_json_file(path: Path, *, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"{label} file was not written") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"{label} must be valid JSON: {exc}") from exc
    _verify_schema_version(payload, label)
    return payload


def _write_json_file(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")


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


def _require_bundle_file(root: str | Path, relative: str) -> Path:
    path = _bundle_path(root, relative)
    if not path.is_file():
        raise FileNotFoundError(f"bundle file {relative!r} does not exist")
    return path


def _bundle_path(root: str | Path, relative: str) -> Path:
    path = Path(relative)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError(f"bundle path {relative!r} is not safe")
    return Path(root) / path


def _is_sha256_uri(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    prefix = "sha256:"
    if len(value) != len(prefix) + 64 or not value.startswith(prefix):
        return False
    digest = value[len(prefix) :]
    return all(char in "0123456789abcdef" for char in digest)


def _contract_hash(payload: Any) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


def _positive_number(value: Any) -> bool:
    return type(value) in {int, float} and value > 0
