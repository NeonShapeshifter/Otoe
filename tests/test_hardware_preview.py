import re

from examples.hardware.control_panel import FakeHardwareProvider, demo_snapshot
from examples.hardware.live_preview import HardwareLivePreview
from examples.hardware.preview import build_preview_html


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
    assert "Otoe Hardware Lab" in html
    assert "Bench Controller A17" in html
    assert "Bus voltage" in html
    assert "Event stream" in html
    assert "Run self-test" in html
    assert "Computed object" not in html
    assert "HardwareControlPanel" not in html


def test_hardware_provider_queues_command_events():
    provider = FakeHardwareProvider(demo_snapshot())

    snapshot = provider.run_command("self-test")

    assert snapshot.mode == "Self-test queued"
    assert snapshot.events[0].source == "diagnostics"
    assert snapshot.events[0].message == "Self-test scheduled"


def test_hardware_live_preview_dispatches_command():
    app = HardwareLivePreview()
    html = app.render_fragment()
    click_id = _click_id_before(html, "Run self-test")

    html = app.dispatch_event(click_id)

    assert "Mode: Self-test queued" in html
    assert "Self-test scheduled" in html


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
