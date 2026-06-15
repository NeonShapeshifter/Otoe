from cli_helpers import (
    importlib,
    pytest,
    main,
    _png_size,
)


def test_cli_render_writes_html_from_node_target(tmp_path, monkeypatch, capsys):
    module = tmp_path / "surface.py"
    module.write_text(
        "from otoe import Text\n"
        "app = Text('Hello')\n",
        encoding="utf-8",
    )
    output = tmp_path / "preview.html"
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(["render", "surface:app", "--out", str(output)])

    captured = capsys.readouterr()
    assert result == 0
    assert f"render surface:app: {output}" in captured.out
    assert '<span class="otoe-text">Hello</span>' in output.read_text(
        encoding="utf-8"
    )

def test_cli_render_writes_html_from_callable_target(tmp_path, monkeypatch):
    module = tmp_path / "surface_factory.py"
    module.write_text(
        "from otoe import Text\n"
        "def app():\n"
        "    return Text('Callable')\n",
        encoding="utf-8",
    )
    output = tmp_path / "preview.html"
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(["render", "surface_factory:app", "--out", str(output)])

    assert result == 0
    assert "Callable" in output.read_text(encoding="utf-8")

def test_cli_render_applies_css_inline(tmp_path, monkeypatch):
    module = tmp_path / "styled_surface.py"
    module.write_text(
        "from otoe import Text\n"
        "app = Text('Styled', className='title')\n",
        encoding="utf-8",
    )
    styles = tmp_path / "styles.css"
    styles.write_text(".title { color: #ff0000; }\n", encoding="utf-8")
    output = tmp_path / "preview.html"
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "render",
            "styled_surface:app",
            "--out",
            str(output),
            "--css",
            str(styles),
        ]
    )

    assert result == 0
    assert 'style="color:#ff0000"' in output.read_text(encoding="utf-8")

def test_cli_render_can_ignore_missing_css_classes(
    tmp_path,
    monkeypatch,
):
    module = tmp_path / "loose_surface.py"
    module.write_text(
        "from otoe import Text\n"
        "app = Text('Loose', className='missing')\n",
        encoding="utf-8",
    )
    styles = tmp_path / "styles.css"
    styles.write_text(".known { color: #ff0000; }\n", encoding="utf-8")
    output = tmp_path / "preview.html"
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "render",
            "loose_surface:app",
            "--out",
            str(output),
            "--css",
            str(styles),
            "--no-strict-styles",
        ]
    )

    assert result == 0
    assert "Loose" in output.read_text(encoding="utf-8")

def test_cli_render_quickstart_example(tmp_path):
    output = tmp_path / "quickstart.html"

    result = main(["render", "examples.quickstart:app", "--out", str(output)])

    assert result == 0
    html = output.read_text(encoding="utf-8")
    assert "Otoe quickstart" in html
    assert "Primary action" in html

def test_cli_render_writes_native_png(tmp_path):
    output = tmp_path / "quickstart.png"

    result = main(
        [
            "render",
            "examples.quickstart:app",
            "--out",
            str(output),
            "--native",
            "--background",
            "#f8fafc",
        ]
    )

    assert result == 0
    assert output.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")

def test_cli_render_writes_scaled_native_png(tmp_path):
    one_x = tmp_path / "quickstart-1x.png"
    two_x = tmp_path / "quickstart-2x.png"

    first_result = main(
        [
            "render",
            "examples.quickstart:app",
            "--out",
            str(one_x),
            "--native",
        ]
    )
    second_result = main(
        [
            "render",
            "examples.quickstart:app",
            "--out",
            str(two_x),
            "--native",
            "--native-scale",
            "2",
        ]
    )

    one_width, one_height = _png_size(one_x.read_bytes())
    two_width, two_height = _png_size(two_x.read_bytes())
    assert first_result == 0
    assert second_result == 0
    assert (two_width, two_height) == (one_width * 2, one_height * 2)

def test_cli_render_native_scale_requires_native(tmp_path, capsys):
    output = tmp_path / "preview.html"

    result = main(
        [
            "render",
            "examples.quickstart:app",
            "--out",
            str(output),
            "--native-scale",
            "2",
        ]
    )

    captured = capsys.readouterr()
    assert result == 1
    assert "--native-scale requires --native" in captured.err
    assert not output.exists()

def test_cli_render_writes_native_png_with_css(tmp_path, monkeypatch):
    module = tmp_path / "native_styled_surface.py"
    module.write_text(
        "from otoe import Text, VStack\n"
        "app = VStack(Text('Native'), className='shell')\n",
        encoding="utf-8",
    )
    styles = tmp_path / "styles.css"
    styles.write_text(".shell { padding: 8; background: #f8fafc; }\n", encoding="utf-8")
    output = tmp_path / "preview.png"
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "render",
            "native_styled_surface:app",
            "--out",
            str(output),
            "--native",
            "--css",
            str(styles),
        ]
    )

    assert result == 0
    assert output.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")

def test_cli_render_pillow_native_text_requires_optional_dependency(
    tmp_path,
    monkeypatch,
    capsys,
):
    if importlib.util.find_spec("PIL") is not None:
        pytest.skip("Pillow is installed")
    module = tmp_path / "pillow_text_surface.py"
    module.write_text(
        "from otoe import Text\n"
        "app = Text('Readable')\n",
        encoding="utf-8",
    )
    output = tmp_path / "preview.png"
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "render",
            "pillow_text_surface:app",
            "--out",
            str(output),
            "--native",
            "--native-text",
            "pillow",
        ]
    )

    captured = capsys.readouterr()
    assert result == 1
    assert "Pillow native text backend requires Pillow" in captured.err
    assert not output.exists()

def test_cli_render_font_requires_pillow_native_text(tmp_path, monkeypatch, capsys):
    module = tmp_path / "font_surface.py"
    module.write_text(
        "from otoe import Text\n"
        "app = Text('Font')\n",
        encoding="utf-8",
    )
    font = tmp_path / "font.ttf"
    font.write_bytes(b"not-a-real-font")
    output = tmp_path / "preview.png"
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "render",
            "font_surface:app",
            "--out",
            str(output),
            "--native",
            "--font",
            str(font),
        ]
    )

    captured = capsys.readouterr()
    assert result == 1
    assert "--font requires --native-text pillow" in captured.err

def test_cli_native_png_render_is_stable_across_runs(tmp_path):
    first = tmp_path / "first.png"
    second = tmp_path / "second.png"

    assert (
        main(["render", "examples.quickstart:app", "--out", str(first), "--native"])
        == 0
    )
    assert (
        main(["render", "examples.quickstart:app", "--out", str(second), "--native"])
        == 0
    )
    assert first.read_bytes() == second.read_bytes()

def test_cli_render_rejects_invalid_target(tmp_path, monkeypatch, capsys):
    module = tmp_path / "bad_surface.py"
    module.write_text("app = object()\n", encoding="utf-8")
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(["render", "bad_surface:app", "--out", str(tmp_path / "out.html")])

    captured = capsys.readouterr()
    assert result == 1
    assert "render target must be a Node, MountedNode" in captured.err

def test_cli_render_reports_css_errors(tmp_path, monkeypatch, capsys):
    module = tmp_path / "surface.py"
    module.write_text("from otoe import Text\napp = Text('Bad CSS')\n", encoding="utf-8")
    styles = tmp_path / "styles.css"
    styles.write_text(".bad { nope: 1; }\n", encoding="utf-8")
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "render",
            "surface:app",
            "--out",
            str(tmp_path / "preview.html"),
            "--css",
            str(styles),
        ]
    )

    captured = capsys.readouterr()
    assert result == 1
    assert "render: css file" in captured.err
    assert "Unknown style property 'nope'" in captured.err
