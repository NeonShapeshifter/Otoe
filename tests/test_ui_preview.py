import re

from examples.ui.live_preview import UIKitLivePreview
from examples.ui.preview import build_preview_html


def _attr_near(html, marker, attr):
    index = html.index(marker)
    start = max(0, index - 720)
    end = min(len(html), index + 720)
    match = re.search(rf'{attr}="([^"]+)"', html[start:end])
    assert match is not None
    return match.group(1)


def test_ui_kit_preview_contains_component_kitchen_sink():
    html = build_preview_html()

    assert "<!doctype html>" in html
    assert "<title>Otoe UI Kit Preview</title>" in html
    assert "otoe-shortcut-scope ui-shortcut-scope" in html
    assert "ui-app-shell ui-demo-shell" in html
    assert "ui-sidebar-nav ui-demo-sidebar" in html
    assert "Command palette" in html
    assert "Review Customers" in html
    assert "Renderer boundary ready" in html
    assert "ui-command-card ui-demo-command" in html
    assert "ui-command-item" in html
    assert "ui-dialog-backdrop" in html
    assert "Computed object" not in html
    assert "UIKitKitchenSink" not in html


def test_ui_kit_live_preview_filters_commands():
    app = UIKitLivePreview()
    html = app.render_fragment()
    change_id = _attr_near(html, "Search Wraith, SaaS, export...", "data-otoe-change")

    html = app.dispatch_event(change_id, "customers")

    assert 'value="customers"' in html
    assert "Review Customers" in html
    assert "Open Mission Exec" not in html
    assert "No commands" not in html


def test_ui_kit_live_preview_selects_command_and_routes_to_surface():
    app = UIKitLivePreview()
    html = app.render_fragment()
    change_id = _attr_near(html, "Search Wraith, SaaS, export...", "data-otoe-change")
    html = app.dispatch_event(change_id, "customers")
    click_id = _attr_near(html, "Review Customers", "data-otoe-click")

    html = app.dispatch_event(click_id)

    assert "SaaS route loaded" in html
    assert "Commercial dashboard" in html
    assert "Route: SaaS" in html
    assert "Command palette" not in html


def test_ui_kit_live_preview_enter_selects_first_filtered_command():
    app = UIKitLivePreview()
    html = app.render_fragment()
    change_id = _attr_near(html, "Search Wraith, SaaS, export...", "data-otoe-change")
    keydown_id = _attr_near(html, "Search Wraith, SaaS, export...", "data-otoe-keydown")

    html = app.dispatch_event(change_id, "customers")
    html = app.dispatch_event(keydown_id, "Enter")

    assert "SaaS route loaded" in html
    assert "Commercial dashboard" in html
    assert "Route: SaaS" in html
    assert "Command palette" not in html


def test_ui_kit_live_preview_ctrl_k_returns_to_command_surface():
    app = UIKitLivePreview()
    html = app.render_fragment()
    nav_id = _attr_near(html, "Wraith", "data-otoe-click")
    html = app.dispatch_event(nav_id)
    shortcut_id = _attr_near(html, "ui-shortcut-scope", "data-otoe-global-keydown")

    html = app.dispatch_event(
        shortcut_id,
        {"key": "k", "ctrlKey": True, "metaKey": False, "altKey": False, "shiftKey": False},
    )

    assert "Command palette" in html
    assert "Route: UI Kit" in html
    assert "Wraith route loaded" not in html


def test_ui_kit_live_preview_global_shortcut_runs_command():
    app = UIKitLivePreview()
    html = app.render_fragment()
    shortcut_id = _attr_near(html, "ui-shortcut-scope", "data-otoe-global-keydown")

    html = app.dispatch_event(
        shortcut_id,
        {"key": "m", "ctrlKey": False, "metaKey": False, "altKey": False, "shiftKey": False},
    )

    assert "Wraith route loaded" in html
    assert "Route: Wraith" in html
    assert "Command palette" not in html


def test_ui_kit_live_preview_escape_clears_dialog_state():
    app = UIKitLivePreview()
    html = app.render_fragment()
    click_id = _attr_near(html, "Toggle Dialog", "data-otoe-click")
    html = app.dispatch_event(click_id)
    assert "Renderer boundary ready" in html
    shortcut_id = _attr_near(html, "ui-shortcut-scope", "data-otoe-global-keydown")

    html = app.dispatch_event(
        shortcut_id,
        {"key": "Escape", "ctrlKey": False, "metaKey": False, "altKey": False, "shiftKey": False},
    )

    assert "Renderer boundary ready" not in html
    assert "Command palette" in html


def test_ui_kit_live_preview_sidebar_navigation_switches_routes():
    app = UIKitLivePreview()
    html = app.render_fragment()
    click_id = _attr_near(html, "Wraith", "data-otoe-click")

    html = app.dispatch_event(click_id)

    assert "Wraith route loaded" in html
    assert "Mission controls" in html
    assert "Route: Wraith" in html
    assert "SaaS route loaded" not in html


def test_ui_kit_live_preview_shows_empty_command_state():
    app = UIKitLivePreview()
    html = app.render_fragment()
    change_id = _attr_near(html, "Search Wraith, SaaS, export...", "data-otoe-change")

    html = app.dispatch_event(change_id, "nothing-matches")

    assert 'value="nothing-matches"' in html
    assert "No commands" in html
    assert "Review Customers" not in html
