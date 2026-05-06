# Otoe Roadmap

**Status:** Phase 2 / Native Renderer Spike
**Updated:** May 6, 2026
**Reference case study:** Framework-neutral native renderer/layout spike

---

## Product Thesis

Otoe is a professional Python desktop UI framework. Its core promise is that a
Python component tree can produce predictable state, layout, pixels, and input
behavior without inheriting the mutation-heavy ergonomics of legacy desktop UI.

Case studies are validation tools, not the product itself. Wraith validates a
dense operational/security surface; the SaaS preview validates a softer
commercial product surface; framework-neutral examples validate that Otoe can be
used without knowing either app exists.

The current framework question is no longer whether signals, components,
control flow, and HTML previews can work. They do. The next question is whether
the same Otoe tree can leave the browser preview path and render through a real
layout/paint boundary.

The order matters. Otoe should be framework-first in architecture and
case-study-validated in practice. Wraith should continue to pressure-test the
API, but the roadmap should not treat Wraith migration as the framework's next
milestone.

The immediate goal is a native renderer spike: Otoe tree -> layout boxes ->
pixels -> hit-tested events. If that path works, CLI/devtools and app migration
work become much more meaningful because they sit on top of a real desktop
backend, not only an HTML preview.

---

## Roadmap Principles

1. **Professional framework first.** Otoe's core API should stand on its own; case studies prove pressure, not ownership.
2. **Case-study-shaped, not case-study-coupled.** Major API decisions should survive Wraith-shaped, SaaS-shaped, and framework-neutral examples, but the core cannot import or assume app internals.
3. **Framework-quality from day one.** Even for personal use, the core needs clean contracts, tests, errors, and separation boundaries.
4. **Runtime before syntax sugar.** Signals, owners, lifecycle, events, `Show`, and `For` come before any JSX-like transpiler.
5. **Deterministic widget contracts.** Widgets declare `props`, `events`, and optional `primary_prop`; unknown props are errors.
6. **No hidden event magic.** Handlers are classified by widget schema before data-prop reactivity.
7. **Renderer boundary before renderer lock-in.** The spike may use Taffy and Skia, but public APIs should describe layout, paint, input, and accessibility contracts rather than one backend's quirks.
8. **Migration is earned later.** Otoe should prove native layout, paint, and input before replacing any production app surface.

---

## Operating Model

Phases 0-2 are framework-first internal R&D. They are successful if Otoe proves
that its component/runtime model can support real app surfaces, deterministic
layout, rendered pixels, and input dispatch. Public adoption, GitHub stars,
conference talks, and community roadmap goals are not success criteria before
Phase 6.

Otoe can start now, but the time budget must be explicit. Phase 1 is not a "small docs cleanup"; the fake-widget runtime with signals, computed values, effects, owners, mounting, events, `Show`, `For`, batching, and tests is a real implementation slice.

Planning estimate:

- **Phase 0:** 8-16 focused hours for ADR-002/ADR-003 and case-study component sketches.
- **Phase 1:** 40-60 focused hours for the pure runtime slice and tests.
- **Phase 2:** 40-80 focused hours for layout, paint, hit-testing, and the first headless native renderer spike.
- **Phase 3:** 20-40 focused hours for an interactive native demo once Phase 2 exists.

At 2-4 hours/week, Phase 1 is a multi-month calendar project. At 8-10 hours/week, it can become a 1-2 month slice. If those hours come from Wraith feature work, that is an explicit priority shift, not background work.

Existing production apps remain unchanged until Otoe proves equivalent behavior
and better maintainability through isolated native surfaces. Migration is a
consumer decision after the renderer/runtime boundary works, not the current
framework milestone.

---

## Current Status

### Completed

- Package scaffold: `pyproject.toml`, `src/otoe`, `tests`, `examples/wraith`.
- `Node` descriptor and widget call syntax.
- Widget schema with `props`, `events`, and `primary_prop`.
- Unknown prop and invalid event errors.
- `signal`, `computed`, and `effect`.
- Component ownership, `on_mount`, `on_cleanup`, and unmount disposal.
- Fake-widget mount with static props, reactive props, events, and child trees.
- Wraith-shaped first examples:
  - `TopBar`
  - `ArsenalView`
- Control-flow primitives:
  - `Show`
  - `For`
- Wraith `ArsenalView` now renders a reactive mission list with keyed mission cards and empty state.
- ADR-003 scheduling decision.
- Minimal batching with `batch(fn)` and `with batch():`.
- Owner-scoped `interval()` helper with deterministic `.tick()` prototype API.
- Wraith `RuntimeStatusCluster` polling example.
- Fake-widget snapshot serializer.
- State-change snapshots for Wraith examples.
- Static HTML renderer from fake widgets.
- Pretty HTML renderer output for deterministic generated previews.
- Wraith static preview page.
- First static Wraith preview CSS polish pass.
- Live HTML renderer with event ids for click and input changes.
- Wraith live preview server backed by the Otoe runtime.
- Live preview interactions for stealth toggle, search filtering, and pagination.
- Web-app visual pass for the Wraith preview CSS.
- Wraith Mission Exec surface extracted from the Wraith frontend/Kivy shape into Otoe components.
- Wraith Mission Exec static preview page.
- Wraith Mission Exec live preview with telemetry filters, pause/resume, abort, clear, and export actions.
- Wraith Mission Exec visible runtime probe for proving live signal/event mutations.
- SaaS-style secondary preview proving a softer commercial dashboard aesthetic.
- SaaS preview spacing pass for cleaner product rhythm.
- SaaS live preview with search filtering and invite/new-deal mutation.
- SaaS live navigation buttons with active-section state.
- SaaS section composition for Customers, Revenue, Automations, and Settings.
- Optional JSX-like `template(...)` authoring path that returns the same `Node` tree.
- ADR-004 template syntax decision.
- Portable `css(...)` / `StyleSheet` prototype with tokens, sizes, strict class resolution, and HTML inline adapter.
- ADR-005 style system decision.
- Public technical preview README.
- GitHub Actions CI for compile and tests.
- Sanitized preview fixtures for public sharing.
- Shared live-preview server helper used by Wraith, Mission Exec, and SaaS demos.
- First `otoe.ui` primitives: `Card`, `Badge`, `ActionButton`, `Toolbar`, `Tabs`, `TabButton`, and `StatCard`.
- SaaS preview topbar, nav, actions, and metrics migrated onto `otoe.ui`.
- `DataTable`, `Dialog`, `Toast`, and `TableColumn` added to `otoe.ui`.
- SaaS Customers view migrated to `DataTable`; Settings status migrated to `Toast`.
- Wraith Mission Exec panels, controls, filters, badges, and toolbar migrated onto `otoe.ui`.
- `CommandPalette` added to `otoe.ui`.
- UI kit kitchen-sink preview added for validating shared primitives outside one case study.
- UI kit live preview proves command filtering, command selection, dialog mounting, empty state, and reactive toast classes.
- `AppShell`, `SidebarNav`, `NavItem`, `NavRoute`, and `RouteView` added for signal-based app routing.
- UI kit preview reworked into a routed shell that switches between UI Kit, SaaS, and Wraith-shaped surfaces.
- Live `onKeyDown` dispatch added to the HTML preview loop.
- `CommandPalette` Enter-key selection added for the first visible command.
- `Command`, `CommandRegistry`, and `ShortcutScope` added for command metadata and global key handling.
- UI kit global shortcuts added: `Ctrl+K`/`Meta+K`, `Escape`, and registered single-key command shortcuts.
- UI kit command palette now has explicit open/close state, a launcher card, and overlay dialog.
- `Input(autoFocus=...)` added with live-preview autofocus after rerender.
- `Menu`, `MenuItem`, `Select`, and `SelectOption` added with controlled state contracts.
- UI kit preview now includes live controlled select and action menu examples.
- Button-backed controls now support live `onKeyDown`.
- Menu and select primitives now support keyboard movement, submit, and Escape close behavior.
- `FocusScope` added with live-preview Tab trapping and focus restoration for dialogs and popovers.
- Keyed `For` now refreshes changed item data for existing keys while preserving stable keyed reorders.
- Async event handler regression tests added for coroutine functions, coroutine-returning sync handlers, and running-loop dispatch.
- Async event error regression tests added for no-loop and running-loop dispatch paths.
- `otoe.ui` internals split into private helper, model, and keyboard modules while preserving public imports.
- Mission Exec event timeline severity filter added as the first recorded Otoe-vs-Wraith change benchmark.
- Mission Exec combo approval modal added as a second Wraith/Kivy benchmark for overlays, focus scope, and critical action state.
- Mission Exec remote snapshot recovery added as a third Wraith/Kivy benchmark for runtime reattach, restored logs, elapsed state, and pending approval state.
- ADR-006 native renderer/layout boundary drafted.
- First headless native layout adapter added with deterministic boxes for stacks, text, buttons, inputs, panels, resolved dimensions, and reactive prop updates.
- First headless native paint adapter added with deterministic rect/text commands and stdlib PNG output.
- Native hit-testing and click dispatch added for coordinate -> mounted event handler -> state update flows.
- Framework-neutral native counter demo added for state -> layout -> paint -> input -> state.
- Native renderer spike support/rejection/deferred-work contract documented.
- `NativeSurface` added as the headless renderer surface API for mount -> layout -> paint -> click -> rerender flows.
- Headless `NativeSurface` focus and keyboard handling added for autofocus, click-to-focus, Tab traversal, focused keydown, button submit keys, and global shortcut payloads.
- Headless controlled input text dispatch added through `NativeSurface.input_text(...)`.
- Framework-neutral native task board demo added for app shell, search, filtered list, empty state, modal state, shortcuts, and PNG frame output.
- Lazy `NativeSurface` auto-refresh added for external reactive prop and control-flow updates.
- `BENCHMARKS.md` added for concrete change-friction notes against Wraith/Kivy.
- CI now builds release distributions and runs `twine check` on package metadata.
- Baseline tests: `148 passed`.

### Current Sprint

1. Write the renderer/layout boundary for `Native Renderer Spike 001`: tree input, style subset, layout output, paint output, hit-test output. **ADR-006 drafted.**
2. Add a headless layout adapter for a small generic subset: `VStack`, `HStack`, `Text`, `Button`, `Input`, `Card`/`Panel`, padding, gap, fixed size, min/max, and flex. **Initial deterministic adapter added.**
3. Add a headless paint adapter that can render boxes, text, backgrounds, borders, and radius to a PNG. **Initial command/PNG adapter added.**
4. Add a framework-neutral native demo surface that proves layout, state update, button dispatch, and rerender without using Wraith fixtures. **Native counter demo added.**
5. Add hit-testing for coordinates -> mounted node -> event dispatch. **Initial click dispatch added.**
6. Add deterministic tests for layout boxes, non-empty PNG output, and simulated click state changes. **Initial coverage added.**
7. Document what the native spike supports, what it rejects, and what is deferred to windowing/accessibility. **Native spike support contract added.**
8. Package the headless native renderer behind a framework-facing surface object so examples do not manually stitch mount/layout/paint/input. **`NativeSurface` added.**
9. Add a headless focus and keyboard subset before windowing: autofocus, click-to-focus, Tab traversal, focused keydown, submit keys, and global shortcuts. **Initial `NativeSurface` support added.**
10. Add controlled headless input text dispatch before windowing. **`NativeSurface.input_text(...)` added.**
11. Add a framework-neutral native app demo with shell, search, list, empty state, modal, and shortcuts. **Native task board demo added.**
12. Add lazy invalidation so external reactive updates refresh `NativeSurface` without manual `refresh()`. **Added for reactive props and control-flow tree changes.**

---

## Phase 0 — Case Study and First Slice

**Goal:** turn the ADR into the smallest buildable slice that can attack real desktop UI pain immediately.

The early case studies proved the domain pressure: dense operational UI,
commercial dashboard UI, overlays, routing, commands, keyboard handling, and
stateful previews. The next slices must stay isolated from production apps until
the native backend proves value.

### Scope

- Keep `ADR-001` authoritative for component model, signals, lifecycle, node tree, and events.
- Write case-study pseudo-components for:
  - `TopBar`
  - `BaseScreen` / app shell
  - `ArsenalView`
  - `MissionCard`
  - `LockScreen` or modal overlay
- Define the API for:
  - `Show`
  - `For`
  - keyed list identity
  - batching and scheduling
  - app shell / routing / overlays
  - interval/timer cleanup
- Create ADRs or short design notes for unresolved high-risk topics:
  - threading and UI ownership
  - layout engine boundary
  - renderer strategy
  - styling and token model
- Start a small prototype package once the first runtime slice is clear:
  - fake-widget mount first
  - visible demo second
  - production app adapters only after the demo works with fixtures

### Exit Criteria

- At least 10 example components exist and read naturally.
- Dense dashboard and operational surfaces can be expressed without manual widget mutation, `bind(...)`, or layout bookkeeping in user code.
- The public API for `Signal`, `Computed`, `Effect`, widget schema, events, `Show`, and `For` is stable enough to implement.
- A first prototype path is chosen: either fake-widget runtime first, or a very thin visible adapter if that gets feedback faster.
- The renderer decision is narrowed to one primary research path and one fallback path.

---

## Phase 1 — Pure Python Runtime Core

**Goal:** implement the framework behavior without a visual backend.

This phase starts immediately after the first Phase 0 API slice is coherent enough to test. It does not wait for any Wraith release milestone.

### Scope

- Package scaffold.
- `Node` representation.
- Widget schema normalization:
  - `props`
  - `events`
  - `primary_prop`
  - unknown prop errors
- Reactive primitives:
  - `signal`
  - `computed`
  - `effect`
  - dependency tracking
  - batching
  - cleanup-on-rerun
- Owner model:
  - component owner context
  - lifecycle registration
  - automatic disposal
- Mounting into fake widgets:
  - static prop assignment
  - reactive prop subscription
  - event handler registration
  - unmount cleanup
- Event dispatcher:
  - sync handlers
  - async handlers
  - sync handlers returning coroutines
  - useful error reporting
- Control-flow primitives:
  - `Show`
  - `For`
  - keyed item disposal
- Tests for every primitive.

### Exit Criteria

- All Phase 0 examples mount into fake widgets.
- Updating a signal changes only subscribed fake-widget properties.
- Event callables never collide with reactive callables.
- `Show` and `For` dispose child owners correctly.
- Batching prevents duplicate effect runs in one update turn.

---

## Phase 2 — Layout, Styling, and Renderer Spike

**Goal:** prove that the runtime can produce deterministic layout, pixels, and
hit-tested events without compromising the public component API.

### Scope

- Choose initial renderer path for the spike:
  - primary candidate: Taffy layout + Skia rendering
  - fallback candidate: a small pure-Python layout/paint adapter for tests only
- Define the renderer boundary:
  - mounted tree input
  - resolved style subset
  - layout box output
  - paint command output
  - hit-test index output
  - unsupported feature diagnostics
- Implement a minimal layout bridge:
  - flex direction
  - gap
  - padding
  - width / height
  - min / max
  - basic scroll container bounds
- Implement a minimal widget catalog:
  - `VStack`
  - `HStack`
  - `Text`
  - `Button`
  - `Input`
  - `Card` or `Panel`
  - `ScrollView` bounds without full scrolling behavior
- Styling baseline:
  - token dictionary
  - `className`
  - utility parser for the small Phase 2 subset
  - deterministic unsupported-class warnings
- Headless paint:
  - backgrounds
  - borders
  - radius
  - text
  - simple clipping
- Headless input:
  - coordinate hit-testing
  - click dispatch
  - rerender after state change
  - focus traversal
  - focused keydown
  - button submit keys
  - global shortcut payloads
  - controlled input text dispatch
- Headless surface:
  - one object owns mounted tree, current layout, current paint, frame count, click dispatch, and PNG rendering
- Defer real windowing until the headless renderer is proven.

### Exit Criteria

- A framework-neutral demo renders to a non-empty PNG.
- A framework-neutral app-shaped demo exercises search, list filtering, empty state, modal state, shortcuts, and multiple frames.
- Layout boxes are deterministic and testable.
- Props update from signals and produce a changed render tree.
- External signal and control-flow updates invalidate the headless surface without manual app code.
- A simulated click dispatches through Otoe's event system and updates state.
- A headless surface API lets framework users render and dispatch input without manually wiring each renderer stage.
- Focus and keyboard behavior can be tested without a window.
- Controlled input changes can be tested without a browser.
- Styling is expressive enough to build both dense operational panels and calmer product dashboards.
- Unsupported styling fails clearly instead of silently.

---

## Phase 3 — Interactive Native Demo

**Goal:** turn the headless renderer spike into a small interactive native app
that feels like a framework demo rather than a screenshot generator.

This is the first native product milestone. If this phase cannot handle state,
layout, paint, input, focus, and rerender in one generic app surface, Otoe is
not ready to talk about app migrations.

### Scope

- Build a standalone Otoe native demo of:
  - app shell
  - toolbar
  - cards/panels
  - form controls
  - data list or table
  - search
  - empty/loading states
  - modal or popover
- Add a minimal windowing adapter only after headless layout/paint/hit-testing passes.
- Support click, keyboard, focus, and text input for the minimal widget subset.
- Add app-level rerender scheduling that does not require user code to manage invalidation.
- Compare the same app against the HTML preview only to verify behavior parity, not visual exactness.

### Exit Criteria

- The demo runs outside a browser.
- Button, input, modal, and list interactions work through the Otoe event system.
- Non-trivial UI changes are materially faster than equivalent manual widget mutation patterns.
- No screen-level canvas/redraw code is needed.
- Tests can assert state and rendered structure without booting the full app.

---

## Phase 4 — Developer Experience

**Goal:** make Otoe pleasant and reliable enough for repeated app development.

This phase turns the native runtime into a usable framework surface. The target
is a small but coherent Python desktop framework that another app can use
without knowing any case-study context.

### Scope

- Typed widget stubs.
- Better diagnostics:
  - unknown prop
  - wrong event name
  - wrong handler arity
  - disposed signal access
  - mutation during mount
- Documentation:
  - mental model
  - component cookbook
  - styling subset
  - renderer/layout subset
  - event signatures
- CLI:
  - `otoe dev`
  - `otoe render`
  - `otoe check`
  - optional `otoe new`
- Snapshot testing for mounted trees.
- Optional watch mode for examples/previews.
- Example corpus:
  - concise idiomatic components
  - native renderer examples
  - HTML preview examples
  - case-study examples

### Exit Criteria

- A developer can build a small app without reading the internals.
- Type checking catches common widget mistakes.
- Error messages point to the component and prop/event that caused the issue.

---

## Phase 5 — Case Study Migration Option

**Goal:** decide whether Otoe should become a real dependency for one existing
app surface.

### Scope

- Do not migrate any app wholesale.
- Pick one low-risk surface after the standalone native demo proves the UI/runtime model.
- Keep service/runtime/data boundaries unchanged.
- Build an adapter that lets Otoe screens consume app services without importing the legacy UI backend.
- Run Otoe and legacy surfaces side by side where possible.
- Preserve operational behavior and tests.

### Exit Criteria

- One real app surface can be implemented in Otoe without weakening runtime safety.
- The migration reduces maintenance burden enough to justify dependency risk.
- The app can still ship without Otoe if Otoe is not ready.

---

## Phase 6 — Optional Framework Extraction

**Goal:** decide whether Otoe should become a reusable public or semi-public framework.

### Scope

- Keep case studies as regression suites.
- Remove accidental app assumptions from public APIs.
- Stabilize package structure and import paths.
- Write framework-neutral examples:
  - dashboard app
  - settings/admin app
  - local database CRUD app
  - hardware/status monitor
- Optionally test AI-assisted code generation against the documented examples. This is validation of API shape, not a core product promise.
- Define compatibility policy.
- Decide whether the project is personal-only, private reusable, or public.

### Exit Criteria

- At least three framework-neutral examples can be built without new framework primitives.
- Public docs explain Otoe without referencing any one case study as required context.
- The framework remains useful for the original case studies after generalization.
- The API feels like a Python-native relative of React/Solid, not a clone and not a Kivy wrapper.
- LLM-generated examples, if tested, follow the schema/event/reactivity rules without special prompting.

---

## Non-Goals For Now

- No JSX/transpiler in Phase 1.
- No full production app rewrite until one Otoe surface proves better maintainability and equivalent behavior.
- No generic virtual DOM.
- No event bubbling in Phase 1.
- No broad Tailwind clone before a small utility subset works.
- No custom animation system before layout, input, and lifecycle are stable.
- No public branding push before a native renderer demo exists.
- No public framework stability promises until native layout, paint, input, and diagnostics are proven.

---

## Immediate Next Actions

1. Draft `ADR-006` for the native renderer/layout boundary. **Done.**
2. Add the first headless layout adapter and deterministic box tests. **Done.**
3. Add the first headless paint adapter and non-empty PNG test. **Done.**
4. Add simulated hit-testing for click dispatch against a framework-neutral demo. **Done for the minimal widget subset.**
