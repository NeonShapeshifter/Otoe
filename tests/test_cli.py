import hashlib
import json
import os
import subprocess
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


def test_cli_plan_reports_cage_summary_for_portable_css(
    tmp_path,
    monkeypatch,
    capsys,
):
    module = tmp_path / "planned_surface.py"
    module.write_text(
        "from otoe import Text, VStack\n"
        "app = VStack(Text('Ready', className='title'), className='shell', gap=8)\n",
        encoding="utf-8",
    )
    styles = tmp_path / "styles.css"
    styles.write_text(
        ".shell { padding: 8; background: #f8fafc; }\n"
        ".title { color: #172033; font-size: 16; }\n",
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "plan",
            "planned_surface:app",
            "--profile",
            "cage",
            "--css",
            str(styles),
        ]
    )

    captured = capsys.readouterr()
    assert result == 0
    assert "plan planned_surface:app: profile cage" in captured.out
    assert "widgets: 2" in captured.out
    assert "classes: 2 used, 2 planned, 0 html-only, 0 invalid" in captured.out
    assert "style declarations: portable=4, html-only=0, deferred=0, invalid=0" in captured.out
    assert "direct style props: portable=1, html-only=0, deferred=0, invalid=0" in captured.out
    assert "status: ok" in captured.out


def test_cli_plan_can_emit_json_report(tmp_path, monkeypatch, capsys):
    module = tmp_path / "json_plan_surface.py"
    module.write_text(
        "from otoe import Text, VStack\n"
        "app = VStack(Text('Ready', className='title'), className='shell')\n",
        encoding="utf-8",
    )
    styles = tmp_path / "styles.css"
    styles.write_text(
        ".shell { padding: 8; background: #f8fafc; }\n"
        ".title { color: #172033; }\n",
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "plan",
            "json_plan_surface:app",
            "--css",
            str(styles),
            "--json",
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert result == 0
    assert payload["schemaVersion"] == 1
    assert payload["target"] == "json_plan_surface:app"
    assert payload["profile"] == "cage"
    assert payload["status"] == "ok"
    assert payload["hasErrors"] is False
    assert payload["classes"] == {
        "used": ["shell", "title"],
        "planned": ["shell", "title"],
        "htmlOnly": [],
        "invalid": [],
    }
    assert payload["styleCounts"]["portable"] == 3
    assert payload["diagnostics"] == []


def test_cli_plan_writes_json_artifact(tmp_path, monkeypatch, capsys):
    module = tmp_path / "plan_artifact_surface.py"
    module.write_text(
        "from otoe import Text, VStack\n"
        "app = VStack(Text('Utility'), className='p-4 bg-panel')\n",
        encoding="utf-8",
    )
    output = tmp_path / "dist" / "otoe-plan.json"
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "plan",
            "plan_artifact_surface:app",
            "--utilities",
            "--out",
            str(output),
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert result == 0
    assert output.is_file()
    assert f"plan artifact: {output}" in captured.out
    assert payload["target"] == "plan_artifact_surface:app"
    assert payload["status"] == "ok"
    assert payload["classes"]["planned"] == ["p-4", "bg-panel"]


def test_cli_plan_writes_invalid_json_artifact(tmp_path, monkeypatch, capsys):
    module = tmp_path / "invalid_plan_artifact_surface.py"
    module.write_text(
        "from otoe import Text\n"
        "app = Text('Missing', className='missing')\n",
        encoding="utf-8",
    )
    output = tmp_path / "dist" / "bad-plan.json"
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "plan",
            "invalid_plan_artifact_surface:app",
            "--out",
            str(output),
            "--json",
        ]
    )

    captured = capsys.readouterr()
    stdout_payload = json.loads(captured.out)
    file_payload = json.loads(output.read_text(encoding="utf-8"))
    assert result == 1
    assert stdout_payload == file_payload
    assert stdout_payload["status"] == "invalid"
    assert stdout_payload["hasErrors"] is True
    assert stdout_payload["classes"]["invalid"] == ["missing"]


def test_cli_plan_loads_default_profile_file(tmp_path, monkeypatch, capsys):
    module = tmp_path / "profile_surface.py"
    module.write_text(
        "from otoe import Text, VStack\n"
        "app = VStack(Text('Profile'), className='p-4 custom')\n",
        encoding="utf-8",
    )
    (tmp_path / "styles.css").write_text(
        ".custom { color: #172033; }\n",
        encoding="utf-8",
    )
    (tmp_path / "otoe.profile.toml").write_text(
        'profile = "cage"\n'
        "utilities = true\n"
        'css = ["styles.css"]\n'
        "\n"
        "[runtime]\n"
        "allow_runtime_installs = false\n"
        "\n"
        "[backend]\n"
        'name = "native"\n',
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(["plan", "profile_surface:app"])

    captured = capsys.readouterr()
    assert result == 0
    assert "classes: 2 used, 2 planned, 0 html-only, 0 invalid" in captured.out
    assert "used classes: p-4, custom" in captured.out


def test_cli_plan_profile_file_resolves_css_relative_to_profile(
    tmp_path,
    monkeypatch,
    capsys,
):
    module = tmp_path / "relative_profile_surface.py"
    module.write_text(
        "from otoe import Text\n"
        "app = Text('Relative', className='custom')\n",
        encoding="utf-8",
    )
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "styles.css").write_text(
        ".custom { color: #172033; }\n",
        encoding="utf-8",
    )
    profile_file = config_dir / "otoe.profile.toml"
    profile_file.write_text(
        'profile = "cage"\n'
        'css = ["styles.css"]\n',
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "plan",
            "relative_profile_surface:app",
            "--profile-file",
            str(profile_file),
        ]
    )

    captured = capsys.readouterr()
    assert result == 0
    assert "classes: 1 used, 1 planned, 0 html-only, 0 invalid" in captured.out


def test_cli_plan_rejects_runtime_installs_in_cage_profile(
    tmp_path,
    monkeypatch,
    capsys,
):
    module = tmp_path / "runtime_install_surface.py"
    module.write_text(
        "from otoe import Text\n"
        "app = Text('No installs')\n",
        encoding="utf-8",
    )
    profile_file = tmp_path / "otoe.profile.toml"
    profile_file.write_text(
        'profile = "cage"\n'
        "\n"
        "[runtime]\n"
        "allow_runtime_installs = true\n",
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "plan",
            "runtime_install_surface:app",
            "--profile-file",
            str(profile_file),
        ]
    )

    captured = capsys.readouterr()
    assert result == 1
    assert "plan: profile 'cage' forbids runtime installs" in captured.err


def test_cli_plan_cli_css_overrides_profile_css(tmp_path, monkeypatch, capsys):
    module = tmp_path / "override_css_surface.py"
    module.write_text(
        "from otoe import Text\n"
        "app = Text('Override', className='cli')\n",
        encoding="utf-8",
    )
    profile_file = tmp_path / "otoe.profile.toml"
    profile_file.write_text(
        'profile = "cage"\n'
        'css = ["missing.css"]\n',
        encoding="utf-8",
    )
    cli_css = tmp_path / "cli.css"
    cli_css.write_text(".cli { color: #172033; }\n", encoding="utf-8")
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "plan",
            "override_css_surface:app",
            "--profile-file",
            str(profile_file),
            "--css",
            str(cli_css),
        ]
    )

    captured = capsys.readouterr()
    assert result == 0
    assert "classes: 1 used, 1 planned, 0 html-only, 0 invalid" in captured.out


def test_cli_plan_no_utilities_overrides_profile_utilities(
    tmp_path,
    monkeypatch,
    capsys,
):
    module = tmp_path / "override_utilities_surface.py"
    module.write_text(
        "from otoe import Text\n"
        "app = Text('Utility', className='p-4')\n",
        encoding="utf-8",
    )
    profile_file = tmp_path / "otoe.profile.toml"
    profile_file.write_text(
        'profile = "cage"\n'
        "utilities = true\n",
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "plan",
            "override_utilities_surface:app",
            "--profile-file",
            str(profile_file),
            "--no-utilities",
        ]
    )

    captured = capsys.readouterr()
    assert result == 1
    assert "classes: 1 used, 0 planned, 0 html-only, 1 invalid" in captured.out


def test_cli_plan_reports_missing_profile_css(tmp_path, monkeypatch, capsys):
    module = tmp_path / "missing_profile_css_surface.py"
    module.write_text(
        "from otoe import Text\n"
        "app = Text('Missing CSS')\n",
        encoding="utf-8",
    )
    profile_file = tmp_path / "otoe.profile.toml"
    profile_file.write_text(
        'profile = "cage"\n'
        'css = ["missing.css"]\n',
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "plan",
            "missing_profile_css_surface:app",
            "--profile-file",
            str(profile_file),
        ]
    )

    captured = capsys.readouterr()
    assert result == 1
    assert "plan: css file" in captured.err
    assert "missing.css" in captured.err


def test_cli_plan_can_include_builtin_utilities(tmp_path, monkeypatch, capsys):
    module = tmp_path / "utility_surface.py"
    module.write_text(
        "from otoe import Text, VStack\n"
        "app = VStack(Text('Utility'), className='p-4 bg-panel font-semibold')\n",
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(["plan", "utility_surface:app", "--utilities"])

    captured = capsys.readouterr()
    assert result == 0
    assert "classes: 3 used, 3 planned, 0 html-only, 0 invalid" in captured.out
    assert "style declarations: portable=2, html-only=1, deferred=0, invalid=0" in captured.out
    assert "status: warnings" in captured.out
    assert "property 'fontWeight' is accepted but ignored by native" in captured.out


def test_cli_plan_rejects_unknown_style_class_by_default(
    tmp_path,
    monkeypatch,
    capsys,
):
    module = tmp_path / "missing_style_surface.py"
    module.write_text(
        "from otoe import Text\n"
        "app = Text('Missing', className='missing')\n",
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(["plan", "missing_style_surface:app"])

    captured = capsys.readouterr()
    assert result == 1
    assert "classes: 1 used, 0 planned, 0 html-only, 1 invalid" in captured.out
    assert "status: invalid" in captured.out
    assert "error: class 'missing' has no portable rule" in captured.out


def test_cli_plan_can_downgrade_unknown_classes_to_html_only(
    tmp_path,
    monkeypatch,
    capsys,
):
    module = tmp_path / "html_only_surface.py"
    module.write_text(
        "from otoe import Text\n"
        "app = Text('HTML', className='marketing-only')\n",
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(["plan", "html_only_surface:app", "--no-strict-styles"])

    captured = capsys.readouterr()
    assert result == 0
    assert "classes: 1 used, 0 planned, 1 html-only, 0 invalid" in captured.out
    assert "status: warnings" in captured.out
    assert "warning: class 'marketing-only' has no portable rule" in captured.out


def test_cli_plan_reports_css_errors(tmp_path, monkeypatch, capsys):
    module = tmp_path / "bad_plan_surface.py"
    module.write_text("from otoe import Text\napp = Text('Bad plan')\n", encoding="utf-8")
    styles = tmp_path / "styles.css"
    styles.write_text(".bad { nope: 1; }\n", encoding="utf-8")
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(["plan", "bad_plan_surface:app", "--css", str(styles)])

    captured = capsys.readouterr()
    assert result == 1
    assert "plan: css file" in captured.err
    assert "Unknown style property 'nope'" in captured.err


def test_cli_build_writes_minimal_bundle_manifest(tmp_path, monkeypatch, capsys):
    module = tmp_path / "build_surface.py"
    module.write_text(
        "from otoe import Text, VStack\n"
        "app = VStack(Text('Build'), className='p-4 bg-panel')\n",
        encoding="utf-8",
    )
    profile_file = tmp_path / "otoe.profile.toml"
    profile_file.write_text(
        'profile = "cage"\n'
        "utilities = true\n"
        "\n"
        "[runtime]\n"
        "allow_runtime_installs = false\n"
        "\n"
        "[backend]\n"
        'name = "native"\n',
        encoding="utf-8",
    )
    output = tmp_path / "dist" / "cage"
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "build",
            "build_surface:app",
            "--profile-file",
            str(profile_file),
            "--out",
            str(output),
        ]
    )

    captured = capsys.readouterr()
    plan = json.loads((output / "otoe-plan.json").read_text(encoding="utf-8"))
    deps = json.loads((output / "otoe-deps.json").read_text(encoding="utf-8"))
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    assert result == 0
    assert f"build build_surface:app: {output}" in captured.out
    assert f"deps artifact: {output / 'otoe-deps.json'}" in captured.out
    assert plan["status"] == "ok"
    assert deps["status"] == "ok"
    framework_files = manifest.pop("frameworkFiles")
    runner = manifest.pop("runner")
    assert {
        "source": "otoe/native.py",
        "bundlePath": "framework/otoe/native.py",
        "size": (output / "framework" / "otoe" / "native.py").stat().st_size,
        "sha256": hashlib.sha256(
            (output / "framework" / "otoe" / "native.py").read_bytes()
        ).hexdigest(),
    } in framework_files
    assert {
        "source": "otoe/__init__.py",
        "bundlePath": "framework/otoe/__init__.py",
        "size": (output / "framework" / "otoe" / "__init__.py").stat().st_size,
        "sha256": hashlib.sha256(
            (output / "framework" / "otoe" / "__init__.py").read_bytes()
        ).hexdigest(),
    } in framework_files
    assert not (output / "framework" / "otoe" / "build.py").exists()
    assert runner == {
        "path": "otoe-run.py",
        "pythonPath": ["app", "framework"],
        "modes": ["check", "png"],
        "size": (output / "otoe-run.py").stat().st_size,
        "sha256": hashlib.sha256((output / "otoe-run.py").read_bytes()).hexdigest(),
    }
    assert manifest == {
        "schemaVersion": 1,
        "target": "build_surface:app",
        "profile": "cage",
        "backend": "native",
        "runtimeInstallsAllowed": False,
        "plan": "otoe-plan.json",
        "deps": "otoe-deps.json",
        "assets": [],
        "runtimeFiles": [],
        "status": "ok",
    }


def test_cli_build_writes_runner_that_loads_copied_runtime_target(
    tmp_path,
    monkeypatch,
    capsys,
):
    app = tmp_path / "bundled_runner_app.py"
    app.write_text(
        "from otoe import Text\n"
        "app = Text('Bundled app')\n",
        encoding="utf-8",
    )
    profile_file = tmp_path / "otoe.profile.toml"
    profile_file.write_text(
        'profile = "cage"\n'
        "\n"
        "[runtime]\n"
        'files = ["bundled_runner_app.py"]\n',
        encoding="utf-8",
    )
    output = tmp_path / "dist" / "runner-build"
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "build",
            "bundled_runner_app:app",
            "--profile-file",
            str(profile_file),
            "--out",
            str(output),
            "--validate",
        ]
    )

    captured = capsys.readouterr()
    env = {**os.environ, "PYTHONPATH": ""}
    check = subprocess.run(
        [sys.executable, str(output / "otoe-run.py"), "--check"],
        capture_output=True,
        cwd=output,
        env=env,
        text=True,
    )
    frame = output / "frame.png"
    png = subprocess.run(
        [sys.executable, str(output / "otoe-run.py"), "--png", str(frame)],
        capture_output=True,
        cwd=output,
        env=env,
        text=True,
    )

    assert result == 0
    assert "validation: ok" in captured.out
    assert check.returncode == 0, check.stderr
    assert "loaded: bundled_runner_app:app" in check.stdout
    assert png.returncode == 0, png.stderr
    assert frame.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")


def test_cli_build_validate_rejects_target_missing_from_bundle(
    tmp_path,
    monkeypatch,
    capsys,
):
    module = tmp_path / "workspace_only_app.py"
    module.write_text(
        "from otoe import Text\n"
        "app = Text('Workspace only')\n",
        encoding="utf-8",
    )
    output = tmp_path / "dist" / "validate-missing"
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "build",
            "workspace_only_app:app",
            "--out",
            str(output),
            "--validate",
        ]
    )

    captured = capsys.readouterr()
    assert result == 1
    assert (output / "otoe-plan.json").is_file()
    assert (output / "otoe-deps.json").is_file()
    assert (output / "manifest.json").is_file()
    assert "build: runner validation failed:" in captured.err
    assert "No module named 'workspace_only_app'" in captured.err


def test_cli_build_copies_runtime_files_into_bundle(tmp_path, monkeypatch):
    module = tmp_path / "runtime_build_surface.py"
    module.write_text(
        "from otoe import Text\n"
        "app = Text('Runtime')\n",
        encoding="utf-8",
    )
    entry = tmp_path / "app.py"
    entry.write_text("from otoe import Text\napp = Text('bundle')\n", encoding="utf-8")
    profile_file = tmp_path / "otoe.profile.toml"
    profile_file.write_text(
        'profile = "cage"\n'
        "\n"
        "[runtime]\n"
        "allow_runtime_installs = false\n"
        'files = ["app.py"]\n',
        encoding="utf-8",
    )
    output = tmp_path / "dist" / "runtime-build"
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "build",
            "runtime_build_surface:app",
            "--profile-file",
            str(profile_file),
            "--out",
            str(output),
        ]
    )

    copied = output / "app" / "app.py"
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    data = entry.read_bytes()
    assert result == 0
    assert copied.read_bytes() == data
    assert manifest["runtimeFiles"] == [
        {
            "source": "app.py",
            "bundlePath": "app/app.py",
            "size": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
        }
    ]


def test_cli_build_rejects_missing_runtime_file_without_manifest(
    tmp_path,
    monkeypatch,
    capsys,
):
    module = tmp_path / "missing_runtime_build_surface.py"
    module.write_text(
        "from otoe import Text\n"
        "app = Text('Missing runtime')\n",
        encoding="utf-8",
    )
    profile_file = tmp_path / "otoe.profile.toml"
    profile_file.write_text(
        'profile = "cage"\n'
        "\n"
        "[runtime]\n"
        'files = ["missing_app.py"]\n',
        encoding="utf-8",
    )
    output = tmp_path / "dist" / "missing-runtime"
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "build",
            "missing_runtime_build_surface:app",
            "--profile-file",
            str(profile_file),
            "--out",
            str(output),
        ]
    )

    captured = capsys.readouterr()
    assert result == 1
    assert (output / "otoe-plan.json").is_file()
    assert not (output / "manifest.json").exists()
    assert "build: runtime file" in captured.err
    assert "missing_app.py" in captured.err


def test_cli_build_rejects_unsafe_runtime_file_path(
    tmp_path,
    monkeypatch,
    capsys,
):
    module = tmp_path / "unsafe_runtime_build_surface.py"
    module.write_text(
        "from otoe import Text\n"
        "app = Text('Unsafe runtime')\n",
        encoding="utf-8",
    )
    profile_file = tmp_path / "otoe.profile.toml"
    profile_file.write_text(
        'profile = "cage"\n'
        "\n"
        "[runtime]\n"
        'files = ["../app.py"]\n',
        encoding="utf-8",
    )
    output = tmp_path / "dist" / "unsafe-runtime"
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "build",
            "unsafe_runtime_build_surface:app",
            "--profile-file",
            str(profile_file),
            "--out",
            str(output),
        ]
    )

    captured = capsys.readouterr()
    assert result == 1
    assert "build: profile file key 'runtime.files[0]' must not contain" in captured.err
    assert not output.exists()


def test_cli_build_copies_profile_assets_into_bundle(tmp_path, monkeypatch):
    module = tmp_path / "asset_build_surface.py"
    module.write_text(
        "from otoe import Text\n"
        "app = Text('Assets')\n",
        encoding="utf-8",
    )
    asset = tmp_path / "static" / "logo.txt"
    asset.parent.mkdir()
    asset.write_text("otoe asset\n", encoding="utf-8")
    profile_file = tmp_path / "otoe.profile.toml"
    profile_file.write_text(
        'profile = "cage"\n'
        'assets = ["static/logo.txt"]\n',
        encoding="utf-8",
    )
    output = tmp_path / "dist" / "asset-build"
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "build",
            "asset_build_surface:app",
            "--profile-file",
            str(profile_file),
            "--out",
            str(output),
        ]
    )

    copied = output / "assets" / "static" / "logo.txt"
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    data = asset.read_bytes()
    assert result == 0
    assert copied.read_bytes() == data
    assert manifest["assets"] == [
        {
            "source": "static/logo.txt",
            "bundlePath": "assets/static/logo.txt",
            "size": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
        }
    ]


def test_cli_build_rejects_missing_asset_without_manifest(
    tmp_path,
    monkeypatch,
    capsys,
):
    module = tmp_path / "missing_asset_build_surface.py"
    module.write_text(
        "from otoe import Text\n"
        "app = Text('Missing asset')\n",
        encoding="utf-8",
    )
    profile_file = tmp_path / "otoe.profile.toml"
    profile_file.write_text(
        'profile = "cage"\n'
        'assets = ["static/missing.txt"]\n',
        encoding="utf-8",
    )
    output = tmp_path / "dist" / "missing-asset"
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "build",
            "missing_asset_build_surface:app",
            "--profile-file",
            str(profile_file),
            "--out",
            str(output),
        ]
    )

    captured = capsys.readouterr()
    assert result == 1
    assert (output / "otoe-plan.json").is_file()
    assert not (output / "manifest.json").exists()
    assert "build: asset file" in captured.err
    assert "static/missing.txt" in captured.err


def test_cli_build_rejects_unsafe_asset_path(tmp_path, monkeypatch, capsys):
    module = tmp_path / "unsafe_asset_build_surface.py"
    module.write_text(
        "from otoe import Text\n"
        "app = Text('Unsafe asset')\n",
        encoding="utf-8",
    )
    profile_file = tmp_path / "otoe.profile.toml"
    profile_file.write_text(
        'profile = "cage"\n'
        'assets = ["../secret.txt"]\n',
        encoding="utf-8",
    )
    output = tmp_path / "dist" / "unsafe-asset"
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "build",
            "unsafe_asset_build_surface:app",
            "--profile-file",
            str(profile_file),
            "--out",
            str(output),
        ]
    )

    captured = capsys.readouterr()
    assert result == 1
    assert "build: profile file key 'assets[0]' must not contain" in captured.err
    assert not output.exists()


def test_cli_build_allows_warning_plan_status(tmp_path, monkeypatch):
    module = tmp_path / "warning_build_surface.py"
    module.write_text(
        "from otoe import Text\n"
        "app = Text('Warning', className='font-semibold')\n",
        encoding="utf-8",
    )
    output = tmp_path / "dist" / "warning"
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "build",
            "warning_build_surface:app",
            "--utilities",
            "--out",
            str(output),
        ]
    )

    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    plan = json.loads((output / "otoe-plan.json").read_text(encoding="utf-8"))
    assert result == 0
    assert plan["status"] == "warnings"
    assert manifest["status"] == "warnings"


def test_cli_build_fails_for_invalid_plan_without_manifest(
    tmp_path,
    monkeypatch,
    capsys,
):
    module = tmp_path / "invalid_build_surface.py"
    module.write_text(
        "from otoe import Text\n"
        "app = Text('Invalid', className='missing')\n",
        encoding="utf-8",
    )
    output = tmp_path / "dist" / "invalid"
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(["build", "invalid_build_surface:app", "--out", str(output)])

    captured = capsys.readouterr()
    plan = json.loads((output / "otoe-plan.json").read_text(encoding="utf-8"))
    assert result == 1
    assert plan["status"] == "invalid"
    assert not (output / "manifest.json").exists()
    assert "build: plan invalid; refusing to write build manifest" in captured.err


def test_cli_build_fails_for_invalid_dependency_audit_without_manifest(
    tmp_path,
    monkeypatch,
    capsys,
):
    module = tmp_path / "invalid_deps_build_surface.py"
    module.write_text(
        "from otoe import Text\n"
        "app = Text('Invalid deps')\n",
        encoding="utf-8",
    )
    profile_file = tmp_path / "otoe.profile.toml"
    profile_file.write_text(
        'profile = "cage"\n'
        "\n"
        "[deps]\n"
        'packages = ["otoe-missing-package-xyz"]\n',
        encoding="utf-8",
    )
    output = tmp_path / "dist" / "invalid-deps"
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "build",
            "invalid_deps_build_surface:app",
            "--profile-file",
            str(profile_file),
            "--out",
            str(output),
        ]
    )

    captured = capsys.readouterr()
    plan = json.loads((output / "otoe-plan.json").read_text(encoding="utf-8"))
    deps = json.loads((output / "otoe-deps.json").read_text(encoding="utf-8"))
    assert result == 1
    assert plan["status"] == "ok"
    assert deps["status"] == "invalid"
    assert deps["packages"][0] == {
        "name": "otoe-missing-package-xyz",
        "status": "missing",
    }
    assert not (output / "manifest.json").exists()
    assert (
        "build: dependency audit invalid; refusing to write build manifest"
        in captured.err
    )


def test_cli_build_rejects_unknown_backend_without_manifest(
    tmp_path,
    monkeypatch,
    capsys,
):
    module = tmp_path / "unknown_backend_build_surface.py"
    module.write_text(
        "from otoe import Text\n"
        "app = Text('Unknown backend')\n",
        encoding="utf-8",
    )
    profile_file = tmp_path / "otoe.profile.toml"
    profile_file.write_text(
        'profile = "cage"\n'
        "\n"
        "[backend]\n"
        'name = "skia"\n',
        encoding="utf-8",
    )
    output = tmp_path / "dist" / "unknown-backend"
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "build",
            "unknown_backend_build_surface:app",
            "--profile-file",
            str(profile_file),
            "--out",
            str(output),
        ]
    )

    captured = capsys.readouterr()
    assert result == 1
    assert (output / "otoe-plan.json").is_file()
    assert (output / "otoe-deps.json").is_file()
    assert not (output / "manifest.json").exists()
    assert "build: unsupported build backend 'skia'; supported: native" in captured.err


def test_cli_deps_reports_ok_without_declared_deps(capsys):
    result = main(["deps", "missing_module:app"])

    captured = capsys.readouterr()
    assert result == 0
    assert "deps missing_module:app: profile cage" in captured.out
    assert "runtime installs: forbidden" in captured.out
    assert "packages: 0 declared, 0 installed, 0 missing" in captured.out
    assert "status: ok" in captured.out


def test_cli_deps_reports_missing_profile_package(tmp_path, capsys):
    profile_file = tmp_path / "otoe.profile.toml"
    profile_file.write_text(
        'profile = "cage"\n'
        "\n"
        "[deps]\n"
        'packages = ["otoe-missing-package-xyz"]\n',
        encoding="utf-8",
    )

    result = main(
        [
            "deps",
            "app:app",
            "--profile-file",
            str(profile_file),
        ]
    )

    captured = capsys.readouterr()
    assert result == 1
    assert "package otoe-missing-package-xyz: missing" in captured.out
    assert "status: invalid" in captured.out
    assert "error: package 'otoe-missing-package-xyz' is not installed" in captured.out


def test_cli_deps_can_emit_json_report(tmp_path, capsys):
    profile_file = tmp_path / "otoe.profile.toml"
    profile_file.write_text(
        'profile = "cage"\n'
        "\n"
        "[deps]\n"
        'packages = ["pytest"]\n',
        encoding="utf-8",
    )

    result = main(
        [
            "deps",
            "app:app",
            "--profile-file",
            str(profile_file),
            "--json",
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert result == 0
    assert payload["schemaVersion"] == 1
    assert payload["target"] == "app:app"
    assert payload["profile"] == "cage"
    assert payload["status"] == "ok"
    assert payload["hasErrors"] is False
    assert payload["runtimeInstallsAllowed"] is False
    assert payload["packages"][0]["name"] == "pytest"
    assert payload["packages"][0]["status"] == "installed"
    assert "version" in payload["packages"][0]
    assert payload["extras"] == []


def test_cli_deps_rejects_unknown_profile_extra(tmp_path, capsys):
    profile_file = tmp_path / "otoe.profile.toml"
    profile_file.write_text(
        'profile = "cage"\n'
        "\n"
        "[deps]\n"
        'extras = ["hardware-magic"]\n',
        encoding="utf-8",
    )

    result = main(
        [
            "deps",
            "app:app",
            "--profile-file",
            str(profile_file),
        ]
    )

    captured = capsys.readouterr()
    assert result == 1
    assert "extra hardware-magic: unknown" in captured.out
    assert "error: extra 'hardware-magic' is not declared by Otoe" in captured.out


def test_cli_deps_rejects_runtime_installs_in_cage_profile(tmp_path, capsys):
    profile_file = tmp_path / "otoe.profile.toml"
    profile_file.write_text(
        'profile = "cage"\n'
        "\n"
        "[runtime]\n"
        "allow_runtime_installs = true\n",
        encoding="utf-8",
    )

    result = main(
        [
            "deps",
            "app:app",
            "--profile-file",
            str(profile_file),
        ]
    )

    captured = capsys.readouterr()
    assert result == 1
    assert "deps: profile 'cage' forbids runtime installs" in captured.err


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
