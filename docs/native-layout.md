# Native Layout

Otoe native layout v0 is stack-first. It is designed for deterministic
operational UI tests, native PNG evidence, and offline bundle checks, not full
browser CSS parity.

For the generated widget, input, style, and renderer-boundary support matrix,
see [`native-support-matrix.md`](native-support-matrix.md).

The decision record is
[`ADR-020-native-layout-v0-v1-decision.md`](../ADR-020-native-layout-v0-v1-decision.md).

## Layout v0 Contract

Use these as the portable native geometry tools:

- `VStack` for vertical stacking.
- `HStack` for horizontal stacking.
- `Panel` for framed container layout.
- `ScrollView` for a fixed vertical viewport with `scrollY` clamping.
- `padding`, `gap`, `width`, `height`, `min-width`, `min-height`,
  `max-width`, and `max-height` with non-negative pixel values.
- `align-items` and `justify-content` on `HStack` and `VStack`.
- explicit dimensions when a target surface must have stable framing.

The stack alignment subset is:

- `align-items`: `start`, `flex-start`, `center`, `end`, `flex-end`, `stretch`
- `justify-content`: `start`, `flex-start`, `center`, `end`, `flex-end`,
  `space-between`, `space-around`, `space-evenly`

`stretch` resizes the child's cross-axis layout box. It does not rerun child
layout or implement CSS flexbox auto-size semantics.

## Explicit Limits

These are not native layout v0 features:

- flex grow/shrink
- wrapping
- percentages or `auto` dimensions
- CSS grid
- absolute/fixed positioning
- baseline alignment
- margin geometry
- browser CSS parity

Some Otoe Style properties such as `display`, `font-weight`, `border-style`,
`margin`, and `opacity` may be accepted for HTML or artifact compatibility but
are ignored by the current native layout or paint path. Treat accepted but
ignored properties as documentation pressure, not product layout features.
The native painter supports the narrow text truncation subset used by
`truncate`: `overflow: hidden`, `text-overflow: ellipsis`, and
`white-space: nowrap`. That clips and ellipsizes the text command only; it does
not add general container clipping, wrapping, or flexbox behavior.

## Product Guidance

For Portable Core UI and product demos:

- prefer explicit surface widths for screenshots and offline evidence
- use `HStack`/`VStack` composition before adding new primitives
- keep dense dashboards within stack layouts and fixed viewport regions
- use `ScrollView` when content can exceed a viewport
- use `--native-scale` for denser PNG output instead of changing layout sizes

## Layout v1

Layout v1 is intentionally undecided. It may extend the Python stack engine or
adopt a layout engine behind the renderer/backend boundary. The next decision
must come with acceptance tests that prove v0 compatibility before advertising
new grow, shrink, wrap, grid, absolute positioning, percentage, or `auto`
features.
