from __future__ import annotations

import argparse
import json
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from examples.wraith.arsenal import ArsenalView
from examples.wraith.runtime_status import RuntimeStatusCluster
from examples.wraith.topbar import TopBar
from otoe import LiveHtmlRenderer, computed, mount, signal


ROOT = Path(__file__).resolve().parents[2]
CSS_PATH = ROOT / "preview" / "wraith.css"
PAGE_SIZE = 3


class WraithLivePreview:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self.renderer = LiveHtmlRenderer()

        self.campaign = signal("Primary Campaign")
        self.wifi_state = signal("UP")
        self.stealth_active = signal(True)
        self.query = signal("")
        self.active_tag = signal("ALL")
        self.page = signal(0)
        self.status_index = 0

        self.visible_missions = computed(self._visible_missions)
        self.page_label = computed(self._page_label)

        self.topbar = mount(
            TopBar(
                campaign=self.campaign,
                wifi_state=self.wifi_state,
                stealth_active=self.stealth_active,
            )
        )
        self.status = mount(RuntimeStatusCluster(probe=self._probe_runtime))
        self.arsenal = mount(
            ArsenalView(
                query=self.query,
                active_tag=self.active_tag,
                missions=self.visible_missions,
                page_label=self.page_label,
                on_search=self._search,
                on_next=self._next_page,
            )
        )

    def render_fragment(self) -> str:
        with self._lock:
            self.renderer.clear()
            return "\n".join(
                [
                    self.renderer.render(self.topbar, pretty=True, indent=4),
                    '    <main class="preview-main">',
                    '      <section class="preview-column preview-column--left">',
                    '        <div class="preview-section-title">Runtime</div>',
                    self.renderer.render(self.status, pretty=True, indent=8),
                    "      </section>",
                    '      <section class="preview-column preview-column--main">',
                    '        <div class="preview-section-title">Arsenal</div>',
                    self.renderer.render(self.arsenal, pretty=True, indent=8),
                    "      </section>",
                    "    </main>",
                ]
            )

    def render_page(self) -> str:
        fragment = self.render_fragment()
        return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Otoe Wraith Live Preview</title>
  <link rel="stylesheet" href="/wraith.css">
</head>
<body>
  <div id="otoe-root" class="app-shell">
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

    def _search(self, value: str) -> None:
        query = value.strip()
        self.query.set(value)
        self.active_tag.set("QUERY" if query else "ALL")
        self.page.set(0)

    def _next_page(self) -> None:
        self.page.set((self.page.value + 1) % self._page_count())

    def _visible_missions(self) -> list[dict[str, str]]:
        items = self._filtered_missions()
        start = self.page.value * PAGE_SIZE
        return items[start : start + PAGE_SIZE]

    def _page_label(self) -> str:
        total_pages = self._page_count()
        current_page = min(self.page.value + 1, total_pages)
        return f"PAGE {current_page}/{total_pages}"

    def _page_count(self) -> int:
        return max(1, (len(self._filtered_missions()) + PAGE_SIZE - 1) // PAGE_SIZE)

    def _filtered_missions(self) -> list[dict[str, str]]:
        query = self.query.value.strip().lower()
        if not query:
            return list(MISSIONS)
        return [
            mission
            for mission in MISSIONS
            if query in mission["name"].lower()
            or query in mission["description"].lower()
            or query in mission["vector"].lower()
            or query in mission["opsec"].lower()
        ]

    def _probe_runtime(self) -> dict[str, str]:
        snapshot = RUNTIME_SNAPSHOTS[self.status_index % len(RUNTIME_SNAPSHOTS)]
        self.status_index += 1
        return dict(snapshot)


class LivePreviewHandler(BaseHTTPRequestHandler):
    app: WraithLivePreview

    def do_GET(self) -> None:
        if self.path in {"/", "/index.html"}:
            self._send_text(self.app.render_page(), "text/html; charset=utf-8")
            return
        if self.path == "/wraith.css":
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


MISSIONS = [
    {
        "id": "wifi",
        "name": "WiFi Scan",
        "description": "Discover nearby networks.",
        "vector": "WiFi",
        "opsec": "LOW",
    },
    {
        "id": "rf",
        "name": "RF Survey",
        "description": "Inspect spectrum activity.",
        "vector": "RF",
        "opsec": "MED",
    },
    {
        "id": "lab",
        "name": "Lab Flow",
        "description": "Restricted validation path.",
        "vector": "USB",
        "opsec": "HIGH",
    },
    {
        "id": "ble",
        "name": "BLE Sweep",
        "description": "Enumerate nearby Bluetooth beacons.",
        "vector": "BLE",
        "opsec": "LOW",
    },
    {
        "id": "payload",
        "name": "Payload Stager",
        "description": "Prepare controlled delivery artifacts.",
        "vector": "USB",
        "opsec": "HIGH",
    },
]

RUNTIME_SNAPSHOTS = [
    {"wifi": "UP", "bluetooth": "READY", "cpu": "42C", "storage": "18GB"},
    {"wifi": "UP", "bluetooth": "READY", "cpu": "43C", "storage": "18GB"},
    {"wifi": "DEGRADED", "bluetooth": "READY", "cpu": "44C", "storage": "17GB"},
]


def run(host: str = "127.0.0.1", port: int = 8765) -> None:
    app = WraithLivePreview()

    class Handler(LivePreviewHandler):
        pass

    Handler.app = app
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"Otoe Wraith live preview: http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8765, type=int)
    args = parser.parse_args()
    run(args.host, args.port)


if __name__ == "__main__":
    main()
