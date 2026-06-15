from cli_helpers import (
    hashlib,
    json,
    os,
    subprocess,
    sys,
    pytest,
    main,
    _system_test_font,
)

def test_cli_build_rejects_pillow_native_text_without_font(
    tmp_path,
    monkeypatch,
    capsys,
):
    app = tmp_path / "pillow_profile_app.py"
    app.write_text(
        "from otoe import Text\n"
        "app = Text('Pillow profile')\n",
        encoding="utf-8",
    )
    profile_file = tmp_path / "otoe.profile.toml"
    profile_file.write_text(
        'profile = "cage"\n'
        "\n"
        "[native.text]\n"
        'renderer = "pillow"\n',
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "build",
            "pillow_profile_app:app",
            "--profile-file",
            str(profile_file),
            "--out",
            str(tmp_path / "dist" / "pillow-profile"),
        ]
    )

    captured = capsys.readouterr()
    assert result == 1
    assert "[native.text] renderer = 'pillow' requires font" in captured.err

def test_cli_build_rejects_native_text_font_with_marker_renderer(
    tmp_path,
    monkeypatch,
    capsys,
):
    app = tmp_path / "marker_font_profile_app.py"
    app.write_text(
        "from otoe import Text\n"
        "app = Text('Marker profile')\n",
        encoding="utf-8",
    )
    fonts_dir = tmp_path / "fonts"
    fonts_dir.mkdir()
    (fonts_dir / "font.ttf").write_bytes(b"not-a-real-font")
    profile_file = tmp_path / "otoe.profile.toml"
    profile_file.write_text(
        'profile = "cage"\n'
        "\n"
        "[native.text]\n"
        'font = "fonts/font.ttf"\n',
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "build",
            "marker_font_profile_app:app",
            "--profile-file",
            str(profile_file),
            "--out",
            str(tmp_path / "dist" / "marker-font-profile"),
        ]
    )

    captured = capsys.readouterr()
    assert result == 1
    assert "[native.text] font requires renderer = 'pillow'" in captured.err

def test_cli_build_runner_uses_profile_pillow_native_text_font(
    tmp_path,
    monkeypatch,
    capsys,
):
    pytest.importorskip("PIL")
    source_font = _system_test_font()
    app = tmp_path / "pillow_bundle_app.py"
    app.write_text(
        "from otoe import Text, VStack\n"
        "app = VStack(Text('Readable bundle'), padding=10)\n",
        encoding="utf-8",
    )
    fonts_dir = tmp_path / "fonts"
    fonts_dir.mkdir()
    font = fonts_dir / source_font.name
    font.write_bytes(source_font.read_bytes())
    profile_file = tmp_path / "otoe.profile.toml"
    profile_file.write_text(
        'profile = "cage"\n'
        "\n"
        "[native.text]\n"
        'renderer = "pillow"\n'
        f'font = "fonts/{source_font.name}"\n'
        "\n"
        "[runtime]\n"
        'files = ["pillow_bundle_app.py"]\n'
        "\n"
        "[deps]\n"
        'packages = ["Pillow"]\n',
        encoding="utf-8",
    )
    output = tmp_path / "dist" / "pillow-runner"
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "build",
            "pillow_bundle_app:app",
            "--profile-file",
            str(profile_file),
            "--out",
            str(output),
            "--validate",
        ]
    )

    captured = capsys.readouterr()
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    native_text_font = manifest["nativeText"]["font"]
    frame = output / "pillow.png"
    png = subprocess.run(
        [sys.executable, str(output / "otoe-run.py"), "--png", str(frame)],
        capture_output=True,
        cwd=output,
        env={**os.environ, "PYTHONPATH": ""},
        text=True,
    )

    assert result == 0
    assert "validation: ok" in captured.out
    assert manifest["nativeText"]["renderer"] == "pillow"
    assert native_text_font == {
        "source": f"fonts/{source_font.name}",
        "bundlePath": f"assets/fonts/{source_font.name}",
        "size": font.stat().st_size,
        "sha256": hashlib.sha256(font.read_bytes()).hexdigest(),
    }
    assert (output / native_text_font["bundlePath"]).is_file()
    assert png.returncode == 0, png.stderr
    assert frame.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")

