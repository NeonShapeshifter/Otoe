# API Tiers

Otoe is pre-alpha. There is no stable API tier yet. The documented surface is
described in tiers so app authors do not treat backend evidence internals as
product API.

Top-level aliases exist for compatibility during pre-alpha. New documentation,
examples, and app code should prefer the import path that matches the API tier.
Experimental tiers are intentionally available for tests, examples, and backend
work, but they do not carry a stability promise.

## Stability Summary

| Stability Level | Runtime Tier | Preferred Import | Compatibility Intent |
| --- | --- | --- | --- |
| Stable | none yet | n/a | Otoe has not declared stable APIs while pre-alpha. |
| Core app-author preview | `core-preview` | `otoe` | First app-authoring surface to protect, but still preview. |
| Product preview | `product-preview-ui` | `otoe.ui` | Useful app primitives; top-level aliases stay for compatibility. |
| Preview support | `preview-support` | `otoe` | Helpful support APIs outside the smallest core model. |
| Experimental native | `experimental-native` | `otoe.experimental.native` | Native/window spike and deterministic renderer evidence. |
| Experimental backend | `experimental-backend` | `otoe.experimental.backend` | Backend-candidate, RenderTree, and evidence tooling. |
| Internal accidentally exported | none known | n/a | `tests/test_api_status.py` requires every `otoe.__all__` name to have a tier. |

The tier registry is available at runtime:

```python
from otoe import API_TIERS, api_status

assert "core-preview" in API_TIERS
assert api_status("Card").tier == "product-preview-ui"
assert api_status("Card").preferred_import == "otoe.ui"
```

## Core Preview

This is the core public app-authoring surface. It is the first surface to
document and protect. Its preferred import path is the top-level `otoe`
package.

```python
from otoe import Button, Text, VStack, component, computed, signal
```

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
from otoe.ui import ActionButton, AppFrame, Card, Surface
```

Top-level aliases such as `from otoe import Card` remain for compatibility, but
new docs should steer users to `otoe.ui` for UI-kit primitives.

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
- RenderTree serialization and validation helpers
- resolved style map artifact loading
- top-level aliases that support backend-candidate evidence tests

Related backend coverage, external runner, and package-manifest tooling remains
in implementation modules until it is intentionally promoted into a public
tier.

They are important to Otoe's architecture, but they should be presented as
advanced renderer-authoring tools, not as the primary app-authoring API.

Programmatically, top-level backend-evidence aliases report
`category == "experimental-backend"`, `tier == "experimental-backend"`, and
`preferred_import == "otoe.experimental.backend"`.

## Compatibility Policy For Now

The release-level rules and deprecation window are defined in
[Compatibility And Versioning](compatibility.md).

Do not break existing imports casually. Instead:

- document the tiers clearly
- prefer tiered imports in new docs and examples
- keep compatibility facades while the project remains pre-alpha
- move or deprecate only after a documented API baseline exists
- keep experimental surfaces behind explicit `otoe.experimental.*` guidance
  instead of implying stable production support

## Incremental Import Strategy

- Keep the current top-level `otoe` exports as compatibility aliases during
  pre-alpha. Removing them would be a breaking change and should wait for an
  API baseline.
- Keep core public preview APIs in `otoe`: components, signals, control flow,
  core widgets, mounting, snapshots, HTML render, style primitives, event
  helpers, and developer-facing errors.
- Prefer `otoe.ui` for product-preview UI components and UI data models. New
  docs should import `ActionButton`, `AppFrame`, `Card`, `DataTable`, `Select`,
  and similar symbols from `otoe.ui` unless showing compatibility aliases.
- Keep implementation modules such as `otoe.native`, `otoe.render_ir`, and
  `otoe.window` importable, but steer new public docs to
  `otoe.experimental.native` and `otoe.experimental.backend` until those
  contracts stabilize.
- Add any new renderer/backend candidate APIs under `otoe.experimental.*`
  first. Promote later by changing `api_status.py`, docs, and tests together.
- Treat unknown names from `api_status(name)` as internal unless a document
  explicitly places them in a tier.

## Current Top-Level Export Map

The following map mirrors the declared tier sets in
`src/otoe/api_status.py`. It is intentionally exhaustive for the current
top-level `otoe.__all__` surface.

<!-- api-tiers:top-level-export-map:start -->
| Tier | Top-Level Names |
| --- | --- |
| `api-metadata` | `API_METADATA_APIS`, `API_STATUSES`, `API_TIERS`, `ApiStatus`, `CORE_PREVIEW_APIS`, `EXPERIMENTAL_APIS`, `EXPERIMENTAL_BACKEND_APIS`, `EXPERIMENTAL_NATIVE_APIS`, `PREVIEW_APIS`, `PREVIEW_SUPPORT_APIS`, `PRODUCT_PREVIEW_UI_APIS`, `api_status`, `is_experimental_api` |
| `core-preview` | `Button`, `Computed`, `DuplicatePrimaryPropError`, `Effect`, `EventHandlerArityError`, `EventHandlerError`, `EventSignature`, `For`, `HStack`, `Input`, `Node`, `OtoeError`, `Panel`, `ReactiveDisposedError`, `ReactiveMutationError`, `ReactiveThreadError`, `ScrollView`, `Show`, `Signal`, `Size`, `StyleError`, `StyleRule`, `StyleSheet`, `StyleSyntaxError`, `Text`, `Token`, `UnknownEventError`, `UnknownPropError`, `UnknownStyleClassError`, `VStack`, `Widget`, `batch`, `component`, `computed`, `css`, `effect`, `event_signature_for`, `format_event_signature`, `mount`, `on_cleanup`, `on_mount`, `render_html`, `root_widget`, `signal`, `snapshot`, `snapshot_text`, `unmount` |
| `product-preview-ui` | `ActionButton`, `AppFrame`, `AppShell`, `Badge`, `Card`, `Command`, `CommandPalette`, `CommandRegistry`, `DataTable`, `Dialog`, `EmptyState`, `FeedbackToast`, `FocusScope`, `ListRow`, `Menu`, `MenuItem`, `MetricGrid`, `MetricTile`, `NavItem`, `NavRoute`, `RouteView`, `SectionHeader`, `Select`, `SelectOption`, `ShortcutScope`, `SidebarFrame`, `SidebarItem`, `SidebarNav`, `StatCard`, `StatusPill`, `Surface`, `TabButton`, `TableColumn`, `Tabs`, `Toast`, `Toolbar`, `TopBar`, `UI_EVENT_SIGNATURES`, `class_names` |
| `preview-support` | `DEFAULT_UTILITY_TOKENS`, `FakeWidget`, `Interval`, `LiveEvent`, `LiveHtmlRenderer`, `MountedNode`, `TemplateError`, `interval`, `template`, `utility_css`, `utility_stylesheet` |
| `experimental-native` | `ComposedNativeRendererBackend`, `LayoutBox`, `NativeBackendAdapter`, `NativeLayout`, `NativeLayoutBackend`, `NativeLayoutError`, `NativePaint`, `NativePaintBackend`, `NativePaintError`, `NativeRasterBackend`, `NativeRendererBackend`, `NativeSurface`, `NativeWindowDriver`, `NativeWindowEvent`, `PYTHON_NATIVE_RENDERER_BACKEND`, `PaintCommand`, `PillowNativeRendererBackend`, `PythonNativeRendererBackend`, `TkNativeBackendAdapter`, `TkNativeWindow`, `dispatch_native_click`, `edit_native_input_value`, `hit_test_native`, `layout_native`, `native_backend_adapter`, `native_backend_names`, `paint_native`, `render_native_png`, `run_native`, `write_native_png`, `write_pillow_native_png` |
| `experimental-backend` | `RENDER_TREE_SCHEMA_VERSION`, `RenderIRError`, `RenderNode`, `RenderTree`, `ResolvedStyleMap`, `assert_render_tree_valid`, `load_render_tree_artifact`, `render_node_to_dict`, `render_tree_from_dict`, `render_tree_from_target`, `render_tree_to_dict`, `resolved_style_map_from_style_ops_artifact`, `validate_render_tree`, `walk_render_nodes` |
<!-- api-tiers:top-level-export-map:end -->
