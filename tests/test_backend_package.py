from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import sys
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
from otoe.bundle_backend_package import verify_backend_package_report
from otoe.cli import main as otoe_cli_main
from otoe.pack import pack_bundle
from otoe.profile import ProfileError, load_plan_profile


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


def test_backend_package_report_rejects_invalid_external_report_once(tmp_path):
    manifest = {
        "backendPackage": {"path": "backend/package/backend-package.json"},
        "externalBackendReport": "",
    }

    with pytest.raises(ValueError) as exc:
        verify_backend_package_report(manifest, root=tmp_path)

    message = "manifest.json: externalBackendReport must be a non-empty string"
    assert str(exc.value) == message
    assert str(exc.value).count(message) == 1


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


def test_profile_loads_backend_package_manifest_path(tmp_path):
    profile = tmp_path / "otoe.profile.toml"
    profile.write_text(
        'profile = "cage"\n'
        "\n"
        "[backend]\n"
        'name = "native"\n'
        "\n"
        "[backend.package]\n"
        'manifest = "path0_external_backend.package.json"\n',
        encoding="utf-8",
    )

    config = load_plan_profile(profile)

    assert config.backend_package_manifest == (
        tmp_path / "path0_external_backend.package.json"
    )


def test_profile_rejects_unsafe_backend_package_manifest_path(tmp_path):
    profile = tmp_path / "otoe.profile.toml"
    profile.write_text(
        'profile = "cage"\n'
        "\n"
        "[backend.package]\n"
        'manifest = "../path0_external_backend.package.json"\n',
        encoding="utf-8",
    )

    with pytest.raises(ProfileError, match="backend.package.manifest"):
        load_plan_profile(profile)


def test_cli_build_copies_profile_backend_package_as_declared_artifacts(
    tmp_path,
    monkeypatch,
    capsys,
):
    module = tmp_path / "backend_package_build_surface.py"
    module.write_text(
        "from otoe import Text\n"
        "app = Text('Backend package build')\n",
        encoding="utf-8",
    )
    package_manifest = tmp_path / PACKAGE_MANIFEST.name
    package_runner = tmp_path / "path0_external_backend.py"
    shutil.copyfile(PACKAGE_MANIFEST, package_manifest)
    shutil.copyfile(
        Path("examples/native/path0_external_backend.py"),
        package_runner,
    )
    profile = tmp_path / "otoe.profile.toml"
    profile.write_text(
        'profile = "cage"\n'
        "\n"
        "[backend]\n"
        'name = "native"\n'
        "\n"
        "[backend.package]\n"
        f'manifest = "{package_manifest.name}"\n',
        encoding="utf-8",
    )
    output = tmp_path / "dist" / "backend-package-build"
    monkeypatch.syspath_prepend(str(tmp_path))

    result = otoe_cli_main(
        [
            "build",
            "backend_package_build_surface:app",
            "--profile-file",
            str(profile),
            "--out",
            str(output),
            "--validate",
        ]
    )

    captured = capsys.readouterr()
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    package = manifest["backendPackage"]
    artifact_paths = {
        artifact["path"]
        for artifact in manifest["artifacts"]
        if isinstance(artifact, dict)
    }
    descriptor_path = output / package["path"]
    descriptor = json.loads(descriptor_path.read_text(encoding="utf-8"))
    backend_check = subprocess.run(
        [
            sys.executable,
            str(output / "otoe-run.py"),
            "--backend-package-check",
        ],
        capture_output=True,
        cwd=output,
        env={"PYTHONPATH": ""},
        text=True,
    )
    external_check = subprocess.run(
        [
            sys.executable,
            str(output / "otoe-run.py"),
            "--external-backend-check",
        ],
        capture_output=True,
        cwd=output,
        env={"PYTHONPATH": ""},
        text=True,
    )
    archive = pack_bundle(output, tmp_path / "bundle.otoe.tar.gz")
    render_tree = json.loads(
        (output / "otoe-render-tree.json").read_text(encoding="utf-8")
    )

    assert result == 0
    assert package["name"] == "path0-external-json-backend"
    assert package["path"] == (
        "backend/path0-external-json-backend/backend-package.json"
    )
    assert package["entrypoint"] == (
        "backend/path0-external-json-backend/path0_external_backend.py"
    )
    assert package["path"] in artifact_paths
    assert package["entrypoint"] in artifact_paths
    assert "otoe-render-tree.json" in artifact_paths
    assert descriptor["packageHash"] == package["packageHash"]
    assert backend_package_payload_errors(descriptor) == []
    assert (output / package["entrypoint"]).is_file()
    assert "backend-package-check" in manifest["runner"]["modes"]
    assert "external-backend-check" in manifest["runner"]["modes"]
    assert manifest["renderTree"] == "otoe-render-tree.json"
    assert render_tree["format"] == "otoe-render-tree"
    assert render_tree["nodeCount"] == 1
    assert backend_check.returncode == 0
    assert (
        "backend package checked: "
        "backend/path0-external-json-backend/backend-package.json"
    ) in backend_check.stdout
    assert external_check.returncode == 0
    assert (
        "external backend checked: "
        "backend/path0-external-json-backend/backend-package.json"
    ) in external_check.stdout
    assert manifest["externalBackendReport"] == "otoe-path0-external-backend.json"
    assert "otoe-path0-external-backend.json" in artifact_paths
    report = json.loads(
        (output / "otoe-path0-external-backend.json").read_text(encoding="utf-8")
    )
    assert report["format"] == "path0-external-backend-report"
    assert report["backend"] == "path0-external-json-backend"
    assert report["source"] == "bundle:otoe-render-tree.json"
    assert report["input"]["renderTreeHash"].startswith("sha256:")
    assert report["input"]["styleOps"]["present"] is True
    assert "backend package: backend/path0-external-json-backend/backend-package.json" in (
        captured.out
    )
    assert f"external backend artifact: {output / 'otoe-path0-external-backend.json'}" in (
        captured.out
    )
    assert archive.files > 0


def test_cli_build_backend_package_verify_rejects_external_report_drift(
    tmp_path,
    monkeypatch,
):
    module = tmp_path / "backend_package_report_tamper_surface.py"
    module.write_text(
        "from otoe import Text\n"
        "app = Text('Backend package report tamper')\n",
        encoding="utf-8",
    )
    package_manifest = tmp_path / PACKAGE_MANIFEST.name
    package_runner = tmp_path / "path0_external_backend.py"
    shutil.copyfile(PACKAGE_MANIFEST, package_manifest)
    shutil.copyfile(
        Path("examples/native/path0_external_backend.py"),
        package_runner,
    )
    profile = tmp_path / "otoe.profile.toml"
    profile.write_text(
        'profile = "cage"\n'
        "\n"
        "[backend.package]\n"
        f'manifest = "{package_manifest.name}"\n',
        encoding="utf-8",
    )
    output = tmp_path / "dist" / "backend-package-report-tamper"
    monkeypatch.syspath_prepend(str(tmp_path))

    assert (
        otoe_cli_main(
            [
                "build",
                "backend_package_report_tamper_surface:app",
                "--profile-file",
                str(profile),
                "--out",
                str(output),
            ]
        )
        == 0
    )

    report_path = output / "otoe-path0-external-backend.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["source"] = "bundle:wrong-render-tree.json"
    report_path.write_text(json.dumps(report, sort_keys=True), encoding="utf-8")
    _refresh_manifest_artifact_hash(output, "otoe-path0-external-backend.json")

    verify = subprocess.run(
        [sys.executable, str(output / "otoe-run.py"), "--verify"],
        capture_output=True,
        cwd=output,
        env={"PYTHONPATH": ""},
        text=True,
    )

    assert verify.returncode == 1
    assert "backend package report source mismatch" in verify.stderr


def test_cli_build_backend_package_verify_rejects_descriptor_file_hash_drift(
    tmp_path,
    monkeypatch,
):
    module = tmp_path / "backend_package_tamper_surface.py"
    module.write_text(
        "from otoe import Text\n"
        "app = Text('Backend package tamper')\n",
        encoding="utf-8",
    )
    package_manifest = tmp_path / PACKAGE_MANIFEST.name
    package_runner = tmp_path / "path0_external_backend.py"
    shutil.copyfile(PACKAGE_MANIFEST, package_manifest)
    shutil.copyfile(
        Path("examples/native/path0_external_backend.py"),
        package_runner,
    )
    profile = tmp_path / "otoe.profile.toml"
    profile.write_text(
        'profile = "cage"\n'
        "\n"
        "[backend.package]\n"
        f'manifest = "{package_manifest.name}"\n',
        encoding="utf-8",
    )
    output = tmp_path / "dist" / "backend-package-tamper"
    monkeypatch.syspath_prepend(str(tmp_path))

    assert (
        otoe_cli_main(
            [
                "build",
                "backend_package_tamper_surface:app",
                "--profile-file",
                str(profile),
                "--out",
                str(output),
            ]
        )
        == 0
    )

    runner = output / "backend/path0-external-json-backend/path0_external_backend.py"
    data = bytearray(runner.read_bytes())
    data[-2] = ord("x") if data[-2] != ord("x") else ord("y")
    runner.write_bytes(data)
    _refresh_manifest_artifact_hash(output, runner.relative_to(output).as_posix())

    verify = subprocess.run(
        [sys.executable, str(output / "otoe-run.py"), "--verify"],
        capture_output=True,
        cwd=output,
        env={"PYTHONPATH": ""},
        text=True,
    )

    assert verify.returncode == 1
    assert (
        "backend/path0-external-json-backend/backend-package.json: file "
        "'backend/path0-external-json-backend/path0_external_backend.py' "
        "sha256 mismatch"
    ) in verify.stderr


def _refresh_manifest_artifact_hash(output: Path, relative: str) -> None:
    manifest_path = output / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    path = output / relative
    data = path.read_bytes()
    for artifact in manifest["artifacts"]:
        if artifact["path"] == relative:
            artifact["size"] = len(data)
            artifact["sha256"] = hashlib.sha256(data).hexdigest()
            break
    else:
        raise AssertionError(f"artifact {relative!r} not found")
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
