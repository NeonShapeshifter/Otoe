import json
from io import BytesIO
from pathlib import Path

from otoe.live_server import (
    LivePreviewConfig,
    LivePreviewStylesheet,
    MAX_EVENT_BODY_BYTES,
    _LivePreviewHandler,
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


def test_live_event_endpoint_accepts_valid_payload():
    state = _live_preview_state()

    status, payload = _post_event(
        state,
        {"id": "x:onClick", "args": ["value"], "clientId": "client-a", "sequence": 1},
    )

    assert status == 200
    assert payload == {"ok": True, "html": "x:onClick:1", "stale": False}


def test_live_event_endpoint_rejects_missing_id():
    status, payload = _post_event(_live_preview_state(), {"args": []})

    assert status == 400
    assert payload == {"ok": False, "error": "event id must be a non-empty string"}


def test_live_event_endpoint_rejects_non_string_id():
    status, payload = _post_event(_live_preview_state(), {"id": 12, "args": []})

    assert status == 400
    assert payload == {"ok": False, "error": "event id must be a non-empty string"}


def test_live_event_endpoint_rejects_non_list_args():
    status, payload = _post_event(_live_preview_state(), {"id": "x:onClick", "args": {}})

    assert status == 400
    assert payload == {"ok": False, "error": "event args must be a list"}


def test_live_event_endpoint_rejects_invalid_json():
    status, payload = _post_event_bytes(_live_preview_state(), b'{"id":')

    assert status == 400
    assert payload == {"ok": False, "error": "invalid JSON event payload"}


def test_live_event_endpoint_rejects_oversized_body():
    status, payload = _post_event_bytes(
        _live_preview_state(),
        b"x" * (MAX_EVENT_BODY_BYTES + 1),
    )

    assert status == 413
    assert payload == {
        "ok": False,
        "error": f"event payload exceeds {MAX_EVENT_BODY_BYTES} bytes",
    }


def _live_preview_state() -> _LivePreviewState:
    return _LivePreviewState(
        DummyPreview(),
        LivePreviewConfig(
            title="Dummy",
            css_route="/dummy.css",
            css_path=Path("dummy.css"),
        ),
    )


def _post_event(
    state: _LivePreviewState,
    payload: dict,
) -> tuple[int, dict]:
    return _post_event_bytes(
        state,
        json.dumps(payload).encode("utf-8"),
    )


def _post_event_bytes(
    state: _LivePreviewState,
    body: bytes,
) -> tuple[int, dict]:
    class Handler(_LivePreviewHandler):
        captured_status = 0
        captured_body: dict | None = None

        def _send_json(self, body, status=200):
            self.captured_status = int(status)
            self.captured_body = body

    handler = object.__new__(Handler)
    handler.state = state
    handler.path = "/event"
    handler.headers = {"content-length": str(len(body))}
    handler.rfile = BytesIO(body)
    handler.do_POST()
    assert handler.captured_body is not None
    return handler.captured_status, handler.captured_body
