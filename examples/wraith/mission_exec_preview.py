from __future__ import annotations

from examples.wraith.mission_exec_fixture import EVENTS, LOG_LINES, MISSION
from examples.wraith.mission_exec_snapshot import (
    normalize_mission_exec_snapshot,
    snapshot_to_signals,
)
from examples.wraith.mission_exec_surface import MissionExecSurface
from otoe import mount, render_html, signal


def build_preview_html() -> str:
    snapshot = normalize_mission_exec_snapshot(
        mission=MISSION,
        status="ENGAGED",
        elapsed="00:01:16",
        logs=LOG_LINES,
        events=EVENTS,
        pending_approval=None,
        runtime_probe={
            "frame": 0,
            "label": "Fixture telemetry loaded",
            "last": "Handshake capture stream is staged for replay.",
            "tone": "ok",
        },
    )
    signals = snapshot_to_signals(snapshot)
    surface = mount(
        MissionExecSurface(
            mission=signals["mission"],
            log_lines=signals["log_lines"],
            events=signals["events"],
            active_filter=signal("ALL"),
            active_event_filter=signal("ALL"),
            pending_approval=signals["pending_approval"],
            status=signals["status"],
            elapsed=signals["elapsed"],
            paused=signal(False),
            runtime_probe=signals["runtime_probe"],
            on_filter=lambda value: None,
            on_event_filter=lambda value: None,
            on_request_approval=lambda: None,
            on_approve_approval=lambda: None,
            on_deny_approval=lambda: None,
            on_abort=lambda: None,
            on_pause=lambda: None,
            on_clear=lambda: None,
            on_export=lambda: None,
            on_simulate=lambda: None,
            on_recover_snapshot=lambda: None,
        )
    )
    body = render_html(surface, pretty=True, indent=4)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Otoe Wraith Mission Exec Preview</title>
  <link rel="stylesheet" href="wraith.css">
</head>
<body>
{body}
</body>
</html>
"""


if __name__ == "__main__":
    print(build_preview_html())
