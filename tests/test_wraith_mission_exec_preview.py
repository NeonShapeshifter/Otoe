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
    assert "QUEUE APPROVAL" in html
    assert "SIMULATE FRAME" in html
    assert "RECOVER SNAPSHOT" in html
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


def test_wraith_mission_exec_live_approval_modal_approve_flow():
    app = MissionExecLivePreview()
    html = app.render_fragment()

    html = app.dispatch_event(_button_click_id(html, "QUEUE APPROVAL"))

    assert "AWAITING APPROVAL" in html
    assert "Operator approval required" in html
    assert "Combo step &#x27;pivot-auth&#x27; is waiting for operator approval." in html
    assert "ui-dialog-backdrop" in html
    assert "APPROVE STEP" in html
    assert "DENY / ABORT" in html

    html = app.dispatch_event(_button_click_id(html, "APPROVE STEP"))

    assert "Approval granted for &#x27;pivot-auth&#x27;." in html
    assert "Combo step pivot-auth may continue." in html
    assert "Operator approval required" not in html
    assert "AWAITING APPROVAL" not in html


def test_wraith_mission_exec_live_approval_modal_deny_flow():
    app = MissionExecLivePreview()
    html = app.render_fragment()

    html = app.dispatch_event(_button_click_id(html, "QUEUE APPROVAL"))
    html = app.dispatch_event(_button_click_id(html, "DENY / ABORT"))

    assert "ABORTED" in html
    assert "Approval denied for &#x27;pivot-auth&#x27;. Aborting combo." in html
    assert "Combo step pivot-auth was denied." in html
    assert "Operator approval required" not in html


def test_wraith_mission_exec_live_recovers_remote_snapshot_with_pending_approval():
    app = MissionExecLivePreview()
    html = app.render_fragment()

    html = app.dispatch_event(_button_click_id(html, "RECOVER SNAPSHOT"))

    assert "AWAITING APPROVAL" in html
    assert "00:03:04" in html
    assert "remote line one: runtime host reattached" in html
    assert "remote line two: combo step pivot-escalate waiting for approval" in html
    assert "Remote snapshot recovered" in html
    assert "Runtime host snapshot restored output and approval state." in html
    assert "Recovered combo step &#x27;pivot-escalate&#x27; is waiting for operator approval." in html
    assert "Runtime host snapshot arrived after UI reconnect" in html
    assert "Recovered approval gate for pivot-escalate" in html
    assert "ui-dialog-backdrop" in html

    html = app.dispatch_event(_button_click_id(html, "APPROVE STEP"))

    assert "Approval granted for &#x27;pivot-escalate&#x27;." in html
    assert "Combo step pivot-escalate may continue." in html
    assert "Operator approval required" not in html


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
