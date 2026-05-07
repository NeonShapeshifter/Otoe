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


def test_cli_render_rejects_invalid_target(tmp_path, monkeypatch, capsys):
    module = tmp_path / "bad_surface.py"
    module.write_text("app = object()\n", encoding="utf-8")
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(["render", "bad_surface:app", "--out", str(tmp_path / "out.html")])

    captured = capsys.readouterr()
    assert result == 1
    assert "render target must be a Node, MountedNode" in captured.err


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
        ]
    )

    assert result == 0
    assert len(calls) == 1
    assert calls[0]["host"] == "127.0.0.1"
    assert calls[0]["port"] == 8899
    assert calls[0]["config"].title == "Dev App"
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
        "class App:\n"
        "    def render_fragment(self):\n"
        "        return '<p>factory</p>'\n"
        "    def dispatch_event(self, event_id, *args):\n"
        "        return '<p>updated</p>'\n"
        "def app():\n"
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
    assert calls[0]["app_factory"]().render_fragment() == "<p>factory</p>"


def test_cli_dev_rejects_invalid_app_target(tmp_path, monkeypatch, capsys):
    module = tmp_path / "bad_dev_app.py"
    module.write_text("app = object()\n", encoding="utf-8")
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(["dev", "bad_dev_app:app"])

    captured = capsys.readouterr()
    assert result == 1
    assert "dev target must expose render_fragment()" in captured.err
