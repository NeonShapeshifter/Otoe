import json
import threading
from http.client import HTTPConnection
from io import BytesIO
from pathlib import Path
from typing import Any, cast

import otoe.live_server as live_server_module
import pytest
from otoe import Text, component, mount, on_cleanup
from otoe.cli_dev import _RenderTargetPreview
from otoe.live_server import (
    LivePreviewConfig,
    LivePreviewStylesheet,
    MAX_EVENT_BODY_BYTES,
    _LivePreviewHandler,
    _LivePreviewServer,
    _LivePreviewState,
    render_live_page,
    run_live_preview,
)
from otoe.scheduler import capture_post, drain_posted, post


class DummyPreview:
    def render_fragment(self) -> str:
        return '    <button data-otoe-click="x:onClick">Ping</button>'

    def dispatch_event(self, event_id, *args):
        return f"{event_id}:{len(args)}"


def test_concurrent_live_hosts_only_drain_their_own_runtime_queue():
    servers = [
        _LivePreviewServer(
            app_factory=DummyPreview,
            config=_live_config(),
            host="127.0.0.1",
            port=0,
        )
        for _ in range(2)
    ]
    hosts = [threading.Thread(target=server.serve_forever) for server in servers]
    callback_threads: list[list[int]] = [[], []]
    try:
        for host in hosts:
            host.start()
        for server in servers:
            assert _request_live_server(server, "/health") == (200, '{"ok": true}')

        with pytest.raises(RuntimeError, match="multiple active runtimes"):
            post(lambda: None)

        for index, server in enumerate(servers):
            server.state.posted_callbacks.post(
                lambda index=index: callback_threads[index].append(
                    threading.get_ident()
                )
            )

        assert _request_live_server(servers[1], "/")[0] == 200
        assert callback_threads == [[], [hosts[1].ident]]

        assert _request_live_server(servers[0], "/")[0] == 200
        assert callback_threads == [[hosts[0].ident], [hosts[1].ident]]
    finally:
        for server in servers:
            server.shutdown()
        for host in hosts:
            host.join(timeout=2)
        for server in servers:
            server.close()

    assert all(not host.is_alive() for host in hosts)


def test_live_preview_server_disposes_app_when_bind_fails(monkeypatch):
    class DisposablePreview(DummyPreview):
        def __init__(self):
            self.dispose_calls = 0

        def dispose(self):
            self.dispose_calls += 1

    app = DisposablePreview()

    def fail_bind(address, handler, *, state):
        raise OSError("bind failed")

    monkeypatch.setattr(live_server_module, "_LivePreviewHTTPServer", fail_bind)

    with pytest.raises(OSError, match="bind failed"):
        _LivePreviewServer(
            app_factory=lambda: app,
            config=_live_config(),
            host="127.0.0.1",
            port=0,
        )

    assert app.dispose_calls == 1


def test_live_preview_factory_failure_drains_and_seals_its_bound_queue():
    seen: list[str] = []
    posters = []

    def fail_factory():
        poster = capture_post()
        posters.append(poster)
        poster(lambda: seen.append("accepted"))
        raise RuntimeError("factory failed")

    with pytest.raises(RuntimeError, match="factory failed"):
        _LivePreviewServer(
            app_factory=fail_factory,
            config=_live_config(),
            host="127.0.0.1",
            port=0,
        )

    assert seen == ["accepted"]
    with pytest.raises(RuntimeError, match="not accepting work"):
        posters[0](lambda: None)


def test_live_preview_bind_failure_preserves_queue_and_app_cleanup_failures(
    monkeypatch,
):
    class BrokenPreview(DummyPreview):
        def dispose(self):
            raise SystemExit("app cleanup failed")

    def fail_queue_callback():
        raise KeyboardInterrupt("queue cleanup failed")

    def app_factory():
        post(fail_queue_callback)
        return BrokenPreview()

    def fail_bind(address, handler, *, state):
        raise OSError("bind failed")

    monkeypatch.setattr(live_server_module, "_LivePreviewHTTPServer", fail_bind)

    with pytest.raises(BaseExceptionGroup) as caught:
        _LivePreviewServer(
            app_factory=app_factory,
            config=_live_config(),
            host="127.0.0.1",
            port=0,
        )

    assert [str(error) for error in caught.value.exceptions] == [
        "bind failed",
        "queue cleanup failed",
        "app cleanup failed",
    ]


def test_live_preview_server_close_is_idempotent(monkeypatch):
    class DisposablePreview(DummyPreview):
        def __init__(self):
            self.dispose_calls = 0

        def dispose(self):
            self.dispose_calls += 1

    class FakeHTTPServer:
        server_address = ("127.0.0.1", 43210)

        def __init__(self, address, handler, *, state):
            self.close_calls = 0

        def server_close(self):
            self.close_calls += 1

    app = DisposablePreview()
    monkeypatch.setattr(live_server_module, "_LivePreviewHTTPServer", FakeHTTPServer)
    server = _LivePreviewServer(
        app_factory=lambda: app,
        config=_live_config(),
        host="127.0.0.1",
        port=0,
    )

    server.close()
    server.close()

    assert server._server.close_calls == 1
    assert app.dispose_calls == 1


def test_live_preview_server_foreign_close_rejects_before_cleanup(monkeypatch):
    class DisposablePreview(DummyPreview):
        def __init__(self):
            self.dispose_calls = 0

        def dispose(self):
            self.dispose_calls += 1

    class FakeHTTPServer:
        server_address = ("127.0.0.1", 43210)

        def __init__(self, address, handler, *, state):
            self.close_calls = 0

        def server_close(self):
            self.close_calls += 1

    app = DisposablePreview()
    monkeypatch.setattr(live_server_module, "_LivePreviewHTTPServer", FakeHTTPServer)
    server = _LivePreviewServer(
        app_factory=lambda: app,
        config=_live_config(),
        host="127.0.0.1",
        port=0,
    )
    errors: list[BaseException] = []

    def close_from_foreign_thread():
        try:
            server.close()
        except BaseException as exc:
            errors.append(exc)

    thread = threading.Thread(target=close_from_foreign_thread)
    thread.start()
    thread.join()

    assert len(errors) == 1
    assert isinstance(errors[0], RuntimeError)
    assert str(errors[0]) == "Live preview server must be closed by its owning thread."
    assert server._server.close_calls == 0
    assert app.dispose_calls == 0
    assert server._posted_callbacks.closed is False

    server.close()
    assert server._server.close_calls == 1
    assert app.dispose_calls == 1


def test_live_preview_server_close_drains_queue_before_disposing_app(monkeypatch):
    events: list[str] = []
    posters = []

    class FakeHTTPServer:
        server_address = ("127.0.0.1", 43210)

        def __init__(self, address, handler, *, state):
            pass

        def server_close(self):
            events.append("socket")

    class DisposablePreview(DummyPreview):
        def dispose(self):
            events.append("dispose")

    def app_factory():
        poster = capture_post()
        posters.append(poster)
        poster(lambda: events.append("callback"))
        return DisposablePreview()

    monkeypatch.setattr(live_server_module, "_LivePreviewHTTPServer", FakeHTTPServer)

    server = _LivePreviewServer(
        app_factory=app_factory,
        config=_live_config(),
        host="127.0.0.1",
        port=0,
    )

    server.close()

    assert events == ["socket", "callback", "dispose"]
    with pytest.raises(RuntimeError, match="not accepting work"):
        posters[0](lambda: None)


def test_live_preview_server_rejects_close_while_serving_before_app_disposal(
    monkeypatch,
):
    events: list[str] = []

    class DisposablePreview(DummyPreview):
        def dispose(self):
            events.append("dispose")

    class FakeHTTPServer:
        server_address = ("127.0.0.1", 43210)

        def __init__(self, address, handler, *, state):
            self.state = state
            self.owner = None

        def serve_forever(self, *, poll_interval):
            assert self.owner is not None
            self.state.posted_callbacks.post(self.owner.close)
            self.state.posted_callbacks.post(lambda: events.append("accepted callback"))
            with pytest.raises(RuntimeError, match="cannot be closed while"):
                self.state.render_page()

        def server_close(self):
            events.append("socket")

    monkeypatch.setattr(live_server_module, "_LivePreviewHTTPServer", FakeHTTPServer)
    server = _LivePreviewServer(
        app_factory=DisposablePreview,
        config=_live_config(),
        host="127.0.0.1",
        port=0,
    )
    server._server.owner = server

    server.serve_forever()

    assert events == ["accepted callback"]
    assert server._app_disposed is False
    server.close()
    assert events == ["accepted callback", "socket", "dispose"]


def test_live_preview_app_cleanup_posts_cannot_escape_its_closed_queue(monkeypatch):
    assert drain_posted() == 0
    escaped: list[str] = []

    class PostingPreview(DummyPreview):
        def dispose(self):
            post(lambda: escaped.append("escaped"))

    class FakeHTTPServer:
        server_address = ("127.0.0.1", 43210)

        def __init__(self, address, handler, *, state):
            pass

        def server_close(self):
            pass

    monkeypatch.setattr(live_server_module, "_LivePreviewHTTPServer", FakeHTTPServer)
    server = _LivePreviewServer(
        app_factory=PostingPreview,
        config=_live_config(),
        host="127.0.0.1",
        port=0,
    )

    with pytest.raises(RuntimeError, match="not accepting work"):
        server.close()

    assert escaped == []
    assert drain_posted() == 0
    assert server._posted_callbacks.closed is True


def test_live_preview_server_aggregates_socket_and_app_cleanup_errors(monkeypatch):
    class BrokenPreview(DummyPreview):
        def __init__(self):
            self.dispose_calls = 0

        def dispose(self):
            self.dispose_calls += 1
            if self.dispose_calls == 1:
                raise RuntimeError("app cleanup failed")

    class BrokenHTTPServer:
        server_address = ("127.0.0.1", 43210)

        def __init__(self, address, handler, *, state):
            self.close_calls = 0

        def server_close(self):
            self.close_calls += 1
            if self.close_calls == 1:
                raise OSError("socket cleanup failed")

    monkeypatch.setattr(live_server_module, "_LivePreviewHTTPServer", BrokenHTTPServer)
    app = BrokenPreview()

    def fail_queue_callback():
        raise KeyboardInterrupt("queue cleanup failed")

    def app_factory():
        post(fail_queue_callback)
        return app

    server = _LivePreviewServer(
        app_factory=app_factory,
        config=_live_config(),
        host="127.0.0.1",
        port=0,
    )

    with pytest.raises(BaseExceptionGroup) as caught:
        server.close()

    assert [str(error) for error in caught.value.exceptions] == [
        "socket cleanup failed",
        "queue cleanup failed",
        "app cleanup failed",
    ]

    server.close()
    server.close()

    assert server._server.close_calls == 2
    assert app.dispose_calls == 2


def test_live_preview_server_does_not_repeat_successful_socket_cleanup(monkeypatch):
    class EventuallyDisposablePreview(DummyPreview):
        def __init__(self):
            self.dispose_calls = 0

        def dispose(self):
            self.dispose_calls += 1
            if self.dispose_calls == 1:
                raise RuntimeError("app cleanup failed")

    class FakeHTTPServer:
        server_address = ("127.0.0.1", 43210)

        def __init__(self, address, handler, *, state):
            self.close_calls = 0

        def server_close(self):
            self.close_calls += 1

    app = EventuallyDisposablePreview()
    monkeypatch.setattr(live_server_module, "_LivePreviewHTTPServer", FakeHTTPServer)
    server = _LivePreviewServer(
        app_factory=lambda: app,
        config=_live_config(),
        host="127.0.0.1",
        port=0,
    )

    with pytest.raises(RuntimeError, match="app cleanup failed"):
        server.close()

    server.close()

    assert server._server.close_calls == 1
    assert app.dispose_calls == 2


def test_live_preview_server_does_not_repeat_successful_app_cleanup(monkeypatch):
    class DisposablePreview(DummyPreview):
        def __init__(self):
            self.dispose_calls = 0

        def dispose(self):
            self.dispose_calls += 1

    class EventuallyClosingHTTPServer:
        server_address = ("127.0.0.1", 43210)

        def __init__(self, address, handler, *, state):
            self.close_calls = 0

        def server_close(self):
            self.close_calls += 1
            if self.close_calls == 1:
                raise OSError("socket cleanup failed")

    app = DisposablePreview()
    monkeypatch.setattr(
        live_server_module,
        "_LivePreviewHTTPServer",
        EventuallyClosingHTTPServer,
    )
    server = _LivePreviewServer(
        app_factory=lambda: app,
        config=_live_config(),
        host="127.0.0.1",
        port=0,
    )

    with pytest.raises(OSError, match="socket cleanup failed"):
        server.close()

    server.close()

    assert server._server.close_calls == 2
    assert app.dispose_calls == 1


def test_run_live_preview_reports_bound_ephemeral_port_and_closes(monkeypatch, capsys):
    calls = []

    class FakeLivePreviewServer:
        server_address = ("127.0.0.1", 43210)

        def __init__(self, **kwargs):
            calls.append(("init", kwargs["port"]))

        def serve_forever(self):
            calls.append(("serve",))

        def close(self):
            calls.append(("close",))

    monkeypatch.setattr(live_server_module, "_LivePreviewServer", FakeLivePreviewServer)

    run_live_preview(
        app_factory=DummyPreview,
        config=_live_config(),
        host="127.0.0.1",
        port=0,
        label="Probe",
    )

    assert capsys.readouterr().out == "Probe: http://127.0.0.1:43210\n"
    assert calls == [("init", 0), ("serve",), ("close",)]


def test_run_live_preview_closes_when_reporting_bound_address_fails(monkeypatch):
    calls = []

    class FakeLivePreviewServer:
        def __init__(self, **kwargs):
            pass

        @property
        def server_address(self):
            raise RuntimeError("address failed")

        def close(self):
            calls.append("close")

    monkeypatch.setattr(live_server_module, "_LivePreviewServer", FakeLivePreviewServer)

    with pytest.raises(RuntimeError, match="address failed"):
        run_live_preview(
            app_factory=DummyPreview,
            config=_live_config(),
            host="127.0.0.1",
            port=0,
            label="Probe",
        )

    assert calls == ["close"]


def test_run_live_preview_preserves_operation_and_cleanup_failures(monkeypatch):
    class FakeLivePreviewServer:
        server_address = ("127.0.0.1", 43210)

        def __init__(self, **kwargs):
            pass

        def serve_forever(self):
            raise RuntimeError("serve failed")

        def close(self):
            raise OSError("close failed")

    monkeypatch.setattr(live_server_module, "_LivePreviewServer", FakeLivePreviewServer)

    with pytest.raises(BaseExceptionGroup) as caught:
        run_live_preview(
            app_factory=DummyPreview,
            config=_live_config(),
            host="127.0.0.1",
            port=0,
            label="Probe",
        )

    assert [str(error) for error in caught.value.exceptions] == [
        "serve failed",
        "close failed",
    ]


def test_run_live_preview_preserves_interruption_and_cleanup_failures(monkeypatch):
    class FakeLivePreviewServer:
        server_address = ("127.0.0.1", 43210)

        def __init__(self, **kwargs):
            pass

        def serve_forever(self):
            raise KeyboardInterrupt("serve interrupted")

        def close(self):
            raise SystemExit("close failed")

    monkeypatch.setattr(live_server_module, "_LivePreviewServer", FakeLivePreviewServer)

    with pytest.raises(BaseExceptionGroup) as caught:
        run_live_preview(
            app_factory=DummyPreview,
            config=_live_config(),
            host="127.0.0.1",
            port=0,
            label="Probe",
        )

    assert [str(error) for error in caught.value.exceptions] == [
        "serve interrupted",
        "close failed",
    ]


def test_render_target_preview_dispose_unmounts_exactly_once():
    cleanups = []

    @component
    def PreviewRoot():
        on_cleanup(lambda: cleanups.append("cleanup"))
        return Text("Ready")

    preview = _RenderTargetPreview(mount(PreviewRoot()))

    preview.dispose()
    preview.dispose()

    assert cleanups == ["cleanup"]


def _live_config():
    return LivePreviewConfig(
        title="Dummy",
        css_route="/dummy.css",
        css_path=None,
    )


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


def test_live_preview_handler_missing_stylesheet_returns_404(tmp_path):
    stylesheet = tmp_path / "missing.css"
    state = _LivePreviewState(
        DummyPreview(),
        LivePreviewConfig(
            title="Dummy",
            css_route="/dummy.css",
            css_path=stylesheet,
        ),
    )

    status, content_type, body = _get_path(state, "/dummy.css")

    assert status == 404
    assert content_type == "text/html"
    assert body == "Stylesheet not found"
    assert str(stylesheet) not in body


def test_live_preview_handler_unreadable_stylesheet_returns_500():
    state = _LivePreviewState(
        DummyPreview(),
        LivePreviewConfig(
            title="Dummy",
            css_route="/dummy.css",
            css_path=cast(Path, _BrokenStylesheetPath(PermissionError("secret path"))),
        ),
    )

    status, content_type, body = _get_path(state, "/dummy.css")

    assert status == 500
    assert content_type == "text/html"
    assert body == "Stylesheet could not be read"
    assert "secret path" not in body


def test_live_preview_handler_stylesheet_read_error_returns_500():
    state = _LivePreviewState(
        DummyPreview(),
        LivePreviewConfig(
            title="Dummy",
            css_route="/dummy.css",
            css_path=cast(Path, _BrokenStylesheetPath(OSError("secret path"))),
        ),
    )

    status, content_type, body = _get_path(state, "/dummy.css")

    assert status == 500
    assert content_type == "text/html"
    assert body == "Stylesheet could not be read"
    assert "secret path" not in body


class _BrokenStylesheetPath:
    def __init__(self, error: Exception):
        self._error = error

    def read_text(self, *, encoding: str) -> str:
        raise self._error


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


def _request_live_server(
    server: _LivePreviewServer,
    path: str,
) -> tuple[int, str]:
    host, port = server.server_address
    connection = HTTPConnection(host, port, timeout=2)
    try:
        connection.request("GET", path)
        response = connection.getresponse()
        return response.status, response.read().decode("utf-8")
    finally:
        connection.close()
