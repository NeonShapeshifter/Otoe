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

The current implementation is exposed as `PYTHON_NATIVE_RENDERER_BACKEND`, an
experimental `NativeRendererBackend` that wraps Python layout, paint, and PNG
writing. Future renderer candidates should attach at this boundary before they
claim parity with the headless native path.
The SPI is split by capability (`NativeLayoutBackend`, `NativePaintBackend`, and
`NativeRasterBackend`), and `ComposedNativeRendererBackend` can combine them.
Use that split when a candidate only replaces one layer.

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
reaching for a window driver. Renderer experiments can pass
`renderer_backend=...` here to prove their layout, paint, and PNG behavior while
keeping input and focus on the existing surface contract.

## NativeWindowDriver

Use `NativeWindowDriver` when the test needs window-shaped events rather than
direct surface calls. It maps click, wheel, key-down, and key-input events to
the current `NativeSurface` behavior while staying headless.

```python
from otoe import NativeWindowDriver

driver = NativeWindowDriver.from_target(App(), stylesheet=styles)
driver.click(20, 20)
driver.key_input("a")
driver.wheel(80, 120, 40)
```

Future backend adapters should drive this same contract. If a backend cannot
replay the current backend acceptance surface through `NativeWindowDriver`, it
is not equivalent to the current native path yet.

Renderer experiments can also pass `renderer_backend=...` to
`NativeWindowDriver.from_target(...)` to test a new renderer behind the same
window-shaped input replay.

The current backend-candidate acceptance bar has three replay surfaces:

- the minimal harness in `tests/test_native_backend_contract.py`
- the app-shaped native task board replay
- the fake adapter replay through `run_native(...)`

New candidates should reproduce those surfaces before adding backend-specific
layout, paint, text, GPU, or packaging behavior.
`examples/native/backend_candidate_skeleton.py` is the first no-dependency
starting point for that work: it records a candidate adapter run, provides a
`HeadlessCandidateBackend`, includes a no-dependency `RecordingRendererCandidate`,
drives the minimal replay and task board replay through `run_native(...)`, and
returns small acceptance reports with layout, paint, focus, frame,
renderer-backend, and visible-text summaries. The
`run_renderer_candidate_acceptance()` helper runs those same replays through the
renderer SPI and records `layout`, `paint`, and `write_png` calls. The
`renderer_contract_snapshot_to_dict(...)` helper and
`--renderer-contract-json` CLI flag produce the schema-versioned JSON snapshot
used as the golden renderer contract. `RasterOnlyRendererCandidate` is the first
partial candidate: it keeps Python layout and paint but replaces `write_png`
with a separate no-dependency raster path. `PaintOnlyRendererCandidate` keeps
Python layout and raster but replaces `paint(...)` with an alternate compatible
paint command stream. `LayoutOnlyRendererCandidate` currently covers the
minimal replay, static task-board layout acceptance, and interactive task-board
replay while preserving Python paint and raster output. The
`run_composed_renderer_candidate_acceptance(...)` helper wires
`LayoutOnlyRendererCandidate`, `PaintOnlyRendererCandidate`, and
`RasterOnlyRendererCandidate` into `ComposedNativeRendererBackend`, then runs
the interactive replays plus a PNG smoke so every capability is exercised.
`--composed-renderer-contract-json` prints that composed contract, and
`--composed-renderer-png` chooses the PNG smoke path. Add
`--compact-contract` to either renderer contract command when the desired
artifact is a smaller signature-and-hash contract instead of the full
layout/paint snapshot.

```bash
PYTHONPATH=src:. python -m examples.native.backend_candidate_skeleton
PYTHONPATH=src:. python -m examples.native.backend_candidate_skeleton --json
PYTHONPATH=src:. python -m examples.native.backend_candidate_skeleton --renderer-contract-json
PYTHONPATH=src:. python -m examples.native.backend_candidate_skeleton --renderer-contract-json --compact-contract
PYTHONPATH=src:. python -m examples.native.backend_candidate_skeleton --composed-renderer-contract-json --composed-renderer-png preview/native/composed_renderer_candidate.png
PYTHONPATH=src:. python -m examples.native.backend_candidate_skeleton --composed-renderer-contract-json --compact-contract --composed-renderer-png preview/native/composed_renderer_candidate.png
PYTHONPATH=src:. python -m examples.native.backend_candidate_skeleton --composed-renderer-contract-json --compact-contract --composed-renderer-png /tmp/composed_renderer_candidate.png --contract-out examples/native/contracts/composed_renderer_compact_expected.json
PYTHONPATH=src:. python -m otoe compare-contract examples/native/contracts/composed_renderer_compact_expected.json actual-contract.json
PYTHONPATH=src:. python -m otoe compare-contract examples/native/contracts/composed_renderer_compact_expected.json actual-contract.json --ignore-path /pngSmoke/path --ignore-path /calls/raster/signature/0/subject --ignore-path /calls/raster/hash
```

Use `otoe compare-contract` for candidate contract comparisons in CI. It exits
zero only when the JSON artifacts match, reports JSON-pointer paths for human
diffs, can emit a machine-readable report with `--json`, and can ignore
intentional environment-specific fields with `--ignore-path`. If the composed
renderer PNG smoke filename differs from the fixture, ignore `/pngSmoke/path`,
`/calls/raster/signature/0/subject`, and `/calls/raster/hash` together. The
checked-in `examples/native/contracts/composed_renderer_compact_expected.json`
fixture is the current expected compact composed-renderer contract. Refresh it
only when an intentional contract change lands, using `--contract-out` so the
update command does not depend on shell redirection.

The native support matrix and renderer spike documentation are also executable
drift checks: `tests/test_native_support_matrix.py` keeps `NATIVE_RENDERER_SPIKE.md`
aligned with supported style, widget, input, fallback, ignored, and deferred
entries.

## run_native

Use `run_native(...)` only for local manual experiments:

```python
from otoe import run_native

run_native(App(), stylesheet=styles, title="Otoe", backend="tk")
```

When `run_native(...)` receives a raw target, renderer experiments may pass
`renderer_backend=...`; when they already pass a `NativeSurface` or
`NativeWindowDriver`, that object must already have the intended renderer
backend attached.

The built-in `"tk"` backend is optional and requires Python's Tk bindings plus a
graphical display. On Debian/Ubuntu:

```bash
sudo apt install python3-tk
```

The Tk wrapper presents the current paint command stream on a Canvas with
readable text items and scale-to-fit geometry. It is a manual-test adapter, not
a production desktop backend or model for future production backends. Do not
treat Tk window behavior, PNG marker text, or current scaling as compatibility
promises.

## Backend Rules

- Component code stays backend-neutral.
- Renderer tests should prefer `NativeSurface` or `NativeWindowDriver`.
- Renderer backend candidates should implement `NativeRendererBackend` and pass
  through the minimal harness, native task board replay, fake adapter replay,
  renderer-candidate replay, and `tests/test_native_renderer_backend.py`.
- Partial renderer candidates should use the layout/paint/raster capability
  split and prove which capability they replace.
- Layout-only candidates must start with the minimal replay, then static
  task-board layout acceptance, then the interactive app-shaped task board
  replay.
- Manual OS windows should go through `run_native(...)`, not custom app-level
  mounting/layout/paint wiring.
- New backend candidates must reproduce the minimal harness, native task board
  replay, and fake adapter replay before expanding backend-specific behavior.
- Public docs should keep native support framed as headless preview/test support
  until a production backend meets the bar in `ADR-012-native-backend-boundary.md`.
