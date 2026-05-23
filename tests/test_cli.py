import sys
import tomllib

from otoe.cli import main


def test_pyproject_declares_otoe_console_script():
    metadata = tomllib.loads(open("pyproject.toml", encoding="utf-8").read())

    assert metadata["project"]["scripts"]["otoe"] == "otoe.cli:main"


def test_cli_check_compiles_requested_path(tmp_path, capsys):
    module = tmp_path / "surface.py"
    module.write_text("value = 1\n", encoding="utf-8")

    result = main(["check", "--path", str(module)])

    captured = capsys.readouterr()
    assert result == 0
    assert f"compile {module}: ok" in captured.out


def test_cli_check_reports_compile_failure(tmp_path, capsys):
    module = tmp_path / "broken.py"
    module.write_text("def nope(:\n", encoding="utf-8")

    result = main(["check", "--path", str(module)])

    captured = capsys.readouterr()
    assert result == 1
    assert f"compile {module}: failed" in captured.out


def test_cli_check_passes_extra_pytest_args(tmp_path, monkeypatch, capsys):
    module = tmp_path / "surface.py"
    module.write_text("value = 1\n", encoding="utf-8")
    calls = []

    class Completed:
        returncode = 0

    def fake_run(command):
        calls.append(command)
        return Completed()

    monkeypatch.setattr("otoe.cli.subprocess.run", fake_run)

    result = main(
        [
            "check",
            "--path",
            str(module),
            "--tests",
            "--pytest-arg",
            "tests/test_cli.py",
            "--",
            "-k",
            "new",
        ]
    )

    captured = capsys.readouterr()
    assert result == 0
    assert calls == [
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "tests/test_cli.py",
            "-k",
            "new",
        ]
    ]
    assert "pytest:" in captured.out


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


def test_cli_dev_runs_live_preview_for_app_target(tmp_path, monkeypatch):
    module = tmp_path / "dev_app.py"
    module.write_text(
        "class App:\n"
        "    def render_fragment(self):\n"
        "        return '<p>ok</p>'\n"
        "    def dispatch_event(self, event_id, *args):\n"
        "        return '<p>updated</p>'\n"
        "app = App()\n",
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    calls = []

    def fake_run_live_preview(**kwargs):
        calls.append(kwargs)

    monkeypatch.setattr("otoe.cli.run_live_preview", fake_run_live_preview)

    result = main(
        [
            "dev",
            "dev_app:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8899",
            "--title",
            "Dev App",
            "--root-class",
            "dev-root",
        ]
    )

    assert result == 0
    assert len(calls) == 1
    assert calls[0]["host"] == "127.0.0.1"
    assert calls[0]["port"] == 8899
    assert calls[0]["config"].title == "Dev App"
    assert calls[0]["config"].root_class == "dev-root"
    assert calls[0]["config"].css_path is None
    assert calls[0]["app_factory"]().render_fragment() == "<p>ok</p>"


def test_cli_dev_uses_callable_preview_object_without_calling_it(
    tmp_path,
    monkeypatch,
):
    module = tmp_path / "callable_dev_app.py"
    module.write_text(
        "class App:\n"
        "    def __call__(self):\n"
        "        raise RuntimeError('should not call app object')\n"
        "    def render_fragment(self):\n"
        "        return '<p>callable object</p>'\n"
        "    def dispatch_event(self, event_id, *args):\n"
        "        return '<p>updated</p>'\n"
        "app = App()\n",
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    calls = []

    def fake_run_live_preview(**kwargs):
        calls.append(kwargs)

    monkeypatch.setattr("otoe.cli.run_live_preview", fake_run_live_preview)

    result = main(["dev", "callable_dev_app:app"])

    assert result == 0
    assert calls[0]["app_factory"]().render_fragment() == "<p>callable object</p>"


def test_cli_dev_runs_live_preview_for_factory_target(tmp_path, monkeypatch):
    module = tmp_path / "dev_app_factory.py"
    module.write_text(
        "calls = 0\n"
        "class App:\n"
        "    def render_fragment(self):\n"
        "        return '<p>factory</p>'\n"
        "    def dispatch_event(self, event_id, *args):\n"
        "        return '<p>updated</p>'\n"
        "def app():\n"
        "    global calls\n"
        "    calls += 1\n"
        "    return App()\n",
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    calls = []

    def fake_run_live_preview(**kwargs):
        calls.append(kwargs)

    monkeypatch.setattr("otoe.cli.run_live_preview", fake_run_live_preview)

    result = main(["dev", "dev_app_factory:app"])

    assert result == 0
    module_obj = __import__("dev_app_factory")
    assert module_obj.calls == 0
    assert calls[0]["app_factory"]().render_fragment() == "<p>factory</p>"
    assert module_obj.calls == 1


def test_cli_dev_rejects_missing_css_file(tmp_path, monkeypatch, capsys):
    module = tmp_path / "dev_app.py"
    module.write_text(
        "class App:\n"
        "    def render_fragment(self):\n"
        "        return '<p>ok</p>'\n"
        "    def dispatch_event(self, event_id, *args):\n"
        "        return '<p>updated</p>'\n"
        "app = App()\n",
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(["dev", "dev_app:app", "--css", str(tmp_path / "missing.css")])

    captured = capsys.readouterr()
    assert result == 1
    assert "dev: css file" in captured.err
    assert "does not exist" in captured.err


def test_cli_dev_live_counter_example(monkeypatch):
    calls = []

    def fake_run_live_preview(**kwargs):
        calls.append(kwargs)

    monkeypatch.setattr("otoe.cli.run_live_preview", fake_run_live_preview)

    result = main(["dev", "examples.live_counter:app"])

    assert result == 0
    app = calls[0]["app_factory"]()
    assert "Count: 0" in app.render_fragment()
    increment_event = next(
        event.id
        for event in app.renderer.events.values()
        if getattr(event.handler, "__name__", "") == "increment"
    )
    assert "Count: 1" in app.dispatch_event(increment_event)


def test_cli_dev_rejects_invalid_app_target(tmp_path, monkeypatch, capsys):
    module = tmp_path / "bad_dev_app.py"
    module.write_text("app = object()\n", encoding="utf-8")
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(["dev", "bad_dev_app:app"])

    captured = capsys.readouterr()
    assert result == 1
    assert "dev target must expose render_fragment()" in captured.err


def test_cli_new_scaffolds_renderable_app(tmp_path, monkeypatch, capsys):
    project = tmp_path / "hello-otoe"

    result = main(["new", str(project)])

    captured = capsys.readouterr()
    assert result == 0
    assert f"new Hello Otoe: {project}" in captured.out
    assert "def app():" in (project / "app.py").read_text(encoding="utf-8")
    assert (project / "styles.css").is_file()
    assert "otoe render app:app --out preview.html --css styles.css" in (
        project / "README.md"
    ).read_text(encoding="utf-8")

    monkeypatch.syspath_prepend(str(project))
    output = tmp_path / "preview.html"

    assert (
        main(
            [
                "render",
                "app:app",
                "--out",
                str(output),
                "--css",
                str(project / "styles.css"),
            ]
        )
        == 0
    )
    assert "Hello Otoe" in output.read_text(encoding="utf-8")


def test_cli_new_can_skip_css(tmp_path):
    project = tmp_path / "plain"

    result = main(["new", str(project), "--no-css"])

    assert result == 0
    assert not (project / "styles.css").exists()
    assert "otoe render app:app --out preview.html --pretty" in (
        project / "README.md"
    ).read_text(
        encoding="utf-8"
    )


def test_cli_new_refuses_existing_scaffold_file_without_force(
    tmp_path,
    capsys,
):
    project = tmp_path / "existing"
    project.mkdir()
    (project / "app.py").write_text("# keep me\n", encoding="utf-8")

    result = main(["new", str(project)])

    captured = capsys.readouterr()
    assert result == 1
    assert "already exists; pass --force to overwrite" in captured.err
    assert (project / "app.py").read_text(encoding="utf-8") == "# keep me\n"
