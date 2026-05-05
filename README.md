# Otoe

Otoe is an experimental Python UI runtime for building desktop-style
interfaces with component functions, reactive state, explicit events, and a
renderer boundary that can evolve beyond the current HTML proof backend.

The project is early. The current repository is a technical preview for the
runtime model, visual case studies, and live preview loop. It is not yet a
stable public framework or a production desktop renderer.

## What Works Today

- Python component functions with typed widget contracts.
- `signal`, `computed`, `effect`, owner cleanup, and lifecycle hooks.
- `Show` and keyed `For` control flow.
- Fake-widget mounting and deterministic snapshots.
- Static HTML preview rendering.
- Shared live HTML preview server with click/input event dispatch.
- Optional JSX-like `template(...)` syntax that returns the same `Node` tree.
- Experimental portable `css(...)` / `StyleSheet` API.
- First `otoe.ui` primitives: cards, badges, action buttons, tabs, toolbars,
  stat cards, data tables, dialogs, toasts, command palettes, app shells,
  sidebar navigation, route views, command registries, and shortcut scopes.
- Live autofocus support for command overlays and other focused inputs.
- Wraith-shaped and SaaS-shaped case studies using the same UI primitives.
- UI kit kitchen-sink preview for validating primitives outside one product shape.

## What Is Not Ready Yet

- Native desktop rendering.
- GPU rendering, layout engine integration, or accessibility tree output.
- Stable public API guarantees.
- Full component library or shadcn/Horizon-style UI kit.
- Packaging for production apps.

## Quick Start

Use Python 3.11 or newer.

Install from PyPI:

```bash
python -m pip install otoe
```

For local development:

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e ".[dev]"
pytest -q
```

Generate the static Wraith Mission Exec preview:

```bash
PYTHONPATH=src:. python -m examples.wraith.mission_exec_preview > preview/wraith_mission_exec.html
```

Run the live Wraith Mission Exec preview:

```bash
PYTHONPATH=src:. python -m examples.wraith.mission_exec_live_preview
```

Then open <http://127.0.0.1:8767>. Use `SIMULATE FRAME` to verify that
signals, events, and rerendering are actually changing visible state.

Run the live SaaS preview:

```bash
PYTHONPATH=src:. python -m examples.saas.live_preview
```

Then open <http://127.0.0.1:8766>.

Generate the static UI kit preview:

```bash
PYTHONPATH=src:. python -m examples.ui.preview > preview/ui.html
```

Run the live UI kit preview:

```bash
PYTHONPATH=src:. python -m examples.ui.live_preview
```

Then open <http://127.0.0.1:8768>. Use the sidebar, command launcher,
`Ctrl+K`/`Meta+K`, command search, Enter key, `Escape`, and single-key command
shortcuts to verify the live command overlay and route switching.

## Tiny Example

```python
from otoe import Button, Text, VStack, component, computed, mount, signal


@component
def Counter():
    count = signal(0)
    label = computed(lambda: f"Clicked {count.value} times")

    return VStack(
        Text(label),
        Button("Increment", onClick=lambda: count.set(count.value + 1)),
        gap=8,
    )


tree = mount(Counter())
```

## Project Shape

Otoe is intentionally split into layers:

- **Core runtime:** nodes, components, signals, effects, events, owners, control flow.
- **Renderer boundary:** fake widgets and HTML preview today; native desktop later.
- **Style system:** portable style representation and CSS preview adapter.
- **UI kits:** current `otoe.ui` primitives, growing toward libraries inspired by systems like shadcn or Horizon UI.
- **Case studies:** Wraith validates dense operational UI; SaaS validates softer product UI.

## Repository Map

- `src/otoe/` - runtime package.
- `examples/wraith/` - Wraith-shaped components and live previews.
- `examples/saas/` - SaaS-shaped generality case study.
- `examples/ui/` - shared UI primitive kitchen-sink preview.
- `preview/` - generated HTML/CSS preview artifacts.
- `tests/` - runtime and preview regression tests.
- `ADR-*.md` - design decisions.
- `ROADMAP.md` - current status and phase plan.

## Fixture Data

Preview data is fictitious and sanitized. The Wraith examples are design and
runtime case studies; they do not run recon, touch network interfaces, or
perform security operations.

## Status

Current status: Phase 1 / Runtime Slice. See `ROADMAP.md` for the active plan.

## License

MIT License. Copyright (c) 2026 Forvara.
