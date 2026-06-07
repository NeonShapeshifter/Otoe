from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from otoe.backend_package import (
    BackendPackageError,
    backend_package_manifest_from_dict,
    backend_package_payload_errors,
    backend_package_to_dict,
    copy_backend_package,
    load_backend_package_manifest,
)
from otoe.cli import main as otoe_cli_main


PACKAGE_MANIFEST = Path("examples/native/path0_external_backend.package.json")
STRICT_SHA256 = re.compile(r"^sha256:[0-9a-f]{64}$")


def test_backend_package_manifest_describes_path0_external_backend():
    manifest = load_backend_package_manifest(PACKAGE_MANIFEST)
    payload = backend_package_to_dict(manifest)

    assert manifest.name == "path0-external-json-backend"
    assert manifest.entrypoint.as_posix() == "path0_external_backend.py"
    assert manifest.entrypoint_source.is_file()
    assert payload["format"] == "backend-package"
    assert payload["name"] == "path0-external-json-backend"
    assert payload["entrypoint"] == "path0_external_backend.py"
    assert payload["contracts"] == {
        "inputs": ["otoe-render-tree"],
        "optionalInputs": ["otoe-styles"],
        "outputs": ["path0-layout-output", "path0-paint-output"],
        "readinessFlag": "--external-path0-backend",
    }
    assert payload["runtime"] == {
        "language": "python",
        "runtimeInstallsAllowed": False,
        "stdlibOnly": True,
    }
    assert payload["files"][0]["path"] == "path0_external_backend.py"
    assert payload["files"][0]["role"] == "runner"
    assert STRICT_SHA256.fullmatch(payload["packageHash"])
    assert backend_package_payload_errors(payload) == []


def test_backend_package_copy_materializes_descriptor_and_files(tmp_path):
    manifest = load_backend_package_manifest(PACKAGE_MANIFEST)
    output = tmp_path / "path0-package"

    payload = copy_backend_package(manifest, output_dir=output)

    descriptor = json.loads((output / "backend-package.json").read_text())
    assert descriptor == payload
    assert (output / "path0_external_backend.py").is_file()
    assert backend_package_payload_errors(descriptor) == []


def test_backend_package_manifest_rejects_unsafe_file_path(tmp_path):
    with pytest.raises(BackendPackageError, match="safe relative file path"):
        backend_package_manifest_from_dict(
            {
                "schemaVersion": 1,
                "format": "backend-package-manifest",
                "name": "unsafe",
                "label": "Unsafe",
                "kind": "path0-external-json",
                "entrypoint": "../runner.py",
                "files": [{"path": "../runner.py", "role": "runner"}],
                "contracts": {
                    "inputs": ["otoe-render-tree"],
                    "outputs": ["path0-layout-output"],
                },
                "runtime": {
                    "language": "python",
                    "runtimeInstallsAllowed": False,
                },
            },
            source_dir=tmp_path,
        )


def test_cli_backend_package_writes_package_dir(tmp_path, capsys):
    package_dir = tmp_path / "package"
    result = otoe_cli_main(
        [
            "backend-package",
            str(PACKAGE_MANIFEST),
            "--package-out",
            str(package_dir),
            "--json",
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert result == 0
    assert payload["format"] == "backend-package"
    assert payload["name"] == "path0-external-json-backend"
    assert (package_dir / "backend-package.json").is_file()
    assert (package_dir / "path0_external_backend.py").is_file()
    assert "backend package artifact:" not in captured.err
