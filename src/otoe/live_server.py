from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from html import escape
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import RLock
from typing import Any, Callable
from urllib.parse import urlsplit

from .live_config import LivePreviewApp, LivePreviewConfig, LivePreviewStylesheet
from .live_events import LiveEventSequenceTracker, live_event_from_payload
from .live_script import LIVE_SCRIPT
from .scheduler import drain_posted

__all__ = [
    "LivePreviewApp",
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
    lock: RLock = field(default_factory=RLock)
    event_sequences: LiveEventSequenceTracker = field(
        default_factory=LiveEventSequenceTracker
    )

    def render_page(self) -> str:
        with self.lock:
            drain_posted()
            return render_live_page(self.app, self.config)

    def dispatch_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        event = live_event_from_payload(payload)

        with self.lock:
            drain_posted()
            if not self.event_sequences.accept(event):
                return {
                    "ok": True,
                    "html": self.app.render_fragment(),
                    "stale": True,
                }
            html = self.app.dispatch_event(event.event_id, *event.args)
        return {"ok": True, "html": html, "stale": False}


def run_live_preview(
    *,
    app_factory: Callable[[], LivePreviewApp],
    config: LivePreviewConfig,
    host: str,
    port: int,
    label: str,
) -> None:
    state = _LivePreviewState(app_factory(), config)

    class Handler(_LivePreviewHandler):
        pass

    Handler.state = state
    server = HTTPServer((host, port), Handler)
    print(f"{label}: http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


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

    def do_GET(self) -> None:
        path = urlsplit(self.path).path
        if path in {"/", "/index.html"}:
            self._send_text(
                self.state.render_page(),
                "text/html; charset=utf-8",
            )
            return
        stylesheet = self.state.config.stylesheet_for(path)
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
            result = self.state.dispatch_payload(payload)
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
