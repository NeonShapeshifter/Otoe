# Changelog

## Unreleased

- Extracted shared live-preview server infrastructure for Wraith, Mission Exec,
  and SaaS demos.
- Added tests for the shared live-page shell and event script.
- Added the first `otoe.ui` primitives: `Card`, `Badge`, `ActionButton`,
  `Toolbar`, `Tabs`, `TabButton`, and `StatCard`.
- Migrated the SaaS preview topbar, nav, actions, and metrics onto `otoe.ui`.
- Added `DataTable`, `Dialog`, `Toast`, and `TableColumn` primitives.
- Migrated the SaaS Customers view to `DataTable` and Settings status to `Toast`.
- Migrated the Wraith Mission Exec surface onto shared `otoe.ui` primitives.
- Added `CommandPalette` and a UI kit kitchen-sink preview for shared
  component validation.
- Added live UI kit preview tests for command filtering, selection, dialog
  opening, empty states, and reactive toast classes.
- Added `AppShell`, `SidebarNav`, `NavItem`, `NavRoute`, and `RouteView`
  primitives for signal-based app routing.
- Reworked the UI kit preview into a routed shell that switches between UI Kit,
  SaaS, and Wraith-shaped surfaces.

## v0.0.1 - Technical Preview

Initial public technical preview of Otoe.

- Reactive Python UI runtime with `signal`, `computed`, `effect`, and batching.
- Component ownership, lifecycle cleanup, explicit widget contracts, and event dispatch.
- `Show` and keyed `For` control-flow primitives.
- Fake-widget mount backend with snapshots and deterministic tests.
- Static and live HTML preview backends.
- Wraith Mission Exec case study with visible runtime mutations.
- SaaS dashboard case study for a softer product UI surface.
- Optional JSX-like `template(...)` syntax.
- Experimental portable `css(...)` / `StyleSheet` prototype.
- MIT license under Forvara.
