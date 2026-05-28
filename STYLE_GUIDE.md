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

## Utility Layer

Otoe includes a first low-level utility layer for app-shaped HTML previews and
portable renderer tests:

```python
from otoe import HStack, Text, VStack, utility_css, utility_stylesheet

html_css = utility_css()
portable_styles = utility_stylesheet()

view = VStack(
    HStack(Text("Queue", className="text-muted text-sm"), className="gap-2"),
    className="p-4 bg-panel rounded-md border",
)
```

`utility_css()` emits a normal CSS string with design tokens and classes for
spacing, colors, borders, radius, shadows, typography, display, alignment, and
common text helpers. It is the right path for linked HTML/live-preview CSS.

`utility_stylesheet()` returns a `StyleSheet` with the portable subset of those
same class names. HTML-only classes such as `shadow-sm`, `truncate`, `px-4`, and
`flex-col` are still known to strict class resolution, but they intentionally
become no-ops for the native renderer until a real backend can honor them.

Most apps should not assemble every screen from raw classes. `otoe.ui` includes
modern presets built on these utilities:

- `AppFrame`
- `SidebarFrame` and `SidebarItem`
- `TopBar`
- `Surface`
- `MetricGrid` and `MetricTile`
- `StatusPill`
- `ListRow`

Those presets are the default path for polished no-custom-CSS screens. Drop to
raw utilities when the preset shape is close but needs local adjustment, and use
custom CSS when an application needs its own visual identity.

Initial stable utility families:

- spacing: `p-0` through `p-12`, `m-*`, `gap-*`, plus HTML `px-*`/`py-*`
- color tokens: `bg-panel`, `bg-panel-soft`, `text-muted`, `border-line`, etc.
- borders and radius: `border`, `border-0`, `rounded-sm`, `rounded-md`,
  `rounded-lg`, `rounded-full`
- typography: `text-xs`, `text-sm`, `text-base`, `text-lg`, `font-medium`,
  `font-semibold`, `font-bold`
- layout helpers: `flex`, `grid`, `items-center`, `justify-between`,
  `min-w-0`, `min-h-0`
- HTML-only polish: `shadow-sm`, `shadow-md`, `truncate`, `overflow-hidden`

## Offline Profile Direction

For browser previews, CSS can stay as normal linked or inline CSS. For future
hardware, cage, or OS-style profiles, Otoe should treat CSS as an authoring
format that is compiled before deployment.

The intended direction is documented in
`ADR-018-offline-profile-build-planner.md`: `otoe plan` now provides the first
diagnostic slice, and future `otoe build` work should resolve tokens, utility
classes, custom portable CSS, assets, and profile dependencies on the
development/build machine. A device runtime should receive a compact offline
bundle and a compiled style plan, not a full browser CSS engine.

That means Otoe can be CSS-facing without being browser-CSS-powered. The style
planner should classify declarations as portable, html-only, deferred, or
invalid for a selected profile such as `--profile cage`. `utility_css()` and
`utility_stylesheet()` are the first small pieces of that path; they are not a
complete production build system yet.

Current examples:

```bash
otoe plan app:app --profile cage --css styles.css
otoe plan app:app --profile cage --utilities
otoe plan app:app --profile cage --utilities --out dist/otoe-plan.json
otoe plan app:app --profile cage --utilities --json
otoe plan app:app --profile-file otoe.profile.toml --out dist/otoe-plan.json
otoe deps app:app --profile-file otoe.profile.toml --json
otoe build app:app --profile-file otoe.profile.toml --out dist/cage
otoe build app:app --profile-file otoe.profile.toml --out dist/cage --validate
otoe plan app:app --profile cage --no-strict-styles
```

By default, missing class rules are invalid because a constrained runtime cannot
rely on external browser CSS. `--no-strict-styles` downgrades missing classes to
html-only warnings for auditing existing preview surfaces.

`--json` prints a stable plan report with `schemaVersion`, target, profile,
status, class groups, style counts, direct style counts, and diagnostics.
`--out` writes the same JSON report as an artifact so future build steps can
consume it without scraping terminal text.

`otoe.profile.toml` is the first profile manifest shape:

```toml
profile = "cage"
utilities = true
css = ["styles.css"]
assets = ["static/logo.png"]

[runtime]
allow_runtime_installs = false
files = ["app.py"]

[backend]
name = "native"

[deps]
packages = ["pytest"]
extras = ["dev"]
```

Profile CSS, asset, and runtime file paths are relative to the TOML file. Asset
and runtime file paths must be relative files and must not contain `.` or `..`.
Explicit CLI flags override the profile file. `allow_runtime_installs = true`
is invalid for `cage`.

`otoe deps` audits `[deps]` against the current build environment without
installing packages, touching the network, importing the app, or writing
artifacts. Missing packages are user-managed setup work, not runtime work for a
hardware/cage target. During `otoe build`, the same audit is written as
`otoe-deps.json` and invalid dependency audits stop the build before
`manifest.json` is written.

`otoe build` is the first bundle contract. It writes `otoe-plan.json`,
`otoe-deps.json`, and `manifest.json` into the output directory, copies selected
Otoe framework/runtime files under `framework/`, copies declared assets under
`assets/`, and copies declared app runtime files under `app/`. Invalid plans,
dependency audits, or backend selections stop the build before a manifest is
written; warning plans are allowed and recorded in the manifest. It does not
auto-discover imports yet. Copied framework files are recorded in
`frameworkFiles`.

The build also writes `otoe-run.py` as the first executable bundle entry. It
loads the manifest target from the copied app/framework paths, supports `--check`
for validation, and supports `--png` for a single headless native frame.
`otoe build --validate` runs that copied runner in `--check` mode after writing
the bundle, so missing app runtime files are caught before deployment.

## Supported Parsed Properties

`css(...)` accepts only these CSS property names:

| CSS Property | Stored Prop | Value Role |
| --- | --- | --- |
| `align-items` | `alignItems` | native stack alignment |
| `background` | `background` | color/token |
| `border-color` | `borderColor` | color/token |
| `border-radius` | `borderRadius` | dimension |
| `border-style` | `borderStyle` | accepted, native no-op |
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

- `borderStyle`
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
- Tailwind compatibility or arbitrary-value utility parsing.
- Native percent layout resolution.
- Native margins.
- Native font weight behavior.
- Real text shaping or font fallback.

The style layer should stay small until the renderer boundary is ready for a
real layout and paint backend.
