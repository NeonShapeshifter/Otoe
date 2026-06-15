# Wraith MissionExec Snapshot Contract

`examples/wraith/mission_exec_snapshot.py` is an **Otoe-local compatibility
contract** for the Wraith-shaped MissionExec example. It mirrors the JSON-safe
snapshot shape Wraith is expected to expose in the future as
`wraith.ui.mission_exec.v0`.

This is a Wraith-shaped contract, not a Wraith dependency.

- It does **not** import Wraith.
- It does **not** execute Wraith missions (no subprocess, no hardware, no I/O).
- It aligns with the intended future Wraith snapshot shape so the example can be
  re-pointed at a real Wraith adapter later with minimal churn.
- It accepts legacy field aliases so existing Otoe fixtures keep working.
- It is safe for HTML render, live preview, native render, and tests: the
  normalization functions are pure, never mutate their inputs, and produce
  JSON-serializable output.

Paths:

- `examples/wraith/mission_exec_snapshot.py`
- `examples/wraith/mission_exec_fixture.py`
- `examples/wraith/mission_exec_surface.py`
- `examples/wraith/mission_exec_preview.py`
- `examples/wraith/mission_exec_live_preview.py`
- `tests/test_wraith_mission_exec_snapshot.py`

## Snapshot Shape

```json
{
  "schema": "wraith.ui.mission_exec.v0",
  "mission": { "id": "", "name": "NO ACTIVE MISSION", "...": "..." },
  "status": "ENGAGED",
  "elapsed": "00:01:16",
  "preflight": [],
  "logs": [
    { "id": "l001", "ts": "08:50:00", "level": "info", "message": "..." }
  ],
  "events": [
    { "id": "e001", "ts": "08:50:00", "tag": "SCOPE", "severity": "ok", "message": "..." }
  ],
  "pending_approval": null,
  "actions": {
    "can_abort": true,
    "can_pause": true,
    "can_resume": false,
    "can_export": true,
    "can_approve": false,
    "can_deny": false
  },
  "runtime_probe": {
    "frame": 0,
    "tone": "ok",
    "label": "Runtime snapshot ready",
    "last": "No live runtime mutation performed."
  }
}
```

## Public API

- `SCHEMA` — the canonical schema string `"wraith.ui.mission_exec.v0"`.
- `format_elapsed(seconds) -> str` — formats seconds as `HH:MM:SS`; `None`,
  invalid, and negative inputs collapse to `"00:00:00"`.
- `normalize_mission_exec_snapshot(snapshot=None, *, mission, status, elapsed,
  elapsed_seconds, preflight, logs, events, pending_approval, actions,
  runtime_probe) -> dict` — returns a normalized, JSON-safe snapshot. A
  `snapshot` dict supplies base values; keyword arguments override individual
  fields when provided. Pure: no imports of Otoe/Wraith, no side effects, never
  mutates inputs.
- `snapshot_to_signals(snapshot) -> dict` — builds Otoe signals from a (raw or
  normalized) snapshot. This is the only function that touches Otoe, and it
  imports `otoe.signal` lazily so the normalization path stays import-free.

## Canonical Fields and Legacy Aliases

The canonical field names are `level` / `severity` / `message` / `id`. For
backwards compatibility with current fixtures, normalization accepts these
aliases:

| Object             | Legacy alias  | Canonical field |
| ------------------ | ------------- | --------------- |
| log line           | `lvl`         | `level`         |
| log line           | `msg`         | `message`       |
| event              | `sev`         | `severity`      |
| event              | `msg`         | `message`       |
| pending approval   | `approval_id` | `id`            |

## Normalization Rules

- `schema` defaults to `SCHEMA`; an unknown input schema is preserved.
- Inputs are never mutated and the output is JSON-safe.
- Missing fields receive safe defaults (mission name `"NO ACTIVE MISSION"`,
  empty log/event lists, `pending_approval` of `null`, default runtime probe).
- `elapsed` wins over `elapsed_seconds` when explicitly provided; otherwise
  `elapsed_seconds` is formatted as `HH:MM:SS`, and invalid seconds become
  `"00:00:00"`.
- Logs default missing ids to `l001`, `l002`, ... and missing level to `info`.
- Events default missing ids to `e001`, `e002`, ... and missing severity to
  `ok`.
- Falsy `pending_approval` normalizes to `null`.
- `actions` defaults are derived from status and content:
  - terminal statuses (`DONE`, `COMPLETE`, `COMPLETED`, `FAILED`, `ABORTED`,
    `CANCELLED`, `CANCELED`) disable `can_abort` and `can_pause`;
  - `can_pause` is true for `ENGAGED` / `RUNNING`, `can_resume` for `PAUSED`;
  - `can_export` is true when logs or events exist;
  - user-provided actions may override defaults, **except** that a pending
    approval always forces `can_approve` and `can_deny` to true.

## Deferred

The `preflight` panel in `MissionExecSurface` is still mission-derived rather
than snapshot-driven. The snapshot carries a `preflight` list for forward
compatibility, but wiring the surface panel to it is deferred to a later change
to avoid altering the existing preview HTML semantics.

## Validation

```sh
PYTHONPATH=src:. python3 -m pytest -q \
  tests/test_wraith_mission_exec_snapshot.py \
  tests/test_wraith_mission_exec_preview.py \
  tests/test_wraith_examples.py \
  tests/test_wraith_live_preview.py
```

Build the static preview HTML (prints to stdout):

```sh
PYTHONPATH=src:. python3 -m examples.wraith.mission_exec_preview
```
