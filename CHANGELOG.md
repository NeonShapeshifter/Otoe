# Changelog

## Unreleased

- Added utility-first styling helpers and modern `otoe.ui` presets for
  no-custom-CSS app surfaces.
- Added the first offline hardware/cage workflow: `otoe plan`, `otoe deps`, and
  manifest-first `otoe build` with `otoe-plan.json`, `otoe-deps.json`,
  `frameworkFiles`, explicit runtime files, and a generated `otoe-run.py`
  load/check plus headless PNG runner.
- Added `otoe build --validate` to run the generated bundle runner in `--check`
  mode and catch targets that only import from the workspace.

## v0.1.4 - Native Backend Acceptance Hardening

- Hardened the backend acceptance contract with reusable named-path harness and
  replay helpers.
- Added app-shaped native task board replay as a Phase 5 pressure surface for
  backend candidates.
- Added fake backend adapter replay through `run_native(...)` to prove adapters
  receive and drive `NativeWindowDriver`.
- Updated native workflow and backend docs to keep future backend candidates
  behind the driver/surface boundary.

## v0.1.3 - Reference Apps and Live Preview Hardening

- Added hardware/control panel, local admin/settings, and data workflow
  reference apps with provider or adapter boundaries, static previews, live
  previews, alternate states, guarded actions, feedback rendering, and tests.
- Added `REFERENCE_APP_PATTERNS.md` to document Phase 5 app-shape, provider,
  route, table, CSS, and test extraction rules.
- Added shared reference preview styling through `preview/reference_theme.css`
  and live preview `extra_css` support.
- Added `SectionHeader`, `EmptyState`, and `FeedbackToast` UI helpers after
  repeated reference-app usage.
- Fixed keyed `For` mounting so duplicate keys are rejected instead of
  reusing one mounted child in multiple positions.
- Escaped live-preview shell metadata and stylesheet routes before rendering
  the dev HTML wrapper.
- Added live-preview client-side ordering so stale event responses cannot
  overwrite newer UI.
- Hardened `template(...)` primary-content parsing for widgets that also nest
  child nodes.

## v0.1.2 - Developer Experience Closeout

- Added framework mental model, component cookbook, widget contracts, style
  guide, native workflow guide, testing guide, and example index docs.
- Added widget, control-flow, and UI component/model typing stubs with PEP 561
  packaging metadata.
- Added `mypy` smoke coverage for valid public API usage and common widget/UI
  typing mistakes.
- Improved unknown prop, unknown event, handler arity, reactive mutation, and
  native renderer diagnostic context.
- Added `otoe new` for minimal app scaffolds with optional `styles.css`.
- Expanded `otoe render` with CSS input, native PNG output, and strict-style
  control.
- Expanded `otoe check` with optional pytest execution, custom paths, and
  pytest argument forwarding.
- Improved `otoe dev` handling for app objects, factories, CSS serving, root
  classes, and CLI validation.

## v0.1.1 - Renderer Contract Hardening

- Added a backend-replay acceptance surface that drives a framework-neutral tree
  through `NativeWindowDriver` and `NativeSurface`.
- Expanded native stack layout support for `alignItems` and `justifyContent`,
  including start/end/stretch and spacing distribution values.
- Added native layout guardrails for negative dimensions while preserving
  `ScrollView(scrollY=...)` clamp behavior.
- Aligned native hit-testing, painter order, and focus hit-testing so
  overlapping controls choose the same topmost path.
- Hardened native diagnostics for strict stylesheet classes, layout dimensions,
  paint colors, PNG command failures, and `NativeSurface` input/focus errors.
- Documented the Phase 2B backend boundary and exit cleanup status.

## v0.1.0 - Native Renderer Spike

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
- Added native paint states for disabled button/input defaults and visible
  focus rings on focused controls.
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
