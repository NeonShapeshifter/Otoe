from __future__ import annotations

import argparse
import json
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from examples.wraith.mission_exec_fixture import EVENTS, LOG_LINES, MISSION
from examples.wraith.mission_exec_surface import MissionExecSurface
from otoe import LiveHtmlRenderer, mount, signal


ROOT = Path(__file__).resolve().parents[2]
CSS_PATH = ROOT / "preview" / "wraith.css"


class MissionExecLivePreview:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self.renderer = LiveHtmlRenderer()
        self.next_line = 1
        self.elapsed_seconds = 76

        self.mission = signal(dict(MISSION))
        self.log_lines = signal([dict(line) for line in LOG_LINES])
        self.events = signal([dict(event) for event in EVENTS])
        self.active_filter = signal("ALL")
        self.status = signal("ENGAGED")
        self.elapsed = signal(self._format_elapsed())
        self.paused = signal(False)
        self.runtime_probe = signal(
            {
                "frame": 0,
                "label": "Signal graph ready",
                "last": "Handshake capture stream is staged for replay.",
                "tone": "ok",
            }
        )

        self.surface = mount(
            MissionExecSurface(
                mission=self.mission,
                log_lines=self.log_lines,
                events=self.events,
                active_filter=self.active_filter,
                status=self.status,
                elapsed=self.elapsed,
                paused=self.paused,
                runtime_probe=self.runtime_probe,
                on_filter=self._set_filter,
                on_abort=self._abort,
                on_pause=self._toggle_pause,
                on_clear=self._clear,
                on_export=self._export,
                on_simulate=self._simulate_frame,
            )
        )

    def render_fragment(self) -> str:
        with self._lock:
            self.renderer.clear()
            return self.renderer.render(self.surface, pretty=True, indent=4)

    def render_page(self) -> str:
        fragment = self.render_fragment()
        return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Otoe Wraith Mission Exec Live Preview</title>
  <link rel="stylesheet" href="/wraith.css">
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

    def _set_filter(self, value: str) -> None:
        self.active_filter.set(value)
        self._set_probe("ok", f"{value} filter active", "Telemetry viewport changed.")

    def _toggle_pause(self) -> None:
        next_value = not self.paused.value
        self.paused.set(next_value)
        self.status.set("PAUSED" if next_value else "ENGAGED")
        self._append_log(
            "warn" if next_value else "ok",
            "operator: capture paused" if next_value else "operator: capture resumed",
        )
        self._set_probe(
            "warn" if next_value else "ok",
            "Capture paused" if next_value else "Capture resumed",
            "Mission clock and operator state changed.",
        )

    def _abort(self) -> None:
        self.status.set("ABORTED")
        self.paused.set(True)
        self._append_log("warn", "operator: mission abort requested; runtime teardown staged")
        self._append_event("ABORT", "warn", "Operator requested mission abort")
        self._set_probe("warn", "Abort staged", "Runtime state moved to ABORTED.")

    def _clear(self) -> None:
        self.log_lines.set([])
        self._set_probe("ok", "Telemetry cleared", "Visible log buffer is empty.")

    def _export(self) -> None:
        self._append_log("ok", "export: mission telemetry bundle prepared for vault")
        self._append_event("EXPORT", "ok", "Telemetry export prepared")
        self._set_probe("ok", "Export prepared", "Telemetry bundle is ready for vault handoff.")

    def _simulate_frame(self) -> None:
        frame = self.runtime_probe.value["frame"] + 1
        samples = [
            ("info", "RADIO", "radio frame accepted on channel 11"),
            ("sig", "EAPOL", "EAPOL replay counter advanced"),
            ("ok", "VAULT", "evidence buffer flushed"),
            ("warn", "RADIO", "RSSI jitter crossed watch threshold"),
        ]
        level, tag, message = samples[(frame - 1) % len(samples)]
        self.elapsed_seconds += 7
        self.elapsed.set(self._format_elapsed())
        self._append_log(level, f"frame {frame:03d}: {message}")
        if frame % 2 == 0:
            severity = "warn" if level == "warn" else "ok"
            self._append_event(tag, severity, f"Frame {frame:03d}: {message}")
        self._set_probe(
            "warn" if level == "warn" else "ok",
            f"{level.upper()} telemetry mutation",
            message,
            frame=frame,
        )

    def _append_log(self, level: str, message: str) -> None:
        self.next_line += 1
        self.log_lines.set(
            [
                *self.log_lines.value,
                {
                    "id": f"live-{self.next_line}",
                    "ts": f"08:52:{self.next_line:02d}",
                    "lvl": level,
                    "msg": message,
                },
            ][-80:]
        )

    def _append_event(self, tag: str, severity: str, message: str) -> None:
        self.next_line += 1
        self.events.set(
            [
                *self.events.value,
                {
                    "id": f"event-{self.next_line}",
                    "ts": f"08:52:{self.next_line:02d}",
                    "tag": tag,
                    "sev": severity,
                    "msg": message,
                },
            ][-16:]
        )

    def _set_probe(
        self,
        tone: str,
        label: str,
        last: str,
        *,
        frame: int | None = None,
    ) -> None:
        current = self.runtime_probe.value
        self.runtime_probe.set(
            {
                "frame": current["frame"] if frame is None else frame,
                "label": label,
                "last": last,
                "tone": tone,
            }
        )

    def _format_elapsed(self) -> str:
        minutes, seconds = divmod(self.elapsed_seconds, 60)
        hours, minutes = divmod(minutes, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


class LivePreviewHandler(BaseHTTPRequestHandler):
    app: MissionExecLivePreview

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

  const sendEvent = async (id, args) => {
    const response = await fetch("/event", {
      method: "POST",
      headers: {"content-type": "application/json"},
      body: JSON.stringify({id, args}),
    });
    const payload = await response.json();
    if (!payload.ok) {
      throw new Error(payload.error || "Otoe event failed");
    }
    root.innerHTML = payload.html;
  };

  document.addEventListener("click", (event) => {
    const target = event.target.closest("[data-otoe-click]");
    if (!target) {
      return;
    }
    event.preventDefault();
    sendEvent(target.dataset.otoeClick, []);
  });
})();
"""


def run(host: str = "127.0.0.1", port: int = 8767) -> None:
    app = MissionExecLivePreview()

    class Handler(LivePreviewHandler):
        pass

    Handler.app = app
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"Otoe Wraith Mission Exec live preview: http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8767, type=int)
    args = parser.parse_args()
    run(args.host, args.port)


if __name__ == "__main__":
    main()
