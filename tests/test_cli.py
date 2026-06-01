import hashlib
import json
import os
import subprocess
import sys
import tarfile
import tomllib
import zlib

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
        "static": [],
        "safelisted": [],
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


def test_cli_plan_compiles_profile_style_safelist(
    tmp_path,
    monkeypatch,
    capsys,
):
    module = tmp_path / "safelist_plan_surface.py"
    module.write_text(
        "from otoe import Text\n"
        "app = Text('Dynamic classes', className='base')\n",
        encoding="utf-8",
    )
    styles = tmp_path / "styles.css"
    styles.write_text(
        ".base { color: #111827; }\n"
        ".is-danger { color: #dc2626; }\n",
        encoding="utf-8",
    )
    profile_file = tmp_path / "otoe.profile.toml"
    profile_file.write_text(
        'profile = "cage"\n'
        'css = ["styles.css"]\n'
        "\n"
        "[styles]\n"
        'safelist = ["is-danger"]\n',
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "plan",
            "safelist_plan_surface:app",
            "--profile-file",
            str(profile_file),
            "--json",
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert result == 0
    assert payload["classes"]["used"] == ["base"]
    assert payload["classes"]["safelisted"] == ["is-danger"]
    assert payload["classes"]["planned"] == ["base", "is-danger"]
    assert payload["styleCounts"]["portable"] == 2


def test_cli_plan_extracts_static_class_names_from_class_name_expressions(
    tmp_path,
    monkeypatch,
    capsys,
):
    module = tmp_path / "static_class_plan_surface.py"
    module.write_text(
        "from otoe import Text, VStack, class_names, computed, signal\n"
        "ready = signal(False)\n"
        "def app():\n"
        "    state_class = computed(\n"
        "        lambda: class_names(\n"
        "            'status',\n"
        "            'is-ready' if ready.value else 'is-idle',\n"
        "        )\n"
        "    )\n"
        "    return VStack(Text('State', className=state_class), className='shell')\n",
        encoding="utf-8",
    )
    styles = tmp_path / "styles.css"
    styles.write_text(
        ".shell { padding: 8; }\n"
        ".status { color: #111827; }\n"
        ".is-idle { background: #ffffff; }\n"
        ".is-ready { background: #dcfce7; }\n",
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "plan",
            "static_class_plan_surface:app",
            "--css",
            str(styles),
            "--json",
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert result == 0
    assert payload["classes"]["used"] == ["shell", "status", "is-idle"]
    assert payload["classes"]["static"] == ["is-ready"]
    assert payload["classes"]["safelisted"] == []
    assert payload["classes"]["planned"] == [
        "shell",
        "status",
        "is-idle",
        "is-ready",
    ]
    assert payload["styleCounts"]["portable"] == 4


def test_cli_plan_does_not_extract_dynamic_f_string_class_fragments(
    tmp_path,
    monkeypatch,
    capsys,
):
    module = tmp_path / "dynamic_fstring_plan_surface.py"
    module.write_text(
        "from otoe import Text, computed, signal\n"
        "tone = signal('idle')\n"
        "app = Text(\n"
        "    'State',\n"
        "    className=computed(lambda: f'status is-{tone.value}'),\n"
        ")\n",
        encoding="utf-8",
    )
    styles = tmp_path / "styles.css"
    styles.write_text(
        ".status { color: #111827; }\n"
        ".is-idle { background: #ffffff; }\n",
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "plan",
            "dynamic_fstring_plan_surface:app",
            "--css",
            str(styles),
            "--json",
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert result == 0
    assert payload["status"] == "warnings"
    assert payload["classes"]["used"] == ["status", "is-idle"]
    assert payload["classes"]["static"] == []
    assert payload["classes"]["planned"] == ["status", "is-idle"]
    assert payload["diagnostics"] == [
        {
            "level": "warning",
            "message": (
                "dynamic className expression in "
                "dynamic_fstring_plan_surface.py:5 uses f-string interpolation; "
                "safelist possible output classes for hardware/cage builds"
            ),
        }
    ]


def test_cli_plan_rejects_invalid_profile_style_safelist_item(
    tmp_path,
    monkeypatch,
    capsys,
):
    module = tmp_path / "bad_safelist_surface.py"
    module.write_text(
        "from otoe import Text\n"
        "app = Text('Bad safelist')\n",
        encoding="utf-8",
    )
    profile_file = tmp_path / "otoe.profile.toml"
    profile_file.write_text(
        'profile = "cage"\n'
        "\n"
        "[styles]\n"
        'safelist = ["bad class"]\n',
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "plan",
            "bad_safelist_surface:app",
            "--profile-file",
            str(profile_file),
        ]
    )

    captured = capsys.readouterr()
    assert result == 1
    assert "[styles] key safelist[0] must be one non-empty class name" in captured.err


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
    runtime_data = module.read_bytes()
    assert result == 0
    assert f"build build_surface:app: {output}" in captured.out
    assert f"deps artifact: {output / 'otoe-deps.json'}" in captured.out
    assert f"styles artifact: {output / 'otoe-styles.json'}" in captured.out
    assert plan["status"] == "ok"
    assert deps["status"] == "ok"
    artifacts = manifest.pop("artifacts")
    framework_files = manifest.pop("frameworkFiles")
    runner = manifest.pop("runner")
    assert artifacts == [
        {
            "path": "otoe-plan.json",
            "size": (output / "otoe-plan.json").stat().st_size,
            "sha256": hashlib.sha256(
                (output / "otoe-plan.json").read_bytes()
            ).hexdigest(),
        },
        {
            "path": "otoe-deps.json",
            "size": (output / "otoe-deps.json").stat().st_size,
            "sha256": hashlib.sha256(
                (output / "otoe-deps.json").read_bytes()
            ).hexdigest(),
        },
        {
            "path": "otoe-styles.json",
            "size": (output / "otoe-styles.json").stat().st_size,
            "sha256": hashlib.sha256(
                (output / "otoe-styles.json").read_bytes()
            ).hexdigest(),
        },
    ]
    assert {
        "source": "otoe/native.py",
        "bundlePath": "framework/otoe/native.py",
        "size": (output / "framework" / "otoe" / "native.py").stat().st_size,
        "sha256": hashlib.sha256(
            (output / "framework" / "otoe" / "native.py").read_bytes()
        ).hexdigest(),
    } in framework_files
    assert {
        "source": "otoe/_native_backend.py",
        "bundlePath": "framework/otoe/_native_backend.py",
        "size": (output / "framework" / "otoe" / "_native_backend.py").stat().st_size,
        "sha256": hashlib.sha256(
            (output / "framework" / "otoe" / "_native_backend.py").read_bytes()
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
        "modes": ["check", "layout-check", "png", "verify"],
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
        "styles": "otoe-styles.json",
        "assets": [],
        "runtimeFiles": [
            {
                "source": "build_surface.py",
                "bundlePath": "app/build_surface.py",
                "size": len(runtime_data),
                "sha256": hashlib.sha256(runtime_data).hexdigest(),
            }
        ],
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
    verify = subprocess.run(
        [sys.executable, str(output / "otoe-run.py"), "--verify"],
        capture_output=True,
        cwd=output,
        env=env,
        text=True,
    )
    check = subprocess.run(
        [sys.executable, str(output / "otoe-run.py"), "--check"],
        capture_output=True,
        cwd=output,
        env=env,
        text=True,
    )
    layout_check = subprocess.run(
        [sys.executable, str(output / "otoe-run.py"), "--layout-check"],
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
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["runtimeFiles"] == [
        {
            "source": "bundled_runner_app.py",
            "bundlePath": "app/bundled_runner_app.py",
            "size": app.stat().st_size,
            "sha256": hashlib.sha256(app.read_bytes()).hexdigest(),
        }
    ]
    assert verify.returncode == 0, verify.stderr
    assert "verified: manifest.json" in verify.stdout
    assert check.returncode == 0, check.stderr
    assert "loaded: bundled_runner_app:app" in check.stdout
    assert layout_check.returncode == 0, layout_check.stderr
    assert "layout checked: bundled_runner_app:app" in layout_check.stdout
    assert png.returncode == 0, png.stderr
    assert frame.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")

    copied_app = output / "app" / "bundled_runner_app.py"
    copied_app.write_text(
        copied_app.read_text(encoding="utf-8").replace("Bundled app", "Bundled bad"),
        encoding="utf-8",
    )
    tampered = subprocess.run(
        [sys.executable, str(output / "otoe-run.py"), "--verify"],
        capture_output=True,
        cwd=output,
        env=env,
        text=True,
    )
    copied_app.unlink()
    missing = subprocess.run(
        [sys.executable, str(output / "otoe-run.py"), "--verify"],
        capture_output=True,
        cwd=output,
        env=env,
        text=True,
    )

    assert tampered.returncode == 1
    assert "sha256 mismatch" in tampered.stderr
    assert missing.returncode == 1
    assert "bundle file 'app/bundled_runner_app.py' does not exist" in missing.stderr


def test_cli_build_runner_rejects_manifest_schema_version(
    tmp_path,
    monkeypatch,
):
    app = tmp_path / "manifest_schema_app.py"
    app.write_text(
        "from otoe import Text\n"
        "app = Text('Manifest schema')\n",
        encoding="utf-8",
    )
    output = tmp_path / "dist" / "manifest-schema"
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "build",
            "manifest_schema_app:app",
            "--out",
            str(output),
            "--validate",
        ]
    )
    manifest_path = output / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["schemaVersion"] = 0
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    verify = subprocess.run(
        [sys.executable, str(output / "otoe-run.py"), "--verify"],
        capture_output=True,
        cwd=output,
        env={**os.environ, "PYTHONPATH": ""},
        text=True,
    )
    layout_check = subprocess.run(
        [sys.executable, str(output / "otoe-run.py"), "--layout-check"],
        capture_output=True,
        cwd=output,
        env={**os.environ, "PYTHONPATH": ""},
        text=True,
    )

    assert result == 0
    assert verify.returncode == 1
    assert "manifest.json: unsupported schemaVersion 0; expected 1" in verify.stderr
    assert layout_check.returncode == 1
    assert "manifest.json: unsupported schemaVersion 0; expected 1" in layout_check.stderr


def test_cli_build_runner_rejects_style_artifact_schema_version(
    tmp_path,
    monkeypatch,
    capsys,
):
    app = tmp_path / "styles_schema_app.py"
    app.write_text(
        "from otoe import Text\n"
        "app = Text('Styles schema')\n",
        encoding="utf-8",
    )
    output = tmp_path / "dist" / "styles-schema"
    archive = tmp_path / "dist" / "styles-schema.tar.gz"
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "build",
            "styles_schema_app:app",
            "--out",
            str(output),
            "--validate",
        ]
    )
    styles_path = output / "otoe-styles.json"
    styles = json.loads(styles_path.read_text(encoding="utf-8"))
    styles["schemaVersion"] = 2
    styles_path.write_text(json.dumps(styles), encoding="utf-8")

    verify = subprocess.run(
        [sys.executable, str(output / "otoe-run.py"), "--verify"],
        capture_output=True,
        cwd=output,
        env={**os.environ, "PYTHONPATH": ""},
        text=True,
    )
    pack_result = main(["pack", str(output), "--out", str(archive)])

    captured = capsys.readouterr()
    assert result == 0
    assert verify.returncode == 1
    assert (
        "otoe-styles.json: unsupported schemaVersion 2; expected 1"
        in verify.stderr
    )
    assert pack_result == 1
    assert not archive.exists()
    assert "pack: runner verification failed:" in captured.err
    assert (
        "otoe-styles.json: unsupported schemaVersion 2; expected 1"
        in captured.err
    )


def test_cli_build_runner_rejects_style_ops_schema_version(
    tmp_path,
    monkeypatch,
):
    app = tmp_path / "style_ops_schema_app.py"
    app.write_text(
        "from otoe import Text\n"
        "app = Text('Style ops schema', className='text-danger')\n",
        encoding="utf-8",
    )
    output = tmp_path / "dist" / "style-ops-schema"
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "build",
            "style_ops_schema_app:app",
            "--out",
            str(output),
            "--utilities",
            "--validate",
        ]
    )
    styles_path = output / "otoe-styles.json"
    styles = json.loads(styles_path.read_text(encoding="utf-8"))
    styles["styleOps"]["schemaVersion"] = 2
    styles_path.write_text(json.dumps(styles), encoding="utf-8")

    verify = subprocess.run(
        [sys.executable, str(output / "otoe-run.py"), "--verify"],
        capture_output=True,
        cwd=output,
        env={**os.environ, "PYTHONPATH": ""},
        text=True,
    )
    layout_check = subprocess.run(
        [sys.executable, str(output / "otoe-run.py"), "--layout-check"],
        capture_output=True,
        cwd=output,
        env={**os.environ, "PYTHONPATH": ""},
        text=True,
    )

    assert result == 0
    assert verify.returncode == 1
    assert (
        "otoe-styles.json styleOps: unsupported schemaVersion 2; expected 1"
        in verify.stderr
    )
    assert layout_check.returncode == 1
    assert (
        "otoe-styles.json styleOps: unsupported schemaVersion 2; expected 1"
        in layout_check.stderr
    )


def test_cli_build_runner_rejects_missing_framework_manifest_entry(
    tmp_path,
    monkeypatch,
):
    app = tmp_path / "missing_framework_entry_app.py"
    app.write_text(
        "from otoe import Text\n"
        "app = Text('Missing framework entry')\n",
        encoding="utf-8",
    )
    output = tmp_path / "dist" / "missing-framework-entry"
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "build",
            "missing_framework_entry_app:app",
            "--out",
            str(output),
            "--validate",
        ]
    )
    manifest_path = output / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["frameworkFiles"] = [
        entry
        for entry in manifest["frameworkFiles"]
        if entry["bundlePath"] != "framework/otoe/native.py"
    ]
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    verify = subprocess.run(
        [sys.executable, str(output / "otoe-run.py"), "--verify"],
        capture_output=True,
        cwd=output,
        env={**os.environ, "PYTHONPATH": ""},
        text=True,
    )

    assert result == 0
    assert verify.returncode == 1
    assert (
        "manifest.json: frameworkFiles missing required file "
        "'framework/otoe/native.py' for backend 'native'"
    ) in verify.stderr


def test_cli_build_runner_rejects_missing_framework_file_on_disk(
    tmp_path,
    monkeypatch,
):
    app = tmp_path / "missing_framework_file_app.py"
    app.write_text(
        "from otoe import Text\n"
        "app = Text('Missing framework file')\n",
        encoding="utf-8",
    )
    output = tmp_path / "dist" / "missing-framework-file"
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "build",
            "missing_framework_file_app:app",
            "--out",
            str(output),
            "--validate",
        ]
    )
    (output / "framework" / "otoe" / "native.py").unlink()

    verify = subprocess.run(
        [sys.executable, str(output / "otoe-run.py"), "--verify"],
        capture_output=True,
        cwd=output,
        env={**os.environ, "PYTHONPATH": ""},
        text=True,
    )

    assert result == 0
    assert verify.returncode == 1
    assert "bundle file 'framework/otoe/native.py' does not exist" in verify.stderr


def test_cli_build_runner_rejects_unsupported_manifest_backend(
    tmp_path,
    monkeypatch,
):
    app = tmp_path / "unsupported_manifest_backend_app.py"
    app.write_text(
        "from otoe import Text\n"
        "app = Text('Unsupported backend')\n",
        encoding="utf-8",
    )
    output = tmp_path / "dist" / "unsupported-manifest-backend"
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "build",
            "unsupported_manifest_backend_app:app",
            "--out",
            str(output),
            "--validate",
        ]
    )
    manifest_path = output / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["backend"] = "skia"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    verify = subprocess.run(
        [sys.executable, str(output / "otoe-run.py"), "--verify"],
        capture_output=True,
        cwd=output,
        env={**os.environ, "PYTHONPATH": ""},
        text=True,
    )

    assert result == 0
    assert verify.returncode == 1
    assert "manifest.json: unsupported backend 'skia'; supported: native" in verify.stderr


def test_cli_build_runner_png_uses_compiled_styles(tmp_path, monkeypatch):
    app = tmp_path / "styled_bundle_app.py"
    app.write_text(
        "from otoe import Text\n"
        "app = Text('Styled', className='danger')\n",
        encoding="utf-8",
    )
    styles = tmp_path / "styles.css"
    styles.write_text(
        ".danger { color: #ff0000; font-size: 18px; }\n",
        encoding="utf-8",
    )
    profile_file = tmp_path / "otoe.profile.toml"
    profile_file.write_text(
        'profile = "cage"\n'
        'css = ["styles.css"]\n'
        "\n"
        "[runtime]\n"
        'files = ["styled_bundle_app.py"]\n',
        encoding="utf-8",
    )
    output = tmp_path / "dist" / "styled-runner"
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "build",
            "styled_bundle_app:app",
            "--profile-file",
            str(profile_file),
            "--out",
            str(output),
            "--validate",
        ]
    )

    styles_payload = json.loads((output / "otoe-styles.json").read_text("utf-8"))
    danger_rule = next(
        rule for rule in styles_payload["rules"] if rule["className"] == "danger"
    )
    frame = output / "styled.png"
    png = subprocess.run(
        [sys.executable, str(output / "otoe-run.py"), "--png", str(frame)],
        capture_output=True,
        cwd=output,
        env={**os.environ, "PYTHONPATH": ""},
        text=True,
    )

    assert result == 0
    assert danger_rule["declarations"]["color"] == {
        "type": "literal",
        "value": "#ff0000",
    }
    assert danger_rule["declarations"]["fontSize"] == {
        "type": "size",
        "value": 18,
        "unit": "px",
    }
    style_ops = {
        entry["className"]: entry
        for entry in styles_payload["styleOps"]["classes"]
    }
    assert styles_payload["styleOps"]["schemaVersion"] == 1
    assert styles_payload["styleOps"]["format"] == "otoe-style-ops"
    assert style_ops["danger"]["ops"] == [
        {
            "op": "setStyle",
            "property": "color",
            "support": "paint",
            "value": {"type": "literal", "value": "#ff0000"},
        },
        {
            "op": "setStyle",
            "property": "fontSize",
            "support": "layout+paint",
            "value": {"type": "size", "value": 18, "unit": "px"},
        },
    ]
    assert style_ops["danger"]["omittedOps"] == []
    assert png.returncode == 0, png.stderr
    assert _png_contains_rgba(frame.read_bytes(), (255, 0, 0, 255))


def test_cli_build_compiles_low_level_style_ops_for_omitted_declarations(
    tmp_path,
    monkeypatch,
):
    app = tmp_path / "style_ops_bundle_app.py"
    app.write_text(
        "from otoe import Text, VStack\n"
        "app = VStack(Text('Ops'), className='shell')\n",
        encoding="utf-8",
    )
    styles = tmp_path / "styles.css"
    styles.write_text(
        ".shell { padding: 8px; width: 50%; border-style: solid; color: #111827; }\n",
        encoding="utf-8",
    )
    profile_file = tmp_path / "otoe.profile.toml"
    profile_file.write_text(
        'profile = "cage"\n'
        'css = ["styles.css"]\n'
        "\n"
        "[runtime]\n"
        'files = ["style_ops_bundle_app.py"]\n',
        encoding="utf-8",
    )
    output = tmp_path / "dist" / "style-ops"
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "build",
            "style_ops_bundle_app:app",
            "--profile-file",
            str(profile_file),
            "--out",
            str(output),
            "--validate",
        ]
    )

    styles_payload = json.loads((output / "otoe-styles.json").read_text("utf-8"))
    shell_ops = styles_payload["styleOps"]["classes"][0]
    assert result == 0
    assert styles_payload["status"] == "warnings"
    assert shell_ops["className"] == "shell"
    assert shell_ops["ops"] == [
        {
            "op": "setStyle",
            "property": "padding",
            "support": "layout",
            "value": {"type": "size", "value": 8, "unit": "px"},
        },
        {
            "op": "setStyle",
            "property": "color",
            "support": "paint",
            "value": {"type": "literal", "value": "#111827"},
        },
    ]
    assert shell_ops["omittedOps"] == [
        {
            "op": "omitStyle",
            "property": "width",
            "support": "layout",
            "status": "deferred",
            "value": {"type": "size", "value": 50, "unit": "%"},
            "message": "property 'width' uses non-px dimension '%'",
        },
        {
            "op": "omitStyle",
            "property": "borderStyle",
            "support": "ignored",
            "status": "html-only",
            "value": {"type": "literal", "value": "solid"},
            "message": "property 'borderStyle' is accepted but ignored by native",
        },
    ]


def test_cli_build_compiles_profile_style_safelist(tmp_path, monkeypatch):
    app = tmp_path / "safelist_bundle_app.py"
    app.write_text(
        "from otoe import Text\n"
        "app = Text('Stateful', className='is-idle')\n",
        encoding="utf-8",
    )
    styles = tmp_path / "styles.css"
    styles.write_text(
        ".is-idle { color: #111827; }\n"
        ".is-danger { color: #dc2626; }\n",
        encoding="utf-8",
    )
    profile_file = tmp_path / "otoe.profile.toml"
    profile_file.write_text(
        'profile = "cage"\n'
        'css = ["styles.css"]\n'
        "\n"
        "[styles]\n"
        'safelist = ["is-danger"]\n'
        "\n"
        "[runtime]\n"
        'files = ["safelist_bundle_app.py"]\n',
        encoding="utf-8",
    )
    output = tmp_path / "dist" / "safelist-runner"
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "build",
            "safelist_bundle_app:app",
            "--profile-file",
            str(profile_file),
            "--out",
            str(output),
            "--validate",
        ]
    )

    styles_payload = json.loads((output / "otoe-styles.json").read_text("utf-8"))
    rules = {rule["className"]: rule for rule in styles_payload["rules"]}
    assert result == 0
    assert styles_payload["classes"]["used"] == ["is-idle"]
    assert styles_payload["classes"]["safelisted"] == ["is-danger"]
    assert styles_payload["classes"]["planned"] == ["is-idle", "is-danger"]
    assert rules["is-danger"]["declarations"]["color"] == {
        "type": "literal",
        "value": "#dc2626",
    }


def test_cli_build_compiles_static_class_names_from_local_target(
    tmp_path,
    monkeypatch,
):
    app = tmp_path / "static_class_bundle_app.py"
    app.write_text(
        "from otoe import Text, VStack, class_names, computed, signal\n"
        "ready = signal(False)\n"
        "def app():\n"
        "    state_class = computed(\n"
        "        lambda: class_names(\n"
        "            'status',\n"
        "            'is-ready' if ready.value else 'is-idle',\n"
        "        )\n"
        "    )\n"
        "    return VStack(Text('State', className=state_class), className='shell')\n",
        encoding="utf-8",
    )
    styles = tmp_path / "styles.css"
    styles.write_text(
        ".shell { padding: 8; }\n"
        ".status { color: #111827; }\n"
        ".is-idle { background: #ffffff; }\n"
        ".is-ready { background: #dcfce7; }\n",
        encoding="utf-8",
    )
    profile_file = tmp_path / "otoe.profile.toml"
    profile_file.write_text(
        'profile = "cage"\n'
        'css = ["styles.css"]\n'
        "\n"
        "[runtime]\n"
        'files = ["static_class_bundle_app.py"]\n',
        encoding="utf-8",
    )
    output = tmp_path / "dist" / "static-class-runner"
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "build",
            "static_class_bundle_app:app",
            "--profile-file",
            str(profile_file),
            "--out",
            str(output),
            "--validate",
        ]
    )

    styles_payload = json.loads((output / "otoe-styles.json").read_text("utf-8"))
    rules = {rule["className"]: rule for rule in styles_payload["rules"]}
    style_ops = {
        entry["className"]: entry
        for entry in styles_payload["styleOps"]["classes"]
    }
    assert result == 0
    assert styles_payload["classes"]["used"] == ["shell", "status", "is-idle"]
    assert styles_payload["classes"]["static"] == ["is-ready"]
    assert styles_payload["classes"]["safelisted"] == []
    assert styles_payload["classes"]["planned"] == [
        "shell",
        "status",
        "is-idle",
        "is-ready",
    ]
    assert rules["is-ready"]["declarations"]["background"] == {
        "type": "literal",
        "value": "#dcfce7",
    }
    assert style_ops["is-ready"]["ops"] == [
        {
            "op": "setStyle",
            "property": "background",
            "support": "paint",
            "value": {"type": "literal", "value": "#dcfce7"},
        }
    ]


def test_cli_build_runner_png_accepts_html_only_missing_class(
    tmp_path,
    monkeypatch,
):
    app = tmp_path / "html_only_bundle_app.py"
    app.write_text(
        "from otoe import Text\n"
        "app = Text('Preview class', className='preview-only')\n",
        encoding="utf-8",
    )
    profile_file = tmp_path / "otoe.profile.toml"
    profile_file.write_text(
        'profile = "cage"\n'
        "\n"
        "[runtime]\n"
        'files = ["html_only_bundle_app.py"]\n',
        encoding="utf-8",
    )
    output = tmp_path / "dist" / "html-only-runner"
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "build",
            "html_only_bundle_app:app",
            "--profile-file",
            str(profile_file),
            "--out",
            str(output),
            "--no-strict-styles",
            "--validate",
        ]
    )

    styles_payload = json.loads((output / "otoe-styles.json").read_text("utf-8"))
    preview_rule = next(
        rule
        for rule in styles_payload["rules"]
        if rule["className"] == "preview-only"
    )
    frame = output / "html-only.png"
    png = subprocess.run(
        [sys.executable, str(output / "otoe-run.py"), "--png", str(frame)],
        capture_output=True,
        cwd=output,
        env={**os.environ, "PYTHONPATH": ""},
        text=True,
    )

    assert result == 0
    assert preview_rule["missing"] is True
    assert preview_rule["declarations"] == {}
    assert png.returncode == 0, png.stderr
    assert frame.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")


def test_cli_build_validate_rejects_bad_compiled_styles(
    tmp_path,
    monkeypatch,
    capsys,
):
    app = tmp_path / "bad_compiled_styles_app.py"
    app.write_text(
        "from otoe import Text\n"
        "app = Text('Bad style', className='text-sm')\n",
        encoding="utf-8",
    )
    profile_file = tmp_path / "otoe.profile.toml"
    profile_file.write_text(
        'profile = "cage"\n'
        "\n"
        "[runtime]\n"
        'files = ["bad_compiled_styles_app.py"]\n',
        encoding="utf-8",
    )
    output = tmp_path / "dist" / "bad-compiled-styles"
    monkeypatch.syspath_prepend(str(tmp_path))

    def bad_compiled_styles(plan, *, target, stylesheet):
        return {
            "schemaVersion": 1,
            "target": target,
            "profile": plan.profile,
            "status": "ok",
            "classes": {
                "used": ["text-sm"],
                "safelisted": [],
                "planned": ["text-sm"],
                "htmlOnly": [],
                "invalid": [],
            },
            "styleCounts": {
                "portable": 1,
                "html-only": 0,
                "deferred": 0,
                "invalid": 0,
            },
            "directStyleCounts": {
                "portable": 0,
                "html-only": 0,
                "deferred": 0,
                "invalid": 0,
            },
            "tokens": {},
            "rules": [
                {
                    "className": "text-sm",
                    "selector": ".text-sm",
                    "declarations": {
                        "fontSize": {"type": "literal", "value": "large"}
                    },
                    "omittedDeclarations": [],
                    "missing": False,
                }
            ],
            "diagnostics": [],
        }

    monkeypatch.setattr("otoe.cli.compiled_styles_to_dict", bad_compiled_styles)

    result = main(
        [
            "build",
            "bad_compiled_styles_app:app",
            "--profile-file",
            str(profile_file),
            "--out",
            str(output),
            "--utilities",
            "--validate",
        ]
    )

    captured = capsys.readouterr()
    assert result == 1
    assert (output / "manifest.json").is_file()
    assert "build: runner layout validation failed:" in captured.err
    assert "Native layout expected numeric fontSize" in captured.err


def test_cli_pack_writes_verified_tarball(tmp_path, monkeypatch, capsys):
    app = tmp_path / "packed_app.py"
    app.write_text(
        "from otoe import Text\n"
        "app = Text('Packed app')\n",
        encoding="utf-8",
    )
    profile_file = tmp_path / "otoe.profile.toml"
    profile_file.write_text(
        'profile = "cage"\n'
        "\n"
        "[runtime]\n"
        'files = ["packed_app.py"]\n',
        encoding="utf-8",
    )
    output = tmp_path / "dist" / "pack-build"
    archive = tmp_path / "dist" / "pack-build.tar.gz"
    monkeypatch.syspath_prepend(str(tmp_path))

    assert (
        main(
            [
                "build",
                "packed_app:app",
                "--profile-file",
                str(profile_file),
                "--out",
                str(output),
                "--validate",
            ]
        )
        == 0
    )
    (output / "app" / "__pycache__").mkdir(exist_ok=True)
    (output / "app" / "__pycache__" / "ignored.pyc").write_bytes(b"ignored")
    (output / ".pytest_cache").mkdir()
    (output / ".pytest_cache" / "ignored").write_text("ignored", encoding="utf-8")
    (output / "frame.png").write_bytes(b"not part of the deploy bundle")

    result = main(["pack", str(output), "--out", str(archive)])

    captured = capsys.readouterr()
    assert result == 0
    assert f"pack {output}: {archive}" in captured.out
    assert "sha256:" in captured.out
    with tarfile.open(archive, "r:gz") as tar:
        names = tar.getnames()
        for member in tar.getmembers():
            target = tmp_path / "extracted" / member.name
            target.parent.mkdir(parents=True, exist_ok=True)
            source = tar.extractfile(member)
            assert source is not None
            target.write_bytes(source.read())
    assert "manifest.json" in names
    assert "otoe-plan.json" in names
    assert "otoe-deps.json" in names
    assert "otoe-styles.json" in names
    assert "otoe-run.py" in names
    assert "app/packed_app.py" in names
    assert "framework/otoe/native.py" in names
    assert "frame.png" not in names
    assert all("__pycache__" not in name for name in names)
    assert all(".pytest_cache" not in name for name in names)

    extracted = tmp_path / "extracted"
    verify = subprocess.run(
        [sys.executable, str(extracted / "otoe-run.py"), "--verify"],
        capture_output=True,
        cwd=extracted,
        env={**os.environ, "PYTHONPATH": ""},
        text=True,
    )
    assert verify.returncode == 0, verify.stderr
    assert "verified: manifest.json" in verify.stdout


def test_cli_pack_rejects_tampered_bundle(tmp_path, monkeypatch, capsys):
    app = tmp_path / "tampered_pack_app.py"
    app.write_text(
        "from otoe import Text\n"
        "app = Text('Packed app')\n",
        encoding="utf-8",
    )
    profile_file = tmp_path / "otoe.profile.toml"
    profile_file.write_text(
        'profile = "cage"\n'
        "\n"
        "[runtime]\n"
        'files = ["tampered_pack_app.py"]\n',
        encoding="utf-8",
    )
    output = tmp_path / "dist" / "tampered-pack"
    archive = tmp_path / "dist" / "tampered-pack.tar.gz"
    monkeypatch.syspath_prepend(str(tmp_path))

    assert (
        main(
            [
                "build",
                "tampered_pack_app:app",
                "--profile-file",
                str(profile_file),
                "--out",
                str(output),
            ]
        )
        == 0
    )
    copied_app = output / "app" / "tampered_pack_app.py"
    copied_app.write_text(
        copied_app.read_text(encoding="utf-8").replace("Packed app", "Tampered!!"),
        encoding="utf-8",
    )

    result = main(["pack", str(output), "--out", str(archive)])

    captured = capsys.readouterr()
    assert result == 1
    assert not archive.exists()
    assert "pack: runner verification failed:" in captured.err
    assert "sha256 mismatch" in captured.err


def test_cli_pack_rejects_missing_manifest(tmp_path, capsys):
    bundle = tmp_path / "empty-bundle"
    bundle.mkdir()

    result = main(["pack", str(bundle), "--out", str(tmp_path / "bundle.tar.gz")])

    captured = capsys.readouterr()
    assert result == 1
    assert "pack: bundle is missing manifest.json" in captured.err


def test_cli_compare_contract_accepts_matching_json(tmp_path, capsys):
    expected = tmp_path / "expected.json"
    actual = tmp_path / "actual.json"
    payload = {
        "schemaVersion": 1,
        "format": "renderer-contract-compact",
        "runs": {
            "minimal": {
                "after": {
                    "hashes": {
                        "layout": "sha256:aaa",
                        "paint": "sha256:bbb",
                    }
                }
            }
        },
    }
    expected.write_text(json.dumps(payload), encoding="utf-8")
    actual.write_text(json.dumps(payload), encoding="utf-8")

    result = main(["compare-contract", str(expected), str(actual)])

    captured = capsys.readouterr()
    assert result == 0
    assert f"contracts match: {expected} == {actual}" in captured.out
    assert captured.err == ""


def test_cli_compare_contract_reports_human_differences(tmp_path, capsys):
    expected = tmp_path / "expected.json"
    actual = tmp_path / "actual.json"
    expected.write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "runs": {
                    "minimal": {
                        "after": {
                            "hashes": {"layout": "sha256:expected"},
                            "visibleText": ["One", "Two"],
                        }
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    actual.write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "runs": {
                    "minimal": {
                        "after": {
                            "hashes": {"layout": "sha256:actual"},
                            "visibleText": ["One"],
                        }
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    result = main(["compare-contract", str(expected), str(actual)])

    captured = capsys.readouterr()
    assert result == 1
    assert "contracts differ: 2 difference(s)" in captured.out
    assert "/runs/minimal/after/hashes/layout" in captured.out
    assert '"sha256:expected"' in captured.out
    assert '"sha256:actual"' in captured.out
    assert "/runs/minimal/after/visibleText: length 2 != 1" in captured.out


def test_cli_compare_contract_ignores_json_pointer_paths(tmp_path, capsys):
    expected = tmp_path / "expected.json"
    actual = tmp_path / "actual.json"
    expected.write_text(
        json.dumps(
            {
                "pngSmoke": {
                    "path": "expected.png",
                    "frame": {"hashes": {"layout": "sha256:same"}},
                },
                "calls": [{"subject": "expected"}, {"subject": "stable"}],
            }
        ),
        encoding="utf-8",
    )
    actual.write_text(
        json.dumps(
            {
                "pngSmoke": {
                    "path": "actual.png",
                    "frame": {"hashes": {"layout": "sha256:same"}},
                },
                "calls": [{"subject": "actual"}, {"subject": "stable"}],
            }
        ),
        encoding="utf-8",
    )

    result = main(
        [
            "compare-contract",
            str(expected),
            str(actual),
            "--ignore-path",
            "/pngSmoke/path",
            "--ignore-path",
            "/calls/0/subject",
            "--json",
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert result == 0
    assert payload["matched"] is True
    assert payload["differenceCount"] == 0
    assert payload["ignoredPaths"] == ["/pngSmoke/path", "/calls/0/subject"]


def test_cli_compare_contract_outputs_json_report(tmp_path, capsys):
    expected = tmp_path / "expected.json"
    actual = tmp_path / "actual.json"
    expected.write_text(json.dumps({"a": {"b": 1}}), encoding="utf-8")
    actual.write_text(json.dumps({"a": {"b": 2}, "extra": True}), encoding="utf-8")

    result = main(["compare-contract", str(expected), str(actual), "--json"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert result == 1
    assert payload["schemaVersion"] == 1
    assert payload["matched"] is False
    assert payload["differenceCount"] == 2
    assert payload["differences"] == [
        {
            "actual": True,
            "expected": None,
            "kind": "extra",
            "path": "/extra",
        },
        {
            "actual": 2,
            "expected": 1,
            "kind": "value",
            "path": "/a/b",
        },
    ]


def test_cli_compare_contract_limits_reported_differences(tmp_path, capsys):
    expected = tmp_path / "expected.json"
    actual = tmp_path / "actual.json"
    expected.write_text(json.dumps({"a": 1, "b": 2, "c": 3}), encoding="utf-8")
    actual.write_text(json.dumps({"a": 4, "b": 5, "c": 6}), encoding="utf-8")

    result = main(
        [
            "compare-contract",
            str(expected),
            str(actual),
            "--max-diffs",
            "1",
        ]
    )

    captured = capsys.readouterr()
    assert result == 1
    assert "contracts differ: 3 difference(s)" in captured.out
    assert "- /a:" in captured.out
    assert "- /b:" not in captured.out
    assert "... 2 more difference(s)" in captured.out


def test_cli_compare_contract_rejects_invalid_ignore_path(tmp_path, capsys):
    expected = tmp_path / "expected.json"
    actual = tmp_path / "actual.json"
    expected.write_text("{}", encoding="utf-8")
    actual.write_text("{}", encoding="utf-8")

    result = main(
        [
            "compare-contract",
            str(expected),
            str(actual),
            "--ignore-path",
            "pngSmoke/path",
        ]
    )

    captured = capsys.readouterr()
    assert result == 1
    assert "compare-contract: ignore path must be a JSON pointer" in captured.err


def test_cli_compare_contract_rejects_missing_or_invalid_json(tmp_path, capsys):
    invalid = tmp_path / "invalid.json"
    valid = tmp_path / "valid.json"
    invalid.write_text("{ nope", encoding="utf-8")
    valid.write_text("{}", encoding="utf-8")

    missing_result = main(
        ["compare-contract", str(tmp_path / "missing.json"), str(valid)]
    )
    invalid_result = main(["compare-contract", str(invalid), str(valid)])

    captured = capsys.readouterr()
    assert missing_result == 1
    assert invalid_result == 1
    assert "compare-contract: expected file" in captured.err
    assert "does not exist" in captured.err
    assert "compare-contract: expected file" in captured.err
    assert "is not valid JSON" in captured.err


def _png_contains_rgba(data: bytes, rgba: tuple[int, int, int, int]) -> bool:
    idat = []
    offset = 8
    while offset < len(data):
        length = int.from_bytes(data[offset : offset + 4], "big")
        kind = data[offset + 4 : offset + 8]
        payload = data[offset + 8 : offset + 8 + length]
        if kind == b"IDAT":
            idat.append(payload)
        offset += length + 12
    return bytes(rgba) in zlib.decompress(b"".join(idat))


def test_cli_build_validate_auto_copies_simple_target_module(
    tmp_path,
    monkeypatch,
    capsys,
):
    module = tmp_path / "auto_runtime_app.py"
    module.write_text(
        "from otoe import Text\n"
        "app = Text('Auto runtime')\n",
        encoding="utf-8",
    )
    output = tmp_path / "dist" / "auto-runtime"
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "build",
            "auto_runtime_app:app",
            "--out",
            str(output),
            "--validate",
        ]
    )

    captured = capsys.readouterr()
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    data = module.read_bytes()
    assert result == 0
    assert "validation: ok" in captured.out
    assert (output / "app" / "auto_runtime_app.py").read_bytes() == data
    assert manifest["runtimeFiles"] == [
        {
            "source": "auto_runtime_app.py",
            "bundlePath": "app/auto_runtime_app.py",
            "size": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
        }
    ]


def test_cli_build_validate_auto_copies_simple_local_imports(
    tmp_path,
    monkeypatch,
):
    module = tmp_path / "auto_import_app.py"
    module.write_text(
        "from otoe import Text\n"
        "from helper_view import view_text\n"
        "app = Text(view_text())\n",
        encoding="utf-8",
    )
    helper = tmp_path / "helper_view.py"
    helper.write_text(
        "from palette import LABEL\n"
        "def view_text():\n"
        "    return LABEL\n",
        encoding="utf-8",
    )
    palette = tmp_path / "palette.py"
    palette.write_text('LABEL = "Auto import"\n', encoding="utf-8")
    output = tmp_path / "dist" / "auto-imports"
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "build",
            "auto_import_app:app",
            "--out",
            str(output),
            "--validate",
        ]
    )

    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    runtime_files = {entry["bundlePath"]: entry for entry in manifest["runtimeFiles"]}
    assert result == 0
    assert sorted(runtime_files) == [
        "app/auto_import_app.py",
        "app/helper_view.py",
        "app/palette.py",
    ]
    for source in (module, helper, palette):
        bundle_path = f"app/{source.name}"
        data = source.read_bytes()
        assert (output / bundle_path).read_bytes() == data
        assert runtime_files[bundle_path] == {
            "source": source.name,
            "bundlePath": bundle_path,
            "size": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
        }


def test_cli_build_validate_rejects_package_target_without_runtime_files(
    tmp_path,
    monkeypatch,
    capsys,
):
    package = tmp_path / "workspace_pkg"
    package.mkdir()
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "app.py").write_text(
        "from otoe import Text\n"
        "app = Text('Package runtime')\n",
        encoding="utf-8",
    )
    output = tmp_path / "dist" / "package-missing"
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "build",
            "workspace_pkg.app:app",
            "--out",
            str(output),
            "--validate",
        ]
    )

    captured = capsys.readouterr()
    assert result == 1
    assert (output / "manifest.json").is_file()
    assert "build: runner validation failed:" in captured.err
    assert "No module named 'workspace_pkg'" in captured.err


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
    module_data = module.read_bytes()
    assert result == 0
    assert copied.read_bytes() == data
    assert manifest["runtimeFiles"] == [
        {
            "source": "runtime_build_surface.py",
            "bundlePath": "app/runtime_build_surface.py",
            "size": len(module_data),
            "sha256": hashlib.sha256(module_data).hexdigest(),
        },
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
