from __future__ import annotations

import threading
from pathlib import Path
from typing import Any

from examples.live_server import (
    LivePreviewConfig,
    parse_host_port,
    render_live_page,
    run_live_preview,
)
from examples.wraith.mission_exec_fixture import EVENTS, LOG_LINES, MISSION
from examples.wraith.mission_exec_snapshot import (
    format_elapsed,
    normalize_mission_exec_snapshot,
)
from examples.wraith.mission_exec_surface import MissionExecSurface
from otoe import LiveHtmlRenderer, mount, signal, unmount


ROOT = Path(__file__).resolve().parents[2]
CSS_PATH = ROOT / "preview" / "wraith.css"
LIVE_CONFIG = LivePreviewConfig(
    title="Otoe Wraith Mission Exec Live Preview",
    css_route="/wraith.css",
    css_path=CSS_PATH,
)


class MissionExecLivePreview:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self.renderer = LiveHtmlRenderer()
        self.next_line = 1
        self.elapsed_seconds = 76

        snapshot = normalize_mission_exec_snapshot(
            mission=MISSION,
            status="ENGAGED",
            elapsed_seconds=self.elapsed_seconds,
            logs=LOG_LINES,
            events=EVENTS,
            pending_approval=None,
            runtime_probe={
                "frame": 0,
                "label": "Signal graph ready",
                "last": "Handshake capture stream is staged for replay.",
                "tone": "ok",
            },
        )

        self.mission = signal(snapshot["mission"])
        self.log_lines = signal(snapshot["logs"])
        self.events = signal(snapshot["events"])
        self.active_filter = signal("ALL")
        self.active_event_filter = signal("ALL")
        self.pending_approval = signal(snapshot["pending_approval"])
        self.status = signal(snapshot["status"])
        self.elapsed = signal(snapshot["elapsed"])
        self.paused = signal(False)
        self.runtime_probe = signal(snapshot["runtime_probe"])

        self.surface = mount(
            MissionExecSurface(
                mission=self.mission,
                log_lines=self.log_lines,
                events=self.events,
                active_filter=self.active_filter,
                active_event_filter=self.active_event_filter,
                pending_approval=self.pending_approval,
                status=self.status,
                elapsed=self.elapsed,
                paused=self.paused,
                runtime_probe=self.runtime_probe,
                on_filter=self._set_filter,
                on_event_filter=self._set_event_filter,
                on_request_approval=self._queue_approval,
                on_approve_approval=self._approve_approval,
                on_deny_approval=self._deny_approval,
                on_abort=self._abort,
                on_pause=self._toggle_pause,
                on_clear=self._clear,
                on_export=self._export,
                on_simulate=self._simulate_frame,
                on_recover_snapshot=self._recover_snapshot,
            )
        )

    def render_fragment(self) -> str:
        with self._lock:
            self.renderer.clear()
            return self.renderer.render(self.surface, pretty=True, indent=4)

    def render_page(self) -> str:
        return render_live_page(self, LIVE_CONFIG)

    def dispatch_event(self, event_id: str, *args: Any) -> str:
        with self._lock:
            self.renderer.dispatch(event_id, *args)
            return self.render_fragment()

    def dispose(self) -> None:
        unmount(self.surface)

    def _set_filter(self, value: str) -> None:
        self.active_filter.set(value)
        self._set_probe("ok", f"{value} filter active", "Telemetry viewport changed.")

    def _set_event_filter(self, value: str) -> None:
        self.active_event_filter.set(value)
        self._set_probe("ok", f"{value} event filter active", "Event timeline viewport changed.")

    def _queue_approval(self) -> None:
        approval = {
            "step_id": "pivot-auth",
            "summary": "Combo step 'pivot-auth' is waiting for operator approval.",
            "detail": "The next step will reuse captured credentials against the scoped demo host.",
        }
        self.pending_approval.set(approval)
        self.status.set("AWAITING APPROVAL")
        self.paused.set(True)
        self._append_log("warn", "[?] Approval required for combo step 'pivot-auth'.")
        self._append_event("WAIT", "warn", "Approval required for combo step pivot-auth")
        self._set_probe("warn", "Approval required", "Combo step pivot-auth is waiting.")

    def _approve_approval(self) -> None:
        approval = self.pending_approval.value or {}
        step_id = approval.get("step_id") or "step"
        self.pending_approval.set(None)
        self.status.set("ENGAGED")
        self.paused.set(False)
        self._append_log("ok", f"[+] Approval granted for '{step_id}'.")
        self._append_event("APPROVE", "ok", f"Approval granted for {step_id}")
        self._set_probe("ok", "Approval granted", f"Combo step {step_id} may continue.")

    def _deny_approval(self) -> None:
        approval = self.pending_approval.value or {}
        step_id = approval.get("step_id") or "step"
        self.pending_approval.set(None)
        self.status.set("ABORTED")
        self.paused.set(True)
        self._append_log("warn", f"[!] Approval denied for '{step_id}'. Aborting combo.")
        self._append_event("ABORT", "warn", f"Approval denied for {step_id}")
        self._set_probe("warn", "Approval denied", f"Combo step {step_id} was denied.")

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

    def _recover_snapshot(self) -> None:
        snapshot = {
            "active": True,
            "execution_kind": "combo",
            "status": "RUNNING",
            "elapsed_seconds": 184,
            "output_lines": [
                "remote line one: runtime host reattached",
                "remote line two: combo step pivot-escalate waiting for approval",
                "remote line three: bridge spool heartbeat ok",
            ],
            "pending_approval": {
                "approval_id": "approval-recovered-1",
                "step_id": "pivot-escalate",
                "summary": (
                    "Recovered combo step 'pivot-escalate' is waiting for "
                    "operator approval."
                ),
                "detail": (
                    "Runtime host snapshot arrived after UI reconnect; approve "
                    "to continue the combo."
                ),
            },
        }
        self._apply_recovered_snapshot(snapshot)

    def _apply_recovered_snapshot(self, snapshot: dict[str, Any]) -> None:
        self.elapsed_seconds = int(snapshot.get("elapsed_seconds") or self.elapsed_seconds)
        self.elapsed.set(self._format_elapsed())

        pending_approval = normalize_mission_exec_snapshot(
            pending_approval=snapshot.get("pending_approval")
        )["pending_approval"]
        self.log_lines.set(self._snapshot_log_lines(snapshot.get("output_lines") or []))
        self.pending_approval.set(pending_approval)

        if pending_approval:
            self.status.set("AWAITING APPROVAL")
            self.paused.set(True)
        elif snapshot.get("active"):
            self.status.set("REATTACHED")
            self.paused.set(False)
        else:
            self.status.set(str(snapshot.get("status") or "RECOVERY REQUIRED"))
            self.paused.set(True)

        recovered_events = [
            {
                "id": "event-recover-snapshot",
                "ts": "08:55:00",
                "tag": "RECOVER",
                "severity": "ok",
                "message": "Remote runtime snapshot restored",
            }
        ]
        if pending_approval:
            step_id = pending_approval.get("step_id") or "step"
            recovered_events.append(
                {
                    "id": "event-recover-approval",
                    "ts": "08:55:01",
                    "tag": "WAIT",
                    "severity": "warn",
                    "message": f"Recovered approval gate for {step_id}",
                }
            )
        self.events.set([*self.events.value, *recovered_events][-16:])
        self._set_probe(
            "warn" if pending_approval else "ok",
            "Remote snapshot recovered",
            "Runtime host snapshot restored output and approval state.",
        )

    def _snapshot_log_lines(self, lines: list[str]) -> list[dict[str, str]]:
        return [
            {
                "id": f"snapshot-{index}",
                "ts": f"08:55:{index:02d}",
                "level": "warn" if "waiting" in line else "info",
                "message": line,
            }
            for index, line in enumerate(lines, start=1)
        ]

    def _append_log(self, level: str, message: str) -> None:
        self.next_line += 1
        self.log_lines.set(
            [
                *self.log_lines.value,
                {
                    "id": f"live-{self.next_line}",
                    "ts": f"08:52:{self.next_line:02d}",
                    "level": level,
                    "message": message,
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
                    "severity": severity,
                    "message": message,
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
        return format_elapsed(self.elapsed_seconds)


def run(host: str = "127.0.0.1", port: int = 8767) -> None:
    run_live_preview(
        app_factory=MissionExecLivePreview,
        config=LIVE_CONFIG,
        host=host,
        port=port,
        label="Otoe Wraith Mission Exec live preview",
    )


def main() -> None:
    args = parse_host_port(default_port=8767)
    run(args.host, args.port)


if __name__ == "__main__":
    main()
