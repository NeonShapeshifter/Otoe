from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from html import escape
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import RLock, get_ident
from typing import Any, Callable, cast
from urllib.parse import urlsplit

from .live_config import (
    DisposableLivePreviewApp,
    LivePreviewApp,
    LivePreviewConfig,
    LivePreviewStylesheet,
)
from .live_events import LiveEventSequenceTracker, live_event_from_payload
from .live_script import LIVE_SCRIPT
from .scheduler import PostedCallbackQueue, drain_posted

__all__ = [
    "LivePreviewApp",
    "DisposableLivePreviewApp",
    "LivePreviewConfig",
    "LivePreviewStylesheet",
    "LiveEventSequenceTracker",
    "live_event_from_payload",
    "LIVE_SCRIPT",
    "render_live_page",
    "run_live_preview",
    "parse_host_port",
]


MAX_EVENT_BODY_BYTES = 64 * 1024


def render_live_page(app: LivePreviewApp, config: LivePreviewConfig) -> str:
    root_class = (
        f' class="{escape(config.root_class, quote=True)}"'
        if config.root_class
        else ""
    )
    stylesheet_links = "\n".join(
        f'  <link rel="stylesheet" href="{escape(stylesheet.route, quote=True)}">'
        for stylesheet in config.stylesheets()
    )
    fragment = app.render_fragment()
    title = escape(config.title)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
{stylesheet_links}
</head>
<body>
  <div id="otoe-root"{root_class}>
{fragment}
  </div>
  <script>{LIVE_SCRIPT}</script>
</body>
</html>
"""


@dataclass
class _LivePreviewState:
    app: LivePreviewApp
    config: LivePreviewConfig
    posted_callbacks: PostedCallbackQueue = field(default_factory=PostedCallbackQueue)
    lock: RLock = field(default_factory=RLock)
    event_sequences: LiveEventSequenceTracker = field(
        default_factory=LiveEventSequenceTracker
    )

    def render_page(self) -> str:
        with self.lock, self.posted_callbacks.bind():
            drain_posted(queue=self.posted_callbacks)
            return render_live_page(self.app, self.config)

    def dispatch_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        event = live_event_from_payload(payload)

        with self.lock, self.posted_callbacks.bind():
            drain_posted(queue=self.posted_callbacks)
            if not self.event_sequences.accept(event):
                return {
                    "ok": True,
                    "html": self.app.render_fragment(),
                    "stale": True,
                }
            html = self.app.dispatch_event(event.event_id, *event.args)
        return {"ok": True, "html": html, "stale": False}


class _LivePreviewHTTPServer(HTTPServer):
    """HTTP server that owns the state consumed by its request handlers."""

    def __init__(
        self,
        server_address: tuple[str, int],
        request_handler_class: type[BaseHTTPRequestHandler],
        *,
        state: _LivePreviewState,
    ) -> None:
        self.live_preview_state = state
        super().__init__(server_address, request_handler_class)


class _LivePreviewServer:
    """Single-thread live-preview host with explicit shutdown and cleanup."""

    def __init__(
        self,
        *,
        app_factory: Callable[[], LivePreviewApp],
        config: LivePreviewConfig,
        host: str,
        port: int,
    ) -> None:
        self._owner_thread = get_ident()
        self._posted_callbacks = PostedCallbackQueue()
        self._lifecycle_lock = RLock()
        self._serving_thread: int | None = None
        self._closing = False
        self._closed = False
        self._socket_closed = False
        self._app_disposed = False

        try:
            with self._posted_callbacks.bind():
                self.app = app_factory()
        except BaseException as primary_error:
            with self._posted_callbacks.bind():
                _cleanup_after_failure(
                    primary_error,
                    self._posted_callbacks.close,
                    message="Live preview app factory and queue cleanup both failed.",
                )
            raise

        try:
            self.state = _LivePreviewState(
                self.app,
                config,
                posted_callbacks=self._posted_callbacks,
            )
            self._server = _LivePreviewHTTPServer(
                (host, port),
                _LivePreviewHandler,
                state=self.state,
            )
        except BaseException as primary_error:
            with self._posted_callbacks.bind():
                _cleanup_after_failure(
                    primary_error,
                    self._posted_callbacks.close,
                    lambda: _dispose_live_preview_app(self.app),
                    message="Live preview startup and cleanup both failed.",
                )
            raise

    @property
    def server_address(self) -> tuple[str, int]:
        host, port = self._server.server_address[:2]
        return str(host), int(port)

    def serve_forever(self, *, poll_interval: float = 0.5) -> None:
        runtime_thread = get_ident()
        with self._lifecycle_lock:
            if self._closed:
                raise RuntimeError("Live preview server is closed.")
            if self._serving_thread is not None:
                raise RuntimeError("Live preview server is already serving.")
            self._serving_thread = runtime_thread
        try:
            with self._posted_callbacks.activate():
                self._server.serve_forever(poll_interval=poll_interval)
        finally:
            with self._lifecycle_lock:
                self._serving_thread = None

    def shutdown(self) -> None:
        """Ask a running serve loop to stop; call from a different thread."""
        self._server.shutdown()

    def close(self) -> None:
        """Close the socket and dispose the app on its owning runtime thread."""
        with self._lifecycle_lock:
            if (
                self._socket_closed
                and self._posted_callbacks.closed
                and self._app_disposed
            ):
                return
            if self._serving_thread is not None:
                raise RuntimeError(
                    "Live preview server cannot be closed while serve_forever() "
                    "is active; call shutdown() from another thread, wait for "
                    "serve_forever() to return, then close it."
                )
            if self._owner_thread != get_ident():
                raise RuntimeError(
                    "Live preview server must be closed by its owning thread."
                )
            if self._closing:
                return
            self._closing = True
            self._closed = True
            try:
                errors: list[BaseException] = []
                with self._posted_callbacks.bind():
                    if not self._socket_closed:
                        try:
                            self._server.server_close()
                        except BaseException as exc:
                            errors.append(exc)
                        else:
                            self._socket_closed = True
                    if not self._posted_callbacks.closed:
                        try:
                            self._posted_callbacks.close()
                        except BaseException as exc:
                            errors.append(exc)
                    if not self._app_disposed:
                        try:
                            _dispose_live_preview_app(self.app)
                        except BaseException as exc:
                            errors.append(exc)
                        else:
                            self._app_disposed = True
                if len(errors) == 1:
                    raise errors[0]
                if errors:
                    raise BaseExceptionGroup(
                        "Live preview server cleanup failed.",
                        errors,
                    )
            finally:
                self._closing = False


def run_live_preview(
    *,
    app_factory: Callable[[], LivePreviewApp],
    config: LivePreviewConfig,
    host: str,
    port: int,
    label: str,
) -> None:
    server = _LivePreviewServer(
        app_factory=app_factory,
        config=config,
        host=host,
        port=port,
    )
    try:
        bound_host, bound_port = server.server_address
        print(f"{label}: http://{bound_host}:{bound_port}", flush=True)
        server.serve_forever()
    except KeyboardInterrupt as primary_error:
        _cleanup_after_failure(
            primary_error,
            server.close,
            message="Live preview interruption and cleanup both failed.",
        )
    except BaseException as primary_error:
        _cleanup_after_failure(
            primary_error,
            server.close,
            message="Live preview operation and cleanup both failed.",
        )
        raise
    else:
        server.close()


def _cleanup_after_failure(
    primary_error: BaseException,
    *cleanups: Callable[[], None],
    message: str,
) -> None:
    errors: list[BaseException] = [primary_error]
    for cleanup in cleanups:
        try:
            cleanup()
        except BaseException as cleanup_error:
            errors.append(cleanup_error)
    if len(errors) > 1:
        raise BaseExceptionGroup(message, errors) from primary_error


def _dispose_live_preview_app(app: LivePreviewApp) -> None:
    dispose = getattr(app, "dispose", None)
    if callable(dispose):
        cast(DisposableLivePreviewApp, app).dispose()


def parse_host_port(
    *,
    default_host: str = "127.0.0.1",
    default_port: int,
) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default=default_host)
    parser.add_argument("--port", default=default_port, type=int)
    return parser.parse_args()


class _LivePreviewHandler(BaseHTTPRequestHandler):
    state: _LivePreviewState

    def _preview_state(self) -> _LivePreviewState:
        server = getattr(self, "server", None)
        state = getattr(server, "live_preview_state", None)
        if isinstance(state, _LivePreviewState):
            return state
        return self.state

    def do_GET(self) -> None:
        state = self._preview_state()
        path = urlsplit(self.path).path
        if path in {"/", "/index.html"}:
            self._send_text(
                state.render_page(),
                "text/html; charset=utf-8",
            )
            return
        stylesheet = state.config.stylesheet_for(path)
        if stylesheet is not None:
            self._send_stylesheet(stylesheet)
            return
        if path == "/health":
            self._send_json({"ok": True})
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        path = urlsplit(self.path).path
        if path != "/event":
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        try:
            payload = self._read_event_payload()
            result = self._preview_state().dispatch_payload(payload)
        except _PayloadTooLargeError as exc:
            self._send_json(
                {"ok": False, "error": str(exc)},
                HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
            )
            return
        except Exception as exc:
            self._send_json({"ok": False, "error": str(exc)}, HTTPStatus.BAD_REQUEST)
            return
        self._send_json(result)

    def log_message(self, fmt: str, *args: Any) -> None:
        return

    def _send_text(
        self,
        body: str,
        content_type: str,
        status: HTTPStatus = HTTPStatus.OK,
    ) -> None:
        encoded = body.encode()
        self.send_response(status)
        self.send_header("content-type", content_type)
        self.send_header("content-length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def _send_json(
        self,
        body: dict[str, Any],
        status: HTTPStatus = HTTPStatus.OK,
    ) -> None:
        self._send_text(
            json.dumps(body),
            "application/json; charset=utf-8",
            status,
        )

    def _send_stylesheet(self, stylesheet: LivePreviewStylesheet) -> None:
        if stylesheet.path is None:
            self._send_text("", "text/css; charset=utf-8")
            return
        try:
            body = stylesheet.path.read_text(encoding="utf-8")
        except FileNotFoundError:
            self.send_error(HTTPStatus.NOT_FOUND, "Stylesheet not found")
            return
        except (PermissionError, OSError, UnicodeError):
            self.send_error(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                "Stylesheet could not be read",
            )
            return
        self._send_text(body, "text/css; charset=utf-8")

    def _read_event_payload(self) -> dict[str, Any]:
        raw_length = self.headers.get("content-length", "0")
        try:
            length = int(raw_length)
        except ValueError as exc:
            raise ValueError("invalid Content-Length") from exc
        if length < 0:
            raise ValueError("invalid Content-Length")
        if length > MAX_EVENT_BODY_BYTES:
            raise _PayloadTooLargeError(
                f"event payload exceeds {MAX_EVENT_BODY_BYTES} bytes"
            )

        raw_body = self.rfile.read(length) or b"{}"
        try:
            payload = json.loads(raw_body)
        except json.JSONDecodeError as exc:
            raise ValueError("invalid JSON event payload") from exc
        if not isinstance(payload, dict):
            raise TypeError("event payload must be a JSON object")
        return payload


class _PayloadTooLargeError(ValueError):
    pass
