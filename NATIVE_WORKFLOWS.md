# Native Workflow Guide

This guide explains which Otoe render path to use while the native renderer is
still experimental. The short rule: use HTML and live preview for app iteration;
use native surfaces and drivers to test the renderer contract; use
`run_native(...)` only for local manual smoke testing.

## Choosing A Path

| Need | Use | Why |
| --- | --- | --- |
| Static app markup or docs screenshots | `otoe render TARGET --out preview.html` | Fast HTML output for an importable `Node` or zero-argument app factory. |
| Interactive browser iteration | `otoe dev TARGET --port 8767` | Local live preview with browser events, signals, rerendering, and app-level workflows. |
| Deterministic native image fixture | `otoe render TARGET --out frame.png --native` | Headless native layout, paint commands, and PNG output without an OS window. |
| Renderer contract test | `NativeSurface` | One mounted tree with layout, paint, hit testing, focus, input, scroll, PNG output, and refresh from a testable object. |
| Window-level input contract test | `NativeWindowDriver` | High-level click, key, text input, and wheel events over the same `NativeSurface` path future backends must drive. |
| Local native window smoke | `run_native(...)` | Optional Tk-backed manual experiment. It is useful for seeing a window, not for production backend claims. |

## HTML Render

Use HTML render when you need a quick static preview of an importable component
tree. It is the least surprising output path and the right first check for docs,
examples, and simple visual snapshots.

```bash
otoe render examples.quickstart:app --out preview.html --pretty
```

HTML render does not prove native layout, paint, input, or backend behavior. It
only proves that the target can be imported and rendered through the HTML
adapter.

## Live Preview

Use `otoe dev` when you are building normal app flows: buttons, forms, route
switching, dialogs, command palettes, and repeated state changes.

```bash
otoe dev examples.live_counter:app --port 8767
```

This is the best workflow for component authoring because it exercises the
browser event path and live rerendering. Keep app code backend-neutral here:
components should not import native modules, Tk, Skia, Taffy, or platform APIs.

## Native PNG

Use native PNG output when you need a deterministic file artifact from the
headless native renderer.

```bash
otoe render examples.quickstart:app --out preview.png --native
```

Native PNG output proves that Otoe can mount the target, compute native layout,
emit paint commands, and rasterize a non-empty frame through the current stdlib
PNG writer. It is not a production raster backend. Text in PNG output remains
deterministic marker output rather than real font shaping.

## NativeSurface

Use `NativeSurface` in tests or examples when you need direct access to the
headless renderer state:

- inspect `surface.layout`, `surface.paint`, or `surface.box(path)`
- render a PNG frame
- dispatch click, key, text input, focus, and scroll behavior
- assert frame changes after state updates
- test native behavior without opening an OS window

```python
from otoe import NativeSurface

surface = NativeSurface(App(), stylesheet=styles)
surface.click(24, 32)
surface.input_text("search")
surface.render_png("frame.png")
```

This is the lowest-level framework-facing native workflow. Use it before
reaching for a window driver.

## NativeWindowDriver

Use `NativeWindowDriver` when the test needs window-shaped events rather than
direct surface calls. It maps click, wheel, key-down, and key-input events to
the current `NativeSurface` behavior while staying headless.

```python
from otoe import NativeWindowDriver

driver = NativeWindowDriver(App(), stylesheet=styles)
driver.click(20, 20)
driver.key_input("a")
driver.wheel(80, 120, 40)
```

Future backend adapters should drive this same contract. If a backend cannot
replay the current backend acceptance surface through `NativeWindowDriver`, it
is not equivalent to the current native path yet.

## run_native

Use `run_native(...)` only for local manual experiments:

```python
from otoe import run_native

run_native(App(), stylesheet=styles, title="Otoe", backend="tk")
```

The built-in `"tk"` backend is optional and requires Python's Tk bindings plus a
graphical display. On Debian/Ubuntu:

```bash
sudo apt install python3-tk
```

The Tk wrapper presents the current paint command stream on a Canvas with
readable text items and scale-to-fit geometry. It is a manual-test adapter, not
a production desktop backend. Do not treat Tk window behavior, PNG marker text,
or current scaling as compatibility promises.

## Backend Rules

- Component code stays backend-neutral.
- Renderer tests should prefer `NativeSurface` or `NativeWindowDriver`.
- Manual OS windows should go through `run_native(...)`, not custom app-level
  mounting/layout/paint wiring.
- New backend candidates must reproduce the backend-replay acceptance test
  before expanding backend-specific behavior.
- Public docs should keep native support framed as headless preview/test support
  until a production backend meets the bar in `ADR-012-native-backend-boundary.md`.
