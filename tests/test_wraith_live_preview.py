import re

from examples.wraith.live_preview import WraithLivePreview


def _attr_near(html, marker, attr):
    index = html.index(marker)
    start = max(0, index - 220)
    end = min(len(html), index + 220)
    match = re.search(rf'{attr}="([^"]+)"', html[start:end])
    assert match is not None
    return match.group(1)


def test_wraith_live_preview_dispatches_stealth_click():
    app = WraithLivePreview()
    html = app.render_fragment()
    click_id = _attr_near(html, "ST</button>", "data-otoe-click")

    html = app.dispatch_event(click_id)

    assert "topbar-stealth is-active" not in html
    assert "topbar-stealth" in html


def test_wraith_live_preview_dispatches_search_change():
    app = WraithLivePreview()
    html = app.render_fragment()
    change_id = _attr_near(html, "SEARCH QUICK ACTIONS", "data-otoe-change")

    html = app.dispatch_event(change_id, "rf")

    assert 'value="rf"' in html
    assert "FILTER: QUERY" in html
    assert "RF Survey" in html
    assert "WiFi Scan" not in html


def test_wraith_live_preview_dispatches_next_page():
    app = WraithLivePreview()
    html = app.render_fragment()
    click_id = _attr_near(html, "NEXT</button>", "data-otoe-click")

    html = app.dispatch_event(click_id)

    assert "PAGE 2/2" in html
    assert "BLE Sweep" in html
