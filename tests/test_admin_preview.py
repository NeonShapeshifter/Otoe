import re

from examples.admin.live_preview import AdminLivePreview
from examples.admin.preview import build_preview_html
from examples.admin.settings_console import (
    MemoryAdminSettingsProvider,
    demo_admin_snapshot,
    invalid_admin_snapshot,
)


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


def _change_id_after(html, marker):
    segment = html[html.index(marker) :]
    match = re.search(r'data-otoe-change="([^"]+)"', segment)
    assert match is not None
    return match.group(1)


def test_admin_preview_contains_reference_app_surface():
    html = build_preview_html()

    assert "<!doctype html>" in html
    assert "<title>Otoe Local Admin Console</title>" in html
    assert "Otoe Admin Console" in html
    assert "Local Workspace" in html
    assert "Settings requiring review" in html
    assert "Recent activity" in html
    assert "Computed object" not in html
    assert "AdminSettingsConsole" not in html


def test_admin_preview_renders_invalid_settings_route():
    html = build_preview_html(invalid_admin_snapshot(), route="settings")

    assert "Validation failed" in html
    assert "Use a port from 1 to 65535" in html
    assert "70000" in html


def test_admin_provider_validates_and_blocks_invalid_save():
    provider = MemoryAdminSettingsProvider(demo_admin_snapshot())

    snapshot = provider.update_setting("http_port", "70000")
    snapshot = provider.run_action("save")

    assert snapshot.status == "Validation failed"
    assert snapshot.settings[2].value == "8765"
    assert snapshot.last_feedback is not None
    assert snapshot.last_feedback.title == "Save blocked"


def test_admin_provider_saves_valid_draft():
    provider = MemoryAdminSettingsProvider(demo_admin_snapshot())

    snapshot = provider.update_setting("workspace_name", "Ops Console")
    snapshot = provider.run_action("save")

    assert snapshot.status == "Saved"
    assert snapshot.workspace == "Ops Console"
    assert snapshot.pending_changes == 0
    assert snapshot.audit_events[0].action == "Applied local settings"
    assert snapshot.last_feedback is not None
    assert snapshot.last_feedback.title == "Settings saved"


def test_admin_provider_toggles_access_rule():
    provider = MemoryAdminSettingsProvider(demo_admin_snapshot())

    snapshot = provider.toggle_access_rule("remote")

    assert snapshot.access_rules[2].enabled is True
    assert snapshot.audit_events[0].action == "Remote admin bridge enabled"
    assert snapshot.last_feedback is not None
    assert snapshot.last_feedback.title == "Access rule updated"


def test_admin_live_preview_updates_and_saves_setting():
    app = AdminLivePreview()
    html = app.render_fragment()
    settings_id = _click_id_before(html, "Settings")

    html = app.dispatch_event(settings_id)
    change_id = _change_id_after(html, "Workspace name")
    html = app.dispatch_event(change_id, "Ops Console")

    assert "Unsaved changes" in html
    assert "Ops Console" in html

    save_id = _click_id_before(html, "Save changes")
    html = app.dispatch_event(save_id)

    assert "Settings saved" in html
    assert "Ops Console" in html


def test_admin_live_preview_toggles_access_rule():
    app = AdminLivePreview()
    html = app.render_fragment()
    access_id = _click_id_before(html, "Access")

    html = app.dispatch_event(access_id)
    remote_id = _click_id_after(html, "Remote admin bridge")
    html = app.dispatch_event(remote_id)

    assert "Access rule updated" in html
    assert "Remote admin bridge is now enabled." in html
