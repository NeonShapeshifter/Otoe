"""Otoe-local snapshot adapter for the Wraith MissionExec example.

This is a *compatibility contract* that mirrors the shape Wraith is expected
to expose in the future as ``wraith.ui.mission_exec.v0``. It is deliberately
self-contained:

* It does not import Wraith and does not execute any mission.
* The normalization functions are pure: no Otoe imports, no filesystem access,
  no subprocess, no side effects, and they never mutate their inputs.
* It accepts the legacy ``lvl`` / ``sev`` / ``msg`` / ``approval_id`` aliases so
  existing Otoe fixtures keep working while the canonical field names are
  ``level`` / ``severity`` / ``message`` / ``id``.

Only :func:`snapshot_to_signals` touches Otoe, and it imports ``otoe.signal``
lazily so the pure normalization path stays import-free.
"""

from __future__ import annotations

from typing import Any

SCHEMA = "wraith.ui.mission_exec.v0"

_MISSION_DEFAULTS: dict[str, str] = {
    "id": "",
    "name": "NO ACTIVE MISSION",
    "description": "",
    "vector": "",
    "opsec": "",
    "validation": "",
    "profile": "",
    "scope": "",
    "target": "",
    "asset": "",
    "posture": "",
}

_RUNTIME_PROBE_DEFAULTS: dict[str, Any] = {
    "frame": 0,
    "tone": "ok",
    "label": "Runtime snapshot ready",
    "last": "No live runtime mutation performed.",
}

_TERMINAL_STATUSES = frozenset(
    {
        "DONE",
        "COMPLETE",
        "COMPLETED",
        "FAILED",
        "ABORTED",
        "CANCELLED",
        "CANCELED",
    }
)

_ACTION_KEYS = (
    "can_abort",
    "can_pause",
    "can_resume",
    "can_export",
    "can_approve",
    "can_deny",
)


def _json_safe(value: Any) -> Any:
    """Coerce ``value`` into a JSON-serializable structure.

    Scalars pass through, dict/list/tuple are coerced recursively (dict keys
    become strings), and anything else falls back to ``str(value)``. The input
    is never mutated.
    """

    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return str(value)


def format_elapsed(seconds: Any) -> str:
    """Format a duration in seconds as ``HH:MM:SS``.

    Invalid, ``None``, or negative inputs collapse to ``"00:00:00"``. Numeric
    strings (e.g. ``"76"``) are accepted.
    """

    try:
        total = int(seconds)
    except (TypeError, ValueError):
        return "00:00:00"
    if total < 0:
        return "00:00:00"
    minutes, secs = divmod(total, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def _normalize_mission(mission: Any) -> dict[str, Any]:
    result = dict(_MISSION_DEFAULTS)
    if isinstance(mission, dict):
        for key, value in mission.items():
            result[str(key)] = _json_safe(value)
    return result


def _normalize_logs(logs: Any) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    for index, raw in enumerate(logs or [], start=1):
        entry = raw if isinstance(raw, dict) else {}
        log_id = entry.get("id") or f"l{index:03d}"
        level = entry.get("level", entry.get("lvl")) or "info"
        message = entry.get("message", entry.get("msg"))
        result.append(
            {
                "id": str(log_id),
                "ts": str(entry.get("ts", "")),
                "level": str(level),
                "message": "" if message is None else str(message),
            }
        )
    return result


def _normalize_events(events: Any) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    for index, raw in enumerate(events or [], start=1):
        entry = raw if isinstance(raw, dict) else {}
        event_id = entry.get("id") or f"e{index:03d}"
        severity = entry.get("severity", entry.get("sev")) or "ok"
        message = entry.get("message", entry.get("msg"))
        result.append(
            {
                "id": str(event_id),
                "ts": str(entry.get("ts", "")),
                "tag": str(entry.get("tag", "")),
                "severity": str(severity),
                "message": "" if message is None else str(message),
            }
        )
    return result


def _normalize_pending_approval(pending: Any) -> dict[str, str] | None:
    if not pending or not isinstance(pending, dict):
        return None
    approval_id = pending.get("id", pending.get("approval_id"))
    return {
        "id": str(approval_id or ""),
        "step_id": str(pending.get("step_id") or ""),
        "summary": str(pending.get("summary") or ""),
        "detail": str(pending.get("detail") or ""),
    }


def _normalize_preflight(preflight: Any) -> list[Any]:
    result: list[Any] = []
    for raw in preflight or []:
        result.append(_json_safe(raw))
    return result


def _normalize_runtime_probe(probe: Any) -> dict[str, Any]:
    result = dict(_RUNTIME_PROBE_DEFAULTS)
    if isinstance(probe, dict):
        for key, value in probe.items():
            result[str(key)] = _json_safe(value)
    try:
        result["frame"] = int(result["frame"])
    except (TypeError, ValueError):
        result["frame"] = 0
    return result


def _resolve_actions(
    overrides: Any,
    *,
    status: str,
    logs: list[Any],
    events: list[Any],
    pending_approval: dict[str, str] | None,
) -> dict[str, bool]:
    terminal = status.upper() in _TERMINAL_STATUSES
    has_pending = pending_approval is not None
    actions: dict[str, bool] = {
        "can_abort": not terminal,
        "can_pause": status.upper() in {"ENGAGED", "RUNNING"},
        "can_resume": status.upper() == "PAUSED",
        "can_export": bool(logs or events),
        "can_approve": has_pending,
        "can_deny": has_pending,
    }
    if isinstance(overrides, dict):
        for key in _ACTION_KEYS:
            if key in overrides:
                actions[key] = bool(overrides[key])
    # A pending approval must always be answerable, regardless of overrides.
    if has_pending:
        actions["can_approve"] = True
        actions["can_deny"] = True
    return actions


def normalize_mission_exec_snapshot(
    snapshot: dict[str, Any] | None = None,
    *,
    mission: Any = None,
    status: str = "PENDING",
    elapsed: Any = None,
    elapsed_seconds: Any = None,
    preflight: Any = None,
    logs: Any = None,
    events: Any = None,
    pending_approval: Any = None,
    actions: Any = None,
    runtime_probe: Any = None,
) -> dict[str, Any]:
    """Normalize a JSON-safe MissionExec snapshot.

    A ``snapshot`` dict supplies the base values; keyword arguments override the
    corresponding fields when provided. The result is JSON-safe, never mutates
    its inputs, and fills missing fields with safe defaults.
    """

    source = dict(snapshot) if isinstance(snapshot, dict) else {}

    schema = source.get("schema") or SCHEMA

    resolved_status = status
    if resolved_status in (None, "PENDING") and source.get("status"):
        resolved_status = source["status"]
    resolved_status = str(resolved_status or "PENDING")

    mission_out = _normalize_mission(
        mission if mission is not None else source.get("mission")
    )
    preflight_out = _normalize_preflight(
        preflight if preflight is not None else source.get("preflight")
    )
    logs_out = _normalize_logs(logs if logs is not None else source.get("logs"))
    events_out = _normalize_events(
        events if events is not None else source.get("events")
    )
    pending_out = _normalize_pending_approval(
        pending_approval if pending_approval is not None else source.get("pending_approval")
    )
    runtime_probe_out = _normalize_runtime_probe(
        runtime_probe if runtime_probe is not None else source.get("runtime_probe")
    )

    elapsed_value = elapsed if elapsed is not None else source.get("elapsed")
    elapsed_seconds_value = (
        elapsed_seconds if elapsed_seconds is not None else source.get("elapsed_seconds")
    )
    if elapsed_value is not None:
        elapsed_out = str(elapsed_value)
    elif elapsed_seconds_value is not None:
        elapsed_out = format_elapsed(elapsed_seconds_value)
    else:
        elapsed_out = "00:00:00"

    actions_out = _resolve_actions(
        actions if actions is not None else source.get("actions"),
        status=resolved_status,
        logs=logs_out,
        events=events_out,
        pending_approval=pending_out,
    )

    return {
        "schema": str(schema),
        "mission": mission_out,
        "status": resolved_status,
        "elapsed": elapsed_out,
        "preflight": preflight_out,
        "logs": logs_out,
        "events": events_out,
        "pending_approval": pending_out,
        "actions": actions_out,
        "runtime_probe": runtime_probe_out,
    }


def snapshot_to_signals(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Build Otoe signals from a (possibly raw) MissionExec snapshot.

    The input is normalized defensively, so this accepts both raw and
    already-normalized snapshots. Only the snapshot-derived data signals are
    returned; UI-only state (active filters, paused) is left to the caller.
    """

    from otoe import signal

    normalized = normalize_mission_exec_snapshot(snapshot)
    return {
        "mission": signal(normalized["mission"]),
        "log_lines": signal(normalized["logs"]),
        "events": signal(normalized["events"]),
        "pending_approval": signal(normalized["pending_approval"]),
        "status": signal(normalized["status"]),
        "elapsed": signal(normalized["elapsed"]),
        "runtime_probe": signal(normalized["runtime_probe"]),
    }
