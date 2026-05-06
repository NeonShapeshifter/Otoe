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
