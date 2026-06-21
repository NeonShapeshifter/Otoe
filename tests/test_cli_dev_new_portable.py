from cli_helpers import (
    json,
    sys,
    tomllib,
    main,
)


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

    monkeypatch.setattr("otoe.cli_check.subprocess.run", fake_run)

    result = main(
        [
            "check",
            "--path",
            str(module),
            "--tests",
            "--pytest-arg",
            "tests/test_cli_dev_new_portable.py",
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
            "tests/test_cli_dev_new_portable.py",
            "-k",
            "new",
        ]
    ]
    assert "pytest:" in captured.out

def test_cli_check_defaults_to_app_py_outside_source_checkout(
    tmp_path,
    monkeypatch,
    capsys,
):
    app = tmp_path / "app.py"
    app.write_text("value = 1\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    result = main(["check", "--tests"])

    captured = capsys.readouterr()
    assert result == 0
    assert "compile app.py: ok" in captured.out
    assert "pytest: skipped (tests directory missing)" in captured.out
    assert "compile src: missing" not in captured.err

def test_cli_portable_core_prints_support_matrix(capsys):
    result = main(["portable-core"])

    captured = capsys.readouterr()
    assert result == 0
    assert "Portable Core UI v0" in captured.out
    assert "`Button`" in captured.out
    assert "Native Window" in captured.out
    assert "Outside Portable Core v0" not in captured.out

def test_cli_portable_core_can_include_examples_and_outside_groups(capsys):
    result = main(["portable-core", "--examples", "--outside"])

    captured = capsys.readouterr()
    assert result == 0
    assert "Example Targets" in captured.out
    assert "examples.portable_core_ui:button_example" in captured.out
    assert "Outside Portable Core v0" in captured.out
    assert "app-shell-navigation" in captured.out

def test_cli_portable_core_can_write_json(capsys):
    result = main(["portable-core", "--json"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert result == 0
    assert payload["format"] == "otoe-portable-core-ui-v0"
    assert payload["entries"][0]["id"] == "text"
    assert payload["outsidePortableCore"][0]["id"] == "app-shell-navigation"

def test_cli_portable_core_accepts_format_json_alias(capsys):
    result = main(["portable-core", "--format", "json"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert result == 0
    assert payload["format"] == "otoe-portable-core-ui-v0"

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

    monkeypatch.setattr("otoe.cli_dev.run_live_preview", fake_run_live_preview)

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

    monkeypatch.setattr("otoe.cli_dev.run_live_preview", fake_run_live_preview)

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

    monkeypatch.setattr("otoe.cli_dev.run_live_preview", fake_run_live_preview)

    result = main(["dev", "dev_app_factory:app"])

    assert result == 0
    module_obj = __import__("dev_app_factory")
    assert module_obj.calls == 0
    assert calls[0]["app_factory"]().render_fragment() == "<p>factory</p>"
    assert module_obj.calls == 1

def test_cli_dev_runs_live_preview_for_renderable_scaffold_target(
    tmp_path,
    monkeypatch,
):
    module = tmp_path / "scaffold_dev_app.py"
    module.write_text(
        "from otoe import Button, Text, VStack, computed, signal\n"
        "count = signal(0)\n"
        "def app():\n"
        "    label = computed(lambda: f'Count: {count.value}')\n"
        "    return VStack(\n"
        "        Text(label),\n"
        "        Button('Increment', onClick=lambda: count.set(count.value + 1)),\n"
        "    )\n",
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    calls = []

    def fake_run_live_preview(**kwargs):
        calls.append(kwargs)

    monkeypatch.setattr("otoe.cli_dev.run_live_preview", fake_run_live_preview)

    result = main(["dev", "scaffold_dev_app:app"])

    assert result == 0
    app = calls[0]["app_factory"]()
    assert "Count: 0" in app.render_fragment()
    increment_event = next(
        event.id
        for event in app.renderer.events.values()
        if getattr(event.handler, "__name__", "") == "<lambda>"
    )
    assert "Count: 1" in app.dispatch_event(increment_event)

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

    monkeypatch.setattr("otoe.cli_dev.run_live_preview", fake_run_live_preview)

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
    assert "or be a Node, MountedNode" in captured.err

def test_cli_new_scaffolds_renderable_app(tmp_path, monkeypatch, capsys):
    project = tmp_path / "hello-otoe"

    result = main(["new", str(project)])

    captured = capsys.readouterr()
    assert result == 0
    assert f"new Hello Otoe: {project}" in captured.out
    app_source = (project / "app.py").read_text(encoding="utf-8")
    readme = (project / "README.md").read_text(encoding="utf-8")
    css_source = (project / "styles.css").read_text(encoding="utf-8")
    assert "def app():" in app_source
    assert (project / "styles.css").is_file()
    assert "otoe check" in readme
    assert "otoe dev app:app --css styles.css" in readme
    assert "otoe render app:app --out preview.html --css styles.css --pretty" in readme
    assert "otoe render app:app --out preview.png --native --css styles.css" in readme
    assert "otoe build app:app --out dist/cage --css styles.css --validate" in readme
    assert "localhost development preview" in readme
    assert "technical preview, not a sandbox" in readme
    assert "examples." not in readme
    assert "PYTHONPATH" not in readme

    from otoe.style import css

    stylesheet = css(css_source)
    assert set(stylesheet.rules) == {".app", ".title"}

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
    readme = (project / "README.md").read_text(encoding="utf-8")
    assert "otoe dev app:app\n" in readme
    assert "otoe render app:app --out preview.html --pretty" in readme
    assert "otoe render app:app --out preview.png --native" in readme
    assert "otoe build app:app --out dist/cage --validate" in readme
    assert "--css styles.css" not in readme

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
