import json
from io import BytesIO
from pathlib import Path
from typing import Any

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


def test_live_preview_state_tracks_stale_sequences_per_client():
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

    first_client = state.dispatch_payload(
        {"id": "a1", "args": [], "clientId": "client-a", "sequence": 1}
    )
    second_client = state.dispatch_payload(
        {"id": "b1", "args": [], "clientId": "client-b", "sequence": 1}
    )
    stale_first_client = state.dispatch_payload(
        {"id": "a0", "args": [], "clientId": "client-a", "sequence": 1}
    )

    assert first_client == {"ok": True, "html": "<p>a1</p>", "stale": False}
    assert second_client == {"ok": True, "html": "<p>a1,b1</p>", "stale": False}
    assert stale_first_client == {"ok": True, "html": "<p>a1,b1</p>", "stale": True}
    assert app.events == ["a1", "b1"]


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


def test_live_event_endpoint_rejects_sequence_without_client_id():
    status, payload = _post_event(
        _live_preview_state(),
        {"id": "x:onClick", "args": [], "sequence": 1},
    )

    assert status == 400
    assert payload == {
        "ok": False,
        "error": "event clientId must be a non-empty string",
    }


def test_live_event_endpoint_rejects_non_positive_sequence():
    status, payload = _post_event(
        _live_preview_state(),
        {"id": "x:onClick", "args": [], "clientId": "client-a", "sequence": 0},
    )

    assert status == 400
    assert payload == {
        "ok": False,
        "error": "event sequence must be a positive integer",
    }


def test_live_event_endpoint_rejects_invalid_json():
    status, payload = _post_event_bytes(_live_preview_state(), b'{"id":')

    assert status == 400
    assert payload == {"ok": False, "error": "invalid JSON event payload"}


def test_live_event_errors_use_json_response_content_type():
    status, content_type, body = _post_event_text_response(
        _live_preview_state(),
        b'{"id":',
    )

    assert status == 400
    assert content_type == "application/json; charset=utf-8"
    assert json.loads(body) == {"ok": False, "error": "invalid JSON event payload"}


def test_live_event_endpoint_rejects_invalid_content_length():
    status, payload = _post_event_bytes(
        _live_preview_state(),
        b"{}",
        content_length="not-a-number",
    )

    assert status == 400
    assert payload == {"ok": False, "error": "invalid Content-Length"}


def test_live_event_endpoint_rejects_negative_content_length():
    status, payload = _post_event_bytes(
        _live_preview_state(),
        b"{}",
        content_length="-1",
    )

    assert status == 400
    assert payload == {"ok": False, "error": "invalid Content-Length"}


def test_live_event_endpoint_rejects_non_object_payload():
    status, payload = _post_event_bytes(_live_preview_state(), b"[]")

    assert status == 400
    assert payload == {"ok": False, "error": "event payload must be a JSON object"}


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


def test_live_event_endpoint_rejects_unknown_path():
    status, payload = _post_event_bytes(
        _live_preview_state(),
        b"{}",
        path="/missing",
    )

    assert status == 404
    assert payload is None


def test_live_preview_handler_serves_page_stylesheets_health_and_404(tmp_path):
    stylesheet = tmp_path / "dummy.css"
    stylesheet.write_text(".dummy { color: red; }\n", encoding="utf-8")
    state = _LivePreviewState(
        DummyPreview(),
        LivePreviewConfig(
            title="Dummy",
            css_route="/dummy.css",
            css_path=stylesheet,
            extra_css=(LivePreviewStylesheet("/empty.css", None),),
        ),
    )

    root = _get_path(state, "/")
    index = _get_path(state, "/index.html")
    css = _get_path(state, "/dummy.css")
    empty_css = _get_path(state, "/empty.css")
    health = _get_path(state, "/health")
    missing = _get_path(state, "/missing")

    assert root == (200, "text/html; charset=utf-8", root[2])
    assert "<title>Dummy</title>" in root[2]
    assert index[0] == 200
    assert css == (200, "text/css; charset=utf-8", ".dummy { color: red; }\n")
    assert empty_css == (200, "text/css; charset=utf-8", "")
    assert health == (200, "application/json; charset=utf-8", '{"ok": true}')
    assert missing[0] == 404


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
    *,
    content_length: str | None = None,
    path: str = "/event",
) -> tuple[int, dict[str, Any] | None]:
    return _post_event_request(
        state,
        body,
        content_length=str(len(body)) if content_length is None else content_length,
        path=path,
    )


def _post_event_request(
    state: _LivePreviewState,
    body: bytes,
    *,
    content_length: str,
    path: str,
) -> tuple[int, dict[str, Any] | None]:
    class Handler(_LivePreviewHandler):
        captured_status = 0
        captured_body: dict[str, Any] | None = None

        def _send_json(self, body, status=200):
            self.captured_status = int(status)
            self.captured_body = body

        def send_error(self, code, message=None, explain=None):
            self.captured_status = int(code)
            self.captured_body = None

    handler = object.__new__(Handler)
    handler.state = state
    handler.path = path
    handler.headers = {"content-length": content_length}
    handler.rfile = BytesIO(body)
    handler.do_POST()
    return handler.captured_status, handler.captured_body


def _post_event_text_response(
    state: _LivePreviewState,
    body: bytes,
    *,
    content_length: str | None = None,
    path: str = "/event",
) -> tuple[int, str, str]:
    class Handler(_LivePreviewHandler):
        captured_status = 0
        captured_content_type = ""
        captured_body = ""

        def _send_text(self, body, content_type, status=200):
            self.captured_status = int(status)
            self.captured_content_type = content_type
            self.captured_body = body

        def send_error(self, code, message=None, explain=None):
            self.captured_status = int(code)
            self.captured_content_type = "text/html"
            self.captured_body = message or ""

    handler = object.__new__(Handler)
    handler.state = state
    handler.path = path
    handler.headers = {
        "content-length": str(len(body)) if content_length is None else content_length
    }
    handler.rfile = BytesIO(body)
    handler.do_POST()
    return (
        handler.captured_status,
        handler.captured_content_type,
        handler.captured_body,
    )


def _get_path(state: _LivePreviewState, path: str) -> tuple[int, str, str]:
    class Handler(_LivePreviewHandler):
        captured_status = 0
        captured_content_type = ""
        captured_body = ""

        def _send_text(self, body, content_type, status=200):
            self.captured_status = int(status)
            self.captured_content_type = content_type
            self.captured_body = body

        def send_error(self, code, message=None, explain=None):
            self.captured_status = int(code)
            self.captured_content_type = "text/html"
            self.captured_body = message or ""

    handler = object.__new__(Handler)
    handler.state = state
    handler.path = path
    handler.do_GET()
    return (
        handler.captured_status,
        handler.captured_content_type,
        handler.captured_body,
    )
