# Wraith Input Console

The Wraith input console is a framework-neutral Otoe example shaped like an
appliance/control-panel surface. It exercises Portable Input Core v0 patterns
without importing the real Wraith project.

This is a Wraith-shaped validation surface, not a Wraith dependency.

Paths:

- `examples/wraith_input_console.py`
- `preview/wraith_input_console.css`
- `tests/test_wraith_input_console.py`

## What It Shows

- Primary activation through click/tap-style buttons and NativeSurface keyboard
  activation.
- Mission search and selection through focusable controls.
- `Dry Run`, `Execute`, `Safe Mode`, and `More` actions with visible touch-sized
  targets.
- Confirmation before the dangerous `Execute` path commits.
- A visible `More` entry point for secondary/context actions such as copy ID,
  copy log line, pin/unpin, and raw inspection.
- Keyboard shortcut handling through `Ctrl+K`.
- Escape dismissal for confirm, command, and context panels.
- A scrollable operator log that records state changes.

## Commands

Run these from the repository root:

```bash
PYTHONPATH=src:. python -m otoe render examples.wraith_input_console:app --out preview/wraith_input_console.html --css preview/wraith_input_console.css --pretty
PYTHONPATH=src:. python -m otoe render examples.wraith_input_console:app --out preview/wraith_input_console.png --native --css preview/wraith_input_console.css
PYTHONPATH=src:. python -m otoe build examples.wraith_input_console:app --out dist/wraith_input_console --css preview/wraith_input_console.css --validate
PYTHONPATH=src:. python -m pytest -q tests/test_wraith_input_console.py
```

The workflow labels are:

```bash
otoe dev
otoe render html
otoe render native
otoe build --validate
pytest
```

For live preview:

```bash
PYTHONPATH=src:. python -m otoe dev examples.wraith_input_console:app --css preview/wraith_input_console.css --port 8767
```

## Input Coverage

The example covers the Portable Input Core v0 primary path:

- click/tap-style activation through visible buttons,
- Enter/Space activation through NativeSurface focused buttons,
- Tab traversal through focusable controls,
- text input through the search field,
- ScrollView log scrolling,
- Escape dismissal,
- Ctrl+K shortcut handling.

It also demonstrates the context action pattern without requiring a runtime
`onContext` event. The visible `More` button is the portable fallback for right
click, long press, keyboard context, and future explicit context dispatch.

## Deferred

The example intentionally does not implement gesture recognition, multi-touch,
drag/drop, native long-press dispatch, hover-only controls, or a real clipboard.
Copy actions write to the operator log so the behavior is deterministic in HTML
render, NativeSurface tests, and offline build validation.

## Relationship To Wraith

The screen uses Wraith-like naming, operator language, mission state, secondary
actions, and confirmation flow to validate Otoe input conventions for an
appliance UI. It does not import Wraith modules, connect to hardware, execute
security logic, or model offensive workflows.
