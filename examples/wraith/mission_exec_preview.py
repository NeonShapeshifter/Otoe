from __future__ import annotations

from examples.wraith.mission_exec_fixture import EVENTS, LOG_LINES, MISSION
from examples.wraith.mission_exec_surface import MissionExecSurface
from otoe import mount, render_html, signal


def build_preview_html() -> str:
    surface = mount(
        MissionExecSurface(
            mission=signal(MISSION),
            log_lines=signal(LOG_LINES),
            events=signal(EVENTS),
            active_filter=signal("ALL"),
            active_event_filter=signal("ALL"),
            pending_approval=signal(None),
            status=signal("ENGAGED"),
            elapsed=signal("00:01:16"),
            paused=signal(False),
            runtime_probe=signal(
                {
                    "frame": 0,
                    "label": "Fixture telemetry loaded",
                    "last": "Handshake capture stream is staged for replay.",
                    "tone": "ok",
                }
            ),
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
