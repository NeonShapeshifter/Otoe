import json
import os
import subprocess
import sys
import tarfile
from pathlib import Path

from otoe.cli import main


ROOT = Path(__file__).resolve().parents[1]


def test_offline_bundle_example_builds_and_packs(tmp_path, monkeypatch):
    example = ROOT / "examples" / "offline_bundle"
    output = tmp_path / "cage"
    archive = tmp_path / "cage.tar.gz"
    extracted = tmp_path / "extracted"
    for module_name in ("app", "helpers", "labels"):
        monkeypatch.delitem(sys.modules, module_name, raising=False)
    monkeypatch.chdir(example)
    monkeypatch.syspath_prepend(str(example))

    build_result = main(
        [
            "build",
            "app:app",
            "--profile-file",
            "otoe.profile.toml",
            "--out",
            str(output),
            "--validate",
        ]
    )
    pack_result = main(["pack", str(output), "--out", str(archive)])

    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    runtime_paths = sorted(entry["bundlePath"] for entry in manifest["runtimeFiles"])
    asset_paths = sorted(entry["bundlePath"] for entry in manifest["assets"])
    assert build_result == 0
    assert pack_result == 0
    assert runtime_paths == ["app/app.py", "app/helpers.py", "app/labels.py"]
    assert asset_paths == ["assets/static/device.txt"]
    assert (output / "otoe-styles.json").is_file()
    assert archive.is_file()

    with tarfile.open(archive, "r:gz") as tar:
        names = tar.getnames()
        for member in tar.getmembers():
            target = extracted / member.name
            target.parent.mkdir(parents=True, exist_ok=True)
            source = tar.extractfile(member)
            assert source is not None
            target.write_bytes(source.read())

    assert "app/helpers.py" in names
    assert "app/labels.py" in names
    assert "assets/static/device.txt" in names
    verify = subprocess.run(
        [sys.executable, str(extracted / "otoe-run.py"), "--layout-check"],
        capture_output=True,
        cwd=extracted,
        env={**os.environ, "PYTHONPATH": ""},
        text=True,
    )
    assert verify.returncode == 0, verify.stderr
    assert "layout checked: app:app" in verify.stdout
