# ADR-021: Native Backend Roadmap With Yoga, Skia, And SDL3

**Status:** Proposed
**Date:** June 12, 2026

## Context

Otoe is an experimental Python UI runtime for operational interfaces. It already
has a useful Python component model, reactivity, HTML/static preview, live HTML
preview, deterministic headless native PNG output, input tests through
`NativeSurface`, offline build validation, and backend-candidate evidence
surfaces.

The current native path is intentionally a deterministic headless renderer
spike. It is good for tests, PNG evidence, fixtures, portable-core validation,
and early backend contracts. It is not yet a production native renderer or
hardware windowing runtime.

Wraith is the first serious product-shaped validation target for Otoe's native
ambitions. Wraith is an appliance/operator UI problem: touch, mouse, keyboard,
local control surfaces, constrained Linux hardware, predictable offline
behavior, and no desire to be trapped forever in Kivy, Qt, or a browser as the
core runtime.

HTML and browser/kiosk rendering remain useful for preview, docs, and fast
iteration. They are not the long-term native vision. The long-term goal is a
native appliance UI runtime that can render and interact with Otoe apps directly
on Linux hardware.

ADR-019 chose Pillow/FreeType as the first optional readable text path for
headless PNG output. ADR-020 deliberately kept native layout v0 stack-first and
postponed layout-engine adoption. This ADR records the larger native backend
vision so the project has a clear north star while still starting with a small
executable path.

## Decision

Otoe will pursue a native backend roadmap with this target stack:

- **Layout:** Yoga.
- **Paint/raster:** Skia.
- **Window/input/presentation host:** SDL3.
- **Linux deployment path:** SDL3's Wayland backend running under a compositor
  such as Weston or Cage.

The first native backend must stay behind Otoe backend boundaries. Otoe core
must not directly depend on Yoga, Skia, or SDL3. The native stack is an optional
backend path, not a required dependency for the Python runtime, HTML preview,
headless tests, or offline bundles.

The initial implementation path is **Skia CPU raster into an SDL3-presented
buffer/texture**. Skia GPU, direct Wayland clients, DRM/KMS, and compositor
implementation are deferred.

## Big Vision

The full target pipeline is:

```text
Python Otoe app
  -> mounted component tree
  -> Otoe native render tree
  -> Yoga layout backend
  -> Otoe display list
  -> Skia paint/raster backend
  -> SDL3 host/input/presentation
  -> SDL3 Wayland backend
  -> Weston/Cage or another Wayland compositor
  -> Linux display/input stack
  -> appliance hardware
```

Otoe should eventually support hardware/appliance surfaces directly:

```bash
otoe run-native examples.wraith.mission_exec_native:app \
  --layout yoga \
  --paint skia \
  --host sdl3 \
  --fullscreen
```

This does not mean Otoe becomes a browser clone, CSS engine, Qt replacement, or
Flutter clone. The product goal is narrower: Python-first operational UI
surfaces that can be tested, snapshotted, bundled, and eventually run natively
on constrained Linux hardware.

## Architecture Boundaries

The native backend must be split into explicit boundaries.

### Native Render Tree

The native render tree is the framework-neutral representation of the mounted
Otoe UI before layout and paint. It should describe:

- node kind,
- children,
- key/identity,
- text content,
- style values,
- focusability,
- disabled state,
- scrollability,
- event handlers or event identities,
- component-aware diagnostics.

It must remain independent of Yoga, Skia, and SDL3.

### Layout Backend

A layout backend receives a layout tree and constraints, then returns boxes for
nodes:

```text
input:  layout tree + constraints
output: x/y/width/height boxes per native node
```

The target backend is Yoga, but the Otoe-facing contract should be generic:

```text
LayoutBackend
  compute(layout_tree, constraints) -> LayoutResult
```

Otoe layout v0 remains stack-first until a Yoga-backed layout engine proves
compatibility and value. The Yoga path should initially support only the subset
needed by Otoe primitives and Wraith-shaped surfaces.

### Text Measurement

Text measurement is a first-class boundary because Yoga needs measured leaf
sizes. The first useful version may be limited to:

- one primary font,
- one monospace font,
- basic Latin text,
- simple single-line measurement,
- limited wrapping,
- explicit font size and line height.

Advanced shaping, font fallback, complex scripts, emoji, IME behavior, text
selection, and caret geometry are future work.

### Display List

Otoe should produce a backend-agnostic display list. Otoe core should not call
Skia directly. The display list should contain commands such as:

- `FillRect`,
- `StrokeRect`,
- `FillRoundedRect`,
- `StrokeRoundedRect`,
- `DrawText`,
- `DrawImage`,
- `PushClip`,
- `PopClip`,
- optional debug markers.

This allows multiple renderers to interpret the same paint intent:

```text
DisplayList -> debug renderer
DisplayList -> deterministic PNG renderer
DisplayList -> Skia renderer
DisplayList -> future alternate renderer
```

### Paint Backend

A paint backend receives a display list and produces pixels, a PNG, or a frame:

```text
PaintBackend
  render(display_list, target) -> frame/pixels/png
```

The target backend is Skia. The first Skia path should be CPU raster. It should
not require Vulkan, OpenGL, Ganesh, Graphite, EGL, or GPU device setup.

### Host Backend

A host backend owns the native window, frame loop, presentation, and platform
input:

```text
HostBackend
  open_window(...)
  present(frame)
  poll_events() -> NativeInputEvent[]
  close()
```

The initial host backend target is SDL3. SDL3 is selected because it gives Otoe
a native window/input/presentation layer without making Otoe implement a direct
Wayland client in v0.

SDL3 is not a UI toolkit. It does not own Otoe widgets, layout, styling, or
state. It is the host/presentation layer below Otoe.

### Native Input Event Model

Platform events must be translated into Otoe-native input events before they
reach components:

- pointer move/down/up,
- touch down/move/up,
- wheel/scroll,
- key down/up,
- text input later,
- window close,
- resize/configure,
- scale/DPI changes.

The Otoe input contract should align with Portable Input Core v0:

- click/tap activation,
- Tab and Shift+Tab focus traversal,
- Enter/Space activation,
- Escape dismiss/cancel,
- wheel and basic touch scroll,
- visible focus,
- disabled state respected,
- no critical hover-only actions.

## Why Yoga

Yoga is a pragmatic layout target because it is C/C++-oriented, mature, and
sufficient for a controlled flexbox-like appliance UI subset. It can support the
layout concepts Otoe needs first:

- vertical and horizontal stacks,
- fixed sizes,
- min/max constraints,
- padding,
- gaps or gap emulation,
- align/justify,
- grow/shrink later,
- text measure callbacks.

Yoga does not make Otoe a full CSS engine and does not solve text measurement by
itself. Otoe still needs a layout boundary, a text measurement boundary, and
compatibility tests against layout v0.

## Why Skia

Skia is a strong long-term paint/raster target. It is used by major rendering
stacks and can draw the primitives Otoe needs for serious appliance UIs:

- anti-aliased rects and rounded rects,
- strokes and clips,
- text,
- images,
- gradients/shadows later,
- CPU raster first,
- GPU acceleration later if needed.

Skia is large and packaging-heavy. This ADR does not make Skia a required Otoe
dependency. The first Skia work should be optional and should not break the
stdlib/Pillow native paths.

## Why SDL3

SDL3 is the selected first host because it provides:

- native window creation,
- fullscreen support,
- presentation of rendered buffers/textures,
- keyboard input,
- mouse input,
- touch input on supported platforms,
- wheel events,
- display scale/DPI information,
- Wayland backend support on Linux,
- a simpler path to hardware than direct Wayland v0.

SDL3 keeps the stack native without turning Otoe into a browser, Qt app, Kivy
app, or WebView. It also keeps direct Wayland, DRM/KMS, and compositor work out
of the first useful milestone.

## Relationship To Wayland, Weston, And Cage

Wayland is the modern Linux display protocol Otoe should expect on appliance
Linux. Weston and Cage are compositor/session choices below the app. They are
not Otoe core architecture.

The first native deployment shape is:

```text
Otoe SDL3 app
  -> SDL3 Wayland backend
  -> Weston or Cage
  -> Linux display/input stack
```

Direct Wayland clients may be considered later if SDL3 becomes a blocker.
DRM/KMS direct output may be considered later for tightly controlled appliance
images. Otoe must not start by implementing a compositor or direct KMS host.

## Minimum V0

The minimum useful native backend is not the full target stack. The smallest
meaningful V0 is:

```text
Otoe can render and interact with one Wraith-shaped MissionExec surface in a
native SDL3 window using an Otoe-native display list, a Skia CPU raster path,
and either layout v0 or a small Yoga-backed subset.
```

Minimum V0 capabilities:

- build a native render tree from a mounted Otoe app,
- produce a display list from a simple scene,
- render the display list to a PNG or pixel buffer,
- render through Skia CPU raster when the optional native dependency is
  available,
- open an SDL3 window,
- present a rendered frame,
- process basic click/tap,
- process Tab and Shift+Tab focus traversal,
- process Enter/Space activation,
- process Escape,
- process vertical wheel scroll,
- render basic text with an explicit font policy,
- render Wraith MissionExec snapshot content without importing Wraith,
- leave HTML preview and current native PNG tests working without native deps.

Minimum V0 does not need:

- full Yoga coverage,
- full flexbox parity,
- Skia GPU,
- direct Wayland,
- DRM/KMS,
- complex text shaping,
- production packaging,
- full Wraith replacement,
- real mission execution.

## Implementation Phases

### Phase A — ADR And Display List Boundary

Deliverables:

- this ADR,
- `native_display_list` module,
- serializable/debuggable display list commands,
- tests proving display-list construction does not import Skia, Yoga, or SDL3.

Acceptance:

- display list supports rects, rounded rects, text, and clips,
- display list can be inspected in tests,
- existing native renderer tests keep passing.

### Phase B — Native Scene Builder

Deliverables:

- conversion from a small Otoe mounted tree to native scene/display-list input,
- support for `Text`, `Button`, `Panel`/`Card`, `VStack`, `HStack`, and simple
  badges or labels,
- no C/C++ dependencies yet.

Acceptance:

- a simple Otoe app produces a deterministic display list,
- component identity and event targets are retained for hit testing,
- no Skia/Yoga/SDL3 imports in the pure path.

### Phase C — Skia CPU PNG Renderer

Deliverables:

- optional Skia renderer for display-list-to-PNG or display-list-to-pixels,
- clear unavailable error or skipped tests when Skia is missing,
- explicit font path support for deterministic text.

Acceptance:

- render `FillRect`, `FillRoundedRect`, `StrokeRect`, `PushClip`, `PopClip`, and
  `DrawText` to a PNG,
- no impact on default no-dependency test suite,
- Pillow/marker native paths remain available.

### Phase D — SDL3 Host Hello Window

Deliverables:

- minimal SDL3 host module or native extension entrypoint,
- open a window,
- present a solid frame or Skia-rendered buffer,
- close on Escape/window close,
- log or surface click/key events in debug mode.

Acceptance:

- manual command opens a native window,
- Escape closes the window,
- click and key events are visible to the Otoe host layer,
- no Wraith involvement.

### Phase E — Yoga Layout Backend

Deliverables:

- layout backend protocol implementation using Yoga,
- mapping for `VStack`, `HStack`, text leaves, buttons, panels, and fixed
  viewport scroll regions,
- text measurement callback using the active text measurement backend.

Acceptance:

- deterministic layout result for simple trees,
- compatibility tests against stack layout v0 behavior for supported cases,
- unsupported layout features fail clearly or remain documented as unsupported.

### Phase F — Otoe Native Window Smoke

Deliverables:

- first end-to-end native smoke app,
- Otoe app -> layout -> display list -> Skia -> SDL3 window,
- click updates reactive state,
- keyboard activation updates state.

Acceptance:

- a counter/button app opens in a native SDL3 window,
- mouse click changes state,
- Tab focus and Enter/Space activation work,
- frame refresh happens after reactive state changes.

### Phase G — Wraith MissionExec Native Smoke

Deliverables:

- Wraith-shaped MissionExec snapshot fixture,
- native window example that renders the snapshot,
- no Wraith import,
- no real mission execution.

Acceptance:

- MissionExec snapshot renders in a native SDL3 window,
- logs are visible,
- vertical scroll works,
- primary buttons render and respect disabled state,
- pending approval dialog or panel can be represented,
- tests prove the JSON contract stays compatible.

### Phase H — Hardware Smoke

Deliverables:

- documented Raspberry Pi/Linux appliance smoke path,
- SDL3 using Wayland under Weston or Cage,
- fullscreen 1280x800 target,
- touch/click/keyboard/scroll manual validation.

Acceptance:

- hardware proof exists: commands, environment, limitations, and screenshot or
  photo/video evidence,
- touch/click activates visible controls,
- keyboard can focus and activate controls,
- scroll works in the MissionExec log viewport,
- no real Wraith mission execution is required.

### Phase I — Packaging And CI

Deliverables:

- optional native extra or separate native package strategy,
- clear install/build docs,
- CI job that can skip cleanly without native system deps,
- eventual Linux x86_64 and Linux aarch64/Pi wheel strategy.

Acceptance:

- default Otoe install remains lightweight,
- native dependency absence gives clear errors,
- native tests are isolated from the default no-dependency suite,
- release docs explain what is experimental.

## Wraith Validation Path

Wraith is a validation target, not a hard dependency of Otoe.

Rules:

- Otoe must not import Wraith.
- Otoe examples must not execute Wraith missions.
- Wraith integration should use JSON snapshot contracts first.
- Wraith command bridges must be controlled, policy-safe, and later than
  read-only rendering.
- Kivy remains Wraith's production UI until native Otoe proves itself on real
  surfaces and hardware.

Suggested Wraith/Otoe sequence:

1. Otoe defines/normalizes `wraith.ui.mission_exec.v0` snapshots.
2. Wraith adds a pure MissionExec snapshot producer with the same shape.
3. Otoe renders JSON exported by Wraith without importing Wraith.
4. Otoe native backend renders the same snapshot to PNG/window.
5. Wraith optionally exposes a read-only preview path.
6. Only later, controlled commands such as pause, abort, approve, deny, and
   export are bridged through existing Wraith policy/runtime services.

## Non-Goals

Not in V0:

- no full CSS engine,
- no browser compatibility,
- no claim that native output matches HTML preview pixel-for-pixel,
- no Skia GPU path,
- no direct Wayland client,
- no DRM/KMS host,
- no compositor implementation,
- no Qt/Kivy/WebView wrapper,
- no full accessibility tree,
- no IME,
- no complex text shaping,
- no full font fallback,
- no drag/drop,
- no advanced gestures or multitouch beyond simple tap/click,
- no animations as a required milestone,
- no production Wraith UI replacement,
- no real offensive/security mission execution from Otoe examples,
- no required native dependencies for default Otoe installation.

## Risks

### Skia Packaging

Skia is the largest dependency risk. Building, linking, and distributing Skia
for Linux x86_64 and aarch64/Pi may be difficult. The first Skia milestone must
be optional and should not break source checkout tests when Skia is unavailable.

### SDL3 Availability

SDL3 is newer than SDL2. Some target distributions may not provide suitable
packages. Otoe needs a documented strategy for system SDL3, vendored builds, or
native wheels before claiming production readiness.

### Yoga Integration

Yoga integration requires bindings, layout mapping, and text measurement
callbacks. Otoe must keep layout v0 compatibility tests so layout-engine work
expands the product contract instead of silently changing it.

### Text Measurement And Shaping

Text is a hidden complexity. Wraith-style UIs need readable labels, clipped log
lines, monospace telemetry, wrapping in panels, and stable screenshots. Complex
shaping, fallback, caret geometry, and IME are deferred but must not be ignored
forever.

### Input, Focus, And Scroll

Native UI quality depends on correct hit testing, focus, activation, disabled
state, and scroll behavior. MissionExec log scrolling and appliance keyboard
smoke tests should be early validation targets.

### Performance And Dirty Regions

CPU raster is acceptable for V0, but repainting full 1280x800 frames at high
frequency may become expensive. Dirty-region rendering, frame pacing, and GPU
paths are future performance work.

### Overengineering

The largest product risk is trying to build a full general-purpose UI toolkit
before validating one serious appliance surface. Wraith MissionExec is the first
validation target precisely to keep scope real.

## Acceptance Criteria

### ADR Acceptance

- The roadmap records the full native vision.
- The roadmap also records a small executable V0.
- The roadmap does not require native dependencies immediately.
- Existing HTML/headless native workflows remain valid.

### Display List Acceptance

- Otoe can build a backend-agnostic display list for a simple app.
- The display-list path imports no Yoga, Skia, or SDL3.
- Tests can inspect display commands deterministically.

### Skia PNG Acceptance

- Optional Skia backend can render a display list to PNG or pixels.
- Missing Skia produces a clear unavailable result or skips native-extra tests.
- The default suite passes without Skia.

### SDL3 Host Acceptance

- A manual native command opens a window.
- Escape/window close exits cleanly.
- Click/key events reach Otoe's host abstraction.
- A frame can be presented from a CPU-rendered buffer.

### Yoga Layout Acceptance

- Yoga backend can layout the supported subset deterministically.
- Text measurement callbacks work for basic text.
- Layout v0 compatibility tests pass for supported stack cases.

### Otoe Native Smoke Acceptance

- A simple reactive Otoe app renders in a native SDL3 window.
- Clicking a button changes state and repaints.
- Tab focus and Enter/Space activation work.

### Wraith Native Smoke Acceptance

- A Wraith MissionExec JSON snapshot renders without importing Wraith.
- Logs are visible and scrollable.
- Buttons and disabled states are represented.
- No mission execution occurs.

### Hardware Smoke Acceptance

- Fullscreen 1280x800 mode runs under a Wayland compositor on target Linux
  hardware.
- Touch/click activates visible controls.
- Keyboard focus and activation work.
- Scroll works in the log viewport.
- Limitations are documented.

## Deferred And Future Work

Deferred beyond V0:

- Skia GPU via OpenGL/Vulkan/Metal/Graphite/Ganesh,
- direct Wayland host,
- DRM/KMS appliance host,
- advanced text shaping and font fallback,
- accessibility tree output,
- IME and text selection,
- animation system,
- dirty-region rendering,
- retained render caches,
- production ARM64 wheel pipeline,
- direct Wraith production replacement,
- advanced gestures,
- drag/drop,
- full CSS/flex/grid parity.

## Consequences

Positive:

- Otoe has a clear native north star aligned with hardware/appliance goals.
- SDL3 makes the first native host achievable without direct Wayland work.
- Yoga and Skia keep the long-term backend serious and native.
- Wraith provides a concrete validation surface instead of abstract UI demos.
- Backend boundaries protect Otoe core from native dependency churn.

Negative:

- This path is significantly harder than HTML/kiosk preview.
- Native packaging, especially Skia and SDL3, will become a serious project.
- The first useful backend still requires multiple staged milestones.
- Otoe must maintain discipline to avoid a half-finished general toolkit.

## First Work To Do

The first implementation work after this ADR should be:

1. **Display list IR.** Add a backend-agnostic native display-list module with
   rect, rounded-rect, text, and clip commands.
2. **Native scene builder.** Convert a small mounted Otoe tree into layout boxes
   and display-list commands without native C/C++ dependencies.
3. **Optional Skia PNG spike.** Render the display list to PNG/pixels when Skia
   is available, while keeping the default test suite dependency-free.
4. **SDL3 hello host.** Open a native window, present a buffer, and report
   click/key events.
5. **Yoga layout spike.** Add a layout backend behind the layout boundary and
   prove compatibility for the supported stack subset.
6. **Wraith MissionExec native smoke.** Render a JSON snapshot in a native
   window without importing Wraith or executing missions.

Do not start with SDL3, Yoga, and Skia all at once. The correct first technical
commit is the display-list boundary.
