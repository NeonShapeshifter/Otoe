# ADR-009: Native Accessibility Metadata

## Status

Accepted

## Context

The native renderer spike currently produces deterministic layout boxes and
paint commands, not a platform accessibility tree. A future backend will need
enough metadata to derive roles, labels, state, focus, bounds, and hierarchy
without reaching back into component internals.

## Decision

`LayoutBox` is the accessibility seed contract for the native backend.

Every native layout box should preserve:

- `path` for stable tree lookup within one render.
- `name` for widget-kind based role mapping.
- `id` when the widget provides one.
- `text` for visible labels and text alternatives where applicable.
- `events` for interactive affordance detection.
- `state` for widget state such as `disabled`.
- `context` for component/widget diagnostic ownership.
- bounds (`x`, `y`, `width`, `height`) for hit targets and platform geometry.
- `children` for hierarchy.

This is not a full accessibility API. It is the minimum metadata the renderer
contract must not lose while layout, paint, and windowing backends are still
experimental.

## Consequences

- Backends can derive initial roles from widget names without exposing
  backend-specific role APIs in Otoe yet.
- Diagnostics can continue to include component context without a separate
  debug tree.
- Future work still needs explicit labels, descriptions, focus reporting,
  platform roles, keyboard navigation policy, and OS accessibility adapters.
