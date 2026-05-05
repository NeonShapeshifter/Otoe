from __future__ import annotations

import argparse
import json
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from examples.saas.overview import SaaSOverview
from examples.saas.preview import CUSTOMERS, DEALS
from otoe import LiveHtmlRenderer, computed, mount, signal


ROOT = Path(__file__).resolve().parents[2]
CSS_PATH = ROOT / "preview" / "saas.css"


class SaaSLivePreview:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self.renderer = LiveHtmlRenderer()

        self.query = signal("")
        self.invites = signal(0)
        self.active_section = signal("Overview")
        self.all_deals = signal([dict(deal) for deal in DEALS])
        self.all_customers = signal([dict(customer) for customer in CUSTOMERS])
        self.workspace = computed(self._workspace_label)
        self.filtered_deals = computed(self._filtered_deals)
        self.filtered_customers = computed(self._filtered_customers)

        self.app = mount(
            SaaSOverview(
                query=self.query,
                workspace=self.workspace,
                active_section=self.active_section,
                deals=self.filtered_deals,
                customers=self.filtered_customers,
                on_search=self._search,
                on_invite=self._add_opportunity,
                on_nav=self._navigate,
            )
        )

    def render_fragment(self) -> str:
        with self._lock:
            self.renderer.clear()
            return self.renderer.render(self.app, pretty=True, indent=4)

    def render_page(self) -> str:
        fragment = self.render_fragment()
        return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Otoe SaaS Live Preview</title>
  <link rel="stylesheet" href="/saas.css">
</head>
<body>
  <div id="otoe-root">
{fragment}
  </div>
  <script>{LIVE_SCRIPT}</script>
</body>
</html>
"""

    def dispatch_event(self, event_id: str, *args: Any) -> str:
        with self._lock:
            self.renderer.dispatch(event_id, *args)
            return self.render_fragment()

    def _workspace_label(self) -> str:
        if self.invites.value == 0:
            return "Growth workspace"
        if self.invites.value == 1:
            return "Growth workspace · 1 update"
        return f"Growth workspace · {self.invites.value} updates"

    def _search(self, value: str) -> None:
        self.query.set(value)

    def _navigate(self, section: str) -> None:
        self.active_section.set(section)

    def _add_opportunity(self) -> None:
        next_index = self.invites.value + 1
        self.invites.set(next_index)
        self.all_deals.set(
            [
                _new_deal(next_index),
                *self.all_deals.value,
            ]
        )
        self.all_customers.set(
            [
                _new_customer(next_index),
                *self.all_customers.value,
            ]
        )

    def _filtered_deals(self) -> list[dict[str, Any]]:
        query = self.query.value.strip().lower()
        deals = self.all_deals.value
        if not query:
            return list(deals)
        return [
            deal
            for deal in deals
            if query in deal["name"].lower()
            or query in deal["owner"].lower()
            or query in deal["stage"].lower()
        ]

    def _filtered_customers(self) -> list[dict[str, str]]:
        query = self.query.value.strip().lower()
        customers = self.all_customers.value
        if not query:
            return list(customers)
        return [
            customer
            for customer in customers
            if query in customer["name"].lower()
            or query in customer["plan"].lower()
            or query in customer["health"].lower()
        ]


class LivePreviewHandler(BaseHTTPRequestHandler):
    app: SaaSLivePreview

    def do_GET(self) -> None:
        if self.path in {"/", "/index.html"}:
            self._send_text(self.app.render_page(), "text/html; charset=utf-8")
            return
        if self.path == "/saas.css":
            self._send_text(
                CSS_PATH.read_text(encoding="utf-8"),
                "text/css; charset=utf-8",
            )
            return
        if self.path == "/health":
            self._send_json({"ok": True})
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        if self.path != "/event":
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


LIVE_SCRIPT = r"""
(() => {
  const root = document.getElementById("otoe-root");

  const escapeSelector = (value) => {
    if (window.CSS && CSS.escape) {
      return CSS.escape(value);
    }
    return value.replace(/["\\]/g, "\\$&");
  };

  const replaceRoot = (html, activeEventId, selectionStart, selectionEnd) => {
    root.innerHTML = html;
    if (!activeEventId) {
      return;
    }
    const selector = `[data-otoe-change="${escapeSelector(activeEventId)}"]`;
    const nextInput = root.querySelector(selector);
    if (!nextInput) {
      return;
    }
    nextInput.focus();
    if (typeof selectionStart === "number" && typeof selectionEnd === "number") {
      nextInput.setSelectionRange(selectionStart, selectionEnd);
    }
  };

  const sendEvent = async (id, args, activeInput = null) => {
    const response = await fetch("/event", {
      method: "POST",
      headers: {"content-type": "application/json"},
      body: JSON.stringify({id, args}),
    });
    const payload = await response.json();
    if (!payload.ok) {
      throw new Error(payload.error || "Otoe event failed");
    }
    replaceRoot(
      payload.html,
      activeInput?.dataset.otoeChange,
      activeInput?.selectionStart,
      activeInput?.selectionEnd,
    );
  };

  document.addEventListener("click", (event) => {
    const target = event.target.closest("[data-otoe-click]");
    if (!target) {
      return;
    }
    event.preventDefault();
    sendEvent(target.dataset.otoeClick, []);
  });

  document.addEventListener("input", (event) => {
    const target = event.target.closest("[data-otoe-change]");
    if (!target) {
      return;
    }
    sendEvent(target.dataset.otoeChange, [target.value], target);
  });
})();
"""


def _new_deal(index: int) -> dict[str, Any]:
    value = 12000 + index * 3400
    return {
        "id": f"new-{index}",
        "stage": "Qualified",
        "confidence": "58%",
        "name": f"Brightline Systems {index}",
        "owner": "Avery Stone",
        "amount": f"${value:,.0f}",
        "value": value,
    }


def _new_customer(index: int) -> dict[str, str]:
    return {
        "id": f"new-{index}",
        "name": f"Brightline Systems {index}",
        "plan": "Pro",
        "health": "New",
        "tone": "good",
    }


def run(host: str = "127.0.0.1", port: int = 8766) -> None:
    app = SaaSLivePreview()

    class Handler(LivePreviewHandler):
        pass

    Handler.app = app
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"Otoe SaaS live preview: http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8766, type=int)
    args = parser.parse_args()
    run(args.host, args.port)


if __name__ == "__main__":
    main()
