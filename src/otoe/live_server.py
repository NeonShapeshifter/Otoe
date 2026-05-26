from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from html import escape
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable, Protocol
from urllib.parse import urlsplit


class LivePreviewApp(Protocol):
    def render_fragment(self) -> str:
        raise NotImplementedError

    def dispatch_event(self, event_id: str, *args: Any) -> str:
        raise NotImplementedError


@dataclass(frozen=True)
class LivePreviewStylesheet:
    route: str
    path: Path | None


@dataclass(frozen=True)
class LivePreviewConfig:
    title: str
    css_route: str
    css_path: Path | None
    root_class: str = ""
    extra_css: tuple[LivePreviewStylesheet, ...] = ()

    def stylesheets(self) -> tuple[LivePreviewStylesheet, ...]:
        return (
            *self.extra_css,
            LivePreviewStylesheet(route=self.css_route, path=self.css_path),
        )

    def stylesheet_for(self, route: str) -> LivePreviewStylesheet | None:
        for stylesheet in self.stylesheets():
            if stylesheet.route == route:
                return stylesheet
        return None


LIVE_SCRIPT = r"""
(() => {
  const root = document.getElementById("otoe-root");
  let lastFocusOutsideScope = null;
  let latestEventRequest = 0;

  const escapeSelector = (value) => {
    if (window.CSS && CSS.escape) {
      return CSS.escape(value);
    }
    return value.replace(/["\\]/g, "\\$&");
  };

  const focusSelectorFor = (target) => {
    if (!target?.dataset) {
      return null;
    }
    if (target.dataset.otoeChange) {
      return `[data-otoe-change="${escapeSelector(target.dataset.otoeChange)}"]`;
    }
    if (target.dataset.otoeKeydown) {
      return `[data-otoe-keydown="${escapeSelector(target.dataset.otoeKeydown)}"]`;
    }
    if (target.dataset.otoeClick) {
      return `[data-otoe-click="${escapeSelector(target.dataset.otoeClick)}"]`;
    }
    return null;
  };

  const focusAutoTarget = () => {
    const target = root.querySelector("[data-otoe-autofocus]");
    if (!target || typeof target.focus !== "function") {
      return;
    }
    target.focus();
    if (typeof target.select === "function") {
      target.select();
    }
  };

  const restoreFocusTarget = (selector) => {
    if (!selector) {
      return false;
    }
    const target = root.querySelector(selector);
    if (!target || typeof target.focus !== "function") {
      return false;
    }
    target.focus();
    return true;
  };

  const replaceRoot = (html, activeTarget = null, selectionStart, selectionEnd, restoreSelector = null) => {
    root.innerHTML = html;
    const focusSelector = focusSelectorFor(activeTarget);
    if (!focusSelector) {
      focusAutoTarget();
      return;
    }
    const nextTarget = root.querySelector(focusSelector);
    if (!nextTarget) {
      if (restoreFocusTarget(restoreSelector)) {
        return;
      }
      focusAutoTarget();
      return;
    }
    nextTarget.focus();
    if (
      typeof nextTarget.setSelectionRange === "function"
      && typeof selectionStart === "number"
      && typeof selectionEnd === "number"
    ) {
      nextTarget.setSelectionRange(selectionStart, selectionEnd);
    }
  };

  const focusableSelector = [
    "button:not([disabled])",
    "input:not([disabled])",
    "select:not([disabled])",
    "textarea:not([disabled])",
    "a[href]",
    "[tabindex]:not([tabindex='-1'])",
  ].join(",");

  const visibleFocusable = (scope) => {
    return Array.from(scope.querySelectorAll(focusableSelector)).filter((node) => {
      return node.offsetParent !== null || node === document.activeElement;
    });
  };

  const trapFocus = (event) => {
    if (event.key !== "Tab") {
      return false;
    }
    const scope = event.target.closest("[data-otoe-focus-scope='trap']");
    if (!scope) {
      return false;
    }
    const focusable = visibleFocusable(scope);
    if (!focusable.length) {
      event.preventDefault();
      return true;
    }
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
      return true;
    }
    if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
      return true;
    }
    return false;
  };

  const isInsideRestoringScope = (target) => {
    if (!target) {
      return false;
    }
    return Boolean(target.closest("[data-otoe-focus-scope='trap'][data-otoe-restore-focus='true']"));
  };

  const sendEvent = async (id, args, activeInput = null) => {
    const requestId = ++latestEventRequest;
    const restoreSelector = activeInput && isInsideRestoringScope(activeInput)
      ? lastFocusOutsideScope
      : null;
    if (activeInput && !isInsideRestoringScope(activeInput)) {
      lastFocusOutsideScope = focusSelectorFor(activeInput) || lastFocusOutsideScope;
    }
    try {
      const response = await fetch("/event", {
        method: "POST",
        headers: {"content-type": "application/json"},
        body: JSON.stringify({id, args}),
      });
      const payload = await response.json();
      if (requestId !== latestEventRequest) {
        return;
      }
      if (!payload.ok) {
        throw new Error(payload.error || "Otoe event failed");
      }
      replaceRoot(
        payload.html,
        activeInput,
        activeInput?.selectionStart,
        activeInput?.selectionEnd,
        restoreSelector,
      );
    } catch (error) {
      if (requestId === latestEventRequest) {
        throw error;
      }
    }
  };

  const keyPayload = (event) => ({
    key: event.key,
    ctrlKey: event.ctrlKey,
    metaKey: event.metaKey,
    altKey: event.altKey,
    shiftKey: event.shiftKey,
  });

  const isEditableTarget = (target) => {
    if (!target) {
      return false;
    }
    return target.matches("input, textarea, [contenteditable='true']");
  };

  const shouldSendGlobalKey = (event) => {
    if (event.ctrlKey || event.metaKey || event.key === "Escape") {
      return true;
    }
    return event.key.length === 1 && !isEditableTarget(event.target);
  };

  document.addEventListener("click", (event) => {
    const target = event.target.closest("[data-otoe-click]");
    if (!target) {
      return;
    }
    event.preventDefault();
    sendEvent(target.dataset.otoeClick, [], target);
  });

  document.addEventListener("focusin", (event) => {
    if (!isInsideRestoringScope(event.target)) {
      lastFocusOutsideScope = focusSelectorFor(event.target);
    }
  });

  document.addEventListener("input", (event) => {
    const target = event.target.closest("[data-otoe-change]");
    if (!target) {
      return;
    }
    sendEvent(target.dataset.otoeChange, [target.value], target);
  });

  document.addEventListener("keydown", (event) => {
    if (trapFocus(event)) {
      return;
    }
    const target = event.target.closest("[data-otoe-keydown]");
    if (target) {
      sendEvent(target.dataset.otoeKeydown, [event.key], target);
    }
    const globalTarget = root.querySelector("[data-otoe-global-keydown]");
    if (!globalTarget || !shouldSendGlobalKey(event)) {
      return;
    }
    event.preventDefault();
    sendEvent(globalTarget.dataset.otoeGlobalKeydown, [keyPayload(event)]);
  });
})();
"""


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


def run_live_preview(
    *,
    app_factory: Callable[[], LivePreviewApp],
    config: LivePreviewConfig,
    host: str,
    port: int,
    label: str,
) -> None:
    app = app_factory()

    class Handler(_LivePreviewHandler):
        pass

    Handler.app = app
    Handler.config = config
    server = ThreadingHTTPServer((host, port), Handler)
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
    app: LivePreviewApp
    config: LivePreviewConfig

    def do_GET(self) -> None:
        path = urlsplit(self.path).path
        if path in {"/", "/index.html"}:
            self._send_text(
                render_live_page(self.app, self.config),
                "text/html; charset=utf-8",
            )
            return
        stylesheet = self.config.stylesheet_for(path)
        if stylesheet is not None:
            if stylesheet.path is None:
                self._send_text("", "text/css; charset=utf-8")
                return
            self._send_text(
                stylesheet.path.read_text(encoding="utf-8"),
                "text/css; charset=utf-8",
            )
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
            length = int(self.headers.get("content-length", "0"))
            payload = json.loads(self.rfile.read(length) or b"{}")
            event_id = payload["id"]
            args = payload.get("args", [])
            if not isinstance(args, list):
                raise TypeError("event args must be a list")
            html = self.app.dispatch_event(event_id, *args)
        except Exception as exc:
            self._send_json({"ok": False, "error": str(exc)}, HTTPStatus.BAD_REQUEST)
            return
        self._send_json({"ok": True, "html": html})

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
