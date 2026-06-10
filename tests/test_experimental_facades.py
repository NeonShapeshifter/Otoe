import json

from otoe.cli import main


def test_experimental_facades_are_available_in_offline_builds(
    tmp_path,
    monkeypatch,
    capsys,
):
    module = tmp_path / "experimental_facade_app.py"
    module.write_text(
        "from otoe import Text\n"
        "from otoe.experimental.backend import RenderTree\n"
        "from otoe.experimental.native import NativeSurface\n"
        "app = Text(f'{NativeSurface.__name__} {RenderTree.__name__}')\n",
        encoding="utf-8",
    )
    output = tmp_path / "dist" / "experimental-facade"
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "build",
            "experimental_facade_app:app",
            "--out",
            str(output),
            "--validate",
        ]
    )

    capsys.readouterr()
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    framework_paths = {entry["bundlePath"] for entry in manifest["frameworkFiles"]}
    assert result == 0
    assert "framework/otoe/experimental/__init__.py" in framework_paths
    assert "framework/otoe/experimental/backend.py" in framework_paths
    assert "framework/otoe/experimental/native.py" in framework_paths
