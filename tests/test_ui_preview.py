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
    assert "Controlled inputs" in html
    assert "ui-select-popover" in html
    assert "Inspect surface" in html
    assert "Renderer boundary ready" in html
    assert 'data-otoe-autofocus="true"' in html
    assert "ui-command-card ui-demo-command" in html
    assert "ui-command-item" in html
    assert "ui-dialog-backdrop" in html
    assert "Computed object" not in html
    assert "UIKitKitchenSink" not in html


def test_ui_kit_live_preview_filters_commands():
    app = UIKitLivePreview()
    html = app.render_fragment()
    assert "Open Command Palette" in html
    assert "Search Wraith, SaaS, export..." not in html
    open_id = _attr_near(html, "Open Command Palette", "data-otoe-click")
    html = app.dispatch_event(open_id)
    change_id = _attr_near(html, "Search Wraith, SaaS, export...", "data-otoe-change")

    assert 'data-otoe-autofocus="true"' in html

    html = app.dispatch_event(change_id, "customers")

    assert 'value="customers"' in html
    assert "Review Customers" in html
    assert "Open Mission Exec" not in html
    assert "No commands" not in html


def test_ui_kit_live_preview_selects_command_and_routes_to_surface():
    app = UIKitLivePreview()
    html = app.render_fragment()
    open_id = _attr_near(html, "Open Command Palette", "data-otoe-click")
    html = app.dispatch_event(open_id)
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
    open_id = _attr_near(html, "Open Command Palette", "data-otoe-click")
    html = app.dispatch_event(open_id)
    change_id = _attr_near(html, "Search Wraith, SaaS, export...", "data-otoe-change")
    keydown_id = _attr_near(html, "Search Wraith, SaaS, export...", "data-otoe-keydown")

    html = app.dispatch_event(change_id, "customers")
    html = app.dispatch_event(keydown_id, "Enter")

    assert "SaaS route loaded" in html
    assert "Commercial dashboard" in html
    assert "Route: SaaS" in html
    assert "Command palette" not in html


def test_ui_kit_live_preview_ctrl_k_opens_command_palette():
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
    assert "Search Wraith, SaaS, export..." in html
    assert 'data-otoe-autofocus="true"' in html
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
    click_id = _attr_near(html, "Open Command Palette", "data-otoe-click")
    html = app.dispatch_event(click_id)
    assert "Search Wraith, SaaS, export..." in html
    shortcut_id = _attr_near(html, "ui-shortcut-scope", "data-otoe-global-keydown")

    html = app.dispatch_event(
        shortcut_id,
        {"key": "Escape", "ctrlKey": False, "metaKey": False, "altKey": False, "shiftKey": False},
    )

    assert "Search Wraith, SaaS, export..." not in html
    assert "Open Command Palette" in html


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
    open_id = _attr_near(html, "Open Command Palette", "data-otoe-click")
    html = app.dispatch_event(open_id)
    change_id = _attr_near(html, "Search Wraith, SaaS, export...", "data-otoe-change")

    html = app.dispatch_event(change_id, "nothing-matches")

    assert 'value="nothing-matches"' in html
    assert "No commands" in html
    assert "Review Customers" not in html


def test_ui_kit_live_preview_select_and_menu_update_state():
    app = UIKitLivePreview()
    html = app.render_fragment()
    select_id = _attr_near(html, "Balanced", "data-otoe-click")

    html = app.dispatch_event(select_id)

    assert "Roomy" in html

    roomy_id = _attr_near(html, "Roomy", "data-otoe-click")
    html = app.dispatch_event(roomy_id)

    assert "Density: Roomy; action: None" in html
    assert "Softer SaaS dashboard spacing." in html

    menu_id = _attr_near(html, "Open Action Menu", "data-otoe-click")
    html = app.dispatch_event(menu_id)

    assert "Duplicate view" in html

    duplicate_id = _attr_near(html, "Duplicate view", "data-otoe-click")
    html = app.dispatch_event(duplicate_id)

    assert "Density: Roomy; action: Duplicate view" in html
    assert "Fork the current app route." not in html


def test_ui_kit_live_preview_select_keyboard_updates_state():
    app = UIKitLivePreview()
    html = app.render_fragment()
    select_keydown_id = _attr_near(html, "Balanced", "data-otoe-keydown")

    html = app.dispatch_event(select_keydown_id, "ArrowDown")

    assert "Density: Roomy; action: None" in html
    assert "Softer SaaS dashboard spacing." in html
    assert "ui-select-popover" in html

    select_keydown_id = _attr_near(html, "Roomy", "data-otoe-keydown")
    html = app.dispatch_event(select_keydown_id, "Escape")

    assert "Density: Roomy; action: None" in html
    assert "ui-select-popover" not in html


def test_ui_kit_live_preview_menu_keyboard_updates_state():
    app = UIKitLivePreview()
    html = app.render_fragment()
    menu_id = _attr_near(html, "Open Action Menu", "data-otoe-click")
    html = app.dispatch_event(menu_id)
    inspect_keydown_id = _attr_near(html, "Inspect surface", "data-otoe-keydown")

    html = app.dispatch_event(inspect_keydown_id, "ArrowDown")

    assert "ui-menu-item is-success is-active" in html
    assert "Density: Balanced; action: None" in html

    duplicate_keydown_id = _attr_near(html, "Duplicate view", "data-otoe-keydown")
    html = app.dispatch_event(duplicate_keydown_id, "Enter")

    assert "Density: Balanced; action: Duplicate view" in html
    assert "Fork the current app route." not in html
