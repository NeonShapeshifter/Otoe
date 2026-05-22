# ADR-016: Tk Canvas Paint/Text Proof

## Status

Accepted

## Date

May 22, 2026

## Context

The Phase 3 manual window smoke proved that Otoe can launch outside the browser,
but it also made the headless PNG renderer's deterministic marker text visible
to humans. That marker text is still valuable for exact headless tests, but it
is not useful for judging whether a native app surface feels real.

ADR-008 intentionally deferred production text shaping, font fallback, DPI, and
real rasterization to backend work. ADR-015 introduced `NativeBackendAdapter` so
backend experiments have an explicit attachment point.

## Decision

The built-in `"tk"` backend now presents `PaintCommand` objects through a Tk
`Canvas` instead of displaying the stdlib PNG marker output. Rect commands map
to canvas rectangles. Text commands map to `Canvas.create_text(...)` using Tk's
default font and the command's text, color, and font size.

The Canvas presenter scales geometry up to 2x to fit the current window size,
but keeps font sizes in logical native units. Pointer and wheel coordinates are
mapped back into the logical `NativeSurface` coordinate space before dispatch.
This gives larger controls and spacing in fullscreen without making text wrap
inside fixed-height cells.

Text presentation uses the logical text command width when calling
`Canvas.create_text(...)`. Paint commands now carry the available text width from
their layout box, so controls and fixed-width cells can constrain real Tk text
instead of letting labels draw over neighboring boxes.

This is a paint/text proof, not a production renderer. It deliberately keeps the
same `NativeSurface`, `NativeWindowDriver`, layout, paint command, and event
dispatch boundaries.

The headless PNG path remains unchanged and still uses marker text for
deterministic tests and file output.

## Consequences

- Manual `run_native(..., backend="tk")` windows can show readable text while
  preserving the current component and driver contracts.
- Resizing the Tk window scales the current native surface geometry up to 2x; it
  does not perform responsive layout reflow yet, and it does not scale fonts
  until text measurement and reflow are real.
- Demo surfaces must keep fixed columns within their container widths. The task
  board demo now has executable coverage for row content fitting inside its
  `ScrollView`.
- Headless PNG tests remain deterministic and do not depend on system fonts.
- Tk Canvas presentation is allowed to be visually approximate. It does not
  solve shaping, font fallback, partial text clipping, DPI, accessibility, GPU
  acceleration, or production packaging.
- The next real renderer can replace this presenter behind
  `NativeBackendAdapter` without changing user components.
