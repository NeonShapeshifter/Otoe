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
  sidebar navigation, route views, command registries, shortcut scopes, menus,
  and controlled selects.
- Keyboard handling for command palettes, menus, selects, and button-backed
  controls in the live preview backend.
- `FocusScope` support for live focus trapping and focus restoration in dialogs
  and popovers.
- Live autofocus support for command overlays and other focused inputs.
- Wraith-shaped and SaaS-shaped case studies using the same UI primitives.
- UI kit kitchen-sink preview for validating primitives outside one product shape.
- Headless native layout, paint, PNG output, hit-testing, and click dispatch
  for the first renderer spike.
- `NativeSurface` for mounting a tree, rendering PNG frames, dispatching
  clicks, and refreshing the headless native frame from one object.
- `NativeWindowDriver` for testable native-window event dispatch over a
  `NativeSurface`, plus an optional Tk wrapper for local experiments.
- `run_native(...)` as the experimental native app entry point, currently backed
  by the optional Tk wrapper.
- Driver-level `key_input(...)` text editing for printable keys, Backspace,
  Delete, Enter/Tab fallback, and shortcut fallback.
- Controlled native `ScrollView(scrollY=..., onScroll=...)` support with
  clipped paint, clipped hit-testing, and wheel dispatch through the native
  window driver.
- Headless native focus and keyboard handling for autofocus, click-to-focus,
  Tab traversal, focused keydown handlers, button submit keys, and global
  shortcut payloads.
- Headless controlled input text dispatch through `NativeSurface.input_text(...)`.
- Framework-neutral native task board demo with search, filtered rows, empty
  state, modal state, shortcuts, controlled scroll, and PNG frame output.
- Lazy `NativeSurface` refresh when reactive props or control-flow branches
  change outside direct surface events.
- Disabled widgets are skipped for native focus and click dispatch.
- `ScrollView` bounds clip native paint output and hit-tested clicks.
- Native paint includes disabled control defaults and focused control rings.

## What Is Not Ready Yet

- Production desktop rendering/windowing.
- GPU rendering, layout engine integration, or accessibility tree output.
- Stable public API guarantees.
- Full component library or shadcn/Horizon-style UI kit.
- Packaging for production apps.

## Native Renderer Status

The native path is currently a deterministic headless renderer spike. It can
layout mounted Otoe trees, emit paint commands, write PNG preview frames, and
exercise click, focus, keyboard, input, and scroll dispatch through
`NativeSurface`.

This is enough for renderer tests, visual fixtures, and early framework API
validation. It is not yet a production desktop backend: there is no GPU
renderer, platform accessibility tree, text shaping engine, retained windowing
backend, or backend compatibility promise. See
`ADR-012-native-backend-boundary.md` for the backend boundary and
`ADR-013-native-layout-hardening.md` for the current layout-hardening contract.
`ADR-014-native-overflow-clipping.md` defines the current overflow policy:
normal containers do not clip, while `ScrollView` clips paint and hit testing.
For day-to-day workflow choices, see `NATIVE_WORKFLOWS.md`.

Native and window-facing exports are intentionally marked as experimental. The
imports remain available for examples and tests, but they are not backend
compatibility promises:

```python
from otoe import api_status

assert api_status("NativeSurface").category == "experimental-native"
```

## Quick Start

Use Python 3.11 or newer.

Install the latest published package from PyPI:

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

On Debian/Ubuntu systems that report an externally managed Python environment,
do not install Otoe into the system Python. Use the virtual environment above,
or run examples directly from a checkout with `PYTHONPATH=src:.`.

Run the local framework health check:

```bash
python -m otoe check
python -m otoe check --tests
python -m otoe check --tests -- tests/test_cli.py -k new
python -m otoe new my_app
```

After installation, the same commands are available through the `otoe` console
script:

```bash
otoe check
otoe new my_app
otoe render examples.quickstart:app --out preview.html --pretty
otoe render examples.quickstart:app --out preview.png --native
otoe dev examples.live_counter:app --port 8767
```

`otoe new my_app` writes a small renderable app plus `styles.css`; pass
`--no-css` when you want only the Python scaffold.

Render the generated app with its stylesheet:

```bash
cd my_app
otoe render app:app --out preview.html --css styles.css --pretty
otoe render app:app --out preview.png --native --css styles.css
```

Render an importable Otoe node or zero-argument factory to HTML:

```bash
python -m otoe render examples.quickstart:app --out preview.html --pretty
```

Apply an Otoe CSS file inline while rendering:

```bash
python -m otoe render examples.quickstart:app --out preview.html --css path/to/styles.css --pretty
```

Render the same target through the native PNG path:

```bash
python -m otoe render examples.quickstart:app --out preview.png --native
```

Run an importable live preview app locally:

```bash
python -m otoe dev examples.live_counter:app --port 8767
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

Generate the framework-neutral native counter PNG frames through
`NativeSurface`:

```bash
PYTHONPATH=src:. python -m examples.native.counter_demo
```

This writes `preview/native/native_counter_before.png` and
`preview/native/native_counter_after.png`.

Generate the framework-neutral native task board PNG frames:

```bash
PYTHONPATH=src:. python -m examples.native.task_board_demo
```

This writes initial, filtered, and modal frames under `preview/native/`.

Generate native-window driver PNG frames, or open the optional Tk wrapper:

```bash
PYTHONPATH=src:. python -m examples.native.window_demo
PYTHONPATH=src:. python -m examples.native.window_demo --window
```

The `--window` command requires Python's Tk bindings and a graphical display. On
Debian/Ubuntu, install the OS package with:

```bash
sudo apt install python3-tk
```

The `--window` mode uses the experimental native entry point:

```python
from otoe import run_native

run_native(App(), stylesheet=styles, title="Otoe")
```

`run_native(...)` routes through the experimental `NativeBackendAdapter`
boundary. The only built-in backend name today is `"tk"`; it is a manual-test
adapter, not a production desktop backend. The `"tk"` adapter presents native
paint commands on a Tk Canvas so manual windows can show readable text. The
Canvas scales geometry up to 2x for larger windows while keeping font sizes in
logical native units; this is a presentation proof, not responsive layout
reflow. The headless PNG output path remains deterministic and still uses marker
text.

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

## Event Signatures

Built-in widget event handlers are plain callables. Otoe validates the handler
arity when the event fires and includes the widget/event contract in developer
errors. Arity mismatches raise `EventHandlerArityError`, which remains an
`EventHandlerError` for compatibility.

| Widget | Event | Handler shape |
| --- | --- | --- |
| `Button` | `onClick` | `lambda: ...` |
| `Button` | `onKeyDown` | `lambda key: ...` |
| `Button` | `onFocus`, `onBlur` | `lambda: ...` |
| `Input` | `onChange` | `lambda value: ...` |
| `Input` | `onKeyDown` | `lambda key: ...` |
| `Input` | `onFocus`, `onBlur` | `lambda: ...` |
| `ScrollView` | `onScroll` | `lambda next_scroll_y: ...` |
| `ShortcutScope` | `onGlobalKeyDown` | `lambda event: ...` |

The same contracts are available programmatically:

```python
from otoe import Button, event_signature_for, format_event_signature

signature = event_signature_for(Button, "onKeyDown")
assert format_event_signature("onKeyDown", signature) == "onKeyDown(key)"
```

The current `otoe.ui` callback surface follows the same style: `onClick()`,
`on_query(value)`, `on_select(command_id | item_id)`, `on_change(value)`,
`on_open_change(open)`, and `on_navigate(route_id)`.

## Project Shape

Otoe is intentionally split into layers:

- **Core runtime:** nodes, components, signals, effects, events, owners, control flow.
- **Renderer boundary:** fake widgets, HTML preview, `NativeSurface`, and an
  early headless native layout/paint/input spike.
- **Style system:** portable style representation and CSS preview adapter.
- **UI kits:** current `otoe.ui` primitives, growing toward libraries inspired by systems like shadcn or Horizon UI.
- **Case studies:** Wraith validates dense operational UI; SaaS validates softer product UI.

## Repository Map

- `src/otoe/` - runtime package.
- `examples/native/` - framework-neutral native renderer spike demos.
- `examples/wraith/` - Wraith-shaped components and live previews.
- `examples/saas/` - SaaS-shaped generality case study.
- `examples/ui/` - shared UI primitive kitchen-sink preview.
- `preview/` - generated HTML/CSS preview artifacts.
- `tests/` - runtime and preview regression tests.
- `ADR-*.md` - design decisions.
- `BENCHMARKS.md` - concrete Otoe-vs-Wraith UI change benchmarks.
- `COMPONENT_COOKBOOK.md` - small component, state, control-flow, live preview,
  and native smoke recipes.
- `EXAMPLES_GUIDE.md` - current quickstart, live, native, UI kit, SaaS, and
  Wraith example surfaces.
- `MENTAL_MODEL.md` - how nodes, components, signals, events, control flow,
  mounting, and renderers fit together.
- `NATIVE_WORKFLOWS.md` - when to use HTML render, native PNG,
  `NativeSurface`, `NativeWindowDriver`, and `run_native(...)`.
- `NATIVE_RENDERER_SPIKE.md` - current native renderer support and deferred work.
- `STYLE_GUIDE.md` - supported style parser, token, HTML, and native style
  subset behavior.
- `TESTING_GUIDE.md` - snapshot, HTML, native surface, window driver, PNG, and
  backend acceptance testing guidance.
- `WIDGET_CONTRACTS.md` - core widget, control node, UI component, callback,
  and model contracts.
- `ROADMAP.md` - current status and phase plan.

## Fixture Data

Preview data is fictitious and sanitized. The Wraith examples are design and
runtime case studies; they do not run recon, touch network interfaces, or
perform security operations.

## Status

Current status: v0.1.2 prepared; Phase 4 developer experience closeout. See
`ROADMAP.md` for the active plan.

## License

MIT License. Copyright (c) 2026 Forvara.
