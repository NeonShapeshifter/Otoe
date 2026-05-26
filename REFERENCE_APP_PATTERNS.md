# Reference App Patterns

Phase 5 reference apps are professional validation surfaces. They are not
runtime features, and they are not product forks. They show whether Otoe can
support polished Python applications with explicit state boundaries.

Current reference apps:

- `examples.hardware.control_panel` - hardware/control panel
- `examples.admin.settings_console` - local admin/settings
- `examples.data_workflow.workbench` - data/table workflow

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

Do not add a new primitive merely because one app wants prettier markup. Add or
extract shared UI only when at least two reference apps repeat the same shape
and the existing `otoe.ui` primitive cannot express it clearly.

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

The three Phase 5 CSS files intentionally repeat some base rules for now:

- `preview/hardware.css`
- `preview/admin.css`
- `preview/data_workflow.css`

That duplication is acceptable until live preview serving supports shared CSS
assets or the project adds a documented preview theme layer. Do not use CSS
`@import` for the shared base yet; each live preview currently exposes one CSS
route.

Safe near-term extraction targets:

- documented class naming conventions for app, topbar, sidebar, route shell,
  panel, section heading, stat grid, table, empty state, and feedback
- optional UI-kit helpers for section headings, empty states, and feedback
  toasts if more examples repeat the same markup
- a shared preview theme only after static preview and live preview both serve
  it predictably

## Test Pattern

Every reference app should have focused tests for three layers:

- preview HTML: title, shell markers, representative content, and no leaked
  component object names
- provider: happy path, blocked path, and state invariants
- live preview: event ID lookup, dispatch, and rerendered content

Full-suite baseline after the current reference app pattern pass: `332 passed`.

## Current Decision

The Phase 5 reference apps satisfy the initial product-shape requirement:
hardware/control panel, local admin/settings, and data/table workflow all exist
with provider boundaries and tests.

The next implementation decision should be one of:

- extract a small UI helper only where markup repeats across at least two apps
- improve preview theme delivery so shared CSS can be served safely
- return to backend work with these apps as acceptance surfaces
