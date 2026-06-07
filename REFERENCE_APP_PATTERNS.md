# Reference App Patterns

Phase 5 reference apps are professional validation surfaces. They are not
runtime features, and they are not product forks. They show whether Otoe can
support polished Python applications with explicit state boundaries.

Current reference apps:

- `examples.hardware.control_panel` - hardware/control panel
- `examples.admin.settings_console` - local admin/settings
- `examples.data_workflow.workbench` - data/table workflow
- `examples.utility.ops_console` - utility-first app styling pressure test

## Purpose

Use reference apps to answer framework questions that tiny examples cannot:

- Can an app shell hold dense, repeated operational controls?
- Can local provider state drive editable rows, validation, guarded commands,
  and visible feedback?
- Can `otoe.ui` primitives produce professional surfaces without one-off
  runtime features?
- Can alternate data states be tested without a browser, window, device, or
  network dependency?

Reference apps should stay framework-neutral unless they are explicitly marked
as case studies. Wraith and SaaS previews remain pressure tests; they should
not define the required app shape for public Otoe users.

## App Shape

The repeated app shape is now stable enough to document:

- an `AppShell` with a topbar, `SidebarNav`, and `RouteView`
- one snapshot object passed through a signal
- an explicit provider or adapter that owns external state
- route components that receive only the handlers they need
- a `last_feedback` field rendered near the route content
- focused fixture helpers for non-happy paths
- static preview and live preview entry points
- tests for static HTML, provider behavior, and live event dispatch

Do not add a new primitive merely because one app wants prettier markup. Shared
UI extraction is justified when at least two reference apps repeat the same
shape and the existing `otoe.ui` primitive cannot express it clearly. The first
extracted helpers from this rule are `SectionHeader`, `EmptyState`, and
`FeedbackToast`.

## Provider Contract

Reference app providers should expose a small synchronous contract:

- `snapshot()` returns the initial immutable snapshot.
- Event methods return a replacement snapshot instead of mutating UI state.
- Guardrails live in the provider, not only in disabled buttons.
- Unsafe or invalid actions return feedback and leave state unchanged.
- Successful actions update both domain state and operator-visible feedback.
- Fake providers model realistic failure, empty, blocked, and loading states.

The UI should not know whether data came from memory, CSV, SQLite, serial,
GPIO, USB, a local service, or another adapter. Component code should receive
snapshots and callbacks only.

## Feedback Pattern

Each reference app uses a visible feedback object:

- hardware: `CommandFeedback`
- admin/settings: `AdminFeedback`
- data workflow: `WorkflowFeedback`

The exact dataclass name can remain app-specific, but the shape should stay
consistent: `title`, `detail`, and `tone`. Feedback belongs in the snapshot so
static render, live render, and tests all see the same state.

## Route Pattern

Use `NavRoute`, `SidebarNav`, and `RouteView` for app-shaped examples. Route
renderers should dispatch to small view components and pass only the relevant
handlers:

- overview/status routes read snapshot state
- settings or queue routes receive edit/filter handlers
- access or selection routes receive toggle handlers
- history/audit routes can be read-only

Keep route IDs stable because tests and live previews dispatch against rendered
event IDs derived from those route buttons.

## Table Pattern

Use `DataTable` when row and column behavior is part of the point of the
example. Keep table data as domain objects, not pre-rendered cells. The table
renderer should map `TableColumn.key` to cell components and leave filtering,
selection, and guard rules in the provider or small pure helpers.

Tests should cover:

- static table render with representative rows
- empty table state
- filter/search behavior
- row action dispatch
- guarded bulk action behavior when applicable

## CSS Pattern

Reference apps now load one shared helper theme before app-specific CSS:

- `preview/reference_theme.css`

The shared theme covers the first extracted helper shapes:

- base Otoe preview selectors: reset, `.otoe-stack`, `.otoe-panel`,
  `.otoe-button`, `.otoe-input`, `.otoe-fragment`, and tone variants
- `SectionHeader`
- `EmptyState`
- `FeedbackToast`/`Toast`

Each app still owns its product-specific layout, density, and visual treatment:

- `preview/hardware.css`
- `preview/admin.css`
- `preview/data_workflow.css`

Static previews link `reference_theme.css` before the app stylesheet. Live
previews use `LivePreviewConfig.extra_css` so shared CSS is served explicitly
without `@import`.

Current extracted targets:

- `SectionHeader` for repeated section title, detail, badge, and action rows
- `EmptyState` for repeated empty-route, empty-list, and empty-table fallbacks
- `FeedbackToast` for snapshot-owned feedback objects with title/detail/tone

The utility-first reference app uses `utility_css()` instead of an app-specific
stylesheet to prove whether low-level classes plus modern presets can build a
professional surface without custom CSS for every screen. The current preset
set is `AppFrame`, `SidebarFrame`, `SidebarItem`, `TopBar`, `Surface`,
`MetricGrid`, `MetricTile`, `StatusPill`, and `ListRow`.

Remaining safe extraction targets:

- documented class naming conventions for app, topbar, sidebar, route shell,
  panel, stat grid, and table
- migration of common app shell, topbar, sidebar, nav, table, and stat-grid
  rules into the shared theme after those rules prove stable across all three
  reference apps

## Test Pattern

Every reference app should have focused tests for three layers:

- preview HTML: title, shell markers, representative content, and no leaked
  component object names
- provider: happy path, blocked path, and state invariants
- live preview: event ID lookup, dispatch, and rerendered content

Full-suite baseline after the live preview, static class hardening, Style IR
pack gate, bundle replay, backend readiness fixture, backend readiness report,
backend coverage declaration, renderer capability audit, StyleOps capability
audit, primitive value validation, bundle manifest hardening, namespace runtime
discovery, dependency audit contract metadata, RenderTree validation, and
backend coverage trace plus Path0 output semantic contract and external Path0
JSON runner/readiness evidence plus backend package manifest pass:
`697 passed, 1 skipped`.

## Current Decision

The Phase 5 reference apps satisfy the initial product-shape requirement:
hardware/control panel, local admin/settings, and data/table workflow all exist
with provider boundaries and tests.

The current implementation direction is to return to backend work with these
apps as acceptance surfaces. More CSS extraction should wait until at least two
reference apps repeat the same shell, nav, table, or stat-grid selector shape.
The utility-first reference app is the exception: it exists specifically to
pressure-test low-level styling ergonomics before those utilities are promoted
into public guidance.
