import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tarfile
import tomllib
import zlib
from pathlib import Path

import pytest

import otoe.deps as deps_module
from otoe.capabilities import backend_capability_profile
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

    monkeypatch.setattr("otoe.cli_check.subprocess.run", fake_run)

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
    assert payload["backend"] == "native-python"
    assert payload["backendCapabilities"]["name"] == "native-python"
    assert payload["backendCapabilities"]["styles"]["padding"] == "layout"
    assert payload["widgetSupportCounts"] == {"container": 1, "text": 1}
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


def test_cli_plan_imports_target_from_current_directory_without_sys_path(
    tmp_path,
    monkeypatch,
    capsys,
):
    module = tmp_path / "cwd_plan_surface.py"
    module.write_text(
        "from otoe import Text\n"
        "app = Text('Ready')\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        sys,
        "path",
        [entry for entry in sys.path if entry not in {"", str(tmp_path)}],
    )

    result = main(["plan", "cwd_plan_surface:app", "--json"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert result == 0
    assert payload["target"] == "cwd_plan_surface:app"
    assert payload["widgetCount"] == 1


def test_cli_plan_accepts_backend_capability_override(
    tmp_path,
    monkeypatch,
    capsys,
):
    module = tmp_path / "backend_capability_surface.py"
    module.write_text(
        "from otoe import Text\n"
        "app = Text('Backend', className='title')\n",
        encoding="utf-8",
    )
    styles = tmp_path / "styles.css"
    styles.write_text(".title { color: #172033; }\n", encoding="utf-8")
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "plan",
            "backend_capability_surface:app",
            "--css",
            str(styles),
            "--backend",
            "native",
            "--json",
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert result == 0
    assert payload["backend"] == "native-python"
    assert payload["backendCapabilities"]["label"] == "Python native renderer"


def test_cli_plan_accepts_backend_capability_profile_json(
    tmp_path,
    monkeypatch,
    capsys,
):
    module = tmp_path / "backend_capability_profile_surface.py"
    module.write_text(
        "from otoe import Text, VStack\n"
        "app = VStack(Text('Backend profile'), className='shell')\n",
        encoding="utf-8",
    )
    styles = tmp_path / "styles.css"
    styles.write_text(
        ".shell { padding: 8; background: #ffffff; }\n",
        encoding="utf-8",
    )
    profile = tmp_path / "candidate-profile.json"
    _write_backend_capability_profile(
        profile,
        name="candidate-cli",
        styles={"background": "paint", "padding": "layout"},
        widgets={"Text": "text", "VStack": "container"},
    )
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "plan",
            "backend_capability_profile_surface:app",
            "--css",
            str(styles),
            "--backend-capability-profile",
            str(profile),
            "--json",
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert result == 0
    assert payload["backend"] == "candidate-cli"
    assert payload["backendCapabilities"]["label"] == "candidate-cli profile"
    assert payload["backendCapabilities"]["styles"] == {
        "background": "paint",
        "padding": "layout",
    }
    assert payload["widgetSupportCounts"] == {"container": 1, "text": 1}
    assert payload["styleCounts"]["portable"] == 2


def test_cli_plan_rejects_unknown_backend_capability(
    tmp_path,
    monkeypatch,
    capsys,
):
    module = tmp_path / "unknown_backend_capability_surface.py"
    module.write_text(
        "from otoe import Text\n"
        "app = Text('Backend')\n",
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "plan",
            "unknown_backend_capability_surface:app",
            "--backend",
            "gpu-magic",
        ]
    )

    captured = capsys.readouterr()
    assert result == 1
    assert "unsupported backend capability profile 'gpu-magic'" in captured.err


def test_cli_plan_rejects_backend_capability_and_profile_together(
    tmp_path,
    monkeypatch,
    capsys,
):
    module = tmp_path / "backend_capability_conflict_surface.py"
    module.write_text(
        "from otoe import Text\n"
        "app = Text('Backend')\n",
        encoding="utf-8",
    )
    profile = tmp_path / "candidate-profile.json"
    _write_backend_capability_profile(profile, name="candidate-conflict")
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "plan",
            "backend_capability_conflict_surface:app",
            "--backend",
            "native",
            "--backend-capability-profile",
            str(profile),
        ]
    )

    captured = capsys.readouterr()
    assert result == 1
    assert (
        "--backend and --backend-capability-profile are mutually exclusive"
        in captured.err
    )


def test_cli_backend_profile_outputs_builtin_summary(capsys):
    result = main(["backend-profile", "native"])

    captured = capsys.readouterr()
    assert result == 0
    assert "backend-profile native-python" in captured.out
    assert "label: Python native renderer" in captured.out
    assert "styles: ignored=5, layout=11, layout+paint=2, paint=4" in captured.out
    assert "widgets: container=8, control=2, text=1" in captured.out
    assert "inputs: deferred=8, supported=8" in captured.out
    assert "renderer boundaries: supported=2" in captured.out
    assert (
        "coverage: rendererBoundaries=2, widgets=11, inputs=8, styles=17, "
        "declaredStyleOmissions=5"
        in captured.out
    )


def test_cli_backend_profile_outputs_json_report(capsys):
    result = main(["backend-profile", "native-python", "--json"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert result == 0
    assert payload["schemaVersion"] == 1
    assert payload["format"] == "backend-profile-report"
    assert payload["profile"]["name"] == "native-python"
    assert payload["summary"]["styles"] == {
        "ignored": 5,
        "layout": 11,
        "layout+paint": 2,
        "paint": 4,
    }
    assert payload["summary"]["coverage"] == {
        "rendererBoundaries": 2,
        "widgets": 11,
        "inputs": 8,
        "styles": 17,
        "declaredStyleOmissions": 5,
    }
    assert payload["coverageDeclaration"]["format"] == "backend-coverage-declaration"


def test_cli_backend_profile_outputs_coverage_declaration(capsys):
    result = main(["backend-profile", "native-python", "--coverage-declaration"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert result == 0
    assert payload["backend"] == "native-python"
    assert payload["format"] == "backend-coverage-declaration"
    assert "Button" in payload["covers"]["widgets"]
    assert "click" in payload["covers"]["inputs"]


def test_cli_backend_profile_writes_coverage_declaration_artifact(tmp_path, capsys):
    output = tmp_path / "native-coverage-declaration.json"

    result = main(
        [
            "backend-profile",
            "native-python",
            "--coverage-declaration",
            "--out",
            str(output),
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert result == 0
    assert captured.out == f"backend profile artifact: {output}\n"
    assert payload["backend"] == "native-python"
    assert payload["format"] == "backend-coverage-declaration"


def test_cli_backend_profile_loads_candidate_profile_json(
    tmp_path,
    capsys,
):
    profile = tmp_path / "candidate-profile.json"
    _write_backend_capability_profile(
        profile,
        name="candidate-inspect",
        styles={"padding": "layout"},
        widgets={"Text": "text"},
        inputs={"click": "supported", "gesture": "deferred"},
    )

    result = main(
        [
            "backend-profile",
            "--backend-capability-profile",
            str(profile),
            "--json",
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert result == 0
    assert payload["profile"]["name"] == "candidate-inspect"
    assert payload["summary"]["styles"] == {"layout": 1}
    assert payload["summary"]["widgets"] == {"text": 1}
    assert payload["summary"]["inputs"] == {"deferred": 1, "supported": 1}
    assert payload["coverageDeclaration"]["covers"] == {
        "widgets": ["Text"],
        "inputs": ["click"],
        "rendererBoundaries": [],
        "styles": ["padding"],
        "declaredStyleOmissions": [],
    }


def test_cli_backend_profile_rejects_name_and_profile_json(
    tmp_path,
    capsys,
):
    profile = tmp_path / "candidate-profile.json"
    _write_backend_capability_profile(profile, name="candidate-conflict")

    result = main(
        [
            "backend-profile",
            "native-python",
            "--backend-capability-profile",
            str(profile),
        ]
    )

    captured = capsys.readouterr()
    assert result == 1
    assert (
        "profile name and --backend-capability-profile are mutually exclusive"
        in captured.err
    )


def test_cli_backend_coverage_accepts_builtin_profile(capsys):
    result = main(
        [
            "backend-coverage",
            "--requirements",
            "examples/native/contracts/backend_readiness_expected.json",
            "--backend",
            "native-python",
            "--json",
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert result == 0
    assert payload["schemaVersion"] == 1
    assert payload["format"] == "backend-coverage-report"
    assert payload["backend"] == "native-python"
    assert payload["passed"] is True
    assert payload["readiness"]["passed"] is True
    assert payload["readiness"]["candidate"]["backend"] == "native-python"
    assert payload["readiness"]["strictEvidence"] is True
    assert payload["readiness"]["evidenceSummary"] == {
        "malformed": 0,
        "malformedByBlocker": {},
    }
    assert payload["blockers"] == []
    assert payload["coverage"]["widgets"]["extra"] == []
    assert payload["coverage"]["widgets"]["evidence"]["claimed"] == [
        "Button",
        "FocusScope",
        "For",
        "HStack",
        "Input",
        "Panel",
        "ScrollView",
        "ShortcutScope",
        "Show",
        "Text",
        "VStack",
    ]
    assert payload["coverage"]["widgets"]["evidence"]["unproven"] == []
    assert payload["coverage"]["widgets"]["summary"]["unproven"] == 0
    assert payload["coverage"]["widgets"]["evidenceMap"]["Button"]["sources"][
        0
    ]["gate"] == "rendererReplay"
    assert payload["coverage"]["styles"]["missing"] == []


def test_cli_backend_coverage_audit_reports_traceable_sources(capsys):
    result = main(
        [
            "backend-coverage",
            "--requirements",
            "examples/native/contracts/backend_readiness_expected.json",
            "--backend",
            "native-python",
            "--audit",
        ]
    )

    captured = capsys.readouterr()
    assert result == 0
    assert "backend-coverage audit native-python" in captured.out
    assert (
        "rendererBoundaries: covered=2/2, missing=0, unproven=0"
        in captured.out
    )
    assert (
        "rendererBoundaries renderTreeLayout: covered required=yes "
        "declared=yes exercised=yes"
    ) in captured.out
    assert (
        "rendererBoundaries renderTreeLayout proof[0]: "
        "source=path0RenderTreeEvidence gate=path0RenderTreeEvidence "
        "kind=rendererBoundary group=0 count=1 phase=layout "
        "boundary=renderTree layoutBoxes=15 "
        "outputHash=sha256:53f705a49cf269a14ea0ca186a11018de87608ef086baa1194f9ae85b792ed4a"
    ) in captured.out
    assert (
        "rendererBoundaries paint proof[0]: "
        "source=path0RenderTreeEvidence gate=path0RenderTreeEvidence "
        "kind=rendererBoundary group=0 count=1 phase=paint paintCommands=18 "
        "outputHash=sha256:455f2fdf5eda9b3602cbe4f7d944de2a484ebe6e8887ce2ae7e593af519042a3"
    ) in captured.out
    assert "widgets: covered=11/11, missing=0, unproven=0" in captured.out
    assert (
        "widgets Button: covered required=yes declared=yes exercised=yes"
        in captured.out
    )
    assert (
        "widgets Button proof[0]: source=rendererReplay gate=rendererReplay "
        "kind=widget support=control group=1 count=9"
    ) in captured.out
    assert (
        "styles borderWidth: covered required=yes declared=yes exercised=yes"
        in captured.out
    )
    assert (
        "styles borderWidth proof[0]: "
        "source=styleOpsReplay+path0RenderTreeEvidence "
        "gate=styleOpsReplay+path0RenderTreeEvidence kind=apply "
        "support=layout+paint group=1 count=3 "
        "runtime=path0-renderer-candidate phases=layout+paint"
    ) in captured.out
    assert "layoutHash=sha256:" in captured.out
    assert "paintHash=sha256:" in captured.out
    assert (
        "declaredStyleOmissions display proof[0]: "
        "source=styleOpsReplay+path0RenderTreeEvidence "
        "gate=styleOpsReplay+path0RenderTreeEvidence kind=omit "
        "status=html-only group=0 count=1 runtime=path0-renderer-candidate "
        "phases=layout+paint"
    ) in captured.out
    assert "blockers: none" in captured.out


def test_cli_backend_coverage_reports_evidence_contract_errors(tmp_path, capsys):
    requirements = json.loads(
        open(
            "examples/native/contracts/backend_readiness_expected.json",
            encoding="utf-8",
        ).read()
    )
    requirements["evidence"]["widgets"][0].pop("source")
    requirements_path = tmp_path / "broken-readiness.json"
    requirements_path.write_text(json.dumps(requirements), encoding="utf-8")

    result = main(
        [
            "backend-coverage",
            "--requirements",
            str(requirements_path),
            "--backend",
            "native-python",
        ]
    )

    captured = capsys.readouterr()
    assert result == 1
    assert "status: failed" in captured.out
    assert "widgets: covered=3/11, missing=0, unproven=8" in captured.out
    assert (
        "widgets unproven: FocusScope, For, HStack, Panel, ScrollView, "
        "ShortcutScope, Show, VStack"
    ) in captured.out
    assert "evidence errors: 1" in captured.out
    assert "evidence malformed: 1" in captured.out
    assert "evidence malformed by blocker: widgetsEvidence=1" in captured.out
    assert (
        "evidence error: evidence.widgets[0].source must be a non-empty string"
        in captured.out
    )
    assert "blockers: widgetsEvidence" in captured.out


def test_cli_backend_coverage_audit_reports_unproven_claims(tmp_path, capsys):
    requirements = json.loads(
        open(
            "examples/native/contracts/backend_readiness_expected.json",
            encoding="utf-8",
        ).read()
    )
    requirements["evidence"]["widgets"][0].pop("source")
    requirements_path = tmp_path / "broken-readiness.json"
    requirements_path.write_text(json.dumps(requirements), encoding="utf-8")

    result = main(
        [
            "backend-coverage",
            "--requirements",
            str(requirements_path),
            "--backend",
            "native-python",
            "--audit",
        ]
    )

    captured = capsys.readouterr()
    assert result == 1
    assert "backend-coverage audit native-python" in captured.out
    assert (
        "widgets FocusScope: unproven required=yes declared=yes exercised=no"
        in captured.out
    )
    assert "widgets FocusScope proof: none" in captured.out
    assert "evidence errors: 1" in captured.out
    assert "evidence malformed: 1" in captured.out
    assert "evidence malformed by blocker: widgetsEvidence=1" in captured.out
    assert "blockers: widgetsEvidence" in captured.out


def test_cli_backend_coverage_rejects_readiness_without_contract_format(
    tmp_path,
    capsys,
):
    readiness = json.loads(
        open(
            "examples/native/contracts/backend_readiness_expected.json",
            encoding="utf-8",
        ).read()
    )
    readiness.pop("format")
    requirements_path = tmp_path / "missing-format-readiness.json"
    requirements_path.write_text(json.dumps(readiness), encoding="utf-8")

    result = main(
        [
            "backend-coverage",
            "--requirements",
            str(requirements_path),
            "--backend",
            "native-python",
        ]
    )

    captured = capsys.readouterr()
    assert result == 1
    assert "status: failed" in captured.out
    assert "evidence errors: 1" in captured.out
    assert "evidence malformed by blocker: backendReadinessContract=1" in captured.out
    assert (
        "evidence error: readiness.format must be 'backend-readiness-report'"
        in captured.out
    )
    assert "blockers: backendReadinessContract" in captured.out


def test_cli_backend_coverage_rejects_readiness_with_wrong_contract_format(
    tmp_path,
    capsys,
):
    readiness = json.loads(
        open(
            "examples/native/contracts/backend_readiness_expected.json",
            encoding="utf-8",
        ).read()
    )
    readiness["format"] = "not-readiness"
    requirements_path = tmp_path / "wrong-format-readiness.json"
    requirements_path.write_text(json.dumps(readiness), encoding="utf-8")

    result = main(
        [
            "backend-coverage",
            "--requirements",
            str(requirements_path),
            "--backend",
            "native-python",
        ]
    )

    captured = capsys.readouterr()
    assert result == 1
    assert "status: failed" in captured.out
    assert "evidence errors: 1" in captured.out
    assert "evidence malformed by blocker: backendReadinessContract=1" in captured.out
    assert (
        "evidence error: readiness.format must be 'backend-readiness-report'"
        in captured.out
    )
    assert "blockers: backendReadinessContract" in captured.out


def test_cli_backend_coverage_rejects_readiness_with_wrong_schema_version(
    tmp_path,
    capsys,
):
    readiness = json.loads(
        open(
            "examples/native/contracts/backend_readiness_expected.json",
            encoding="utf-8",
        ).read()
    )
    readiness["schemaVersion"] = 2
    requirements_path = tmp_path / "wrong-schema-readiness.json"
    requirements_path.write_text(json.dumps(readiness), encoding="utf-8")

    result = main(
        [
            "backend-coverage",
            "--requirements",
            str(requirements_path),
            "--backend",
            "native-python",
        ]
    )

    captured = capsys.readouterr()
    assert result == 1
    assert "status: failed" in captured.out
    assert "evidence errors: 1" in captured.out
    assert "evidence malformed by blocker: backendReadinessContract=1" in captured.out
    assert "evidence error: readiness.schemaVersion must be 1" in captured.out
    assert "blockers: backendReadinessContract" in captured.out


def test_cli_backend_coverage_rejects_backend_identity_mismatch(tmp_path, capsys):
    declaration = json.loads(
        open(
            "examples/native/contracts/backend_coverage_full_declaration.json",
            encoding="utf-8",
        ).read()
    )
    declaration["backend"] = "totally-fake-backend"
    declaration_path = tmp_path / "fake-backend-declaration.json"
    declaration_path.write_text(json.dumps(declaration), encoding="utf-8")

    result = main(
        [
            "backend-coverage",
            "--requirements",
            "examples/native/contracts/backend_readiness_expected.json",
            "--coverage-declaration",
            str(declaration_path),
        ]
    )

    captured = capsys.readouterr()
    assert result == 1
    assert "backend-coverage totally-fake-backend" in captured.out
    assert "status: failed" in captured.out
    assert "evidence malformed by blocker: backendIdentity=1" in captured.out
    assert (
        "evidence error: coverage declaration backend must match "
        "readiness.candidate.backend"
    ) in captured.out
    assert "blockers: backendIdentity" in captured.out


def test_cli_backend_coverage_reports_partial_profile_gaps(capsys):
    result = main(
        [
            "backend-coverage",
            "--requirements",
            "examples/native/contracts/backend_readiness_expected.json",
            "--backend-capability-profile",
            "examples/native/contracts/backend_candidate_partial_profile.json",
        ]
    )

    captured = capsys.readouterr()
    assert result == 1
    assert "backend-coverage partial-backend-candidate" in captured.out
    assert "status: failed" in captured.out
    assert (
        "rendererBoundaries: covered=0/2, missing=2, unproven=0"
        in captured.out
    )
    assert "rendererBoundaries missing: paint, renderTreeLayout" in captured.out
    assert "widgets: covered=8/11, missing=3, unproven=0" in captured.out
    assert "widgets missing: Button, FocusScope, Panel" in captured.out
    assert "inputs missing: focus, key_down, key_input, tab_focus" in captured.out
    assert (
        "styles missing: background, borderColor, borderRadius, borderWidth, "
        "color, fontSize, maxHeight, maxWidth, minHeight, minWidth"
        in captured.out
    )
    assert (
        "declaredStyleOmissions missing: display, fontWeight, margin, opacity"
        in captured.out
    )
    assert (
        "blockers: backendIdentity, rendererBoundariesCoverage, "
        "widgetsCoverage, inputsCoverage, stylesCoverage, "
        "declaredStyleOmissionsCoverage"
        in captured.out
    )


def test_cli_backend_coverage_rejects_requirements_without_evidence(tmp_path, capsys):
    readiness = json.loads(
        open(
            "examples/native/contracts/backend_readiness_expected.json",
            encoding="utf-8",
        ).read()
    )
    requirements_path = tmp_path / "requirements-only.json"
    requirements_path.write_text(
        json.dumps(readiness["requirements"]),
        encoding="utf-8",
    )

    result = main(
        [
            "backend-coverage",
            "--requirements",
            str(requirements_path),
            "--backend",
            "native-python",
            "--json",
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert result == 1
    assert payload["passed"] is False
    assert payload["readiness"]["strictEvidence"] is True
    assert payload["readiness"]["evidenceBlockers"] == ["capabilityEvidence"]
    assert payload["readiness"]["evidenceSummary"] == {
        "malformed": 1,
        "malformedByBlocker": {
            "capabilityEvidence": 1,
        },
    }
    assert payload["coverage"]["widgets"]["exercised"] == []
    assert payload["coverage"]["widgets"]["summary"]["unproven"] == 11
    assert "capabilityEvidence" in payload["blockers"]
    assert "widgetsEvidence" in payload["blockers"]


def test_cli_backend_coverage_rejects_audit_with_json_or_out(tmp_path, capsys):
    out = tmp_path / "coverage.json"

    json_result = main(
        [
            "backend-coverage",
            "--requirements",
            "examples/native/contracts/backend_readiness_expected.json",
            "--backend",
            "native-python",
            "--audit",
            "--json",
        ]
    )
    out_result = main(
        [
            "backend-coverage",
            "--requirements",
            "examples/native/contracts/backend_readiness_expected.json",
            "--backend",
            "native-python",
            "--audit",
            "--out",
            str(out),
        ]
    )

    captured = capsys.readouterr()
    assert json_result == 1
    assert out_result == 1
    assert not out.exists()
    assert captured.err.count("--audit cannot be combined with --json or --out") == 2


def test_cli_backend_coverage_accepts_explicit_declaration(capsys):
    result = main(
        [
            "backend-coverage",
            "--requirements",
            "examples/native/contracts/backend_readiness_expected.json",
            "--coverage-declaration",
            "examples/native/contracts/backend_coverage_full_declaration.json",
            "--json",
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert result == 0
    assert payload["backend"] == "native-python"
    assert payload["passed"] is True
    assert payload["blockers"] == []
    assert payload["declarationErrors"] == []


def test_cli_backend_coverage_writes_report_artifact(tmp_path, capsys):
    output = tmp_path / "backend-coverage.json"

    result = main(
        [
            "backend-coverage",
            "--requirements",
            "examples/native/contracts/backend_readiness_expected.json",
            "--backend",
            "native-python",
            "--out",
            str(output),
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert result == 0
    assert captured.out == f"backend coverage artifact: {output}\n"
    assert payload["backend"] == "native-python"
    assert payload["passed"] is True
    assert payload["blockers"] == []


def test_cli_backend_coverage_rejects_multiple_coverage_sources(capsys):
    result = main(
        [
            "backend-coverage",
            "--requirements",
            "examples/native/contracts/backend_readiness_expected.json",
            "--backend",
            "native-python",
            "--coverage-declaration",
            "examples/native/contracts/backend_coverage_full_declaration.json",
        ]
    )

    captured = capsys.readouterr()
    assert result == 1
    assert (
        "--coverage-declaration, --backend, and --backend-capability-profile "
        "are mutually exclusive"
        in captured.err
    )


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


def test_cli_plan_static_class_scan_ignores_condition_literals(
    tmp_path,
    monkeypatch,
    capsys,
):
    module = tmp_path / "conditional_class_plan_surface.py"
    module.write_text(
        "from otoe import Text, class_names, computed, signal\n"
        "theme = signal('light')\n"
        "def app():\n"
        "    state_class = computed(\n"
        "        lambda: class_names(\n"
        "            'status',\n"
        "            'is-dark' if theme.value == 'dark' else 'is-light',\n"
        "        )\n"
        "    )\n"
        "    return Text('State', className=state_class)\n",
        encoding="utf-8",
    )
    styles = tmp_path / "styles.css"
    styles.write_text(
        ".status { color: #111827; }\n"
        ".is-light { background: #ffffff; }\n"
        ".is-dark { background: #000000; }\n",
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "plan",
            "conditional_class_plan_surface:app",
            "--css",
            str(styles),
            "--json",
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert result == 0
    assert payload["classes"]["used"] == ["status", "is-light"]
    assert payload["classes"]["static"] == ["is-dark"]
    assert payload["classes"]["planned"] == ["status", "is-light", "is-dark"]
    assert payload["diagnostics"] == []


def test_cli_plan_safelists_matching_ui_dynamic_classes(
    tmp_path,
    monkeypatch,
    capsys,
):
    module = tmp_path / "ui_dynamic_class_plan_surface.py"
    module.write_text(
        "from otoe import Badge, signal\n"
        "tone = signal('neutral')\n"
        "def app():\n"
        "    return Badge('State', tone=tone)\n",
        encoding="utf-8",
    )
    styles = tmp_path / "styles.css"
    styles.write_text(
        ".ui-badge { padding: 4; }\n"
        ".is-neutral { background: #ffffff; }\n"
        ".is-success { background: #dcfce7; }\n",
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "plan",
            "ui_dynamic_class_plan_surface:app",
            "--css",
            str(styles),
            "--json",
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert result == 0
    assert payload["classes"]["used"] == ["ui-badge", "is-neutral"]
    assert payload["classes"]["static"] == ["is-success"]
    assert payload["classes"]["safelisted"] == []
    assert payload["classes"]["planned"] == [
        "ui-badge",
        "is-neutral",
        "is-success",
    ]
    assert payload["diagnostics"] == []


def test_cli_plan_does_not_safelist_missing_ui_dynamic_rules(
    tmp_path,
    monkeypatch,
    capsys,
):
    module = tmp_path / "ui_dynamic_missing_rule_plan_surface.py"
    module.write_text(
        "from otoe import Badge, signal\n"
        "tone = signal('neutral')\n"
        "def app():\n"
        "    return Badge('State', tone=tone)\n",
        encoding="utf-8",
    )
    styles = tmp_path / "styles.css"
    styles.write_text(
        ".ui-badge { padding: 4; }\n"
        ".is-neutral { background: #ffffff; }\n",
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "plan",
            "ui_dynamic_missing_rule_plan_surface:app",
            "--css",
            str(styles),
            "--json",
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert result == 0
    assert payload["classes"]["used"] == ["ui-badge", "is-neutral"]
    assert payload["classes"]["static"] == []
    assert payload["classes"]["planned"] == ["ui-badge", "is-neutral"]
    assert payload["diagnostics"] == []


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


def test_cli_plan_loads_backend_capability_from_profile(
    tmp_path,
    monkeypatch,
    capsys,
):
    module = tmp_path / "profile_backend_capability_surface.py"
    module.write_text(
        "from otoe import Text\n"
        "app = Text('Profile', className='custom')\n",
        encoding="utf-8",
    )
    styles = tmp_path / "styles.css"
    styles.write_text(".custom { color: #172033; }\n", encoding="utf-8")
    profile_file = tmp_path / "otoe.profile.toml"
    profile_file.write_text(
        'profile = "cage"\n'
        'css = ["styles.css"]\n'
        "\n"
        "[backend]\n"
        'name = "native"\n'
        'capability = "native"\n',
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "plan",
            "profile_backend_capability_surface:app",
            "--profile-file",
            str(profile_file),
            "--json",
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert result == 0
    assert payload["backend"] == "native-python"


def test_cli_plan_loads_backend_capability_profile_from_profile_file(
    tmp_path,
    monkeypatch,
    capsys,
):
    module = tmp_path / "profile_backend_capability_json_surface.py"
    module.write_text(
        "from otoe import Text, VStack\n"
        "app = VStack(Text('Profile JSON'), className='shell')\n",
        encoding="utf-8",
    )
    styles = tmp_path / "styles.css"
    styles.write_text(".shell { padding: 8; }\n", encoding="utf-8")
    profile_json = tmp_path / "candidate-profile.json"
    _write_backend_capability_profile(
        profile_json,
        name="candidate-profile-file",
        styles={"padding": "layout"},
        widgets={"Text": "text", "VStack": "container"},
    )
    profile_file = tmp_path / "otoe.profile.toml"
    profile_file.write_text(
        'profile = "cage"\n'
        'css = ["styles.css"]\n'
        "\n"
        "[backend]\n"
        'name = "native"\n'
        'capability_profile = "candidate-profile.json"\n',
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "plan",
            "profile_backend_capability_json_surface:app",
            "--profile-file",
            str(profile_file),
            "--json",
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert result == 0
    assert payload["backend"] == "candidate-profile-file"
    assert payload["backendCapabilities"]["styles"] == {"padding": "layout"}


def test_cli_plan_reports_backend_coverage_from_profile_file(
    tmp_path,
    monkeypatch,
    capsys,
):
    module = tmp_path / "profile_backend_coverage_surface.py"
    module.write_text(
        "from otoe import Text\n"
        "app = Text('Coverage profile')\n",
        encoding="utf-8",
    )
    requirements = tmp_path / "backend-requirements.json"
    _write_backend_coverage_requirements(requirements)
    profile_file = tmp_path / "otoe.profile.toml"
    profile_file.write_text(
        'profile = "cage"\n'
        "\n"
        "[backend]\n"
        'name = "native"\n'
        'coverage_requirements = "backend-requirements.json"\n',
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "plan",
            "profile_backend_coverage_surface:app",
            "--profile-file",
            str(profile_file),
            "--json",
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert result == 0
    assert payload["backendCoverage"]["backend"] == "native-python"
    assert payload["backendCoverage"]["passed"] is True
    assert payload["backendCoverage"]["blockers"] == []


def test_cli_plan_fails_when_backend_coverage_is_incomplete(
    tmp_path,
    monkeypatch,
    capsys,
):
    module = tmp_path / "profile_backend_coverage_failure_surface.py"
    module.write_text(
        "from otoe import Text\n"
        "app = Text('Coverage failure')\n",
        encoding="utf-8",
    )
    requirements = tmp_path / "backend-requirements.json"
    _write_backend_coverage_requirements(requirements, widgets=("Text", "Button"))
    profile_json = tmp_path / "candidate-profile.json"
    _write_backend_capability_profile(
        profile_json,
        name="candidate-coverage-failure",
        widgets={"Text": "text"},
    )
    profile_file = tmp_path / "otoe.profile.toml"
    profile_file.write_text(
        'profile = "cage"\n'
        "\n"
        "[backend]\n"
        'name = "native"\n'
        'capability_profile = "candidate-profile.json"\n'
        'coverage_requirements = "backend-requirements.json"\n',
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "plan",
            "profile_backend_coverage_failure_surface:app",
            "--profile-file",
            str(profile_file),
            "--json",
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert result == 1
    assert payload["status"] == "ok"
    assert payload["backendCoverage"]["passed"] is False
    assert "widgetsCoverage" in payload["backendCoverage"]["blockers"]
    assert payload["backendCoverage"]["coverage"]["widgets"]["missing"] == ["Button"]


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
    assert f"render tree artifact: {output / 'otoe-render-tree.json'}" in captured.out
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
        {
            "path": "otoe-render-tree.json",
            "size": (output / "otoe-render-tree.json").stat().st_size,
            "sha256": hashlib.sha256(
                (output / "otoe-render-tree.json").read_bytes()
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
    assert {
        "source": "otoe/style_ops.py",
        "bundlePath": "framework/otoe/style_ops.py",
        "size": (output / "framework" / "otoe" / "style_ops.py").stat().st_size,
        "sha256": hashlib.sha256(
            (output / "framework" / "otoe" / "style_ops.py").read_bytes()
        ).hexdigest(),
    } in framework_files
    assert {
        "source": "otoe/bundle_backend_coverage.py",
        "bundlePath": "framework/otoe/bundle_backend_coverage.py",
        "size": (
            output / "framework" / "otoe" / "bundle_backend_coverage.py"
        ).stat().st_size,
        "sha256": hashlib.sha256(
            (output / "framework" / "otoe" / "bundle_backend_coverage.py").read_bytes()
        ).hexdigest(),
    } in framework_files
    assert {
        "source": "otoe/bundle_backend_package.py",
        "bundlePath": "framework/otoe/bundle_backend_package.py",
        "size": (
            output / "framework" / "otoe" / "bundle_backend_package.py"
        ).stat().st_size,
        "sha256": hashlib.sha256(
            (output / "framework" / "otoe" / "bundle_backend_package.py").read_bytes()
        ).hexdigest(),
    } in framework_files
    assert {
        "source": "otoe/bundle_deps.py",
        "bundlePath": "framework/otoe/bundle_deps.py",
        "size": (output / "framework" / "otoe" / "bundle_deps.py").stat().st_size,
        "sha256": hashlib.sha256(
            (output / "framework" / "otoe" / "bundle_deps.py").read_bytes()
        ).hexdigest(),
    } in framework_files
    assert {
        "source": "otoe/_render_identity.py",
        "bundlePath": "framework/otoe/_render_identity.py",
        "size": (
            output / "framework" / "otoe" / "_render_identity.py"
        ).stat().st_size,
        "sha256": hashlib.sha256(
            (output / "framework" / "otoe" / "_render_identity.py").read_bytes()
        ).hexdigest(),
    } in framework_files
    assert not (output / "framework" / "otoe" / "build.py").exists()
    assert runner == {
        "path": "otoe-run.py",
        "pythonPath": ["app", "framework"],
        "modes": [
            "backend-package-check",
            "check",
            "external-backend-check",
            "layout-check",
            "png",
            "verify",
        ],
        "size": (output / "otoe-run.py").stat().st_size,
        "sha256": hashlib.sha256((output / "otoe-run.py").read_bytes()).hexdigest(),
    }
    assert manifest == {
        "schemaVersion": 1,
        "target": "build_surface:app",
        "profile": "cage",
        "backend": "native",
        "backendCapability": "native-python",
        "runtimeInstallsAllowed": False,
        "plan": "otoe-plan.json",
        "deps": "otoe-deps.json",
        "styles": "otoe-styles.json",
        "renderTree": "otoe-render-tree.json",
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


def test_cli_build_uses_backend_capability_profile_json(
    tmp_path,
    monkeypatch,
    capsys,
):
    module = tmp_path / "build_backend_profile_surface.py"
    module.write_text(
        "from otoe import Text, VStack\n"
        "app = VStack(Text('Build profile'), className='shell')\n",
        encoding="utf-8",
    )
    styles = tmp_path / "styles.css"
    styles.write_text(
        ".shell { padding: 8; background: #ffffff; }\n",
        encoding="utf-8",
    )
    backend_profile = tmp_path / "candidate-profile.json"
    _write_backend_capability_profile(
        backend_profile,
        name="candidate-build",
        styles={"background": "paint", "padding": "layout"},
        widgets={"Text": "text", "VStack": "container"},
    )
    output = tmp_path / "dist" / "candidate-build"
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "build",
            "build_backend_profile_surface:app",
            "--css",
            str(styles),
            "--backend-capability-profile",
            str(backend_profile),
            "--out",
            str(output),
        ]
    )

    capsys.readouterr()
    plan = json.loads((output / "otoe-plan.json").read_text(encoding="utf-8"))
    styles_payload = json.loads(
        (output / "otoe-styles.json").read_text(encoding="utf-8")
    )
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    assert result == 0
    assert plan["backend"] == "candidate-build"
    assert plan["backendCapabilities"]["styles"] == {
        "background": "paint",
        "padding": "layout",
    }
    assert styles_payload["backend"] == "candidate-build"
    assert styles_payload["styleOps"]["backend"] == "candidate-build"
    assert styles_payload["styleOps"]["capabilities"]["styles"] == {
        "background": "paint",
        "padding": "layout",
    }
    assert manifest["backendCapability"] == "candidate-build"


def test_cli_build_writes_backend_coverage_artifact_from_profile_file(
    tmp_path,
    monkeypatch,
    capsys,
):
    module = tmp_path / "build_backend_coverage_surface.py"
    module.write_text(
        "from otoe import Text\n"
        "app = Text('Build coverage')\n",
        encoding="utf-8",
    )
    requirements = tmp_path / "backend-requirements.json"
    _write_backend_coverage_requirements(requirements)
    profile_file = tmp_path / "otoe.profile.toml"
    profile_file.write_text(
        'profile = "cage"\n'
        "\n"
        "[backend]\n"
        'name = "native"\n'
        'coverage_requirements = "backend-requirements.json"\n',
        encoding="utf-8",
    )
    output = tmp_path / "dist" / "coverage"
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "build",
            "build_backend_coverage_surface:app",
            "--profile-file",
            str(profile_file),
            "--out",
            str(output),
        ]
    )

    captured = capsys.readouterr()
    coverage_path = output / "otoe-backend-coverage.json"
    coverage = json.loads(coverage_path.read_text(encoding="utf-8"))
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    assert result == 0
    assert f"backend coverage artifact: {coverage_path}" in captured.out
    assert coverage["passed"] is True
    assert coverage["trace"] == {
        "candidateScope": {
            "level": "path0-render-tree-ir-v0",
        },
        "path0": {
            "renderTreeHash": _backend_coverage_test_hash("test-render-tree"),
            "layoutOutputHash": coverage["coverage"]["rendererBoundaries"][
                "evidenceMap"
            ]["renderTreeLayout"]["sources"][0]["boundaryProof"]["outputHash"],
            "paintOutputHash": coverage["coverage"]["rendererBoundaries"][
                "evidenceMap"
            ]["paint"]["sources"][0]["boundaryProof"]["outputHash"],
            "semanticValidation": {
                "passed": True,
                "errors": [],
            },
        },
    }
    assert manifest["backendCoverage"] == "otoe-backend-coverage.json"
    assert {
        "path": "otoe-backend-coverage.json",
        "size": coverage_path.stat().st_size,
        "sha256": hashlib.sha256(coverage_path.read_bytes()).hexdigest(),
    } in manifest["artifacts"]


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


def test_cli_build_validate_accepts_relative_output_path(
    tmp_path,
    monkeypatch,
    capsys,
):
    app = tmp_path / "relative_build_app.py"
    app.write_text(
        "from otoe import Text\n"
        "app = Text('Relative build')\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "build",
            "relative_build_app:app",
            "--out",
            "dist/cage",
            "--validate",
        ]
    )

    captured = capsys.readouterr()
    assert result == 0
    assert "validation: ok" in captured.out
    assert (tmp_path / "dist" / "cage" / "otoe-run.py").exists()
    assert (tmp_path / "dist" / "cage" / "manifest.json").exists()


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


def test_cli_build_runner_rejects_bad_direct_style_ops_shape(
    tmp_path,
    monkeypatch,
):
    app = tmp_path / "bad_direct_style_ops_app.py"
    app.write_text(
        "from otoe import Text, VStack\n"
        "app = VStack(Text('Direct styles'), padding=8)\n",
        encoding="utf-8",
    )
    profile_file = tmp_path / "otoe.profile.toml"
    profile_file.write_text(
        'profile = "cage"\n'
        "\n"
        "[runtime]\n"
        'files = ["bad_direct_style_ops_app.py"]\n',
        encoding="utf-8",
    )
    output = tmp_path / "dist" / "bad-direct-style-ops"
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "build",
            "bad_direct_style_ops_app:app",
            "--profile-file",
            str(profile_file),
            "--out",
            str(output),
            "--validate",
        ]
    )
    styles_path = output / "otoe-styles.json"
    styles = json.loads(styles_path.read_text(encoding="utf-8"))
    styles["styleOps"]["directStyles"] = {}
    styles_path.write_text(json.dumps(styles), encoding="utf-8")

    verify = subprocess.run(
        [sys.executable, str(output / "otoe-run.py"), "--verify"],
        capture_output=True,
        cwd=output,
        env={**os.environ, "PYTHONPATH": ""},
        text=True,
    )

    assert result == 0
    assert verify.returncode == 1
    assert "otoe-styles.json: styleOps directStyles must be a list" in verify.stderr


def test_cli_style_ir_inspects_compiled_artifact(tmp_path, monkeypatch, capsys):
    app = tmp_path / "style_ir_inspect_app.py"
    app.write_text(
        "from otoe import Text, VStack\n"
        "app = VStack(Text('Inspect'), className='shell', gap=4, padding=8)\n",
        encoding="utf-8",
    )
    styles = tmp_path / "styles.css"
    styles.write_text(".shell { color: #111827; }\n", encoding="utf-8")
    profile_file = tmp_path / "otoe.profile.toml"
    profile_file.write_text(
        'profile = "cage"\n'
        'css = ["styles.css"]\n'
        "\n"
        "[runtime]\n"
        'files = ["style_ir_inspect_app.py"]\n',
        encoding="utf-8",
    )
    output = tmp_path / "dist" / "style-ir-inspect"
    monkeypatch.syspath_prepend(str(tmp_path))

    build_result = main(
        [
            "build",
            "style_ir_inspect_app:app",
            "--profile-file",
            str(profile_file),
            "--out",
            str(output),
        ]
    )
    capsys.readouterr()

    styles_path = output / "otoe-styles.json"
    summary_result = main(["style-ir", str(styles_path)])
    summary = capsys.readouterr()
    json_result = main(["style-ir", str(styles_path), "--json"])
    captured_json = capsys.readouterr()
    payload = json.loads(captured_json.out)

    assert build_result == 0
    assert summary_result == 0
    assert f"style-ir {styles_path}" in summary.out
    assert "styleOps: schema=1 format=otoe-style-ops passed" in summary.out
    assert "classes: 1 rules, 1 primitive entries" in summary.out
    assert "direct styles: 1 entries, 1 primitive entries" in summary.out
    assert "errors: none" in summary.out
    assert json_result == 0
    assert payload["passed"] is True
    assert payload["target"] == "style_ir_inspect_app:app"
    assert payload["counts"] == {
        "rules": 1,
        "classOps": 1,
        "directStyles": 1,
        "directStyleOps": 1,
        "errors": 0,
    }
    assert payload["classes"][0]["appliedDeclarations"]["color"] == {
        "type": "literal",
        "value": "#111827",
    }
    assert payload["directStyles"][0]["appliedDeclarations"] == {
        "gap": {"type": "size", "value": 4, "unit": "px"},
        "padding": {"type": "size", "value": 8, "unit": "px"},
    }


def test_cli_style_ir_strict_detects_style_ops_drift(tmp_path, monkeypatch, capsys):
    app = tmp_path / "style_ir_strict_app.py"
    app.write_text(
        "from otoe import Text\n"
        "app = Text('Strict', className='shell')\n",
        encoding="utf-8",
    )
    styles = tmp_path / "styles.css"
    styles.write_text(".shell { color: #111827; }\n", encoding="utf-8")
    profile_file = tmp_path / "otoe.profile.toml"
    profile_file.write_text(
        'profile = "cage"\n'
        'css = ["styles.css"]\n'
        "\n"
        "[runtime]\n"
        'files = ["style_ir_strict_app.py"]\n',
        encoding="utf-8",
    )
    output = tmp_path / "dist" / "style-ir-strict"
    monkeypatch.syspath_prepend(str(tmp_path))

    build_result = main(
        [
            "build",
            "style_ir_strict_app:app",
            "--profile-file",
            str(profile_file),
            "--out",
            str(output),
        ]
    )
    capsys.readouterr()

    styles_path = output / "otoe-styles.json"
    payload = json.loads(styles_path.read_text(encoding="utf-8"))
    payload["styleOps"]["classes"][0]["ops"][0]["value"] = {
        "type": "literal",
        "value": "#dc2626",
    }
    styles_path.write_text(json.dumps(payload), encoding="utf-8")

    loose_result = main(["style-ir", str(styles_path)])
    loose = capsys.readouterr()
    strict_result = main(["style-ir", str(styles_path), "--strict", "--json"])
    strict = capsys.readouterr()
    strict_payload = json.loads(strict.out)

    assert build_result == 0
    assert loose_result == 0
    assert "errors: none" in loose.out
    assert strict_result == 1
    assert strict_payload["passed"] is False
    assert strict_payload["strict"]["enabled"] is True
    assert strict_payload["strict"]["passed"] is False
    assert (
        "styleOps class 'shell' applied declarations do not match compiled rules"
        in strict_payload["strict"]["errors"]
    )


def test_cli_style_ir_rejects_invalid_artifact(tmp_path, capsys):
    artifact = tmp_path / "bad-otoe-styles.json"
    artifact.write_text('{"schemaVersion": 2}\n', encoding="utf-8")

    result = main(["style-ir", str(artifact)])

    captured = capsys.readouterr()
    assert result == 1
    assert (
        "style-ir: style artifact: unsupported schemaVersion 2; expected 1"
        in captured.err
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
    assert styles_payload["backend"] == "native-python"
    assert styles_payload["backendCapabilities"]["styles"]["width"] == "layout"
    assert styles_payload["styleOps"]["backend"] == "native-python"
    assert styles_payload["styleOps"]["capabilities"]["styles"]["width"] == "layout"
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


def test_cli_build_safelists_reactive_ui_variant_classes(tmp_path, monkeypatch):
    app = tmp_path / "ui_variant_safelist_bundle_app.py"
    app.write_text(
        "from otoe import Badge, signal\n"
        "tone = signal('neutral')\n"
        "app = Badge('Health', tone=tone)\n",
        encoding="utf-8",
    )
    styles = tmp_path / "styles.css"
    styles.write_text(
        ".ui-badge { color: #111827; }\n"
        ".is-neutral { background: #f8fafc; }\n"
        ".is-success { background: #dcfce7; }\n",
        encoding="utf-8",
    )
    profile_file = tmp_path / "otoe.profile.toml"
    profile_file.write_text(
        'profile = "cage"\n'
        'css = ["styles.css"]\n'
        "\n"
        "[styles]\n"
        'safelist = ["is-success"]\n'
        "\n"
        "[runtime]\n"
        'files = ["ui_variant_safelist_bundle_app.py"]\n',
        encoding="utf-8",
    )
    output = tmp_path / "dist" / "ui-variant-safelist"
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "build",
            "ui_variant_safelist_bundle_app:app",
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
    assert styles_payload["classes"]["used"] == ["ui-badge", "is-neutral"]
    assert styles_payload["classes"]["static"] == []
    assert styles_payload["classes"]["safelisted"] == ["is-success"]
    assert styles_payload["classes"]["planned"] == [
        "ui-badge",
        "is-neutral",
        "is-success",
    ]
    assert rules["is-success"]["declarations"]["background"] == {
        "type": "literal",
        "value": "#dcfce7",
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
            "directStyles": [],
            "styleOps": {
                "schemaVersion": 1,
                "format": "otoe-style-ops",
                "capabilities": {"styles": {"fontSize": "layout"}},
                "classes": [
                    {
                        "className": "text-sm",
                        "selector": ".text-sm",
                        "missing": False,
                        "ops": [
                            {
                                "op": "setStyle",
                                "property": "fontSize",
                                "support": "layout",
                                "value": {"type": "literal", "value": "large"},
                            }
                        ],
                        "omittedOps": [],
                    }
                ],
                "directStyles": [],
            },
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


def test_cli_pack_rejects_unmanifested_packable_files(
    tmp_path,
    monkeypatch,
    capsys,
):
    app = tmp_path / "hermetic_pack_app.py"
    app.write_text(
        "from otoe import Text\n"
        "app = Text('Hermetic pack')\n",
        encoding="utf-8",
    )
    profile_file = tmp_path / "otoe.profile.toml"
    profile_file.write_text(
        'profile = "cage"\n'
        "\n"
        "[runtime]\n"
        'files = ["hermetic_pack_app.py"]\n'
        "\n",
        encoding="utf-8",
    )
    output = tmp_path / "dist" / "hermetic-pack"
    archive = tmp_path / "dist" / "hermetic-pack.tar.gz"
    monkeypatch.syspath_prepend(str(tmp_path))

    assert (
        main(
            [
                "build",
                "hermetic_pack_app:app",
                "--profile-file",
                str(profile_file),
                "--out",
                str(output),
                "--validate",
            ]
        )
        == 0
    )
    capsys.readouterr()

    extras = (
        output / "app" / "debug.py",
        output / "assets" / "secret.txt",
        output / "framework" / "otoe" / "old_runtime.py",
    )
    for extra in extras:
        extra.parent.mkdir(parents=True, exist_ok=True)
        extra.write_text("extra\n", encoding="utf-8")

        verify = subprocess.run(
            [sys.executable, str(output / "otoe-run.py"), "--verify"],
            capture_output=True,
            cwd=output,
            env={**os.environ, "PYTHONPATH": ""},
            text=True,
        )
        result = main(["pack", str(output), "--out", str(archive)])

        captured = capsys.readouterr()
        assert verify.returncode == 1
        assert f"unmanifested bundle file '{extra.relative_to(output)}'" in (
            verify.stderr
        )
        assert result == 1
        assert f"pack: unmanifested bundle file '{extra.relative_to(output)}'" in (
            captured.err
        )
        assert not archive.exists()
        extra.unlink()


def test_cli_pack_includes_backend_coverage_artifact(
    tmp_path,
    monkeypatch,
    capsys,
):
    app = tmp_path / "packed_backend_coverage_app.py"
    app.write_text(
        "from otoe import Text\n"
        "app = Text('Packed coverage app')\n",
        encoding="utf-8",
    )
    requirements = tmp_path / "backend-requirements.json"
    _write_backend_coverage_requirements(requirements)
    profile_file = tmp_path / "otoe.profile.toml"
    profile_file.write_text(
        'profile = "cage"\n'
        "\n"
        "[runtime]\n"
        'files = ["packed_backend_coverage_app.py"]\n'
        "\n"
        "[backend]\n"
        'coverage_requirements = "backend-requirements.json"\n',
        encoding="utf-8",
    )
    output = tmp_path / "dist" / "pack-backend-coverage"
    archive = tmp_path / "dist" / "pack-backend-coverage.tar.gz"
    extracted = tmp_path / "extracted-backend-coverage"
    monkeypatch.syspath_prepend(str(tmp_path))

    assert (
        main(
            [
                "build",
                "packed_backend_coverage_app:app",
                "--profile-file",
                str(profile_file),
                "--out",
                str(output),
                "--validate",
            ]
        )
        == 0
    )

    result = main(["pack", str(output), "--out", str(archive)])

    capsys.readouterr()
    assert result == 0
    with tarfile.open(archive, "r:gz") as tar:
        names = tar.getnames()
        for member in tar.getmembers():
            target = extracted / member.name
            target.parent.mkdir(parents=True, exist_ok=True)
            source = tar.extractfile(member)
            assert source is not None
            target.write_bytes(source.read())

    assert "otoe-backend-coverage.json" in names
    verify = subprocess.run(
        [sys.executable, str(extracted / "otoe-run.py"), "--verify"],
        capture_output=True,
        cwd=extracted,
        env={**os.environ, "PYTHONPATH": ""},
        text=True,
    )
    assert verify.returncode == 0, verify.stderr
    assert "verified: manifest.json" in verify.stdout


def test_cli_build_runner_requires_core_artifacts_in_manifest_artifacts(
    tmp_path,
    monkeypatch,
    capsys,
):
    app = tmp_path / "missing_core_artifact_entry_app.py"
    app.write_text(
        "from otoe import Text\n"
        "app = Text('Missing core artifact entry')\n",
        encoding="utf-8",
    )
    output = tmp_path / "dist" / "missing-core-artifact-entry"
    archive = tmp_path / "dist" / "missing-core-artifact-entry.tar.gz"
    monkeypatch.syspath_prepend(str(tmp_path))

    assert (
        main(
            [
                "build",
                "missing_core_artifact_entry_app:app",
                "--out",
                str(output),
            ]
        )
        == 0
    )
    manifest_path = output / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["artifacts"] = [
        artifact
        for artifact in manifest["artifacts"]
        if artifact["path"] != "otoe-plan.json"
    ]
    manifest_path.write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")

    verify = subprocess.run(
        [sys.executable, str(output / "otoe-run.py"), "--verify"],
        capture_output=True,
        cwd=output,
        env={**os.environ, "PYTHONPATH": ""},
        text=True,
    )
    check = subprocess.run(
        [sys.executable, str(output / "otoe-run.py"), "--check"],
        capture_output=True,
        cwd=output,
        env={**os.environ, "PYTHONPATH": ""},
        text=True,
    )
    result = main(["pack", str(output), "--out", str(archive)])

    captured = capsys.readouterr()
    assert verify.returncode == 1
    assert "manifest.json: artifacts missing 'otoe-plan.json'" in verify.stderr
    assert check.returncode == 1
    assert "manifest.json: artifacts missing 'otoe-plan.json'" in check.stderr
    assert result == 1
    assert "pack: runner verification failed:" in captured.err
    assert "artifacts missing 'otoe-plan.json'" in captured.err


def test_cli_build_runner_requires_manifest_file_entry_hashes(
    tmp_path,
    monkeypatch,
    capsys,
):
    app = tmp_path / "missing_manifest_hash_app.py"
    app.write_text(
        "from otoe import Text\n"
        "app = Text('Missing manifest hash')\n",
        encoding="utf-8",
    )
    output = tmp_path / "dist" / "missing-manifest-hash"
    archive = tmp_path / "dist" / "missing-manifest-hash.tar.gz"
    monkeypatch.syspath_prepend(str(tmp_path))

    assert (
        main(
            [
                "build",
                "missing_manifest_hash_app:app",
                "--out",
                str(output),
            ]
        )
        == 0
    )
    manifest_path = output / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    del manifest["runtimeFiles"][0]["sha256"]
    manifest_path.write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")

    verify = subprocess.run(
        [sys.executable, str(output / "otoe-run.py"), "--verify"],
        capture_output=True,
        cwd=output,
        env={**os.environ, "PYTHONPATH": ""},
        text=True,
    )
    result = main(["pack", str(output), "--out", str(archive)])

    captured = capsys.readouterr()
    assert verify.returncode == 1
    assert (
        "manifest.json: runtimeFiles[0].sha256 must be a lowercase sha256 hex digest"
        in verify.stderr
    )
    assert result == 1
    assert "pack: runner verification failed:" in captured.err
    assert "runtimeFiles[0].sha256 must be a lowercase sha256 hex digest" in (
        captured.err
    )
    assert not archive.exists()


def test_cli_build_runner_rejects_duplicate_manifest_bundle_paths(
    tmp_path,
    monkeypatch,
    capsys,
):
    app = tmp_path / "duplicate_manifest_path_app.py"
    app.write_text(
        "from otoe import Text\n"
        "app = Text('Duplicate manifest path')\n",
        encoding="utf-8",
    )
    output = tmp_path / "dist" / "duplicate-manifest-path"
    archive = tmp_path / "dist" / "duplicate-manifest-path.tar.gz"
    monkeypatch.syspath_prepend(str(tmp_path))

    assert (
        main(
            [
                "build",
                "duplicate_manifest_path_app:app",
                "--out",
                str(output),
            ]
        )
        == 0
    )
    manifest_path = output / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["runtimeFiles"].append(dict(manifest["runtimeFiles"][0]))
    manifest_path.write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")

    verify = subprocess.run(
        [sys.executable, str(output / "otoe-run.py"), "--verify"],
        capture_output=True,
        cwd=output,
        env={**os.environ, "PYTHONPATH": ""},
        text=True,
    )
    result = main(["pack", str(output), "--out", str(archive)])

    captured = capsys.readouterr()
    assert verify.returncode == 1
    assert (
        "manifest.json: duplicate bundle path "
        "'app/duplicate_manifest_path_app.py' in runtimeFiles[1].bundlePath; "
        "already declared by runtimeFiles[0].bundlePath"
    ) in verify.stderr
    assert result == 1
    assert "pack: runner verification failed:" in captured.err
    assert "duplicate bundle path 'app/duplicate_manifest_path_app.py'" in (
        captured.err
    )
    assert not archive.exists()


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


def test_cli_pack_rejects_invalid_plan_after_hash_update(
    tmp_path,
    monkeypatch,
    capsys,
):
    app = tmp_path / "invalid_plan_drift_pack_app.py"
    app.write_text(
        "from otoe import Text\n"
        "app = Text('Invalid plan drift')\n",
        encoding="utf-8",
    )
    output = tmp_path / "dist" / "invalid-plan-drift-pack"
    archive = tmp_path / "dist" / "invalid-plan-drift-pack.tar.gz"
    monkeypatch.syspath_prepend(str(tmp_path))

    assert (
        main(
            [
                "build",
                "invalid_plan_drift_pack_app:app",
                "--out",
                str(output),
            ]
        )
        == 0
    )
    capsys.readouterr()

    plan_path = output / "otoe-plan.json"
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    plan["hasErrors"] = True
    plan["status"] = "invalid"
    plan_path.write_text(json.dumps(plan, sort_keys=True), encoding="utf-8")
    _refresh_manifest_artifact_hash(output, "otoe-plan.json")

    verify = subprocess.run(
        [sys.executable, str(output / "otoe-run.py"), "--verify"],
        capture_output=True,
        cwd=output,
        env={**os.environ, "PYTHONPATH": ""},
        text=True,
    )
    result = main(["pack", str(output), "--out", str(archive)])

    captured = capsys.readouterr()
    assert verify.returncode == 1
    assert "otoe-plan.json: plan has errors" in verify.stderr
    assert result == 1
    assert not archive.exists()
    assert "pack: runner verification failed:" in captured.err
    assert "otoe-plan.json: plan has errors" in captured.err


def test_cli_pack_rejects_invalid_deps_after_hash_update(
    tmp_path,
    monkeypatch,
    capsys,
):
    app = tmp_path / "invalid_deps_drift_pack_app.py"
    app.write_text(
        "from otoe import Text\n"
        "app = Text('Invalid deps drift')\n",
        encoding="utf-8",
    )
    output = tmp_path / "dist" / "invalid-deps-drift-pack"
    archive = tmp_path / "dist" / "invalid-deps-drift-pack.tar.gz"
    monkeypatch.syspath_prepend(str(tmp_path))

    assert (
        main(
            [
                "build",
                "invalid_deps_drift_pack_app:app",
                "--out",
                str(output),
            ]
        )
        == 0
    )
    capsys.readouterr()

    deps_path = output / "otoe-deps.json"
    deps = json.loads(deps_path.read_text(encoding="utf-8"))
    deps["hasErrors"] = True
    deps["status"] = "invalid"
    deps_path.write_text(json.dumps(deps, sort_keys=True), encoding="utf-8")
    _refresh_manifest_artifact_hash(output, "otoe-deps.json")

    verify = subprocess.run(
        [sys.executable, str(output / "otoe-run.py"), "--verify"],
        capture_output=True,
        cwd=output,
        env={**os.environ, "PYTHONPATH": ""},
        text=True,
    )
    result = main(["pack", str(output), "--out", str(archive)])

    captured = capsys.readouterr()
    assert verify.returncode == 1
    assert "otoe-deps.json: dependency audit has errors" in verify.stderr
    assert result == 1
    assert not archive.exists()
    assert "pack: runner verification failed:" in captured.err
    assert "otoe-deps.json: dependency audit has errors" in captured.err


def test_cli_pack_rejects_dependency_audit_resolution_drift_after_hash_update(
    tmp_path,
    monkeypatch,
    capsys,
):
    app = tmp_path / "deps_resolution_drift_pack_app.py"
    app.write_text(
        "from otoe import Text\n"
        "app = Text('Dependency resolution drift')\n",
        encoding="utf-8",
    )
    output = tmp_path / "dist" / "deps-resolution-drift-pack"
    archive = tmp_path / "dist" / "deps-resolution-drift-pack.tar.gz"
    monkeypatch.syspath_prepend(str(tmp_path))

    assert (
        main(
            [
                "build",
                "deps_resolution_drift_pack_app:app",
                "--out",
                str(output),
            ]
        )
        == 0
    )
    capsys.readouterr()

    deps_path = output / "otoe-deps.json"
    deps = json.loads(deps_path.read_text(encoding="utf-8"))
    deps["resolution"]["lockfile"] = True
    deps_path.write_text(json.dumps(deps, sort_keys=True), encoding="utf-8")
    _refresh_manifest_artifact_hash(output, "otoe-deps.json")

    verify = subprocess.run(
        [sys.executable, str(output / "otoe-run.py"), "--verify"],
        capture_output=True,
        cwd=output,
        env={**os.environ, "PYTHONPATH": ""},
        text=True,
    )
    result = main(["pack", str(output), "--out", str(archive)])

    captured = capsys.readouterr()
    assert verify.returncode == 1
    assert "otoe-deps.json: resolution.lockfile must be false" in verify.stderr
    assert result == 1
    assert not archive.exists()
    assert "pack: runner verification failed:" in captured.err
    assert "otoe-deps.json: resolution.lockfile must be false" in captured.err


def test_cli_pack_rejects_dependency_runtime_policy_drift_after_hash_update(
    tmp_path,
    monkeypatch,
    capsys,
):
    app = tmp_path / "deps_runtime_policy_drift_pack_app.py"
    app.write_text(
        "from otoe import Text\n"
        "app = Text('Dependency runtime policy drift')\n",
        encoding="utf-8",
    )
    output = tmp_path / "dist" / "deps-runtime-policy-drift-pack"
    archive = tmp_path / "dist" / "deps-runtime-policy-drift-pack.tar.gz"
    monkeypatch.syspath_prepend(str(tmp_path))

    assert (
        main(
            [
                "build",
                "deps_runtime_policy_drift_pack_app:app",
                "--out",
                str(output),
            ]
        )
        == 0
    )
    capsys.readouterr()

    deps_path = output / "otoe-deps.json"
    deps = json.loads(deps_path.read_text(encoding="utf-8"))
    deps["runtimePolicy"]["mode"] = "enforced"
    deps_path.write_text(json.dumps(deps, sort_keys=True), encoding="utf-8")
    _refresh_manifest_artifact_hash(output, "otoe-deps.json")

    verify = subprocess.run(
        [sys.executable, str(output / "otoe-run.py"), "--verify"],
        capture_output=True,
        cwd=output,
        env={**os.environ, "PYTHONPATH": ""},
        text=True,
    )
    result = main(["pack", str(output), "--out", str(archive)])

    captured = capsys.readouterr()
    assert verify.returncode == 1
    assert "otoe-deps.json: runtimePolicy.mode must be 'audit-only'" in verify.stderr
    assert result == 1
    assert not archive.exists()
    assert "pack: runner verification failed:" in captured.err
    assert "otoe-deps.json: runtimePolicy.mode must be 'audit-only'" in captured.err


def test_cli_pack_rejects_invalid_styles_after_hash_update(
    tmp_path,
    monkeypatch,
    capsys,
):
    app = tmp_path / "invalid_styles_drift_pack_app.py"
    app.write_text(
        "from otoe import Text\n"
        "app = Text('Invalid styles drift')\n",
        encoding="utf-8",
    )
    output = tmp_path / "dist" / "invalid-styles-drift-pack"
    archive = tmp_path / "dist" / "invalid-styles-drift-pack.tar.gz"
    monkeypatch.syspath_prepend(str(tmp_path))

    assert (
        main(
            [
                "build",
                "invalid_styles_drift_pack_app:app",
                "--out",
                str(output),
            ]
        )
        == 0
    )
    capsys.readouterr()

    styles_path = output / "otoe-styles.json"
    styles = json.loads(styles_path.read_text(encoding="utf-8"))
    styles["status"] = "invalid"
    styles_path.write_text(json.dumps(styles, sort_keys=True), encoding="utf-8")
    _refresh_manifest_artifact_hash(output, "otoe-styles.json")

    verify = subprocess.run(
        [sys.executable, str(output / "otoe-run.py"), "--verify"],
        capture_output=True,
        cwd=output,
        env={**os.environ, "PYTHONPATH": ""},
        text=True,
    )
    result = main(["pack", str(output), "--out", str(archive)])

    captured = capsys.readouterr()
    assert verify.returncode == 1
    assert "otoe-styles.json: style artifact is invalid" in verify.stderr
    assert result == 1
    assert not archive.exists()
    assert "pack: runner verification failed:" in captured.err
    assert "otoe-styles.json: style artifact is invalid" in captured.err


def test_cli_build_runner_rejects_runtime_installs_allowed_manifest(
    tmp_path,
    monkeypatch,
):
    app = tmp_path / "runtime_install_manifest_drift_app.py"
    app.write_text(
        "from otoe import Text\n"
        "app = Text('Runtime install drift')\n",
        encoding="utf-8",
    )
    output = tmp_path / "dist" / "runtime-install-manifest-drift"
    monkeypatch.syspath_prepend(str(tmp_path))

    assert (
        main(
            [
                "build",
                "runtime_install_manifest_drift_app:app",
                "--out",
                str(output),
            ]
        )
        == 0
    )
    manifest_path = output / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["runtimeInstallsAllowed"] = True
    manifest_path.write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")

    verify = subprocess.run(
        [sys.executable, str(output / "otoe-run.py"), "--verify"],
        capture_output=True,
        cwd=output,
        env={**os.environ, "PYTHONPATH": ""},
        text=True,
    )

    assert verify.returncode == 1
    assert "manifest.json: runtimeInstallsAllowed must be false" in verify.stderr


def test_cli_pack_rejects_failing_backend_coverage_after_hash_update(
    tmp_path,
    monkeypatch,
    capsys,
):
    app = tmp_path / "backend_coverage_drift_pack_app.py"
    app.write_text(
        "from otoe import Text\n"
        "app = Text('Backend coverage drift')\n",
        encoding="utf-8",
    )
    requirements = tmp_path / "backend-requirements.json"
    _write_backend_coverage_requirements(requirements)
    profile_file = tmp_path / "otoe.profile.toml"
    profile_file.write_text(
        'profile = "cage"\n'
        "\n"
        "[runtime]\n"
        'files = ["backend_coverage_drift_pack_app.py"]\n'
        "\n"
        "[backend]\n"
        'coverage_requirements = "backend-requirements.json"\n',
        encoding="utf-8",
    )
    output = tmp_path / "dist" / "backend-coverage-drift-pack"
    archive = tmp_path / "dist" / "backend-coverage-drift-pack.tar.gz"
    monkeypatch.syspath_prepend(str(tmp_path))

    assert (
        main(
            [
                "build",
                "backend_coverage_drift_pack_app:app",
                "--profile-file",
                str(profile_file),
                "--out",
                str(output),
                "--validate",
            ]
        )
        == 0
    )
    capsys.readouterr()

    coverage_path = output / "otoe-backend-coverage.json"
    coverage = json.loads(coverage_path.read_text(encoding="utf-8"))
    coverage["passed"] = False
    coverage["blockers"] = ["widgetsCoverage"]
    coverage_path.write_text(json.dumps(coverage, sort_keys=True), encoding="utf-8")

    manifest_path = output / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for artifact in manifest["artifacts"]:
        if artifact["path"] == "otoe-backend-coverage.json":
            data = coverage_path.read_bytes()
            artifact["size"] = len(data)
            artifact["sha256"] = hashlib.sha256(data).hexdigest()
            break
    manifest_path.write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")

    verify = subprocess.run(
        [sys.executable, str(output / "otoe-run.py"), "--verify"],
        capture_output=True,
        cwd=output,
        env={**os.environ, "PYTHONPATH": ""},
        text=True,
    )
    result = main(["pack", str(output), "--out", str(archive)])

    captured = capsys.readouterr()
    assert verify.returncode == 1
    assert (
        "otoe-backend-coverage.json: backend coverage failed: widgetsCoverage"
        in verify.stderr
    )
    assert result == 1
    assert not archive.exists()
    assert "pack: runner verification failed:" in captured.err
    assert "backend coverage failed: widgetsCoverage" in captured.err


def test_cli_pack_rejects_backend_coverage_without_traceable_evidence_map(
    tmp_path,
    monkeypatch,
    capsys,
):
    app = tmp_path / "backend_coverage_trace_pack_app.py"
    app.write_text(
        "from otoe import Text\n"
        "app = Text('Backend coverage traceability')\n",
        encoding="utf-8",
    )
    requirements = tmp_path / "backend-requirements.json"
    _write_backend_coverage_requirements(requirements)
    profile_file = tmp_path / "otoe.profile.toml"
    profile_file.write_text(
        'profile = "cage"\n'
        "\n"
        "[runtime]\n"
        'files = ["backend_coverage_trace_pack_app.py"]\n'
        "\n"
        "[backend]\n"
        'coverage_requirements = "backend-requirements.json"\n',
        encoding="utf-8",
    )
    output = tmp_path / "dist" / "backend-coverage-trace-pack"
    archive = tmp_path / "dist" / "backend-coverage-trace-pack.tar.gz"
    monkeypatch.syspath_prepend(str(tmp_path))

    assert (
        main(
            [
                "build",
                "backend_coverage_trace_pack_app:app",
                "--profile-file",
                str(profile_file),
                "--out",
                str(output),
                "--validate",
            ]
        )
        == 0
    )
    capsys.readouterr()

    coverage_path = output / "otoe-backend-coverage.json"
    coverage = json.loads(coverage_path.read_text(encoding="utf-8"))
    coverage["coverage"]["widgets"]["evidenceMap"]["Text"]["sources"] = []
    coverage_path.write_text(json.dumps(coverage, sort_keys=True), encoding="utf-8")
    _refresh_manifest_artifact_hash(output, "otoe-backend-coverage.json")

    verify = subprocess.run(
        [sys.executable, str(output / "otoe-run.py"), "--verify"],
        capture_output=True,
        cwd=output,
        env={**os.environ, "PYTHONPATH": ""},
        text=True,
    )
    result = main(["pack", str(output), "--out", str(archive)])

    captured = capsys.readouterr()
    assert verify.returncode == 1
    assert (
        "otoe-backend-coverage.json: coverage.widgets.evidenceMap.Text.sources "
        "must not be empty for exercised coverage"
    ) in verify.stderr
    assert result == 1
    assert not archive.exists()
    assert "pack: runner verification failed:" in captured.err
    assert "coverage.widgets.evidenceMap.Text.sources" in captured.err


def test_cli_build_runner_rejects_backend_coverage_trace_tampering(
    tmp_path,
    monkeypatch,
    capsys,
):
    app = tmp_path / "backend_coverage_trace_tamper_app.py"
    app.write_text(
        "from otoe import Text\n"
        "app = Text('Backend coverage trace tamper')\n",
        encoding="utf-8",
    )
    requirements = tmp_path / "backend-requirements.json"
    _write_backend_coverage_requirements(requirements)
    profile_file = tmp_path / "otoe.profile.toml"
    profile_file.write_text(
        'profile = "cage"\n'
        "\n"
        "[runtime]\n"
        'files = ["backend_coverage_trace_tamper_app.py"]\n'
        "\n"
        "[backend]\n"
        'coverage_requirements = "backend-requirements.json"\n',
        encoding="utf-8",
    )
    output = tmp_path / "dist" / "backend-coverage-trace-tamper"
    monkeypatch.syspath_prepend(str(tmp_path))

    assert (
        main(
            [
                "build",
                "backend_coverage_trace_tamper_app:app",
                "--profile-file",
                str(profile_file),
                "--out",
                str(output),
                "--validate",
            ]
        )
        == 0
    )
    capsys.readouterr()

    coverage_path = output / "otoe-backend-coverage.json"
    original_coverage = json.loads(coverage_path.read_text(encoding="utf-8"))

    def verify_tamper(mutator, expected_error: str) -> None:
        coverage = json.loads(json.dumps(original_coverage))
        mutator(coverage)
        coverage_path.write_text(json.dumps(coverage, sort_keys=True), encoding="utf-8")
        _refresh_manifest_artifact_hash(output, "otoe-backend-coverage.json")

        verify = subprocess.run(
            [sys.executable, str(output / "otoe-run.py"), "--verify"],
            capture_output=True,
            cwd=output,
            env={**os.environ, "PYTHONPATH": ""},
            text=True,
        )

        assert verify.returncode == 1
        assert expected_error in verify.stderr

    verify_tamper(
        lambda coverage: coverage.pop("trace"),
        "otoe-backend-coverage.json: trace must be an object",
    )
    verify_tamper(
        lambda coverage: coverage["trace"]["path0"].__setitem__(
            "renderTreeHash",
            _backend_coverage_test_hash("wrong-render-tree"),
        ),
        "boundaryProof.renderTreeHash must match trace.path0.renderTreeHash",
    )
    verify_tamper(
        lambda coverage: coverage["trace"]["path0"].__setitem__(
            "renderTreeHash",
            "sha256:" + "a" * 63,
        ),
        "trace.path0.renderTreeHash must be a sha256 string",
    )
    verify_tamper(
        lambda coverage: coverage["trace"]["path0"].__setitem__(
            "layoutOutputHash",
            _backend_coverage_test_hash("wrong-layout"),
        ),
        "boundaryProof.outputHash must match trace.path0.layoutOutputHash",
    )
    verify_tamper(
        lambda coverage: coverage["trace"]["path0"].__setitem__(
            "paintOutputHash",
            _backend_coverage_test_hash("wrong-paint"),
        ),
        "boundaryProof.outputHash must match trace.path0.paintOutputHash",
    )
    verify_tamper(
        lambda coverage: coverage["trace"]["path0"].pop("semanticValidation"),
        "trace.path0.semanticValidation must be an object",
    )
    verify_tamper(
        lambda coverage: coverage["readiness"]["candidate"].__setitem__(
            "backend",
            "totally-fake-backend",
        ),
        "backend must match readiness.candidate.backend",
    )
    verify_tamper(
        lambda coverage: coverage["coverage"]["widgets"]["evidenceMap"]["Text"][
            "sources"
        ][0]["capabilityProof"].__setitem__(
            "auditHash",
            "sha256:" + "A" * 64,
        ),
        "coverage.widgets.evidenceMap.Text.sources[0].capabilityProof.auditHash "
        "must be a sha256 string",
    )
    verify_tamper(
        lambda coverage: coverage["trace"]["path0"]["semanticValidation"].__setitem__(
            "passed",
            False,
        ),
        "trace.path0.semanticValidation.passed must be true",
    )
    verify_tamper(
        lambda coverage: coverage["trace"]["path0"]["semanticValidation"].__setitem__(
            "errors",
            ["semantic drift"],
        ),
        "trace.path0.semanticValidation.errors must be []",
    )


def test_cli_pack_rejects_backend_coverage_without_capability_proof_observation(
    tmp_path,
    monkeypatch,
    capsys,
):
    app = tmp_path / "backend_coverage_capability_trace_pack_app.py"
    app.write_text(
        "from otoe import Text\n"
        "app = Text('Backend coverage capability traceability')\n",
        encoding="utf-8",
    )
    requirements = tmp_path / "backend-requirements.json"
    _write_backend_coverage_requirements(requirements)
    profile_file = tmp_path / "otoe.profile.toml"
    profile_file.write_text(
        'profile = "cage"\n'
        "\n"
        "[runtime]\n"
        'files = ["backend_coverage_capability_trace_pack_app.py"]\n'
        "\n"
        "[backend]\n"
        'coverage_requirements = "backend-requirements.json"\n',
        encoding="utf-8",
    )
    output = tmp_path / "dist" / "backend-coverage-capability-trace-pack"
    archive = tmp_path / "dist" / "backend-coverage-capability-trace-pack.tar.gz"
    monkeypatch.syspath_prepend(str(tmp_path))

    assert (
        main(
            [
                "build",
                "backend_coverage_capability_trace_pack_app:app",
                "--profile-file",
                str(profile_file),
                "--out",
                str(output),
                "--validate",
            ]
        )
        == 0
    )
    capsys.readouterr()

    coverage_path = output / "otoe-backend-coverage.json"
    coverage = json.loads(coverage_path.read_text(encoding="utf-8"))
    text_source = coverage["coverage"]["widgets"]["evidenceMap"]["Text"][
        "sources"
    ][0]
    text_source["capabilityProof"]["observedWidgets"].remove("Text")
    coverage_path.write_text(json.dumps(coverage, sort_keys=True), encoding="utf-8")
    _refresh_manifest_artifact_hash(output, "otoe-backend-coverage.json")

    verify = subprocess.run(
        [sys.executable, str(output / "otoe-run.py"), "--verify"],
        capture_output=True,
        cwd=output,
        env={**os.environ, "PYTHONPATH": ""},
        text=True,
    )
    result = main(["pack", str(output), "--out", str(archive)])

    captured = capsys.readouterr()
    assert verify.returncode == 1
    assert (
        "otoe-backend-coverage.json: coverage.widgets.evidenceMap.Text.sources[0]"
        ".capabilityProof.observedWidgets must include 'Text'"
    ) in verify.stderr
    assert result == 1
    assert not archive.exists()
    assert "pack: runner verification failed:" in captured.err
    assert "capabilityProof.observedWidgets must include 'Text'" in captured.err


def test_cli_pack_rejects_style_ir_drift_after_hash_update(
    tmp_path,
    monkeypatch,
    capsys,
):
    app = tmp_path / "drift_pack_app.py"
    app.write_text(
        "from otoe import Text\n"
        "app = Text('Style drift', className='shell')\n",
        encoding="utf-8",
    )
    styles = tmp_path / "styles.css"
    styles.write_text(".shell { color: #111827; }\n", encoding="utf-8")
    profile_file = tmp_path / "otoe.profile.toml"
    profile_file.write_text(
        'profile = "cage"\n'
        'css = ["styles.css"]\n'
        "\n"
        "[runtime]\n"
        'files = ["drift_pack_app.py"]\n',
        encoding="utf-8",
    )
    output = tmp_path / "dist" / "style-ir-drift-pack"
    archive = tmp_path / "dist" / "style-ir-drift-pack.tar.gz"
    monkeypatch.syspath_prepend(str(tmp_path))

    assert (
        main(
            [
                "build",
                "drift_pack_app:app",
                "--profile-file",
                str(profile_file),
                "--out",
                str(output),
                "--validate",
            ]
        )
        == 0
    )
    capsys.readouterr()

    styles_path = output / "otoe-styles.json"
    styles_payload = json.loads(styles_path.read_text(encoding="utf-8"))
    styles_payload["styleOps"]["classes"][0]["ops"][0]["value"] = {
        "type": "literal",
        "value": "#dc2626",
    }
    styles_path.write_text(json.dumps(styles_payload, sort_keys=True), encoding="utf-8")

    manifest_path = output / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for artifact in manifest["artifacts"]:
        if artifact["path"] == "otoe-styles.json":
            data = styles_path.read_bytes()
            artifact["size"] = len(data)
            artifact["sha256"] = hashlib.sha256(data).hexdigest()
            break
    manifest_path.write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")

    verify = subprocess.run(
        [sys.executable, str(output / "otoe-run.py"), "--verify"],
        capture_output=True,
        cwd=output,
        env={**os.environ, "PYTHONPATH": ""},
        text=True,
    )
    result = main(["pack", str(output), "--out", str(archive)])

    captured = capsys.readouterr()
    assert verify.returncode == 1
    assert (
        "otoe-styles.json: styleOps validation failed: "
        "styleOps class 'shell' applied declarations do not match compiled rules"
        in verify.stderr
    )
    assert result == 1
    assert not archive.exists()
    assert "pack: runner verification failed:" in captured.err
    assert (
        "styleOps class 'shell' applied declarations do not match compiled rules"
        in captured.err
    )


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


def _write_backend_capability_profile(
    path,
    *,
    name: str,
    styles: dict[str, str] | None = None,
    widgets: dict[str, str] | None = None,
    inputs: dict[str, str] | None = None,
) -> None:
    path.write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "format": "backend-capability-profile",
                "name": name,
                "label": f"{name} profile",
                "styles": styles or {},
                "widgets": widgets or {},
                "inputs": inputs or {},
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def _write_backend_coverage_requirements(
    path,
    *,
    widgets: tuple[str, ...] = ("Text",),
    inputs: tuple[str, ...] = ("click",),
    styles: tuple[str, ...] = ("padding",),
    omitted: tuple[str, ...] = ("borderStyle",),
) -> None:
    declared = backend_capability_profile("native-python").coverage_declaration()[
        "covers"
    ]
    evidenced_widgets = tuple(declared["widgets"])
    evidenced_inputs = tuple(declared["inputs"])
    evidenced_styles = tuple(declared["styles"])
    evidenced_omissions = tuple(declared["declaredStyleOmissions"])
    evidenced_boundaries = tuple(declared["rendererBoundaries"])
    path0_output = _backend_coverage_path0_output()
    path0_render_tree_hash = _backend_coverage_test_hash("test-render-tree")
    path0_runtime = {
        "source": "test:requirements",
        "rendererBackend": "test-renderer",
        "styleOpsPresent": True,
        "styleOpsMatchesRenderTree": True,
        "styledNodes": 1,
        "layoutBoxes": 1,
        "paintCommands": 1,
        "layoutEvidence": {
            "observationCount": 1,
            "observationHash": _backend_coverage_test_hash("test-layout"),
            "styleProperties": list(evidenced_styles),
            "observedProperties": list(evidenced_styles),
        },
        "paintEvidence": {
            "observationCount": 1,
            "observationHash": _backend_coverage_test_hash("test-paint"),
            "styleProperties": list(evidenced_styles),
            "observedProperties": list(evidenced_styles),
        },
    }
    path.write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "format": "backend-readiness-report",
                "passed": True,
                "blockers": [],
                "candidateScope": {
                    "level": "path0-render-tree-ir-v0",
                },
                "candidate": {
                    "backend": "native-python",
                },
                "gates": {
                    "rendererReplay": True,
                    "styleOpsReplay": True,
                    "path0RenderTreeEvidence": True,
                },
                "path0": {
                    "input": {
                        "renderTreeHash": path0_render_tree_hash,
                    },
                    "output": path0_output,
                    "semanticValidation": {
                        "passed": True,
                        "errors": [],
                    },
                },
                "requirements": {
                    "rendererBoundaries": [
                        {
                            "kind": "rendererBoundary",
                            "boundaries": [
                                {"boundary": boundary}
                                for boundary in evidenced_boundaries
                            ],
                        }
                    ],
                    "widgets": [
                        {
                            "widgets": [{"name": name} for name in widgets],
                        }
                    ],
                    "inputs": [
                        {
                            "capabilities": [
                                {"capability": capability} for capability in inputs
                            ],
                        }
                    ],
                    "styles": [
                        {
                            "properties": [{"property": prop} for prop in styles],
                        }
                    ],
                    "declaredStyleOmissions": [
                        {
                            "properties": [{"property": prop} for prop in omitted],
                        }
                    ],
                },
                "evidence": {
                    "rendererBoundaries": [
                        {
                            "kind": "rendererBoundary",
                            "source": "test:requirements",
                            "gate": "path0RenderTreeEvidence",
                            "boundaries": [
                                {
                                    "boundary": "paint",
                                    "count": 1,
                                    "proof": {
                                        "phase": "paint",
                                        "source": "test:requirements",
                                        "paintCommands": 1,
                                        "outputHash": path0_output["paint"][
                                            "outputHash"
                                        ],
                                    },
                                },
                                {
                                    "boundary": "renderTreeLayout",
                                    "count": 1,
                                    "proof": {
                                        "phase": "layout",
                                        "boundary": "renderTree",
                                        "source": "test:requirements",
                                        "renderTreeHash": path0_render_tree_hash,
                                        "layoutBoxes": 1,
                                        "outputHash": path0_output["layout"][
                                            "outputHash"
                                        ],
                                    },
                                },
                            ],
                        }
                    ],
                    "path0": {
                        "source": "test:requirements",
                        "gate": "path0RenderTreeEvidence",
                        "rendererBackend": "test-renderer",
                        "styleOpsPresent": True,
                        "styleOpsMatchesRenderTree": True,
                        "renderTreeHash": path0_render_tree_hash,
                        "renderTreeBoundary": {
                            "phase": "layout",
                            "boundary": "renderTree",
                            "source": "test:requirements",
                            "renderTreeHash": path0_render_tree_hash,
                            "layoutBoxes": 1,
                            "outputHash": path0_output["layout"]["outputHash"],
                        },
                        "styledNodes": 1,
                        "layoutBoxes": 1,
                        "paintCommands": 1,
                        "phases": ["layout", "paint"],
                        "layoutOutputHash": path0_output["layout"]["outputHash"],
                        "paintOutputHash": path0_output["paint"]["outputHash"],
                        "layoutEvidence": path0_runtime["layoutEvidence"],
                        "paintEvidence": path0_runtime["paintEvidence"],
                    },
                    "widgets": [
                        {
                            "source": "test:requirements",
                            "gate": "rendererReplay",
                            "proof": {
                                "source": "test:requirements",
                                "auditHash": _backend_coverage_test_hash(
                                    "test-widgets"
                                ),
                                "itemCount": len(evidenced_widgets),
                                "observedWidgets": list(evidenced_widgets),
                            },
                            "widgets": [
                                {"name": name} for name in evidenced_widgets
                            ],
                        }
                    ],
                    "inputs": [
                        {
                            "source": "test:requirements",
                            "gate": "rendererReplay",
                            "proof": {
                                "source": "test:requirements",
                                "auditHash": _backend_coverage_test_hash(
                                    "test-inputs"
                                ),
                                "itemCount": len(evidenced_inputs),
                                "observedCapabilities": list(evidenced_inputs),
                            },
                            "capabilities": [
                                {"capability": capability}
                                for capability in evidenced_inputs
                            ],
                        }
                    ],
                    "styles": [
                        {
                            "kind": "apply",
                            "source": "test:requirements",
                            "gate": "styleOpsReplay+path0RenderTreeEvidence",
                            "support": "layout+paint",
                            "properties": [
                                {"property": prop} for prop in evidenced_styles
                            ],
                            "runtime": path0_runtime,
                        }
                    ],
                    "declaredStyleOmissions": [
                        {
                            "kind": "omit",
                            "source": "test:requirements",
                            "gate": "styleOpsReplay+path0RenderTreeEvidence",
                            "status": "test-omitted",
                            "properties": [
                                {"property": prop} for prop in evidenced_omissions
                            ],
                            "runtime": path0_runtime,
                        }
                    ],
                },
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def _system_test_font() -> Path:
    for candidate in (
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf"),
        Path("/Library/Fonts/Arial.ttf"),
        Path("/System/Library/Fonts/Supplemental/Arial.ttf"),
    ):
        if candidate.is_file():
            return candidate
    pytest.skip("no TrueType system font available for Pillow native text smoke")


def _backend_coverage_path0_output() -> dict:
    layout = {
        "schemaVersion": 1,
        "format": "path0-layout-output",
        "boxCount": 1,
        "rootPath": [],
        "boxes": [
            {
                "path": [],
                "name": "Text",
                "bounds": [0, 0, 10, 10],
                "id": None,
                "context": "Text",
                "text": "Backend coverage",
                "events": [],
                "state": [],
                "style": {},
                "children": [],
            }
        ],
    }
    paint = {
        "schemaVersion": 1,
        "format": "path0-paint-output",
        "width": 10,
        "height": 10,
        "commandCount": 1,
        "commands": [
            {
                "kind": "rect",
                "path": [],
                "bounds": [0, 0, 10, 10],
                "fill": "#ffffff",
                "stroke": None,
                "strokeWidth": 0,
                "radius": 0,
                "text": None,
                "color": None,
                "fontSize": 14,
                "clip": None,
                "context": "test",
            }
        ],
    }
    return {
        "layout": {**layout, "outputHash": _backend_coverage_output_hash(layout)},
        "paint": {**paint, "outputHash": _backend_coverage_output_hash(paint)},
    }


def _backend_coverage_output_hash(payload: dict) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


def _backend_coverage_test_hash(label: str) -> str:
    return f"sha256:{hashlib.sha256(label.encode('utf-8')).hexdigest()}"


def _refresh_manifest_artifact_hash(output, artifact_name: str) -> None:
    artifact_path = output / artifact_name
    manifest_path = output / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for artifact in manifest["artifacts"]:
        if artifact["path"] == artifact_name:
            data = artifact_path.read_bytes()
            artifact["size"] = len(data)
            artifact["sha256"] = hashlib.sha256(data).hexdigest()
            manifest_path.write_text(
                json.dumps(manifest, sort_keys=True),
                encoding="utf-8",
            )
            return
    raise AssertionError(f"manifest artifact {artifact_name!r} not found")


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


def test_cli_build_validate_auto_copies_package_target_runtime_files(
    tmp_path,
    monkeypatch,
):
    package = tmp_path / "workspace_pkg"
    package.mkdir()
    (package / "__init__.py").write_text(
        "from .boot import APP_NAME\n",
        encoding="utf-8",
    )
    (package / "boot.py").write_text("APP_NAME = 'Package'\n", encoding="utf-8")
    (package / "app.py").write_text(
        "from otoe import Text\n"
        "from . import views\n"
        "app = Text(views.view_text(), className='package-shell')\n",
        encoding="utf-8",
    )
    (package / "views.py").write_text(
        "from .palette import LABEL\n"
        "from workspace_pkg.tokens import SUFFIX\n"
        "def view_text():\n"
        "    return f'{LABEL} {SUFFIX}'\n",
        encoding="utf-8",
    )
    (package / "palette.py").write_text(
        "LABEL = 'Package runtime'\n",
        encoding="utf-8",
    )
    (package / "tokens.py").write_text(
        "SUFFIX = 'ready'\n",
        encoding="utf-8",
    )
    styles = tmp_path / "styles.css"
    styles.write_text(".package-shell { color: #111827; }\n", encoding="utf-8")
    output = tmp_path / "dist" / "package-auto"
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "build",
            "workspace_pkg.app:app",
            "--css",
            str(styles),
            "--out",
            str(output),
            "--validate",
        ]
    )

    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    runtime_files = {entry["bundlePath"]: entry for entry in manifest["runtimeFiles"]}
    assert result == 0
    assert sorted(runtime_files) == [
        "app/workspace_pkg/__init__.py",
        "app/workspace_pkg/app.py",
        "app/workspace_pkg/boot.py",
        "app/workspace_pkg/palette.py",
        "app/workspace_pkg/tokens.py",
        "app/workspace_pkg/views.py",
    ]
    for source in (
        package / "__init__.py",
        package / "app.py",
        package / "boot.py",
        package / "views.py",
        package / "palette.py",
        package / "tokens.py",
    ):
        relative = source.relative_to(tmp_path)
        bundle_path = f"app/{relative.as_posix()}"
        data = source.read_bytes()
        assert (output / bundle_path).read_bytes() == data
        assert runtime_files[bundle_path] == {
            "source": relative.as_posix(),
            "bundlePath": bundle_path,
            "size": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
        }


def test_cli_build_validate_auto_copies_namespace_package_runtime_files(
    tmp_path,
    monkeypatch,
):
    package = tmp_path / "namespace_pkg"
    package.mkdir()
    (package / "app.py").write_text(
        "from otoe import Text\n"
        "from namespace_pkg.views import view_text\n"
        "app = Text(view_text())\n",
        encoding="utf-8",
    )
    (package / "views.py").write_text(
        "from namespace_pkg.tokens import LABEL\n"
        "def view_text():\n"
        "    return LABEL\n",
        encoding="utf-8",
    )
    (package / "tokens.py").write_text(
        "LABEL = 'Namespace package runtime'\n",
        encoding="utf-8",
    )
    output = tmp_path / "dist" / "namespace-package-auto"
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "build",
            "namespace_pkg.app:app",
            "--out",
            str(output),
            "--validate",
        ]
    )

    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    runtime_files = {entry["bundlePath"]: entry for entry in manifest["runtimeFiles"]}
    assert result == 0
    assert sorted(runtime_files) == [
        "app/namespace_pkg/app.py",
        "app/namespace_pkg/tokens.py",
        "app/namespace_pkg/views.py",
    ]
    for source in (
        package / "app.py",
        package / "views.py",
        package / "tokens.py",
    ):
        relative = source.relative_to(tmp_path)
        bundle_path = f"app/{relative.as_posix()}"
        data = source.read_bytes()
        assert (output / bundle_path).read_bytes() == data
        assert runtime_files[bundle_path] == {
            "source": relative.as_posix(),
            "bundlePath": bundle_path,
            "size": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
        }


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


def test_cli_build_rejects_undeclared_external_runtime_import(
    tmp_path,
    monkeypatch,
    capsys,
):
    module = tmp_path / "undeclared_external_import_app.py"
    module.write_text(
        "import pytest\n"
        "from otoe import Text\n"
        "app = Text(pytest.__name__)\n",
        encoding="utf-8",
    )
    output = tmp_path / "dist" / "undeclared-external-import"
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "build",
            "undeclared_external_import_app:app",
            "--out",
            str(output),
        ]
    )

    captured = capsys.readouterr()
    deps = json.loads((output / "otoe-deps.json").read_text(encoding="utf-8"))
    assert result == 1
    assert deps["status"] == "invalid"
    assert deps["externalImports"] == [
        {
            "module": "pytest",
            "source": "undeclared_external_import_app.py",
            "line": 1,
            "packages": ["pytest"],
            "declared": False,
            "declaredBy": None,
        }
    ]
    assert deps["diagnostics"] == [
        {
            "level": "error",
            "message": (
                "external import 'pytest' from "
                "undeclared_external_import_app.py:1 is not declared in "
                "[deps] packages (candidate packages: pytest)"
            ),
        }
    ]
    assert not (output / "manifest.json").exists()
    assert (
        "build: dependency audit invalid; refusing to write build manifest"
        in captured.err
    )


def test_cli_build_fails_for_invalid_backend_coverage_without_manifest(
    tmp_path,
    monkeypatch,
    capsys,
):
    module = tmp_path / "invalid_backend_coverage_build_surface.py"
    module.write_text(
        "from otoe import Text\n"
        "app = Text('Invalid backend coverage')\n",
        encoding="utf-8",
    )
    requirements = tmp_path / "backend-requirements.json"
    _write_backend_coverage_requirements(requirements, widgets=("Text", "Button"))
    profile_json = tmp_path / "candidate-profile.json"
    _write_backend_capability_profile(
        profile_json,
        name="candidate-build-coverage-failure",
        widgets={"Text": "text"},
    )
    profile_file = tmp_path / "otoe.profile.toml"
    profile_file.write_text(
        'profile = "cage"\n'
        "\n"
        "[backend]\n"
        'name = "native"\n'
        'capability_profile = "candidate-profile.json"\n'
        'coverage_requirements = "backend-requirements.json"\n',
        encoding="utf-8",
    )
    output = tmp_path / "dist" / "invalid-backend-coverage"
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "build",
            "invalid_backend_coverage_build_surface:app",
            "--profile-file",
            str(profile_file),
            "--out",
            str(output),
        ]
    )

    captured = capsys.readouterr()
    coverage = json.loads(
        (output / "otoe-backend-coverage.json").read_text(encoding="utf-8")
    )
    assert result == 1
    assert coverage["passed"] is False
    assert coverage["coverage"]["widgets"]["missing"] == ["Button"]
    assert not (output / "manifest.json").exists()
    assert (
        "build: backend coverage invalid; refusing to write build manifest"
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
    assert "resolution: audit-only; no lockfile; no wheel closure" in captured.out
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
    assert payload["resolution"] == {
        "mode": "audit-only",
        "lockfile": False,
        "wheelClosure": False,
        "runtimeInstallsAllowed": False,
    }
    assert payload["packages"][0]["name"] == "pytest"
    assert payload["packages"][0]["status"] == "installed"
    assert "version" in payload["packages"][0]
    assert payload["extras"] == []
    assert payload["externalImports"] == []
    assert payload["runtimePolicy"] == {
        "mode": "audit-only",
        "network": "warn",
        "subprocess": "warn",
        "findings": [],
    }


def test_cli_deps_reports_declared_external_runtime_import(
    tmp_path,
    monkeypatch,
    capsys,
):
    module = tmp_path / "declared_external_import_app.py"
    module.write_text(
        "import pytest\n"
        "from otoe import Text\n"
        "app = Text('Declared external')\n",
        encoding="utf-8",
    )
    profile_file = tmp_path / "otoe.profile.toml"
    profile_file.write_text(
        'profile = "cage"\n'
        "\n"
        "[deps]\n"
        'packages = ["pytest"]\n',
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "deps",
            "declared_external_import_app:app",
            "--profile-file",
            str(profile_file),
            "--json",
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert result == 0
    assert payload["status"] == "ok"
    assert payload["externalImports"] == [
        {
            "module": "pytest",
            "source": "declared_external_import_app.py",
            "line": 1,
            "packages": ["pytest"],
            "declared": True,
            "declaredBy": "pytest",
        }
    ]


def test_cli_deps_accepts_external_import_declared_by_distribution_name(
    tmp_path,
    monkeypatch,
    capsys,
):
    module = tmp_path / "pillow_alias_import_app.py"
    module.write_text(
        "import PIL\n"
        "from otoe import Text\n"
        "app = Text('Pillow alias')\n",
        encoding="utf-8",
    )
    profile_file = tmp_path / "otoe.profile.toml"
    profile_file.write_text(
        'profile = "cage"\n'
        "\n"
        "[deps]\n"
        'packages = ["Pillow"]\n',
        encoding="utf-8",
    )
    original_version = deps_module.metadata.version

    def fake_version(name):
        if name == "Pillow":
            return "10.0.0"
        return original_version(name)

    monkeypatch.syspath_prepend(str(tmp_path))
    monkeypatch.setattr(
        deps_module.metadata,
        "packages_distributions",
        lambda: {"PIL": ["Pillow"]},
    )
    monkeypatch.setattr(deps_module.metadata, "version", fake_version)

    result = main(
        [
            "deps",
            "pillow_alias_import_app:app",
            "--profile-file",
            str(profile_file),
            "--json",
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert result == 0
    assert payload["packages"] == [
        {
            "name": "Pillow",
            "status": "installed",
            "version": "10.0.0",
        }
    ]
    assert payload["externalImports"] == [
        {
            "module": "PIL",
            "source": "pillow_alias_import_app.py",
            "line": 1,
            "packages": ["Pillow"],
            "declared": True,
            "declaredBy": "Pillow",
        }
    ]


def test_cli_deps_reports_unknown_external_import_metadata(
    tmp_path,
    monkeypatch,
    capsys,
):
    module = tmp_path / "unknown_external_import_app.py"
    module.write_text(
        "import vendorlib\n"
        "from otoe import Text\n"
        "app = Text('Unknown external')\n",
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    monkeypatch.setattr(
        deps_module.metadata,
        "packages_distributions",
        lambda: {},
    )

    result = main(["deps", "unknown_external_import_app:app"])

    captured = capsys.readouterr()
    assert result == 1
    assert (
        "external import vendorlib: undeclared; no installed package metadata "
        "found at unknown_external_import_app.py:1"
    ) in captured.out
    assert (
        "error: external import 'vendorlib' from unknown_external_import_app.py:1 "
        "is not declared in [deps] packages (no installed package metadata found)"
    ) in captured.out


def test_cli_deps_ignores_type_checking_only_external_import(
    tmp_path,
    monkeypatch,
    capsys,
):
    module = tmp_path / "type_checking_import_app.py"
    module.write_text(
        "from typing import TYPE_CHECKING\n"
        "from otoe import Text\n"
        "if TYPE_CHECKING:\n"
        "    import pytest\n"
        "app = Text('Type checking only')\n",
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(["deps", "type_checking_import_app:app", "--json"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert result == 0
    assert payload["externalImports"] == []


def test_cli_deps_reports_dynamic_literal_import_warning(
    tmp_path,
    monkeypatch,
    capsys,
):
    module = tmp_path / "dynamic_literal_import_app.py"
    module.write_text(
        "import importlib as imports\n"
        "from otoe import Text\n"
        "imports.import_module('pytest')\n"
        "app = Text('Dynamic literal import')\n",
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(["deps", "dynamic_literal_import_app:app", "--json"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert result == 0
    assert payload["status"] == "warnings"
    assert payload["externalImports"] == []
    assert payload["dynamicImports"] == [
        {
            "module": "pytest",
            "source": "dynamic_literal_import_app.py",
            "line": 3,
            "mechanism": "importlib.import_module",
            "packages": ["pytest"],
            "declared": False,
            "declaredBy": None,
        }
    ]
    assert payload["diagnostics"] == [
        {
            "level": "warning",
            "message": (
                "dynamic import 'pytest' from dynamic_literal_import_app.py:3 "
                "via importlib.import_module is not statically copied; declare "
                "required [runtime] files and [deps] packages manually "
                "(candidate packages: pytest)"
            ),
        }
    ]


def test_cli_deps_reports_unresolved_dynamic_import_expression(
    tmp_path,
    monkeypatch,
    capsys,
):
    module = tmp_path / "dynamic_expression_import_app.py"
    module.write_text(
        "def load_dynamic(module_name):\n"
        "    load_module(module_name)\n"
        "from importlib import import_module as load_module\n"
        "from otoe import Text\n"
        "module_name = 'pytest'\n"
        "__import__(module_name)\n"
        "app = Text('Dynamic expression import')\n",
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(["deps", "dynamic_expression_import_app:app", "--json"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert result == 0
    assert payload["status"] == "warnings"
    assert payload["dynamicImports"] == [
        {
            "module": None,
            "source": "dynamic_expression_import_app.py",
            "line": 2,
            "mechanism": "importlib.import_module",
            "packages": [],
            "declared": False,
            "declaredBy": None,
        },
        {
            "module": None,
            "source": "dynamic_expression_import_app.py",
            "line": 6,
            "mechanism": "__import__",
            "packages": [],
            "declared": False,
            "declaredBy": None,
        },
    ]
    assert payload["diagnostics"] == [
        {
            "level": "warning",
            "message": (
                "dynamic import expression from dynamic_expression_import_app.py:2 "
                "via importlib.import_module cannot be resolved statically; declare "
                "required [runtime] files and [deps] packages manually"
            ),
        },
        {
            "level": "warning",
            "message": (
                "dynamic import expression from dynamic_expression_import_app.py:6 "
                "via __import__ cannot be resolved statically; declare required "
                "[runtime] files and [deps] packages manually"
            ),
        },
    ]


def test_cli_deps_reports_runtime_policy_warnings(
    tmp_path,
    monkeypatch,
    capsys,
):
    module = tmp_path / "runtime_policy_warning_app.py"
    module.write_text(
        "import os\n"
        "import socket\n"
        "from otoe import Text\n"
        "os.system('echo runtime policy')\n"
        "app = Text('Runtime policy')\n",
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(["deps", "runtime_policy_warning_app:app", "--json"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert result == 0
    assert payload["status"] == "warnings"
    assert payload["runtimePolicy"] == {
        "mode": "audit-only",
        "network": "warn",
        "subprocess": "warn",
        "findings": [
            {
                "category": "network",
                "module": "socket",
                "source": "runtime_policy_warning_app.py",
                "line": 2,
                "mechanism": "import socket",
                "action": "warning",
            },
            {
                "category": "subprocess",
                "module": "os",
                "source": "runtime_policy_warning_app.py",
                "line": 4,
                "mechanism": "os.system",
                "action": "warning",
            },
        ],
    }
    assert payload["diagnostics"] == [
        {
            "level": "warning",
            "message": (
                "runtime policy network use from "
                "runtime_policy_warning_app.py:2 via import socket"
            ),
        },
        {
            "level": "warning",
            "message": (
                "runtime policy subprocess use from "
                "runtime_policy_warning_app.py:4 via os.system"
            ),
        },
    ]


def test_cli_deps_runtime_policy_error_can_block_hardware_profile(
    tmp_path,
    monkeypatch,
    capsys,
):
    module = tmp_path / "runtime_policy_error_app.py"
    module.write_text(
        "import subprocess\n"
        "from otoe import Text\n"
        "app = Text('Runtime policy error')\n",
        encoding="utf-8",
    )
    profile_file = tmp_path / "otoe.profile.toml"
    profile_file.write_text(
        'profile = "cage"\n'
        "\n"
        "[runtime.policy]\n"
        'subprocess = "error"\n',
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "deps",
            "runtime_policy_error_app:app",
            "--profile-file",
            str(profile_file),
            "--json",
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert result == 1
    assert payload["status"] == "invalid"
    assert payload["runtimePolicy"]["subprocess"] == "error"
    assert payload["runtimePolicy"]["findings"] == [
        {
            "category": "subprocess",
            "module": "subprocess",
            "source": "runtime_policy_error_app.py",
            "line": 1,
            "mechanism": "import subprocess",
            "action": "error",
        }
    ]
    assert payload["diagnostics"] == [
        {
            "level": "error",
            "message": (
                "runtime policy subprocess use from "
                "runtime_policy_error_app.py:1 via import subprocess"
            ),
        }
    ]


def test_cli_deps_rejects_invalid_runtime_policy_action(tmp_path, capsys):
    profile_file = tmp_path / "otoe.profile.toml"
    profile_file.write_text(
        'profile = "cage"\n'
        "\n"
        "[runtime.policy]\n"
        'network = "forbidden"\n',
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
    assert (
        "deps: [runtime.policy] key 'network' must be one of "
        "'allow', 'error', 'warn'"
    ) in captured.err


def test_cli_build_rejects_runtime_policy_error(
    tmp_path,
    monkeypatch,
    capsys,
):
    module = tmp_path / "runtime_policy_build_error_app.py"
    module.write_text(
        "from subprocess import run\n"
        "from otoe import Text\n"
        "app = Text('Runtime policy build error')\n",
        encoding="utf-8",
    )
    profile_file = tmp_path / "otoe.profile.toml"
    profile_file.write_text(
        'profile = "cage"\n'
        "\n"
        "[runtime.policy]\n"
        'subprocess = "error"\n',
        encoding="utf-8",
    )
    output = tmp_path / "dist" / "runtime-policy-build-error"
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "build",
            "runtime_policy_build_error_app:app",
            "--profile-file",
            str(profile_file),
            "--out",
            str(output),
        ]
    )

    captured = capsys.readouterr()
    deps = json.loads((output / "otoe-deps.json").read_text(encoding="utf-8"))
    assert result == 1
    assert deps["status"] == "invalid"
    assert not (output / "manifest.json").exists()
    assert "build: dependency audit invalid" in captured.err


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


def _png_size(data: bytes) -> tuple[int, int]:
    assert data.startswith(b"\x89PNG\r\n\x1a\n")
    return (
        int.from_bytes(data[16:20], "big"),
        int.from_bytes(data[20:24], "big"),
    )
