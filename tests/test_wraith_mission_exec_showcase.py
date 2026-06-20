import ast
from pathlib import Path

from examples.wraith.mission_exec_showcase import (
    MissionExecShowcaseDemo,
    app,
    load_stylesheet,
)
from otoe import mount, render_html
from otoe.cli import main


ROOT = Path(__file__).resolve().parents[1]
STYLES = ROOT / "preview" / "wraith_mission_exec.css"
SOURCE = ROOT / "examples" / "wraith" / "mission_exec_showcase.py"


def test_wraith_mission_exec_showcase_html_render_contains_key_sections():
    html = render_html(mount(app()), stylesheet=load_stylesheet(), pretty=True)

    assert "Mission Exec" in html
    assert "Preflight" in html
    assert "Emergency Controls" in html
    assert "Live Telemetry" in html
    assert "Event Timeline" in html


def test_wraith_mission_exec_showcase_native_render_smoke(tmp_path):
    demo = MissionExecShowcaseDemo()
    output = tmp_path / "mission-exec.png"

    demo.surface.render_png(output)

    assert output.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")


def test_wraith_mission_exec_showcase_native_clicks_log_filter():
    demo = MissionExecShowcaseDemo()

    demo.click_text("WARN")

    assert demo.model.active_filter.value == "WARN"
    texts = demo.visible_texts()
    assert "approval: destructive command remains gated" in texts
    assert "mission_exec: showcase booted with local fixture data" not in texts


def test_wraith_mission_exec_showcase_approval_dialog_opens_and_closes():
    demo = MissionExecShowcaseDemo()

    demo.click_text("QUEUE APPROVAL")

    assert demo.model.pending_approval.value is not None
    assert "Operator approval required" in demo.visible_texts()

    demo.click_text("CANCEL REVIEW")

    assert demo.model.pending_approval.value is None
    assert "Operator approval required" not in demo.visible_texts()


def test_wraith_mission_exec_showcase_pause_resume_changes_visible_label():
    demo = MissionExecShowcaseDemo()

    demo.click_text("PAUSE SIMULATION")

    assert demo.model.paused.value is True
    assert "RESUME SIMULATION" in demo.visible_texts()

    demo.click_text("RESUME SIMULATION")

    assert demo.model.paused.value is False
    assert "PAUSE SIMULATION" in demo.visible_texts()


def test_wraith_mission_exec_showcase_build_validate_smoke(tmp_path, capsys):
    output = tmp_path / "mission-exec-build"

    result = main(
        [
            "build",
            "examples.wraith.mission_exec_showcase:app",
            "--out",
            str(output),
            "--css",
            str(STYLES),
            "--validate",
        ]
    )

    captured = capsys.readouterr()
    assert result == 0
    assert "validation: ok" in captured.out
    assert (output / "manifest.json").exists()


def test_wraith_mission_exec_showcase_has_no_wraith_imports():
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    imports: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imports.append(node.module)

    assert not [
        name
        for name in imports
        if name == "wraith" or name.startswith("wraith.")
    ]
