# ADR-006: Native Renderer and Layout Boundary

**Status:** Proposed
**Date:** May 6, 2026

## Context

Otoe already has a working component/runtime model, fake-widget mount backend,
HTML rendering, live event dispatch, portable style parsing, and case-study
previews. The next framework question is whether the same mounted tree can
leave the browser preview path and become a native desktop renderer.

The renderer spike must avoid two traps:

- Baking Skia, Taffy, or any other backend's quirks into Otoe's public API.
- Building more HTML/devtool surface before proving layout, pixels, and input
  can exist outside the browser.

## Decision

Define a headless native renderer boundary before adding a real windowing
backend.

The first boundary has these stages:

1. **Mounted tree input**
   - Input is `MountedNode` or `FakeWidget`.
   - Renderer code consumes widget names, resolved props, events, and child
     order.
   - Components and control-flow nodes are already flattened by `mount(...)`.

2. **Resolved style subset**
   - Renderer receives explicit widget props plus optional `StyleSheet`
     resolution from `className`.
   - Supported layout properties are intentionally small: direction, gap,
     padding, width, height, min/max, border width, radius, colors, and text
     size.
   - Unsupported styles must be reported deterministically instead of silently
     ignored.

3. **Layout output**
   - Layout returns deterministic boxes with:
     - stable path
     - widget name
     - x/y position
     - width/height
     - event names
     - child boxes
   - The first implementation can be a pure-Python fallback. Taffy can replace
     the layout solver later if it satisfies the same output contract.

4. **Paint output**
   - Paint consumes layout boxes and resolved styles.
   - The first paint backend may render to a headless image file.
   - Skia can become the primary paint backend once the command contract is
     stable.

5. **Hit-test output**
   - Hit-testing maps coordinates to the deepest box with an event handler.
   - Dispatch remains Otoe's existing event system; the renderer only finds
     the target.

6. **Windowing later**
   - Real windows, OS event loops, accessibility trees, IME, GPU surfaces, and
     platform packaging are deferred until headless layout/paint/input works.

## Consequences

This makes the native renderer spike framework-first. Wraith, SaaS, and other
case studies can keep validating pressure, but the boundary is generic and does
not require any one app.

Taffy and Skia are treated as backend candidates, not public API concepts. If a
backend changes or fails, Otoe's renderer contract can survive.

The first implementation should ship with tests for deterministic layout boxes,
non-empty image output, and simulated click dispatch. Only after that should
Otoe add a windowing adapter.

The current implemented support matrix lives in `NATIVE_RENDERER_SPIKE.md` so
the ADR can stay focused on the architectural decision while the spike evolves.
