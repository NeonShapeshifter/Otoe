# Examples Guide

Otoe examples are validation surfaces. They should stay framework-neutral where
possible and case-study-shaped where useful. Use this guide to pick the smallest
example that proves the behavior you want to inspect.

## Quickstart

Path: `examples/quickstart.py`

Use this when you need the smallest static render target for the CLI.

```bash
otoe render examples.quickstart:app --out preview.html --pretty
otoe render examples.quickstart:app --out preview.png --native
```

This example proves import-target rendering. It does not prove live events.

## Live Counter

Path: `examples/live_counter.py`

Use this when you need the smallest live preview app shape:

- app object with `render_fragment()`
- app object with `dispatch_event(event_id, *args)`
- `LiveHtmlRenderer`
- mounted component tree reused across events
- signal-driven rerendering

```bash
otoe dev examples.live_counter:app --port 8767
```

This is the reference for future tiny live-preview examples.

## Native Counter

Path: `examples/native/counter_demo.py`

Use this when you need the smallest native renderer smoke:

- `NativeSurface`
- before/after PNG frames
- native click dispatch
- state update through an Otoe event

```bash
PYTHONPATH=src:. python -m examples.native.counter_demo
```

This writes native counter frames under `preview/native/`.

## Native Task Board

Path: `examples/native/task_board_demo.py`

Use this as the current framework-neutral native app surface:

- controlled search input
- filtered `For(...)` rows
- empty state
- `Show(...)` modal state
- shortcuts
- controlled `ScrollView(scrollY=..., onScroll=...)`
- PNG frame sequence

```bash
PYTHONPATH=src:. python -m examples.native.task_board_demo
```

This is the main native app-shaped example without Wraith or SaaS coupling.

## Native Window Demo

Path: `examples/native/window_demo.py`

Use this when you need `NativeWindowDriver` or optional `run_native(...)` smoke:

```bash
PYTHONPATH=src:. python -m examples.native.window_demo
PYTHONPATH=src:. python -m examples.native.window_demo --window
```

The `--window` mode requires Tk and a graphical display. It is a manual
experiment, not a production desktop backend.

## UI Kitchen Sink

Paths:

- `examples/ui/kitchen_sink.py`
- `examples/ui/preview.py`
- `examples/ui/live_preview.py`

Use this when changing shared `otoe.ui` primitives:

- app shell
- sidebar navigation
- route view
- command palette
- dialog
- menu
- select
- data table
- cards, badges, tabs, toolbar, toast

```bash
PYTHONPATH=src:. python -m examples.ui.preview > preview/ui.html
PYTHONPATH=src:. python -m examples.ui.live_preview
```

This example is intentionally broader than quickstart; it catches primitive
integration issues.

## SaaS Preview

Paths:

- `examples/saas/overview.py`
- `examples/saas/preview.py`
- `examples/saas/live_preview.py`

Use this to validate calmer product-dashboard UI:

- metrics
- account/customer tables
- settings/status surfaces
- shared UI primitives in a less operational visual rhythm

```bash
PYTHONPATH=src:. python -m examples.saas.preview > preview/saas.html
PYTHONPATH=src:. python -m examples.saas.live_preview
```

This is a case study, not a product dependency.

## Wraith Previews

Paths:

- `examples/wraith/topbar.py`
- `examples/wraith/arsenal.py`
- `examples/wraith/runtime_status.py`
- `examples/wraith/preview.py`
- `examples/wraith/live_preview.py`
- `examples/wraith/mission_exec_surface.py`
- `examples/wraith/mission_exec_preview.py`
- `examples/wraith/mission_exec_live_preview.py`

Use these to validate dense operational UI pressure:

- topbar/status surfaces
- mission cards
- runtime status polling
- event timelines
- command and approval flows
- recovered snapshot state

```bash
PYTHONPATH=src:. python -m examples.wraith.preview > preview/wraith.html
PYTHONPATH=src:. python -m examples.wraith.live_preview
PYTHONPATH=src:. python -m examples.wraith.mission_exec_preview > preview/wraith_mission_exec.html
PYTHONPATH=src:. python -m examples.wraith.mission_exec_live_preview
```

Wraith examples should pressure-test Otoe without leaking Wraith-specific
assumptions into the runtime.

## Choosing An Example

| Need | Start With |
| --- | --- |
| Static CLI render target | `examples.quickstart:app` |
| Minimal live preview app | `examples.live_counter:app` |
| Minimal native PNG smoke | `examples.native.counter_demo` |
| App-shaped native renderer surface | `examples.native.task_board_demo` |
| Window-driver or Tk smoke | `examples.native.window_demo` |
| Shared UI primitive regression | `examples.ui.kitchen_sink` |
| Product-dashboard case study | `examples.saas.overview` |
| Dense operational case study | `examples.wraith.mission_exec_surface` |

## Example Rules

- Keep framework-neutral examples free of case-study language.
- Keep case-study examples outside core runtime assumptions.
- Prefer small examples for docs and CLI behavior.
- Prefer app-shaped examples for renderer and UI primitive integration.
- Do not add a new primitive just to make an example prettier.
- When an example exposes a new framework boundary, add a focused test for that
  boundary.
