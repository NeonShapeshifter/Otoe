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
otoe plan app:app --profile cage --backend native-python --css styles.css
otoe plan app:app --profile cage --utilities
otoe plan app:app --profile cage --utilities --out dist/otoe-plan.json
otoe plan app:app --profile cage --utilities --json
otoe plan app:app --profile-file otoe.profile.toml --out dist/otoe-plan.json
otoe deps app:app --profile-file otoe.profile.toml --json
otoe build app:app --profile-file otoe.profile.toml --out dist/cage
otoe build app:app --profile-file otoe.profile.toml --out dist/cage --validate
otoe pack dist/cage --out dist/cage.tar.gz
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

[styles]
safelist = ["is-danger", "bg-alert"]

[runtime]
allow_runtime_installs = false
files = ["app.py"]

[runtime.policy]
network = "warn"
subprocess = "warn"

[backend]
name = "native"
capability = "native-python"
# Optional backend coverage gate:
# coverage_requirements = "backend-readiness.json"

[deps]
packages = ["pytest"]
extras = ["dev"]
```

Profile CSS, asset, and runtime file paths are relative to the TOML file.
Backend capability profile and backend coverage requirement paths are relative
to the same TOML file. Asset, runtime file, backend capability profile, and
backend coverage requirement paths must be relative files and must not contain
`.` or `..`.
For local targets such as `app:app` or `workspace_pkg.app:app`, `otoe plan` and
`otoe build` statically extract literal class tokens from `className`
expressions in the target file and static local imports, including
package-relative imports such as `from .views import card`. This covers static
literals and conditional literal branches, including common `class_names(...)` state classes
inside `computed(...)`. `[styles].safelist` declares extra class names that
should be compiled when they cannot be extracted or do not appear in the first
mounted render. Each safelist entry must be one class name, not a
space-separated class list. Explicit CLI flags override the profile file.
`allow_runtime_installs = true` is invalid for `cage`. `[runtime.policy]`
uses `allow`, `warn`, or `error` for visible stdlib `network` and
`subprocess`/process-spawning usage. This is static audit, not a runtime
sandbox.

### Dynamic Class Extraction Examples

This form is build-time enumerable because every possible class is a literal
token in the local `className` expression:

```python
from otoe import Text, class_names, computed, signal

ready = signal(False)

state_class = computed(
    lambda: class_names(
        "status",
        "is-ready" if ready.value else "is-idle",
    )
)

app = Text("State", className=state_class)
```

`otoe plan` sees `status`, `is-ready`, and `is-idle`, then records the class
that did not appear in the first render under `classes.static` so `otoe build`
can compile it into `otoe-styles.json` and `styleOps`.

This form is not build-time enumerable because one class is assembled from a
runtime value:

```python
from otoe import Text, computed, signal

tone = signal("idle")

app = Text(
    "State",
    className=computed(lambda: f"status is-{tone.value}"),
)
```

For hardware/cage builds, list the possible outputs explicitly:

```toml
[styles]
safelist = ["is-idle", "is-ready", "is-danger"]
```

The mounted first render may still include `status` and `is-idle`, but the
build cannot infer future values such as `is-ready` or `is-danger` from the
f-string. `otoe plan` warns on that expression with the source file and line.

`otoe deps` audits `[deps]` and static external imports found in discovered
local runtime files against the current build environment without installing
packages, touching the network, importing the app target, or writing artifacts.
Missing packages and undeclared external imports are user-managed setup work,
not runtime work for a hardware/cage target. Declare the installable
distribution package when package metadata maps an import to a different name,
such as `Pillow` for `import PIL`; imports with no package metadata are reported
as unknown candidates. The same audit records `runtimePolicy` findings for
visible stdlib network/process usage and can raise them to errors through
`[runtime.policy]`. During `otoe build`, the same audit is written as
`otoe-deps.json` and invalid dependency audits stop the build before
`manifest.json` is written.

`otoe build` is the first bundle contract. It writes `otoe-plan.json`,
`otoe-deps.json`, `otoe-styles.json`, and `manifest.json` into the output
directory, copies selected Otoe framework/runtime files under `framework/`,
copies declared assets under `assets/`, auto-copies local target modules or
packages while preserving package paths, follows static local imports such as
`import helpers`, `from helpers import view`, and `from .views import card`, and
copies declared extra runtime files under `app/`. Invalid plans, dependency
audits, or backend
selections stop the build before a manifest is written; warning plans are
allowed and recorded in the manifest. It reports visible
`importlib.import_module(...)` and `__import__(...)` dynamic import calls as
dependency warnings, but does not auto-copy arbitrary dynamic imports, so
`[runtime] files` remains the explicit place for dynamic import edges, external
app files, and anything the static scanner cannot see. It also reports visible
stdlib network imports and process-spawning APIs such as `socket`, `urllib`,
`subprocess`, and `os.system(...)` through audit-only runtime policy findings.
Copied framework files are
recorded in `frameworkFiles`.

The build also writes `otoe-run.py` as the first executable bundle entry. It
loads the manifest target from the copied app/framework paths, supports `--check`
for import validation, supports `--verify` for file size/hash checks, supports
`--backend-package-check` for the bundled Path0 backend package smoke, supports
`--layout-check` for layout/paint validation without writing a PNG, and supports
`--png` for a single headless native frame using the bundled compiled styles.
Every runner mode validates `schemaVersion = 1` for `manifest.json`,
`otoe-plan.json`, `otoe-deps.json`, and `otoe-styles.json` before loading the
target or rendering a frame, so old bundle formats fail cleanly instead of
running with ambiguous artifacts.
Runner verification also requires the core `plan`, `deps`, `styles`, and
`backendCoverage` artifacts to be listed in `manifest.json` `artifacts` with
size/hash metadata. It rejects invalid plan, dependency, or style artifact
status even if those hashes were updated after tampering, and keeps
`runtimeInstallsAllowed = false` as a runner/pack invariant for hardware
bundles. When `backendPackage` is declared, it verifies the package descriptor's
own file hashes against the copied backend files and runs a JSON-in/JSON-out
Path0 smoke from inside the bundle.
The runner also enforces the backend framework policy: a `native` bundle must
declare and include the expected `frameworkFiles` set before `--check`,
`--layout-check`, `--png`, `--verify`, or `otoe pack` can succeed.
`otoe plan --backend native-python` and `[backend].capability =
"native-python"` select the backend capability profile used for diagnostics.
The current `native` profile file value remains an alias for `native-python`.
Plan and style artifacts record that capability map so future hardware/backend
candidates can define their own style, widget, and input support without
changing app code.
`[backend].coverage_requirements` and `--backend-coverage-requirements` attach
a readiness/requirements JSON artifact to that same capability profile.
`otoe plan` records the comparison as `backendCoverage` and exits nonzero when
coverage is incomplete; `otoe build` writes `otoe-backend-coverage.json` and
refuses to write `manifest.json` if required widget, input, style, or declared
omission coverage is missing. Strict backend-readiness artifacts must include
source/gate evidence for exercised groups, and style evidence must include
runtime Path 0 proof from `styleOps` plus layout/paint observations for each
property's declared support phase; declared style omissions must not appear as
runtime-applied layout/paint evidence. Malformed evidence is reported as an
`*Evidence` blocker.

`otoe-styles.json` records used classes, statically extracted classes,
safelisted classes, resolved portable declarations, direct widget style props,
omitted html-only/deferred declarations, diagnostics, tokens, backend capability
metadata, and low-level `styleOps`.
The `styleOps` section is the hardware-facing view: each planned
class and each direct widget style entry becomes deterministic `setStyle`
operations for portable declarations plus `omitStyle` records for html-only,
deferred, or invalid declarations, with support categories taken from the
selected backend capability profile, so backend candidates can consume a
resolved artifact instead of parsing CSS on device.

### Style IR v1 Contract

`otoe-styles.json` is the current Style IR artifact. It is generated by
`otoe.style_ir` during `otoe build`; device/runtime code should consume the
artifact, not parse source CSS.

The top-level Style IR uses `schemaVersion = 1` and keeps:

- `tokens`: serialized build-time tokens for traceability and HTML/native
  rehydration.
- `classes`: `used`, `static`, `safelisted`, `planned`, `htmlOnly`, and
  `invalid` class groups.
- `rules`: one entry per planned class. `declarations` contains only portable,
  token-resolved values. `omittedDeclarations` contains html-only, deferred, or
  invalid declarations with original serialized values and diagnostic messages.
- `directStyles`: one entry per widget path that carries direct style props such
  as `gap`, `padding`, `scrollY`, or `color`. The style artifact stores portable
  direct dimensions as resolved px `size` values.
- `backendCapabilities`: the selected backend style/widget/input capability
  profile used to classify the artifact.
- `styleOps`: the low-level backend contract. It uses `schemaVersion = 1` and
  `format = "otoe-style-ops"`, and contains deterministic `setStyle` and
  `omitStyle` records for each planned class and direct style entry.

Build-time owns parsing CSS, resolving tokens, class extraction, safelists, and
backend capability classification. Runtime owns loading the copied app,
verifying hashes/schema versions, checking declared backend coverage reports,
checking Style IR drift through `otoe.style_ops`, rehydrating resolved rules for
the Python native renderer, and applying `styleOps` in backend candidate checks.
A backend candidate should treat `styleOps` as the primitive style stream; it
should not depend on raw CSS being present on the target device.
`stylesheet_from_artifact(..., strict=True)` is the default runtime
rehydration path and rejects artifacts whose `styleOps` no longer match
compiled `rules` or `directStyles`. Strict validation also checks serialized
value payloads (`literal`, `size`, `token`, and `runtime`) so malformed
primitive values fail before backend replay.

`otoe.style_ops` exposes the runtime replay helpers for backend candidates:
they apply `setStyle` ops into resolved declarations and normalize `omitStyle`
records against the artifact's capability map for both class rules and direct
widget style entries. `otoe.style_ir` owns build-time compilation and reexports
those helpers for compatibility; hardware bundles consume the JSON artifact and
the small copied `style_ops.py` verifier, not the compiler module.

Backend tooling can use the public artifact API instead of indexing the JSON by
hand:

```python
import json
from pathlib import Path

from otoe.style_ops import apply_style_ops, load_style_ir

artifact = load_style_ir(
    json.loads(Path("dist/cage/otoe-styles.json").read_text())
)
applied = apply_style_ops(artifact)

class_styles = applied.classes_by_name["shell"].applied_declarations
root_direct_styles = applied.direct_styles_by_path[()].applied_declarations
```

For quick inspection, use the CLI:

```bash
otoe style-ir dist/cage/otoe-styles.json --summary
otoe style-ir dist/cage/otoe-styles.json --json
otoe style-ir dist/cage/otoe-styles.json --strict
```

For hardware/cage profiles, arbitrary runtime class construction is not a
portable contract: a dynamic class must appear in the initial mounted tree, be
statically extracted from local `className` expressions, or be listed in
`[styles].safelist` so the build can resolve it before deployment. F-strings or
string interpolation with unknown runtime fragments still require safelisting
the possible output classes. `otoe plan` emits a warning with the source file
and line when it sees a dynamic `className` f-string or string interpolation,
so the missing safelist edge is visible before `otoe build`. `otoe build
--validate` runs that copied runner in `--verify`, `--check`, and
`--layout-check` modes after writing the bundle, so missing, modified,
unbundled, or renderer-invalid files are caught before deployment.

`otoe pack` is the first deployment archive step. It runs the copied runner in
`--verify` mode, runs strict Style IR drift detection against `otoe-styles.json`,
preserves `otoe-backend-coverage.json` when the manifest declares
`backendCoverage`, writes a `.tar.gz` with the bundle contents at archive root,
rejects invalid core artifacts or runtime-install drift, and excludes local
cache directories such as `__pycache__/` and `.pytest_cache/`. Generated runner
verification also rejects malformed `runtimePolicy` metadata after hash updates.

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
