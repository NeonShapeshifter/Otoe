import re

from examples.saas.live_preview import SaaSLivePreview


def _attr_near(html, marker, attr):
    index = html.index(marker)
    start = max(0, index - 240)
    end = min(len(html), index + 240)
    match = re.search(rf'{attr}="([^"]+)"', html[start:end])
    assert match is not None
    return match.group(1)


def _button_click_id(html, label):
    match = re.search(
        rf'<button[^>]*data-otoe-click="([^"]+)"[^>]*>{label}</button>',
        html,
    )
    assert match is not None
    return match.group(1)


def test_saas_live_preview_dispatches_search_change():
    app = SaaSLivePreview()
    html = app.render_fragment()
    change_id = _attr_near(html, "Search customers", "data-otoe-change")

    html = app.dispatch_event(change_id, "arcadia")

    assert 'value="arcadia"' in html
    assert "Arcadia Finance" in html
    assert "1 active" in html
    assert "Northstar Analytics" not in html


def test_saas_live_preview_dispatches_invite_click():
    app = SaaSLivePreview()
    html = app.render_fragment()
    click_id = _attr_near(html, "Invite</button>", "data-otoe-click")

    html = app.dispatch_event(click_id)

    assert "Growth workspace · 1 update" in html
    assert "Brightline Systems 1" in html
    assert "$103,700" in html


def test_saas_live_preview_dispatches_nav_click():
    app = SaaSLivePreview()
    html = app.render_fragment()
    click_id = _button_click_id(html, "Customers")

    html = app.dispatch_event(click_id)

    assert "Customer intelligence" in html
    assert "Account health, plan mix" in html
    assert "Mercury Labs" in html
    assert "Share expansion brief" in html
    assert 'nav-item is-active" type="button" data-otoe-click' in html


def test_saas_live_preview_dispatches_all_section_views():
    expected = {
        "Revenue": "Forecast mix",
        "Automations": "Renewal risk alert",
        "Settings": "Workspace name",
    }

    for label, marker in expected.items():
        app = SaaSLivePreview()
        html = app.render_fragment()
        click_id = _button_click_id(html, label)

        html = app.dispatch_event(click_id)

        assert marker in html
