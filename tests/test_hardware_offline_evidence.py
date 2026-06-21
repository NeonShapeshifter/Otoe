from __future__ import annotations

from pathlib import Path

from cli_helpers import hashlib, json, main, os, subprocess, sys


TARGET = "examples.hardware.control_panel:app"
PORTABLE_CSS = "preview/hardware_portable.css"
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def test_hardware_control_panel_offline_evidence_bundle(tmp_path, capsys, monkeypatch):
    plan_path = tmp_path / "hardware-plan.json"
    output = tmp_path / "hardware-bundle"
    monkeypatch.setenv("PYTHONDONTWRITEBYTECODE", "1")

    plan_result = main(
        [
            "plan",
            TARGET,
            "--css",
            PORTABLE_CSS,
            "--out",
            str(plan_path),
        ]
    )
    capsys.readouterr()

    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    assert plan_result == 0
    assert plan["target"] == TARGET
    assert plan["hasErrors"] is False
    assert plan["status"] in {"ok", "warnings"}
    assert plan["classes"]["invalid"] == []
    assert plan["styleCounts"]["invalid"] == 0
    assert plan["widgetCount"] > 100

    build_result = main(
        [
            "build",
            TARGET,
            "--css",
            PORTABLE_CSS,
            "--out",
            str(output),
            "--validate",
        ]
    )
    captured = capsys.readouterr()

    assert build_result == 0
    assert "validation: ok" in captured.out
    assert f"build {TARGET}: {output}" in captured.out

    manifest = _load_json(output / "manifest.json")
    styles = _load_json(output / "otoe-styles.json")
    render_tree = _load_json(output / "otoe-render-tree.json")
    deps = _load_json(output / "otoe-deps.json")
    build_plan = _load_json(output / "otoe-plan.json")

    assert manifest["target"] == TARGET
    assert manifest["profile"] == "cage"
    assert manifest["backend"] == "native"
    assert manifest["backendCapability"] == "native-python"
    assert manifest["runtimeInstallsAllowed"] is False
    assert manifest["status"] in {"ok", "warnings"}
    assert manifest["plan"] == "otoe-plan.json"
    assert manifest["deps"] == "otoe-deps.json"
    assert manifest["styles"] == "otoe-styles.json"
    assert manifest["renderTree"] == "otoe-render-tree.json"
    assert manifest["runner"]["path"] == "otoe-run.py"
    assert (output / "otoe-run.py").is_file()
    assert _runtime_sources(manifest) == {
        "examples/hardware/__init__.py",
        "examples/hardware/control_panel.py",
    }

    assert build_plan["target"] == TARGET
    assert build_plan["hasErrors"] is False
    assert deps["hasErrors"] is False
    assert deps["runtimeInstallsAllowed"] is False
    assert styles["target"] == TARGET
    assert styles["status"] in {"ok", "warnings"}
    assert styles["styleOps"]["format"] == "otoe-style-ops"
    assert styles["styleOps"]["backend"] == "native-python"
    assert styles["styleOps"]["classes"]
    assert render_tree["format"] == "otoe-render-tree"
    assert render_tree["nodeCount"] == build_plan["widgetCount"]
    assert render_tree["nodeCount"] > 100

    _assert_manifest_files_match(output, manifest["artifacts"], path_key="path")
    _assert_manifest_files_match(
        output,
        manifest["runtimeFiles"],
        path_key="bundlePath",
    )
    _assert_manifest_file_matches(output, manifest["runner"], path_key="path")
    _assert_bundle_has_no_cache_artifacts(output)

    verify = _run_runner(output, "--verify")
    check = _run_runner(output, "--check")
    layout_check = _run_runner(output, "--layout-check")
    png_path = tmp_path / "hardware-runner.png"
    png = _run_runner(output, "--png", str(png_path))

    assert verify.returncode == 0, verify.stderr
    assert "verified: manifest.json" in verify.stdout
    assert check.returncode == 0, check.stderr
    assert f"loaded: {TARGET}" in check.stdout
    assert layout_check.returncode == 0, layout_check.stderr
    assert f"layout checked: {TARGET}" in layout_check.stdout
    assert png.returncode == 0, png.stderr
    assert png_path.read_bytes().startswith(PNG_SIGNATURE)
    assert png_path.stat().st_size > 100


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _runtime_sources(manifest: dict) -> set[str]:
    return {
        entry["source"]
        for entry in manifest["runtimeFiles"]
        if isinstance(entry, dict)
    }


def _assert_manifest_files_match(
    root: Path,
    entries: list[dict],
    *,
    path_key: str,
) -> None:
    for entry in entries:
        _assert_manifest_file_matches(root, entry, path_key=path_key)


def _assert_manifest_file_matches(
    root: Path,
    entry: dict,
    *,
    path_key: str,
) -> None:
    relative = entry[path_key]
    path = root / relative
    data = path.read_bytes()

    assert path.is_file()
    assert entry["size"] == len(data)
    assert entry["sha256"] == hashlib.sha256(data).hexdigest()


def _assert_bundle_has_no_cache_artifacts(root: Path) -> None:
    blocked_names = {
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".venv",
        "__pycache__",
        "dist",
    }
    blocked_suffixes = {".pyc", ".pyo"}
    for path in root.rglob("*"):
        relative = path.relative_to(root)
        assert not (set(relative.parts) & blocked_names), relative.as_posix()
        assert path.suffix not in blocked_suffixes, relative.as_posix()


def _run_runner(output: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(output / "otoe-run.py"), *args],
        capture_output=True,
        cwd=output,
        env={**os.environ, "PYTHONPATH": ""},
        text=True,
        timeout=20,
    )
