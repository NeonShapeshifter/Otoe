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

## Benchmark 003 - Mission Exec Remote Snapshot Recovery

**Date:** May 5, 2026
**Surface:** Wraith Mission Exec
**Change:** simulate reconnecting to a remote mission runtime, apply a recovered
snapshot, restore output lines and elapsed time, and reopen any pending combo
approval gate.

### Otoe Implementation

Touched production-preview code:

- `examples/wraith/mission_exec_surface.py`
- `examples/wraith/mission_exec_live_preview.py`
- `examples/wraith/mission_exec_preview.py`
- `preview/wraith.css`

Behavioral shape:

- Add one `RECOVER SNAPSHOT` runtime action beside live frame simulation.
- Apply a snapshot object with `active`, `status`, `elapsed_seconds`,
  `output_lines`, and `pending_approval`.
- Replace visible telemetry with recovered remote output lines.
- Restore elapsed time from the snapshot.
- Reopen the existing approval dialog from recovered pending approval state.
- Append recovery and approval-gate events to the timeline.
- Add a live regression test proving the recovered dialog can be approved and
  cleared through the same approval flow as a locally queued gate.

This benchmark is intentionally still a preview simulation, not a real remote
host adapter. The useful signal is that the surface does not need custom widget
reconstruction for the recovered state: the snapshot updates signals, and the
same terminal, status panel, timeline, probe, and modal projections rerender.

### Wraith/Kivy Equivalent

Current relevant files:

- `wraith/src/services/mission_execution.py`
- `wraith/src/screens/mission_exec.py`

The current Wraith runtime has the real domain behavior in
`RemoteMissionExecutionController._apply_snapshot`,
`_sync_pending_approval`, `_recover_remote_snapshot`, and
`_handle_remote_poll_failure`. The screen restoration path is in
`MissionExec._restore_active_execution`.

The Kivy implementation has to coordinate several mutable UI surfaces during
reattach:

- Replace terminal output lines.
- Restore log and execution ids.
- Restore status and start/elapsed timer state.
- Rebuild pending approval status and modal state.
- Rehydrate event timeline from runtime messages.
- Continue or stop polling depending on remote `active` and terminal status.

That complexity is legitimate because Wraith owns the real remote process,
but the UI state is spread across screen attributes, modal references, output
widgets, timeline widgets, labels, and controller callbacks.

### Result

Otoe wins the preview-level recovery benchmark on state projection. The same
signals that power local interactions also accept recovered remote state, so
the UI can rehydrate without a separate imperative rebuild path. This does not
mean Otoe is ready to replace Wraith's execution controller; it means the
surface API is compatible with the shape of Wraith's remote snapshots.

The next meaningful test should either wrap this preview in a broader Wraith
app shell, or spike the renderer/layout boundary so the framework can start
answering native desktop constraints instead of only HTML-preview ergonomics.
