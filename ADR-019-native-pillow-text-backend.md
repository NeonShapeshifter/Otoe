# ADR-019: First Real Native Text Backend

**Status:** Accepted
**Date:** June 9, 2026

## Context

ADR-008 intentionally kept deterministic marker text for the first native
renderer milestone. That was the right decision while Otoe needed stable
layout, paint, PNG output, hit testing, and backend boundaries before choosing
a real text stack.

The next native product milestone is visual credibility. Otoe needs readable
headless PNG text before it should claim anything stronger about native UI
quality. The first step should improve screenshots and fixture realism without
turning the stdlib marker renderer into a second production renderer or forcing
heavy system dependencies into the default package.

Options considered:

- **Pillow/FreeType.** Good fit for optional Python-first PNG text rendering.
  It can measure and rasterize TrueType text, has broad wheel availability, and
  is already a familiar dependency for Python image output.
- **Cairo toy text through pycairo.** Useful for vector drawing, but pycairo's
  own docs describe the text APIs as Cairo's toy text API. That is not the
  right place to build Otoe's first real text milestone.
- **Pango/PangoCairo.** Correct direction for complex shaping, layout, and
  fallback, but it brings GI/system dependency complexity that is too high for
  the first product-visible PNG milestone.
- **Skia.** Strong long-term candidate for a real renderer backend, but too
  broad for the immediate need. Choosing Skia now would mix text rendering,
  rasterization, future GPU/window decisions, and backend ABI questions into
  one step.

## Decision

Otoe will use **Pillow/FreeType as the first optional real text backend** for
headless native PNG output.

The stdlib marker renderer remains the default deterministic backend and test
baseline. Pillow support is opt-in through the `native-text` extra, the
`--native-text pillow` render flag, and `PillowNativeRendererBackend`. Apps and
components must remain backend-neutral.

The first implementation:

- add an optional Pillow-backed text measurement and PNG drawing path
- keep `measure_native_text(...)` semantics aligned between layout and paint
- support a configured font path for deterministic builds
- support offline bundle profiles through `[native.text]`
- provide a safe fallback or clear error when Pillow or the requested font is
  unavailable
- leave `NativeRendererBackend` as the attachment point
- avoid exposing Pillow types in core component APIs
- add visual smoke tests that prove text is readable without making the whole
  suite depend on Pillow

## Consequences

Positive:

- Otoe gets readable native PNG output sooner.
- The installed-package story can stay Python-first and wheel-friendly.
- The existing marker backend remains useful for deterministic no-dependency
  tests.
- The work is scoped to text/PNG credibility instead of a full renderer rewrite.

Negative:

- Pillow is not full text shaping, platform font fallback, accessibility, or a
  production desktop renderer.
- Complex scripts, IME behavior, caret geometry, selection geometry, and
  platform text parity remain deferred.
- Deterministic visual output now needs an explicit font asset or font policy.

## Deferred

Pango/PangoCairo remains the right future candidate for serious shaping and
font fallback on Linux appliances. Skia remains a candidate for a fuller paint
and raster backend once Otoe is ready to evaluate renderer replacement beyond
text. Layout engine selection remains separate and should not be coupled to the
Pillow text milestone.
