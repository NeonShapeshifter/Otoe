from pathlib import Path

from otoe.live_server import (
    LivePreviewConfig,
    LivePreviewStylesheet,
    _LivePreviewState,
    render_live_page,
)


class DummyPreview:
    def render_fragment(self) -> str:
        return '    <button data-otoe-click="x:onClick">Ping</button>'

    def dispatch_event(self, event_id, *args):
        return f"{event_id}:{len(args)}"


def test_render_live_page_wraps_fragment_with_shared_shell():
    html = render_live_page(
        DummyPreview(),
        LivePreviewConfig(
            title="Dummy",
            css_route="/dummy.css",
            css_path=Path("dummy.css"),
            root_class="dummy-root",
        ),
    )

    assert "<!doctype html>" in html
    assert "<title>Dummy</title>" in html
    assert '<link rel="stylesheet" href="/dummy.css">' in html
    assert '<div id="otoe-root" class="dummy-root">' in html
    assert 'data-otoe-click="x:onClick"' in html


def test_render_live_page_links_extra_stylesheets_before_primary_css():
    config = LivePreviewConfig(
        title="Dummy",
        css_route="/dummy.css",
        css_path=Path("dummy.css"),
        extra_css=(
            LivePreviewStylesheet("/theme.css", Path("theme.css")),
            LivePreviewStylesheet("/helpers.css", Path("helpers.css")),
        ),
    )

    html = render_live_page(DummyPreview(), config)

    assert [
        stylesheet.route
        for stylesheet in config.stylesheets()
    ] == ["/theme.css", "/helpers.css", "/dummy.css"]
    assert html.index('href="/theme.css"') < html.index('href="/dummy.css"')
    assert config.stylesheet_for("/helpers.css").path == Path("helpers.css")
    assert config.stylesheet_for("/missing.css") is None


def test_render_live_page_escapes_shell_config_values():
    html = render_live_page(
        DummyPreview(),
        LivePreviewConfig(
            title="<script>alert(1)</script>",
            css_route='"/><script>alert(2)</script>',
            css_path=Path("dummy.css"),
            root_class='root" onclick="alert(3)',
        ),
    )

    assert "<title>&lt;script&gt;alert(1)&lt;/script&gt;</title>" in html
    assert 'href="&quot;/&gt;&lt;script&gt;alert(2)&lt;/script&gt;"' in html
    assert 'class="root&quot; onclick=&quot;alert(3)"' in html
    assert "<script>alert(2)</script>" not in html
    assert 'onclick="alert(3)' not in html


def test_render_live_page_includes_click_input_and_keydown_dispatchers():
    html = render_live_page(
        DummyPreview(),
        LivePreviewConfig(
            title="Dummy",
            css_route="/dummy.css",
            css_path=Path("dummy.css"),
        ),
    )

    assert 'closest("[data-otoe-click]")' in html
    assert 'closest("[data-otoe-change]")' in html
    assert 'closest("[data-otoe-keydown]")' in html
    assert 'querySelector("[data-otoe-global-keydown]")' in html
    assert 'querySelector("[data-otoe-autofocus]")' in html
    assert "[data-otoe-focus-scope='trap']" in html
    assert "trapFocus(event)" in html
    assert "lastFocusOutsideScope" in html
    assert "restoreFocusTarget(restoreSelector)" in html
    assert "focusSelectorFor(activeTarget)" in html
    assert "focusAutoTarget()" in html
    assert "event.key" in html
    assert "ctrlKey" in html
    assert "metaKey" in html
    assert 'fetch("/event"' in html


def test_render_live_page_ignores_stale_event_responses():
    html = render_live_page(
        DummyPreview(),
        LivePreviewConfig(
            title="Dummy",
            css_route="/dummy.css",
            css_path=Path("dummy.css"),
        ),
    )

    assert "latestEventRequest" in html
    assert "liveClientId" in html
    assert "sequence: requestId" in html
    assert "clientId: liveClientId" in html
    assert "requestId !== latestEventRequest" in html


def test_live_preview_state_ignores_stale_event_sequences():
    class StatefulPreview:
        def __init__(self):
            self.events = []

        def render_fragment(self) -> str:
            return f"<p>{','.join(self.events)}</p>"

        def dispatch_event(self, event_id, *args):
            self.events.append(event_id)
            return self.render_fragment()

    app = StatefulPreview()
    state = _LivePreviewState(
        app,
        LivePreviewConfig(
            title="Dummy",
            css_route="/dummy.css",
            css_path=Path("dummy.css"),
        ),
    )

    latest = state.dispatch_payload(
        {"id": "new", "args": [], "clientId": "client-a", "sequence": 2}
    )
    stale = state.dispatch_payload(
        {"id": "old", "args": [], "clientId": "client-a", "sequence": 1}
    )

    assert latest == {"ok": True, "html": "<p>new</p>", "stale": False}
    assert stale == {"ok": True, "html": "<p>new</p>", "stale": True}
    assert app.events == ["new"]
