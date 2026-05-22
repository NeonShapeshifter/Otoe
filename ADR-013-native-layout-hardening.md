# ADR-013: Native Layout Hardening

## Status

Accepted

## Context

Otoe's headless native layout adapter is now good enough to drive the native
task board demo through `NativeSurface`, `NativeWindowDriver`, and
`run_native(...)`. The next risk is not whether layout can produce boxes; it is
whether the small Python layout contract is precise enough to harden before a
future Taffy or other layout backend spike.

The current adapter intentionally supports stack layout, pixel dimensions,
padding, gap, min/max constraints, center alignment for stacks, text measurement
approximation, and `ScrollView` vertical offset/clamping. It does not implement
flex distribution, wrapping, percentage sizing, `auto`, real text measurement,
or broader alignment values.

## Decision

The next layout spike stays in Python. Otoe will harden the existing contract
before introducing a layout engine adapter.

The hardened minimum native layout contract is:

- `VStack` lays out children vertically.
- `HStack` lays out children horizontally.
- Unknown widgets use the documented column-container fallback.
- Empty containers still produce deterministic boxes.
- `padding`, `gap`, `width`, `height`, `minWidth`, `minHeight`, `maxWidth`, and
  `maxHeight` use numeric pixel values only.
- Exact dimensions override intrinsic content size, then max constraints cap the
  result, then min constraints floor the result. If min and max conflict, min
  wins.
- `ScrollView` keeps viewport bounds fixed, vertically offsets children by
  `scrollY`, clamps excessive scroll values to content bounds, and clips paint
  and hit testing elsewhere in the native pipeline.
- `alignItems` and `justifyContent` support only `center`, only on `HStack` and
  `VStack`. Other values or non-stack widgets fail with `NativeLayoutError`.

## Non-Goals

- No Taffy adapter in this hardening pass.
- No Skia or GPU renderer dependency.
- No CSS parity promise.
- No flex distribution, wrapping, percentage dimensions, `auto` sizing,
  baseline alignment, non-center alignment values, margins, absolute
  positioning, or intrinsic platform text measurement.
- No public stability promise for the native renderer beyond the documented
  experimental API status.

## Consequences

- Layout edge cases become executable tests instead of implicit behavior.
- A future Taffy-backed adapter has a smaller target: it must first match the
  hardened Python contract before expanding layout features.
- Alignment remains intentionally narrow. If a future change adds values beyond
  `center` or supports non-stack widgets, it must update the support matrix,
  this ADR, `NATIVE_RENDERER_SPIKE.md`, and layout tests in the same change.
