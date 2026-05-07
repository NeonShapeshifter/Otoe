# Changelog

## Unreleased

## v0.0.5 - Native Renderer Spike

- Added `NativeSurface` to package mount/layout/paint/click/rerender into one
  headless renderer surface API.
- Added headless `NativeSurface` focus and keyboard handling: autofocus,
  click-to-focus, Tab traversal, focused `onKeyDown`, button submit keys, and
  global shortcut payload dispatch.
- Added headless `NativeSurface.input_text(...)` dispatch for controlled input
  `onChange` flows.
- Added a framework-neutral native task board demo with app shell, search,
  filtered list, empty state, modal, shortcuts, and multi-frame PNG output.
- Added lazy `NativeSurface` auto-refresh when external signal or control-flow
  updates mutate the mounted fake-widget tree.
- Added native `ScrollView` viewport clipping for paint output, PNG rendering,
  and hit-tested click dispatch.
- Fixed native click dispatch so disabled widgets do not fire click handlers.
- Fixed keyed `For` updates when an item keeps the same key but changes data.
- Added async event handler regression coverage for coroutine functions,
  coroutine-returning sync handlers, and running-loop dispatch.
- Added async event error regression coverage for no-loop and running-loop
  dispatch paths.
- Split `otoe.ui` internals into private helper, model, and keyboard modules
  while preserving the public `otoe.ui` import surface.
- Added live Mission Exec event timeline severity filtering as the first
  recorded Wraith/Kivy change benchmark.
- Added live Mission Exec combo approval modal benchmark with approve and deny
  flows using existing dialog/focus primitives.
- Added live Mission Exec remote snapshot recovery benchmark with restored
  telemetry, runtime status, elapsed time, and pending approval state.
- Added ADR-006 for the native renderer/layout boundary.
- Added the first headless native layout adapter with deterministic boxes for
  stacks, text, buttons, inputs, panels, and resolved style dimensions.
- Added the first headless native paint adapter with deterministic rect/text
  commands and a stdlib PNG writer for non-empty image output.
- Added native hit-testing and click dispatch that maps coordinates to mounted
  event handlers and supports state-changing rerender flows.
- Added a framework-neutral native counter demo proving state -> layout ->
  paint -> input -> state without Wraith fixtures.
- Documented the native renderer spike support matrix, explicit rejections,
  and deferred backend work.
- Added `BENCHMARKS.md` to track concrete Otoe-vs-Wraith UI change friction.
- Expanded CI to build the package and run `twine check` on generated
  distributions.

## v0.0.3 - Controlled UI Primitives

- Prepared PyPI package metadata and Trusted Publishing release automation.
- Added `Menu`, `MenuItem`, `Select`, and `SelectOption` primitives with
  controlled open/selection state.
- Expanded the UI kit preview with controlled select and action menu examples.
- Added keyboard handling for button-backed controls, menus, and selects:
  Arrow keys, Home/End, Enter/Space, and Escape.
- Added `FocusScope` plus live-preview Tab trapping and focus restoration for
  dialogs and popovers.

## v0.0.2 - App Shell and Command System Preview

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
- Added live `onKeyDown` dispatch and `CommandPalette` Enter-key selection for
  the first visible command.
- Added `Command`, `CommandRegistry`, and `ShortcutScope` for command metadata
  and global key handling.
- Added UI kit global shortcuts: `Ctrl+K`/`Meta+K` returns to the command
  surface, `Escape` clears transient state, and command shortcut keys execute
  registered commands.
- Added explicit command-palette open state to the UI kit preview, with a
  launcher card, overlay dialog, and Escape close behavior.
- Added `Input(autoFocus=...)` support plus live-preview autofocus after
  rerender, so command overlays can focus their search field immediately.

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
