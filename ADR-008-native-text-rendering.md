# ADR-008: Native Text Rendering Milestone

**Status:** Proposed
**Date:** May 7, 2026

## Context

The current native renderer is a headless spike. It needs deterministic layout,
paint commands, PNG output, and state-change tests before Otoe chooses a real
layout, paint, or windowing backend.

Text is the highest-risk part of making screenshots look like a real desktop UI:
real text rendering needs font discovery, measurement, shaping, fallback,
hinting, DPI scaling, and platform behavior. Implementing that inside the
stdlib PNG marker renderer would create a second renderer instead of a clean
backend boundary.

## Decision

For the current native milestone, Otoe keeps deterministic marker text.

`measure_native_text(...)` is the private text contract for the headless backend.
Layout and paint both use that shared metric function so text-sized boxes and
text paint commands agree exactly.

The marker renderer is allowed to be visually crude. Its job is to prove:

- state changes affect rendered frames
- text layout is deterministic
- paint commands are non-empty and clipped correctly
- future backends have a stable text measurement boundary to replace

Real font measurement and rasterization are deferred until Otoe evaluates a real
paint/text backend.

## Consequences

Phase 3 should not block on font rendering. The native demo can remain useful
while text is represented by deterministic markers, as long as the limitation is
documented and tests prove the metrics are shared.

Future backend work must replace both measurement and rasterization together.
Text metrics, shaping, font selection, fallback, caret geometry, selection
geometry, and DPI behavior belong in that backend layer, not in component code.
