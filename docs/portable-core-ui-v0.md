# Portable Core UI v0

Portable Core UI v0 is the subset that should be treated as the first
product-facing target for parity across HTML render, live HTML where relevant,
headless native rendering, and native-window driver input.

This matrix is intentionally conservative. It should shrink ambiguity before
more primitives are added.

The machine-readable source for this table is
[`docs/portable-core-ui-v0.json`](portable-core-ui-v0.json). Tests validate that
the packaged matrix, JSON, Markdown table, example targets, exported symbols,
outside-v0 classifications, native capability profile, and sample render paths
stay aligned.

Inspect the packaged support matrix from any installed or editable checkout:

```bash
otoe portable-core
otoe portable-core --examples --outside
otoe portable-core --json
```

| Primitive | HTML | Live HTML | Native Headless | Native Window Driver | Status |
| --- | --- | --- | --- | --- | --- |
| `Text` | yes | n/a | yes | n/a | core preview |
| `Button` | yes | click/key events | click/focus/key | click/focus/key | core preview |
| `Input` | yes | change/key/focus | focus/key/text | focus/key/text | core preview |
| `VStack` | yes | n/a | stack layout | n/a | core preview |
| `HStack` | yes | n/a | stack layout | n/a | core preview |
| `Panel` | yes | n/a | basic layout/paint | n/a | core preview |
| `ScrollView` | yes | scroll event shape | clipped paint/hit test/scroll | wheel dispatch | core preview |
| `Card` | yes | n/a | through composed widgets/styles | n/a | product preview |
| `Badge` | yes | n/a | through composed widgets/styles | n/a | product preview |
| `ActionButton` | yes | click | through `Button` behavior | through `Button` behavior | product preview |
| `Tabs`/`TabButton` | yes | click | partial through buttons/layout | partial through buttons/layout | product preview |
| `Dialog` | yes | focus overlay behavior in live path | partial layout/paint | partial focus behavior | experimental UI |
| `ListRow` | yes | n/a | through composed widgets/styles | n/a | product preview |
| `MetricTile` | yes | n/a | through composed widgets/styles | n/a | product preview |
| `AppFrame` | yes | n/a | app-shaped layout smoke | n/a | product preview |

`Dialog` is listed because it is already a common UI primitive and has partial
HTML/live/native coverage, but it is not counted as Portable Core UI v0 until
focus behavior and native parity are tightened.

## Runnable Examples

The examples for this matrix live in `examples/portable_core_ui.py`. Render the
whole portable gallery from a source checkout:

```bash
PYTHONPATH=src:. python -m otoe render examples.portable_core_ui:app --out preview/portable_core_ui.html --css preview/portable_core_ui.css --pretty
PYTHONPATH=src:. python -m otoe render examples.portable_core_ui:app --out preview/portable_core_ui.png --native --css preview/portable_core_ui.css
PYTHONPATH=src:. python -m otoe build examples.portable_core_ui:app --out dist/portable_core_ui_cage --css preview/portable_core_ui.css --validate
```

`preview/portable_core_ui.css` is the strict Otoe Style subset used by CLI
render, native PNG, plan, and build smoke tests for the gallery.

For native visual evidence over the same product-facing subset:

```bash
PYTHONPATH=src:. python -m examples.native.portable_core_ui_demo --marker-only
PYTHONPATH=src:. python -m examples.native.portable_core_ui_demo --pillow --scale 2
```

Each matrix row has a single import target:

| Primitive | Example Target |
| --- | --- |
| `Text` | `examples.portable_core_ui:text_example` |
| `Button` | `examples.portable_core_ui:button_example` |
| `Input` | `examples.portable_core_ui:input_example` |
| `VStack` | `examples.portable_core_ui:vstack_example` |
| `HStack` | `examples.portable_core_ui:hstack_example` |
| `Panel` | `examples.portable_core_ui:panel_example` |
| `ScrollView` | `examples.portable_core_ui:scrollview_example` |
| `Card` | `examples.portable_core_ui:card_example` |
| `Badge` | `examples.portable_core_ui:badge_example` |
| `ActionButton` | `examples.portable_core_ui:action_button_example` |
| `Tabs`/`TabButton` | `examples.portable_core_ui:tabs_example` |
| `Dialog` | `examples.portable_core_ui:dialog_example` |
| `ListRow` | `examples.portable_core_ui:list_row_example` |
| `MetricTile` | `examples.portable_core_ui:metric_tile_example` |
| `AppFrame` | `examples.portable_core_ui:app_frame_example` |

Use top-level imports for core widgets:

```python
from otoe import Button, HStack, Input, Panel, ScrollView, Text, VStack
```

Use `otoe.ui` for product-preview UI:

```python
from otoe.ui import ActionButton, AppFrame, Badge, Card, ListRow, MetricTile
```

## Outside Portable Core v0

The JSON source also classifies every product-preview `otoe.ui` symbol that is
not counted as a v0 primitive.

| Group | Classification | Symbols |
| --- | --- | --- |
| `app-shell-navigation` | product-preview-app-shell | `AppShell`, `NavItem`, `NavRoute`, `RouteView`, `SidebarNav` |
| `app-shell-presets` | product-preview-app-shell | `SidebarFrame`, `SidebarItem`, `TopBar` |
| `surface-composites` | product-preview-composite | `EmptyState`, `MetricGrid`, `SectionHeader`, `StatCard`, `StatusPill`, `Surface`, `Toolbar` |
| `data-table` | product-preview-composite | `DataTable` |
| `transient-feedback` | product-preview-composite | `FeedbackToast`, `Toast` |
| `interactive-overlays` | interactive-preview | `CommandPalette`, `FocusScope`, `Menu`, `Select`, `ShortcutScope` |
| `ui-models-and-helpers` | support-model | `Command`, `CommandRegistry`, `MenuItem`, `SelectOption`, `TableColumn`, `UI_EVENT_SIGNATURES`, `class_names` |

Those symbols remain public product-preview APIs. They are outside v0 because
their native, focus, overlay, keyboard, table, timing, or app-shell contracts
need narrower acceptance tests before they can be treated as portable core.

## Acceptance Bar

For a primitive to be considered part of Portable Core UI v0, it should have:

- an HTML render test or preview fixture
- a native layout test when it affects geometry
- a native paint test when it affects visible output
- a native click/key/text/scroll test when it exposes input
- a doc example showing the intended app-authoring shape

## Explicit Non-Goals For v0

- Full browser CSS parity.
- Production desktop windowing.
- Accessibility tree output.
- Complex native text shaping.
- A large component catalog.

Primitives outside the matrix can still exist, but docs should label them as
HTML preview or experimental until the parity bar is met.
