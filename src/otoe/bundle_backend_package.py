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
        render_tree_path.write_text(
            json.dumps(_backend_package_smoke_render_tree(), sort_keys=True),
            encoding="utf-8",
        )
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
            "bundle-backend-package-smoke",
        ]
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
            raise ValueError(f"{package['path']}: backend package smoke timed out") from exc
        if result.returncode != 0:
            details = result.stderr.strip() or result.stdout.strip()
            if not details:
                details = f"backend package exited with status {result.returncode}"
            raise ValueError(f"{package['path']}: backend package smoke failed: {details}")
        layout = _load_json_file(layout_path, label="backend package layout output")
        paint = _load_json_file(paint_path, label="backend package paint output")
        report = _load_json_file(report_path, label="backend package report")
        _verify_path0_external_smoke_output(
            package=package,
            layout=layout,
            paint=paint,
            report=report,
        )


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
    output = report.get("output")
    if not isinstance(output, dict):
        raise ValueError("backend package report output must be an object")
    report_layout = output.get("layout")
    report_paint = output.get("paint")
    if not isinstance(report_layout, dict) or not isinstance(report_paint, dict):
        raise ValueError("backend package report must include layout and paint output")
    if report_layout.get("outputHash") != layout["outputHash"]:
        raise ValueError("backend package report layout hash mismatch")
    if report_paint.get("outputHash") != paint["outputHash"]:
        raise ValueError("backend package report paint hash mismatch")


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


def _positive_number(value: Any) -> bool:
    return type(value) in {int, float} and value > 0
