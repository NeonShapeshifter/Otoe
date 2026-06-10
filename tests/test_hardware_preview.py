import json
import os
import re
import subprocess
import sys
from pathlib import Path

from examples.hardware.control_panel import (
    FakeHardwareProvider,
    demo_snapshot,
    empty_snapshot,
    error_snapshot,
    loading_snapshot,
    offline_snapshot,
)
from examples.hardware.live_preview import LIVE_CONFIG, HardwareLivePreview
from examples.hardware.preview import build_preview_html
from otoe.cli import main


ROOT = Path(__file__).resolve().parents[1]


def _click_id_before(html, marker):
    segment = html[: html.index(marker)]
    matches = re.findall(r'data-otoe-click="([^"]+)"', segment)
    assert matches
    return matches[-1]


def _click_id_after(html, marker):
    segment = html[html.index(marker) :]
    match = re.search(r'data-otoe-click="([^"]+)"', segment)
    assert match is not None
    return match.group(1)


def test_hardware_preview_contains_reference_app_surface():
    html = build_preview_html()

    assert "<!doctype html>" in html
    assert "<title>Otoe Hardware Control Panel</title>" in html
    assert '<link rel="stylesheet" href="reference_theme.css">' in html
    assert LIVE_CONFIG.stylesheets()[0].route == "/reference_theme.css"
    assert "Otoe Hardware Lab" in html
    assert "Bench Controller A17" in html
    assert "Provider healthy" in html
    assert "Bus voltage" in html
    assert "Event stream" in html
    assert "Run self-test" in html
    assert "Computed object" not in html
    assert "HardwareControlPanel" not in html


def test_hardware_control_panel_app_cli_renders_html_and_native_png(tmp_path):
    styles = ROOT / "preview" / "hardware_portable.css"
    html_output = tmp_path / "hardware.html"
    png_output = tmp_path / "hardware.png"

    html_result = main(
        [
            "render",
            "examples.hardware.control_panel:app",
            "--out",
            str(html_output),
            "--css",
            str(styles),
            "--pretty",
        ]
    )
    native_result = main(
        [
            "render",
            "examples.hardware.control_panel:app",
            "--out",
            str(png_output),
            "--native",
            "--css",
            str(styles),
        ]
    )

    html = html_output.read_text(encoding="utf-8")
    assert html_result == 0
    assert native_result == 0
    assert "Otoe Hardware Lab" in html
    assert "Bench Controller A17" in html
    assert "Provider healthy" in html
    assert 'style="' in html
    assert png_output.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")


def test_hardware_control_panel_app_build_validates_offline_bundle(
    tmp_path,
    capsys,
):
    styles = ROOT / "preview" / "hardware_portable.css"
    output = tmp_path / "hardware-cage"
    frame = tmp_path / "hardware-frame.png"

    result = main(
        [
            "build",
            "examples.hardware.control_panel:app",
            "--out",
            str(output),
            "--css",
            str(styles),
            "--validate",
        ]
    )

    captured = capsys.readouterr()
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    plan = json.loads((output / "otoe-plan.json").read_text(encoding="utf-8"))
    runtime_paths = sorted(entry["bundlePath"] for entry in manifest["runtimeFiles"])
    png = subprocess.run(
        [sys.executable, str(output / "otoe-run.py"), "--png", str(frame)],
        capture_output=True,
        cwd=output,
        env={**os.environ, "PYTHONPATH": ""},
        text=True,
    )

    assert result == 0
    assert "validation: ok" in captured.out
    assert manifest["target"] == "examples.hardware.control_panel:app"
    assert manifest["status"] == "warnings"
    assert plan["status"] == "warnings"
    assert plan["hasErrors"] is False
    assert runtime_paths == [
        "app/examples/hardware/__init__.py",
        "app/examples/hardware/control_panel.py",
    ]
    assert png.returncode == 0, png.stderr
    assert frame.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")


def test_hardware_provider_queues_command_events():
    provider = FakeHardwareProvider(demo_snapshot())

    snapshot = provider.run_command("self-test")

    assert snapshot.mode == "Self-test queued"
    assert snapshot.events[0].source == "diagnostics"
    assert snapshot.events[0].message == "Self-test scheduled"
    assert snapshot.last_feedback is not None
    assert snapshot.last_feedback.title == "Self-test queued"
    assert snapshot.last_feedback.tone == "success"


def test_hardware_provider_blocks_disabled_commands():
    provider = FakeHardwareProvider(demo_snapshot())

    snapshot = provider.run_command("safe-mode")

    assert snapshot.mode == "Closed-loop monitor"
    assert snapshot.events[0].source == "safety"
    assert snapshot.events[0].message == "Arm safe mode blocked: Supervisor key required."
    assert snapshot.last_feedback is not None
    assert snapshot.last_feedback.title == "Command blocked"
    assert snapshot.last_feedback.detail == "Arm safe mode: Supervisor key required."


def test_hardware_preview_renders_offline_state_and_locked_controls():
    html = build_preview_html(offline_snapshot(), route="controls")

    assert "OFFLINE" in html
    assert "Operator controls" in html
    assert "Device is offline." in html
    assert "disabled=\"disabled\"" in html


def test_hardware_preview_renders_offline_overview_state():
    html = build_preview_html(offline_snapshot())

    assert "OFFLINE" in html
    assert "Last heartbeat missed" in html
    assert "No live sample" in html
    assert "Provider offline" in html


def test_hardware_preview_renders_disabled_command_reasons():
    html = build_preview_html(route="controls")

    assert "Supervisor key required." in html


def test_hardware_preview_renders_empty_telemetry_state():
    html = build_preview_html(empty_snapshot())

    assert "No telemetry samples" in html
    assert "No hardware events" in html
    assert "No telemetry sample" in html


def test_hardware_preview_renders_loading_and_error_fixtures():
    loading_html = build_preview_html(loading_snapshot())
    error_html = build_preview_html(error_snapshot(), route="controls")

    assert "LOADING" in loading_html
    assert "Opening USB serial" in loading_html
    assert "Connecting to provider" in loading_html
    assert "ERROR" in error_html
    assert "Resolve provider error first." in error_html
    assert "Provider error" in error_html


def test_hardware_live_preview_dispatches_command():
    app = HardwareLivePreview()
    html = app.render_fragment()
    click_id = _click_id_before(html, "Run self-test")

    html = app.dispatch_event(click_id)

    assert "Mode: Self-test queued" in html
    assert "Self-test scheduled" in html
    assert "Diagnostics will run without changing output state." in html


def test_hardware_live_preview_navigates_to_controls_and_runs_calibration():
    app = HardwareLivePreview()
    html = app.render_fragment()
    controls_id = _click_id_before(html, "Controls")

    html = app.dispatch_event(controls_id)

    assert "Operator controls" in html
    assert "Calibrate sensors" in html

    calibrate_id = _click_id_after(html, "Calibrate sensors")
    html = app.dispatch_event(calibrate_id)

    assert "Mode: Calibration queued" in html
    assert "Calibration queued" in html
    assert "Sensor offsets are waiting for operator review." in html
