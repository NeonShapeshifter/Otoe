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
