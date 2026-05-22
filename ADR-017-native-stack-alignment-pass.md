# ADR-017: Native Stack Alignment Pass

## Status

Accepted

## Context

After the Tk Canvas proof, the next backend decision should reduce risk before
introducing a real layout engine. The most useful small target is another
Python layout pass: it keeps the adapter dependency-free while making the stack
contract precise enough for a future Taffy or other layout backend to match.

ADR-013 intentionally limited stack alignment to `center`. That was enough for
the first hardening pass, but it left common app-shaped layouts unable to express
end alignment, cross-axis stretching, or simple item distribution without custom
dimensions.

## Decision

The first post-release backend spike target is a Python stack-alignment pass.
Otoe still does not adopt Taffy or Skia here.

Native layout now supports these stack-only values:

- `alignItems`: `start`, `flex-start`, `center`, `end`, `flex-end`, `stretch`
- `justifyContent`: `start`, `flex-start`, `center`, `end`, `flex-end`,
  `space-between`, `space-around`, `space-evenly`

The behavior remains deterministic and integer-based. `stretch` resizes a
child's cross-axis layout box to the stack's inner cross-axis size. It does not
rerun child layout or implement CSS flexbox auto-size semantics. `space-between`
distributes remaining main-axis space between existing children and falls back
to start alignment for zero or one child. `space-around` and `space-evenly`
distribute remaining main-axis space with deterministic integer rounding.

Alignment remains limited to `HStack` and `VStack`. Unsupported values or
alignment styles on other widgets still fail with `NativeLayoutError`.
All layout dimensions used by this pass remain non-negative integer pixel
values; invalid negative sizes fail before alignment is applied.

## Non-Goals

- No Taffy adapter in this pass.
- No flex grow/shrink, wrapping, baseline alignment, percentages, or `auto`.
- No change to paint, hit testing, event dispatch, or Tk window ownership.
- No CSS parity promise.

## Consequences

- The native stack contract is closer to common app layouts while staying small
  enough for a future backend to reproduce exactly.
- Backends can treat this as the first concrete layout-acceptance target beyond
  center alignment.
- Any future expansion must add executable tests and update
  `NATIVE_RENDERER_SPIKE.md` in the same change.
