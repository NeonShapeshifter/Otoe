# Otoe Change Benchmarks

These notes compare real Wraith-shaped UI changes in Otoe against the current
Kivy implementation shape. The goal is to test whether Otoe reduces product UI
friction, not just whether the preview looks better.

## Benchmark 001 - Mission Exec Event Severity Filter

**Date:** May 5, 2026
**Surface:** Wraith Mission Exec
**Change:** add a severity filter for the Event Timeline so the operator can
switch between all events, successful events, and warning events.

### Otoe Implementation

Touched production-preview code:

- `examples/wraith/mission_exec_surface.py`
- `examples/wraith/mission_exec_live_preview.py`
- `examples/wraith/mission_exec_preview.py`

Behavioral shape:

- Add one `active_event_filter` signal.
- Add one computed `visible_events` list.
- Reuse the existing `Tabs` / `TabButton` filter pattern.
- Keep event rows keyed by event id through `For`.
- Add one live regression test proving warning-event filtering updates visible
  rows and probe state.

The change stays declarative: event rows are still a projection of `events` and
`active_event_filter`. There is no manual widget clearing/rebuilding in the
surface code.

### Wraith/Kivy Equivalent

Current relevant file: `wraith/src/screens/mission_exec.py`.

The same change would likely touch:

- `MissionExec.__init__`: add active event filter state.
- `_build_right_column`: add filter controls and bind callbacks.
- `_render_events`: filter the reversed event list before manual row creation.
- `_record_event`: decide whether count means total events or visible events.
- `_event_row`: possibly add active/disabled visual state for filter buttons.
- `tests/test_ui/test_screens.py`: add a screen-level regression around event
  filtering.

The Kivy version already has good operational logic, but view changes are
coupled to mutable widgets: `events_layout.clear_widgets()`, manual row
construction, label mutation, and scroll state updates. That makes the change
more error-prone than the Otoe version.

### Result

Otoe wins this benchmark for view-state ergonomics. The useful difference is
not fewer lines by itself; it is that the filter is represented as state and a
derived list, while the renderer owns reconciliation. Wraith/Kivy still owns the
real mission execution integration, so this is not enough to replace the screen,
but it is a good signal that Otoe is reducing UI mutation work.

### Follow-Up Benchmark

The next benchmark should be harder: either approval-modal depth for combo
steps, remote runtime polling/recovery, or the full app shell around Mission
Exec. Event filtering validates list/view state; it does not validate overlays,
host lifecycle, or native-renderer constraints.

## Benchmark 002 - Mission Exec Combo Approval Modal

**Date:** May 5, 2026
**Surface:** Wraith Mission Exec
**Change:** simulate a combo step that requires operator approval, display a
modal overlay, and support approve/deny decisions.

### Otoe Implementation

Touched production-preview code:

- `examples/wraith/mission_exec_surface.py`
- `examples/wraith/mission_exec_live_preview.py`
- `examples/wraith/mission_exec_preview.py`
- `preview/wraith.css`

Behavioral shape:

- Add one `pending_approval` signal.
- Render the modal with the existing `Dialog` and `FocusScope` primitives.
- Keep approval copy derived from pending approval state.
- Approve clears the modal, resumes engaged status, appends telemetry, and
  records an event.
- Deny clears the modal, moves the surface to `ABORTED`, appends telemetry, and
  records an event.
- Add live regression tests for both approve and deny flows.

The Otoe version keeps the overlay as declarative state: if
`pending_approval.value` is truthy, the dialog exists; if it is `None`, it is
removed and cleanup belongs to the runtime.

### Wraith/Kivy Equivalent

Current relevant file: `wraith/src/screens/mission_exec.py`, especially
`_on_combo_approval_required`.

The current Kivy implementation handles the same domain by:

- Manually appending terminal output.
- Recording a timeline event.
- Dismissing an existing `_approval_modal` if present.
- Constructing a `ModalView`.
- Constructing a `BoxLayout`, `Label`, and two `WraithButton` instances.
- Defining nested `_approve` and `_abort` callbacks.
- Manually dismissing the modal and clearing `_approval_modal`.

That implementation is operationally explicit and understandable, but each
overlay introduces manual lifecycle work. Otoe's version still needs a native
renderer before it can replace Wraith, but the state ownership is cleaner:
modal visibility, copy, and actions are all a projection of `pending_approval`.

### Result

Otoe wins this benchmark on overlay lifecycle and testability. The approval
modal benchmark is more meaningful than the event filter because it exercises
critical action state, focus scope, modal visibility, and divergent approve/deny
outcomes. The remaining risk is renderer/runtime maturity, not component API
shape.

### Follow-Up Benchmark

The next benchmark should test runtime polling/recovery, because that is where
Wraith's real mission execution host and remote snapshot behavior become harder
than local component state.
