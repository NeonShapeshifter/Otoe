# ADR-020: Native Layout v0 And v1 Decision

**Status:** Accepted
**Date:** June 10, 2026

## Context

Otoe's native renderer is now useful for deterministic layout, paint, PNG,
input, build validation, Portable Core UI smoke tests, and backend-candidate
evidence. The product risk is no longer whether native layout exists; it is
whether users and backend authors can tell what layout promises exist today.

The current native layout path is intentionally stack-first. `VStack`, `HStack`,
`Panel`, `ScrollView`, alignment, clipping, and fixed/min/max pixel dimensions
cover the first operational dashboard and appliance surfaces. They do not make
Otoe a CSS flexbox/grid engine.

Choosing a layout engine too early would mix product scope, dependency policy,
backend ABI design, renderer replacement, and future UI-kit promises before the
Portable Core UI v0 contract is fully closed.

## Decision

Otoe layout v0 remains the existing Python stack layout engine.

Layout v0 is the only product-facing native layout contract for now:

- `VStack` stacks children vertically.
- `HStack` stacks children horizontally.
- `Panel`, `Show`, `For`, `FocusScope`, `ShortcutScope`, and unknown containers
  use deterministic container layout.
- `ScrollView` is a fixed viewport with vertical `scrollY` clamping, clipped
  paint, and clipped hit testing.
- `padding`, `gap`, exact dimensions, min/max dimensions, stack alignment, and
  stack item distribution are the supported geometry tools.
- dimensions are non-negative logical pixels; PNG raster scale is a separate
  output concern.
- native layout diagnostics must stay component-aware where possible.

Layout v0 explicitly does not provide:

- flex grow/shrink
- wrapping
- percentage or `auto` layout dimensions
- CSS grid
- absolute or fixed positioning
- baseline alignment
- margin geometry
- text shaping-driven paragraph layout
- browser CSS parity

Layout v1 is a future decision. It may either extend the Python stack engine or
adopt a layout engine such as Taffy/Yoga through the renderer/backend boundary.
That decision must be made with executable acceptance tests, not by adding a
dependency first.

## Consequences

Positive:

- Otoe can document a small native layout promise users can rely on today.
- Portable Core UI v0 can target a stable stack-first layout surface.
- Backend candidates have a smaller compatibility target before expanding.
- Product work can continue without prematurely coupling Otoe to Taffy, Yoga,
  Skia, Qt, Tk, or another renderer stack.

Negative:

- Native layouts that need full flexbox, grid, wrapping, or absolute
  positioning still need to be expressed with stack primitives and explicit
  dimensions.
- Some HTML preview layouts can look more capable than the native portable
  subset unless docs keep the distinction clear.
- Future layout-engine adoption will need migration and parity work.

## Required Acceptance Bar For Layout v1

Before Otoe adopts or advertises layout v1, the change must include:

- an ADR choosing between extending Python layout and adopting an engine
- a compatibility matrix against layout v0 behavior
- tests for Portable Core UI v0 across HTML, native layout, native paint, and
  generated bundle runners
- tests for any new layout features such as grow, shrink, wrap, grid, absolute
  positioning, percentages, or `auto`
- updated backend-candidate acceptance evidence
- updated docs explaining what remains unsupported

## Non-Goals

- No layout-engine dependency in this decision.
- No new UI primitives just to hide layout limits.
- No claim that native layout matches browser CSS.
- No promise that layout v1 will be Taffy, Yoga, Skia, Qt, Tk, or any specific
  engine.
