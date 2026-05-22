# Native Renderer Spike

**Status:** experimental headless spike with optional local window wrapper
**Updated:** May 22, 2026

This document describes the renderer boundary that exists today. It is not a
production desktop backend yet. The goal is to keep the contract precise while
Otoe proves that a mounted component tree can produce layout boxes, paint
commands, PNG pixels, hit-tested input, and rerendered state without using the
HTML preview backend.

The `examples.native.counter_demo`, `examples.native.task_board_demo`, and
`examples.native.window_demo` modules are the current framework-neutral
validation surfaces. The task board demo is intentionally app-shaped: shell,
search, filtered rows, empty state, modal state, shortcuts, controlled input,
controlled scroll, and multi-frame PNG output. The window demo drives that same
app-shaped surface through `NativeWindowDriver` and can optionally open a Tk
window for manual experiments.

The task board also has behavior-parity coverage against the HTML render path:
after native input, click, Escape, and shortcut dispatch, the native layout text
and controlled input values must match the same mounted tree rendered through
`render_html(...)`.

## Current Pipeline

The supported path is:

```text
Node tree -> mount(...) -> layout_native(...) -> paint_native(...) -> write_native_png(...)
                                    |
                                    v
                         hit_test_native(...) / dispatch_native_click(...)
```

The framework-facing helper for that path is `NativeSurface`. It owns the
headless frame loop for one mounted tree:

```python
surface = NativeSurface(App(), stylesheet=APP_STYLES)
surface.render_png("frame.png")
surface.click(x, y)
surface.render_png("next-frame.png")
```

`NativeSurface` keeps the current `layout`, `paint`, and `frame` count, exposes
`box(path)` for deterministic tests, tracks a focused path, refreshes
layout/paint after click or keyboard dispatch, and lazily refreshes when
reactive prop or control-flow updates mutate the mounted fake-widget tree. It
is still headless; it does not create windows or run an OS event loop.

`NativeWindowDriver` is the testable window-facing wrapper over `NativeSurface`.
It accepts high-level click, key-down, and controlled text-input events, then
delegates to the surface and exposes the resulting frame, paint, size, focus,
and PNG output. `TkNativeWindow` is an optional local experiment layer on top of
that driver; it imports `tkinter` only when constructed and is not part of the
production renderer contract. On Debian/Ubuntu, the optional window smoke needs
the OS Tk package: `sudo apt install python3-tk`.

The headless PNG path still uses deterministic marker text for tests and file
output. The Tk wrapper is now a small paint/text proof: it presents the current
`PaintCommand` stream on a Tk `Canvas`, mapping text commands to Tk text items so
manual windows can show readable labels. Resizing the window scales the current
paint geometry up to 2x and maps pointer events back to logical `NativeSurface`
coordinates, while font sizes remain in logical native units to avoid wrapping
inside fixed-height cells. This does not perform responsive layout reflow yet.
It is not a production text renderer; ADR-008 still owns the full text-shaping
and font-fallback deferral, and ADR-016 documents the Tk Canvas proof.

To keep Tk text from drawing over neighboring widgets, text paint commands use
the available width from their layout boxes and the Canvas presenter passes that
width to `create_text(...)`. This is still a simple bounds discipline, not full
font measurement or native clipping.

`run_native(...)` is the experimental framework-facing entry point for launching
a native tree. Today it creates the same `NativeWindowDriver` and uses the
optional Tk backend. The public entry point is intentionally backend-neutral so
the implementation can move to another windowing layer later.

Backend selection is now routed through `NativeBackendAdapter`. Registered
backend names can be inspected with `native_backend_names()` and resolved with
`native_backend_adapter(...)`. `run_native(..., backend=...)` accepts either a
registered name such as `"tk"` or an object implementing the adapter protocol.
Invalid backends fail before the target is mounted. ADR-015 defines the adapter
contract.

These native and window-facing names are also declared in the executable API
status registry as `experimental-native`. This preserves today's imports for
examples and tests while making the lack of a compatibility promise explicit:

```python
from otoe import api_status

assert api_status("run_native").category == "experimental-native"
```

Window, event loop, and backend ownership are defined in
`ADR-007-native-window-ownership.md`. The short version: `NativeSurface` owns the
headless renderer state, `NativeWindowDriver` owns testable high-level input
dispatch, and concrete window backends own OS resources.

The native spike consumes `MountedNode` or `FakeWidget` trees. Components,
`Show`, and `For` are already resolved by `mount(...)`, so the renderer only
sees widget names, resolved props, event handlers, and ordered children.

## Supported Widgets

The current layout adapter has explicit behavior for:

- `VStack`: vertical child layout.
- `HStack`: horizontal child layout.
- `Text`: text-sized leaf box.
- `Button`: text-sized leaf box with default padding, fill, border, and click
  event support.
- `Input`: text-sized leaf box with default width, padding, fill, and border.
- `Panel`, `FocusScope`, and `ShortcutScope`: container boxes.
- `ScrollView`: bounded container box with `scrollY`, clipped descendant paint,
  hit-testing, and controlled `onScroll`.
- `Show` and `For`: container boxes after mount-time control-flow resolution.

Unknown widgets, for example a user-defined `Hero` widget, are treated as column
containers for now. That keeps the spike useful for generic trees while the
formal native widget set is still small.
This behavior is intentional and covered by the executable widget matrix in
`otoe._native_shared`: `Text` is a text leaf, `Button` and `Input` are controls,
known stack/scope/control-flow wrappers are containers, and unknown widgets are
fallback containers.

The executable widget support categories are:

- `text`: `Text`
- `control`: `Button`, `Input`
- `container`: `FocusScope`, `For`, `HStack`, `Panel`, `ScrollView`,
  `ShortcutScope`, `Show`, `VStack`
- fallback: any unknown widget name, such as `Hero`

## Supported Layout

Layout is deterministic and integer-based. The output is a `NativeLayout`
containing stable `LayoutBox` entries with path, widget name, position, size,
text, events, resolved style, and child boxes.

The layout adapter currently supports:

- Vertical and horizontal stacking.
- Child order.
- `alignItems` on `HStack` and `VStack` for `start`, `flex-start`, `center`,
  `end`, `flex-end`, and `stretch`.
- `gap`.
- `justifyContent` on `HStack` and `VStack` for `start`, `flex-start`,
  `center`, `end`, `flex-end`, and `space-between`.
- `padding`.
- `width` and `height`.
- `min-width`, `min-height`, `max-width`, and `max-height`.
- Text measurement approximation from string length and `font-size`.
- Reactive prop updates through rerunning `layout_native(...)`.
- `ScrollView` viewport bounds for constrained children.
- `ScrollView(scrollY=...)` vertical child offset.
- Strict class resolution through `StyleSheet.resolve(...)`.

Exact dimensions override intrinsic content size, max constraints cap the
result, and min constraints floor the result. If min and max constraints
conflict, min wins so controls do not shrink below their declared minimum.

All layout dimensions must be non-negative numeric pixels. Percent units,
`auto`, negative sizes, flex grow/shrink distribution, wrapping, margins,
horizontal scroll offsets, baseline alignment, and intrinsic platform text
measurement are intentionally not implemented yet. `alignItems` and
`justifyContent` are stack-only features on `HStack` and `VStack`; unsupported
values or non-stack widgets fail with
`NativeLayoutError`. `ADR-013-native-layout-hardening.md` documents this
hardening boundary, and `ADR-017-native-stack-alignment-pass.md` documents the
first post-release Python layout pass.

`ScrollView(scrollY=...)` accepts numeric pixel values, clamps negative scroll
to zero, and clamps excessive scroll to the current content bounds.

Normal containers do not clip overflow. Fixed `width` and `height` constrain the
container box, but descendants may paint and receive hit-tested input outside
that box. `ScrollView` is the only current clipping boundary: descendant paint
commands receive the scroll viewport clip, and hit testing ignores descendants
outside the scroll viewport. `ADR-014-native-overflow-clipping.md` documents this
overflow policy.

Each `LayoutBox` carries a `context` string when it comes from a component tree,
for example `TaskList > VStack`. Native layout and paint diagnostics use that
context for unsupported dimensions, style keys, and paint colors where possible.

## Accessibility Metadata Expectations

The native spike does not implement a platform accessibility tree yet.
`LayoutBox` is the current seed contract for that future work. It must preserve
widget `name`, tree `path`, optional `id`, visible `text`, event names, widget
state, component `context`, bounds, and child hierarchy.

`ADR-009-native-accessibility-metadata.md` documents this boundary. Backend
work can derive provisional roles from widget names later, but Otoe does not
expose public role, label, or OS accessibility APIs yet.

## Native Style Support Matrix

The native backend has an executable style matrix in `otoe._native_shared`.
Styles parsed by `css(...)` are not automatically native behavior.

Native layout-only style keys currently are:

- `alignItems`
- `gap`
- `height`
- `justifyContent`
- `maxHeight`
- `maxWidth`
- `minHeight`
- `minWidth`
- `padding`
- `scrollY`
- `width`

Native paint-only style keys currently are:

- `background`
- `borderColor`
- `borderRadius`
- `color`

Native layout-and-paint style keys currently are:

- `borderWidth`
- `fontSize`

The following parsed properties are accepted and preserved in `LayoutBox.style`,
but intentionally have no native effect yet:

- `display`
- `fontWeight`
- `margin`
- `opacity`

Unknown CSS properties still fail in `css(...)`. Unknown style keys injected
through a manually constructed `StyleSheet` fail in the native style matrix with
`NativeLayoutError`; for example, `lineHeight` is not in the native matrix.
Non-pixel dimensions fail in layout, and unresolved or invalid colors fail in
paint.

## Supported Paint

The paint adapter converts layout boxes into deterministic `PaintCommand`
objects and can write a PNG using only the Python standard library.

The current painter supports:

- Background rect for the surface.
- Box fills from `background`.
- Box strokes from `border-color` and `border-width`.
- Rounded rect masking from `border-radius`.
- Text marker output from box text, `color`, and `font-size`.
- Default button and input colors when styles are not provided.
- Disabled button and input paint defaults.
- Focus ring commands for focused buttons and inputs through
  `paint_native(..., focused_path=...)` and `NativeSurface`.
- Token-resolved colors from `css(..., tokens={...})`.
- `ScrollView` descendant clipping through paint command clip rects, including
  stdlib PNG output.
- Normal container overflow remains unclipped in paint commands.

The text output is a deterministic marker, not font rasterization. Layout and
paint share the private `measure_native_text(...)` metric contract so text box
sizes and text paint commands agree exactly. This is good enough for non-empty
image tests and state-change detection, but it is not a real text renderer.
`ADR-008-native-text-rendering.md` documents why real font measurement and
rasterization are deferred to a backend spike.

## Supported Input

The input spike supports click dispatch:

- `hit_test_native(layout, x, y, event="onClick")` returns the deepest box that
  contains the coordinate, then walks ancestors until it finds a matching event.
- `dispatch_native_click(mounted, layout, x, y)` triggers the matched Otoe
  handler through the existing event system.
- `NativeSurface.click(x, y)` dispatches through the current layout and then
  refreshes layout/paint for the next headless frame.
- Hit-testing respects `ScrollView` viewport bounds, so clipped descendants do
  not receive clicks.
- Hit-testing does not use normal container bounds as clipping boundaries, so
  overflow from stacks and panels remains interactive.
- Disabled widgets are skipped for focus and do not fire native click handlers.
- Low-level callers own rerendering by running layout/paint again after state
  changes.
- `NativeSurface.layout`, `NativeSurface.paint`, and `NativeSurface.box(...)`
  lazily refresh if external signal updates changed reactive props or
  `Show`/`For` child structure outside direct surface events.

The `NativeSurface` focus and keyboard subset supports:

- Initial `Input(autoFocus=True)` focus.
- Click-to-focus for buttons and inputs.
- `onFocus` and `onBlur` dispatch when focus changes.
- `Tab` and `Shift+Tab` traversal across enabled buttons and inputs.
- Focused `onKeyDown` dispatch with the same string key shape used by the live
  HTML preview backend.
- `Enter`, space, and `Spacebar` activation for focused buttons.
- `ShortcutScope` global key payload dispatch with the same `{key, ctrlKey,
  metaKey, altKey, shiftKey}` shape used by the live HTML preview backend.
- Controlled input text dispatch through `NativeSurface.input_text(...)`, which
  sends the new value to the focused or explicitly targeted `Input.onChange`
  handler and refreshes the next headless frame.
- Controlled scroll dispatch through `NativeSurface.scroll(x, y, delta_y)`,
  which finds the containing `ScrollView`, clamps the next `scrollY`, calls
  `onScroll(next_scroll_y)`, and refreshes the next headless frame.
- Layout clamps excessive `scrollY` values to the current content bounds.
- `NativeWindowDriver` event dispatch for high-level `click`, `key_down`, and
  `input_text` events over the current `NativeSurface`.
- `NativeWindowDriver.wheel(x, y, delta_y)` and `NativeWindowEvent("wheel", ...)`
  dispatch for controlled scroll views.
- `NativeWindowDriver.key_input(...)` dispatch for platform keypress events:
  printable text edits focused inputs, Backspace/Delete mutate the controlled
  value, Enter/Tab fall through to `key_down`, and modified keys remain
  available to shortcut handlers.
- Optional `TkNativeWindow` wrapper for local manual experiments with OS mouse
  and keyboard events translated into `NativeWindowDriver` events.
- `TkNativeBackendAdapter` registered as `"tk"` for routing `run_native(...)`
  through the same backend interface future window adapters must implement.
- Tk Canvas presentation of `PaintCommand` rectangles and text for manual
  paint/text validation without changing the headless PNG path.
- Tk Canvas scale-to-fit presentation capped at 2x with pointer/wheel coordinate
  mapping back to logical native coordinates.
- Text paint commands carry layout-box text width so Tk Canvas labels respect
  fixed control and cell bounds.
- `run_native(...)` as the experimental native app runner, currently backed by
  the optional Tk backend adapter.

Caret movement, text selection, uncontrolled input mutation, pointer movement,
IME, drag, inertial scroll physics, gesture, and bubbling/capture semantics are
deferred.

The native input support matrix is executable in `otoe._native_shared`.
Currently supported entries are:

- `click`
- `focus`
- `input_text`
- `key_down`
- `key_input`
- `shortcut`
- `tab_focus`
- `wheel`

Deferred entries are:

- `caret_movement`
- `drag`
- `gesture`
- `ime`
- `inertial_scroll`
- `pointer_move`
- `text_selection`
- `uncontrolled_input`

Unknown entries, such as a hypothetical `pinch` event, are not in the matrix.

## Rejected For This Spike

These are intentionally outside the current headless boundary:

- GPU rendering.
- Skia-specific public APIs.
- Taffy-specific public APIs.
- CSS layout parity.
- DOM-style event bubbling.
- Native text shaping or font fallback.
- Pixel-perfect parity between Tk Canvas presentation and PNG marker output.
- Animation timing.
- Production packaging.
- Production security model for a remotely exposed preview server.

The optional Tk wrapper is deliberately not a production backend. It is a thin
manual-test adapter over the same headless surface contract.

The spike should fail clearly where possible. Unsupported style classes are
strict by default. Non-pixel layout dimensions raise `NativeLayoutError`.
Unresolved or invalid paint colors raise `NativePaintError`.
When a box was produced by a component, these errors include the component and
widget context, such as `PaintPanel > VStack`.

## Deferred Backend Work

Once the headless contract is stable, the next backend layers can be evaluated
without changing the component API:

- Taffy or another layout solver behind `layout_native(...)`.
- Skia or another raster backend behind the paint command contract.
- Production windowing and OS event loop adapters.
- Production-quality implementations of the `NativeBackendAdapter` protocol.
- Accessibility tree generation from `LayoutBox` metadata.
- Backend-level focus synchronization and platform key routing.
- Text shaping, font selection, and DPI scaling.
- Dirty-region or retained-render optimizations.

The success criterion is not "use Skia and Taffy." The success criterion is
that Otoe keeps a small, testable renderer contract that can swap those engines
in without rewriting user components.
