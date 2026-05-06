import re

from examples.wraith.mission_exec_live_preview import MissionExecLivePreview
from examples.wraith.mission_exec_preview import build_preview_html


def _button_click_id(html, label):
    match = re.search(
        rf'<button[^>]*data-otoe-click="([^"]+)"[^>]*>{label}</button>',
        html,
    )
    assert match is not None
    return match.group(1)


def _button_click_ids(html, label):
    return re.findall(
        rf'<button[^>]*data-otoe-click="([^"]+)"[^>]*>{label}</button>',
        html,
    )


def test_wraith_mission_exec_preview_contains_extracted_surface():
    html = build_preview_html()

    assert "<!doctype html>" in html
    assert "Mission Exec / Handshake Hunter" in html
    assert "LIVE TELEMETRY / wlan1mon" in html
    assert "CAPTURE FEED" in html
    assert "EVENT TIMELINE" in html
    assert "exec-event-filters" in html
    assert "SIMULATE FRAME" in html
    assert "PREFLIGHT" in html
    assert "ABORT MISSION" in html
    assert "ui-card is-default exec-terminal-panel" in html
    assert "ui-button is-danger is-md danger-button" in html
    assert "ui-tab filter-button is-active" in html
    assert "MissionExecSurface" not in html


def test_wraith_mission_exec_live_filters_telemetry():
    app = MissionExecLivePreview()
    html = app.render_fragment()
    click_id = _button_click_id(html, "WARN")

    html = app.dispatch_event(click_id)

    assert "1 lines" in html
    assert "beacon anomaly" in html
    assert "attach interface wlan1mon" not in html
    assert "ui-tab filter-button is-active" in html


def test_wraith_mission_exec_live_filters_event_timeline():
    app = MissionExecLivePreview()
    html = app.render_fragment()
    warn_event_click_id = _button_click_ids(html, "WARN")[-1]

    html = app.dispatch_event(warn_event_click_id)

    assert "2 events" in html
    assert "RSSI delta - possible client roam" in html
    assert "Escalated to workbench queue" in html
    assert "Policy guard approved DEMO-SCOPE-001" not in html
    assert "WARN event filter active" in html


def test_wraith_mission_exec_live_pause_and_abort_actions():
    app = MissionExecLivePreview()
    html = app.render_fragment()

    html = app.dispatch_event(_button_click_id(html, "PAUSE CAPTURE"))

    assert "PAUSED" in html
    assert "RESUME CAPTURE" in html
    assert "operator: capture paused" in html

    html = app.dispatch_event(_button_click_id(html, "ABORT MISSION"))

    assert "ABORTED" in html
    assert "Operator requested mission abort" in html


def test_wraith_mission_exec_live_simulates_visible_runtime_frame():
    app = MissionExecLivePreview()
    html = app.render_fragment()

    html = app.dispatch_event(_button_click_id(html, "SIMULATE FRAME"))

    assert "FRAME 001" in html
    assert "INFO telemetry mutation" in html
    assert "frame 001: radio frame accepted on channel 11" in html
    assert "00:01:23" in html


def test_wraith_mission_exec_live_clear_action():
    app = MissionExecLivePreview()
    html = app.render_fragment()

    html = app.dispatch_event(_button_click_id(html, "CLEAR"))

    assert "0 lines" in html
    assert "attach interface wlan1mon" not in html
