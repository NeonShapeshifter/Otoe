# Mission Exec Showcase

`examples.wraith.mission_exec_showcase:app` is the primary Otoe showcase for a
Wraith-shaped operator console without depending on Wraith.

The screen is public-product Otoe code: it imports only Otoe and Python
stdlib modules, owns all state locally, uses fake deterministic data, and never
touches hardware, sessions, vaults, secrets, or mission runners.

## Purpose

Mission Exec proves that Otoe can describe a dense appliance/operator console
with:

- operator topbar and chrome;
- mission brief and runtime status;
- elapsed state and pause/resume simulation;
- preflight checklist;
- visible emergency controls;
- runtime probe panel;
- filterable terminal/log feed;
- filterable event timeline;
- approval dialog with deterministic approve, deny, and cancel paths.

This is intentionally still pre-alpha evidence. The showcase should look and
behave like a real product direction, but it should also reveal current gaps in
native layout, native text rendering, and portable styling instead of hiding
them behind browser-only CSS.

This showcase is the strict portable baseline. It is separate from the richer
legacy `examples.wraith.mission_exec_surface` preview, which uses
`preview/wraith.css` and remains browser-only. Passing this showcase does not
claim that the legacy browser layout is portable.

## Commands

```bash
PYTHONPATH=src:. python -m otoe check --target examples.wraith.mission_exec_showcase:app --css preview/wraith_mission_exec.css
PYTHONPATH=src:. python -m otoe render examples.wraith.mission_exec_showcase:app --out preview/wraith_mission_exec.html --css preview/wraith_mission_exec.css --pretty
PYTHONPATH=src:. python -m otoe render examples.wraith.mission_exec_showcase:app --out preview/wraith_mission_exec.png --native --css preview/wraith_mission_exec.css
PYTHONPATH=src:. python -m otoe build examples.wraith.mission_exec_showcase:app --out dist/wraith_mission_exec --css preview/wraith_mission_exec.css --validate
PYTHONPATH=src:. python -m pytest -q tests/test_wraith_mission_exec_showcase.py
```

## Design Notes

- The CSS is limited to the portable Otoe subset: flat class selectors and
  supported layout/paint properties. The current strict check parses 143 rules.
- The first frame targets a fixed `1280x800` appliance canvas.
- All actions mutate local signals only. `STAGE ABORT` is a visible danger path,
  but it records fake state and appends fake telemetry rather than dispatching
  external commands.
- The approval dialog pauses the simulation and can approve, deny, or close the
  fake step deterministically.
- The native PNG path uses the current native renderer. Default text rendering
  remains a known limitation unless the optional Pillow-backed path is selected.

## Current Gaps Exposed

- Native layout is still stack-first; repeated children cannot yet be freely
  arranged into richer grids without explicit structure.
- Native text does not provide production wrapping or shaping in the default
  renderer, so copy must be short and carefully sized.
- The portable CSS subset is intentionally narrower than browser CSS. Browser
  polish is not used as a requirement for the showcase to function.
