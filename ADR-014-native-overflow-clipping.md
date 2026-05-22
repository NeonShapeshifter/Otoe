# ADR-014: Native Overflow And Clipping Policy

## Status

Accepted

## Context

The headless native renderer now supports fixed stack dimensions, nested stack
layout, centered stack alignment, scroll views, paint command clips, PNG clipping,
and hit-tested input. That makes overflow behavior part of the renderer
contract: when content exceeds a box, the backend must know whether descendants
remain visible and interactive or are clipped by the parent bounds.

Without an explicit policy, normal containers and `ScrollView` can drift into
different implicit behavior across layout, paint, PNG output, and hit testing.

## Decision

Only `ScrollView` clips descendants in the current native renderer contract.

- `VStack`, `HStack`, `Panel`, `FocusScope`, `ShortcutScope`, `Show`, `For`, and
  unknown fallback containers do not clip descendants, even when they have fixed
  `width` or `height` smaller than their content.
- Overflow from normal containers remains visible in paint commands.
- Overflow from normal containers remains hit-testable if a descendant box
  contains the coordinate.
- If multiple boxes contain the same coordinate, hit testing chooses the deepest
  eligible box; ties at the same depth choose the later box in paint/tree order.
- `ScrollView` clips descendant paint through paint command clip rects.
- `ScrollView` clips hit testing: descendants outside the scroll viewport do not
  receive focus or click dispatch.
- Nested normal containers inside a `ScrollView` inherit the nearest scroll
  viewport clip for paint and hit testing.

## Non-Goals

- No general `overflow` style property yet.
- No `overflow: hidden`, `overflow: auto`, horizontal scroll, scrollbars, or
  inertial scroll physics.
- No clipping for normal stack or panel containers.
- No CSS overflow parity promise.

## Consequences

- Apps that need clipping must use `ScrollView` for now.
- Fixed `width` and `height` on normal containers constrain the container box,
  but they do not create a clipping boundary.
- A future overflow style must update this ADR, the native support matrix,
  `NATIVE_RENDERER_SPIKE.md`, paint tests, and hit-test tests in the same change.
