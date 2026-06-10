# API Tiers

Otoe is pre-alpha, but the public surface is described in tiers so app authors
do not treat backend evidence internals as product API.

The tier registry is available at runtime:

```python
from otoe import API_TIERS, api_status

assert "core-preview" in API_TIERS
assert api_status("Card").tier == "product-preview-ui"
assert api_status("Card").preferred_import == "otoe.ui"
```

## Core Preview

This is the first app-authoring surface to document and protect. Its preferred
import path is the top-level `otoe` package.

- `component`, `on_mount`, `on_cleanup`
- `signal`, `computed`, `effect`, `batch`
- `Show`, `For`
- `Node`, `Widget`
- `Text`, `Button`, `Input`, `VStack`, `HStack`, `Panel`, `ScrollView`
- `mount`, `unmount`, `root_widget`
- `snapshot`, `snapshot_text`
- `render_html`
- event signature helpers and developer-facing errors

These APIs are still preview APIs, but they are the core programming model.
Programmatically, they report `category == "preview"` and
`tier == "core-preview"`.

## Product Preview UI

`otoe.ui` is the app-primitives layer. It is useful today, but should be
documented by support matrix rather than implied as fully native portable.

Examples:

- `Card`, `Badge`, `ActionButton`
- `AppFrame`, `SidebarFrame`, `TopBar`, `Surface`
- `Tabs`, `Toolbar`, `DataTable`
- `Dialog`, `Toast`, `FeedbackToast`
- `CommandPalette`, `Menu`, `Select`
- `ListRow`, `MetricGrid`, `MetricTile`, `StatusPill`

The preferred import style for product UI is:

```python
from otoe.ui import Card, MetricTile, Surface
```

Top-level aliases may remain for compatibility, but docs should steer users to
`otoe.ui` for UI-kit primitives.

Programmatically, these APIs report `category == "preview"`,
`tier == "product-preview-ui"`, and `preferred_import == "otoe.ui"`.

## Preview Support

These APIs are useful for app authors and examples, but they sit outside the
smallest core model:

- `LiveHtmlRenderer`, `LiveEvent`
- `MountedNode`, `FakeWidget`
- `Interval`, `interval`
- `TemplateError`, `template`
- `DEFAULT_UTILITY_TOKENS`, `utility_css`, `utility_stylesheet`

Programmatically, they report `category == "preview"` and
`tier == "preview-support"`.

## Experimental Native

Native-facing APIs are available for tests, examples, and backend experiments,
not as production desktop promises. Prefer the explicit experimental import
path for new code:

```python
from otoe.experimental.native import NativeSurface, render_native_png
```

- `NativeSurface`
- `NativeWindowDriver`
- `PillowNativeRendererBackend`
- `run_native`
- native layout, paint, raster, and backend adapter types
- Tk adapter types

The current status is exposed programmatically:

```python
from otoe import api_status

assert api_status("NativeSurface").category == "experimental-native"
assert api_status("NativeSurface").tier == "experimental-native"
assert api_status("NativeSurface").preferred_import == "otoe.experimental.native"
```

## Experimental Backend Evidence

These are advanced backend-candidate and bundle-verification surfaces. Prefer
the explicit experimental import path for new code:

```python
from otoe.experimental.backend import RenderTree, render_tree_from_target
```

Examples:

- `RenderTree` IR helpers
- `styleOps` helpers and artifacts
- backend capability profiles
- backend coverage and readiness evidence
- external Path0 JSON runner artifacts
- backend package manifests
- contract comparison tooling

They are important to Otoe's architecture, but they should be presented as
advanced renderer-authoring tools, not as the primary app-authoring API.

Programmatically, top-level backend-evidence aliases report
`category == "experimental-backend"`, `tier == "experimental-backend"`, and
`preferred_import == "otoe.experimental.backend"`.

## Compatibility Policy For Now

Do not break existing imports casually. Instead:

- document the tiers clearly
- prefer tiered imports in new docs and examples
- keep compatibility facades while the project remains pre-alpha
- move or deprecate only after a documented API baseline exists
