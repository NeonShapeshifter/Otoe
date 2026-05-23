# Style Guide

Otoe has a small portable style layer. It is intentionally not a full CSS
engine. `css(...)` parses a constrained class-based subset, stores declarations
in `StyleSheet`, and lets renderers decide which supported properties they can
honor.

## Basic Shape

Only single class selectors are supported:

```python
from otoe import css

styles = css(
    """
    .surface {
      width: 420;
      padding: 16;
      gap: 12;
      background: panel;
      color: ink;
    }
    """,
    tokens={"panel": "#f8fafc", "ink": "#111827"},
)
```

Class names are resolved from the widget `className` prop:

```python
VStack(..., className="surface")
```

Multiple classes are applied left to right; later classes override earlier
declarations for the same property.

## Supported Parsed Properties

`css(...)` accepts only these CSS property names:

| CSS Property | Stored Prop | Value Role |
| --- | --- | --- |
| `align-items` | `alignItems` | native stack alignment |
| `background` | `background` | color/token |
| `border-color` | `borderColor` | color/token |
| `border-radius` | `borderRadius` | dimension |
| `border-width` | `borderWidth` | dimension |
| `color` | `color` | color/token |
| `display` | `display` | accepted, native no-op |
| `font-size` | `fontSize` | dimension |
| `font-weight` | `fontWeight` | accepted, native no-op |
| `gap` | `gap` | dimension |
| `height` | `height` | dimension |
| `justify-content` | `justifyContent` | native stack distribution |
| `margin` | `margin` | accepted, native no-op |
| `max-height` | `maxHeight` | dimension |
| `max-width` | `maxWidth` | dimension |
| `min-height` | `minHeight` | dimension |
| `min-width` | `minWidth` | dimension |
| `opacity` | `opacity` | accepted, native no-op |
| `padding` | `padding` | dimension |
| `width` | `width` | dimension |

Unknown properties fail during `css(...)` parsing. For example,
`line-height` is not accepted today.

## Values

The parser supports:

- numbers, stored as pixel `Size(...)` for dimension properties
- explicit `px` and `%` dimensions
- booleans: `true`, `false`
- quoted strings
- hex colors such as `#2563eb`
- selected raw keywords such as `auto`, `none`, `center`, `row`, `column`,
  `bold`, `transparent`
- token references for `background`, `border-color`, and `color`

Token references are resolved through the `tokens={...}` mapping:

```python
css(
    ".button { background: accent; color: white; }",
    tokens={"accent": "#2563eb", "white": "#ffffff"},
)
```

For HTML output, unresolved color tokens become CSS custom properties such as
`var(--accent)`. Native paint requires resolved colors and raises
`NativePaintError` for unresolved or invalid paint colors.

## HTML Output

The HTML renderer turns resolved class styles into inline CSS. Numeric dimension
values become pixel strings:

```python
styles = css(".card { padding: 16; background: panel; }")
html = render_html(mounted, stylesheet=styles)
```

The resulting inline style uses normal CSS property names, for example
`padding:16px;background:var(--panel)`.

HTML rendering is broader than native rendering. A property being accepted by
`css(...)` does not mean it has native behavior.

## Native Style Matrix

The native renderer has an executable style support matrix in
`otoe._native_shared`.

Native layout-only properties:

- `alignItems`
- `gap`
- `height`
- `justifyContent`
- `maxHeight`
- `maxWidth`
- `minHeight`
- `minWidth`
- `padding`
- `scrollY`
- `width`

Native paint-only properties:

- `background`
- `borderColor`
- `borderRadius`
- `color`

Native layout-and-paint properties:

- `borderWidth`
- `fontSize`

Accepted but intentionally ignored in native rendering:

- `display`
- `fontWeight`
- `margin`
- `opacity`

`scrollY` is not parsed from CSS. It is a native style key produced from the
`ScrollView(scrollY=...)` widget prop.

## Stack Layout Values

Native `alignItems` currently applies only to `HStack` and `VStack`.

Supported values:

- `start`
- `flex-start`
- `center`
- `end`
- `flex-end`
- `stretch`

Native `justifyContent` also applies only to `HStack` and `VStack`.

Supported values:

- `start`
- `flex-start`
- `center`
- `end`
- `flex-end`
- `space-between`
- `space-around`
- `space-evenly`

Unsupported values raise `NativeLayoutError`. Using these properties on
non-stack widgets also raises `NativeLayoutError`.

## Dimension Rules

Native layout accepts non-negative pixel dimensions. It rejects negative
`width`, `height`, `padding`, `gap`, and `fontSize` values.

Percent dimensions can be parsed by `css(...)`, but native layout rejects them
today because it does not implement percentage resolution. HTML output can still
emit percent values.

`ScrollView(scrollY=...)` is special: negative scroll values clamp to zero, and
excessive scroll values clamp to the current content bounds.

## Direct Widget Props

Some widget props also feed native style:

- `VStack(..., gap=..., padding=...)`
- `HStack(..., gap=..., padding=...)`
- `ScrollView(..., scrollY=...)`
- `Text(..., color=...)`

Stylesheet declarations and direct widget props are resolved before native
layout. Prefer stylesheets for repeated visual rules and direct props for small
structural values in examples.

## Strict Class Resolution

`StyleSheet.resolve(className, strict=True)` raises
`UnknownStyleClassError` when a class name has no rule. Native layout wraps that
as a component-aware `NativeLayoutError` when possible.

Use strict mode for renderer tests. It catches misspelled classes early:

```python
styles.resolve("missing-class")  # UnknownStyleClassError
```

## Current Non-Goals

- Full CSS selectors.
- Descendant, attribute, pseudo-class, or media queries.
- CSS cascade parity.
- Tailwind-style utility generation.
- Native percent layout resolution.
- Native margins.
- Native font weight behavior.
- Real text shaping or font fallback.

The style layer should stay small until the renderer boundary is ready for a
real layout and paint backend.
