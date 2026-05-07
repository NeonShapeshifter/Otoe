# Native Renderer Spike

**Status:** experimental headless spike with optional local window wrapper
**Updated:** May 7, 2026

This document describes the renderer boundary that exists today. It is not a
production desktop backend yet. The goal is to keep the contract precise while
Otoe proves that a mounted component tree can produce layout boxes, paint
commands, PNG pixels, hit-tested input, and rerendered state without using the
HTML preview backend.

The `examples.native.counter_demo`, `examples.native.task_board_demo`, and
`examples.native.window_demo` modules are the current framework-neutral
validation surfaces. The task board demo is intentionally app-shaped: shell,
search, filtered rows, empty state, modal state, shortcuts, controlled input,
and multi-frame PNG output. The window demo drives that same app-shaped surface
through `NativeWindowDriver` and can optionally open a Tk window for manual
experiments.

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
production renderer contract.

`run_native(...)` is the experimental framework-facing entry point for launching
a native tree. Today it creates the same `NativeWindowDriver` and uses the
optional Tk backend. The public entry point is intentionally backend-neutral so
the implementation can move to another windowing layer later.

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

Unknown widgets are treated as column containers for now. That keeps the spike
useful for generic trees while the formal native widget set is still small.
This behavior is intentional and covered by the executable widget matrix in
`otoe._native_shared`: `Text` is a text leaf, `Button` and `Input` are controls,
known stack/scope/control-flow wrappers are containers, and unknown widgets are
fallback containers.

## Supported Layout

Layout is deterministic and integer-based. The output is a `NativeLayout`
containing stable `LayoutBox` entries with path, widget name, position, size,
text, events, resolved style, and child boxes.

The layout adapter currently supports:

- Vertical and horizontal stacking.
- Child order.
- `gap`.
- `padding`.
- `width` and `height`.
- `min-width`, `min-height`, `max-width`, and `max-height`.
- Text measurement approximation from string length and `font-size`.
- Reactive prop updates through rerunning `layout_native(...)`.
- `ScrollView` viewport bounds for constrained children.
- `ScrollView(scrollY=...)` vertical child offset.
- Strict class resolution through `StyleSheet.resolve(...)`.

All layout dimensions must be numeric pixels. Percent units, `auto`, flex
distribution, wrapping, alignment, margins, horizontal scroll offsets, and
intrinsic platform text measurement are intentionally not implemented yet.

## Native Style Support Matrix

The native backend has an executable style matrix in `otoe._native_shared`.
Styles parsed by `css(...)` are not automatically native behavior.

Native layout currently uses:

- `gap`
- `padding`
- `scrollY`
- `width` and `height`
- `minWidth`, `minHeight`, `maxWidth`, and `maxHeight`
- `fontSize` for approximate text measurement
- `borderWidth` for leaf sizing

Native paint currently uses:

- `background`
- `borderColor`
- `borderWidth`
- `borderRadius`
- `color`
- `fontSize`

The following parsed properties are accepted and preserved in `LayoutBox.style`,
but intentionally have no native effect yet:

- `alignItems`
- `display`
- `fontWeight`
- `justifyContent`
- `margin`
- `opacity`

Unknown CSS properties still fail in `css(...)`. Unknown style keys injected
through a manually constructed `StyleSheet` fail in the native style matrix with
`NativeLayoutError`. Non-pixel dimensions fail in layout, and unresolved or
invalid colors fail in paint.

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

The text output is a deterministic marker, not font rasterization. It is good
enough for non-empty image tests and state-change detection, but it is not a
real text renderer.

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
- `run_native(...)` as the experimental native app runner, currently backed by
  the optional Tk wrapper.

Caret movement, text selection, uncontrolled input mutation, pointer movement,
IME, drag, inertial scroll physics, gesture, and bubbling/capture semantics are
deferred.

## Rejected For This Spike

These are intentionally outside the current headless boundary:

- GPU rendering.
- Skia-specific public APIs.
- Taffy-specific public APIs.
- CSS layout parity.
- DOM-style event bubbling.
- Native text shaping or font fallback.
- Animation timing.
- Production packaging.
- Production security model for a remotely exposed preview server.

The optional Tk wrapper is deliberately not a production backend. It is a thin
manual-test adapter over the same headless surface contract.

The spike should fail clearly where possible. Unsupported style classes are
strict by default. Non-pixel layout dimensions raise `NativeLayoutError`.
Unresolved or invalid paint colors raise `NativePaintError`.

## Deferred Backend Work

Once the headless contract is stable, the next backend layers can be evaluated
without changing the component API:

- Taffy or another layout solver behind `layout_native(...)`.
- Skia or another raster backend behind the paint command contract.
- Production windowing and OS event loop adapters.
- Accessibility tree generation from `LayoutBox` metadata.
- Backend-level focus synchronization and platform key routing.
- Text shaping, font selection, and DPI scaling.
- Dirty-region or retained-render optimizations.

The success criterion is not "use Skia and Taffy." The success criterion is
that Otoe keeps a small, testable renderer contract that can swap those engines
in without rewriting user components.
