# Otoe Roadmap

**Status:** Phase 1 / Runtime Slice  
**Updated:** May 5, 2026  
**Reference case study:** Wraith OS Kivy UI

---

## Product Thesis

Otoe is a professional Python desktop UI framework. Wraith is the flagship case study: the real app that proves whether the framework is useful, maintainable, and visually strong enough.

Secondary case studies are allowed when they test generality without distracting from Wraith. A SaaS-style dashboard is useful because it proves Otoe's primitives can support a softer commercial product surface, not only a dense operational/security UI.

The framework exists because Wraith needs a better UI layer now, but the bar is framework-quality from the beginning: modern component patterns, explicit data flow, typed widget contracts, predictable runtime behavior, and a developer experience closer to React/Solid than to legacy desktop UI.

The order matters. Otoe should be framework-first in architecture and Wraith-first in validation. It should solve real Wraith screens before chasing public-framework polish, but it should avoid Wraith-specific shortcuts that would make the core impossible to reuse.

Wraith is the first case study. The goal is not to build a toy counter demo; it is to make screens like Wraith's `TopBar`, `ArsenalView`, app shell, overlays, runtime status, and mission workflows easier to express, test, and maintain than their Kivy equivalents.

---

## Roadmap Principles

1. **Professional framework, Wraith case study.** Otoe's core API should stand on its own; Wraith proves whether it works under real product pressure.
2. **Wraith-shaped, not Wraith-coupled.** Every major API decision must survive at least one Wraith-shaped example, but the core cannot import or assume Wraith internals.
3. **Framework-quality from day one.** Even for personal use, the core needs clean contracts, tests, errors, and separation boundaries.
4. **Runtime before syntax sugar.** Signals, owners, lifecycle, events, `Show`, and `For` come before any JSX-like transpiler.
5. **Deterministic widget contracts.** Widgets declare `props`, `events`, and optional `primary_prop`; unknown props are errors.
6. **No hidden event magic.** Handlers are classified by widget schema before data-prop reactivity.
7. **No renderer lock-in too early.** The first runtime should mount into fake widgets before committing to Skia, Taffy, Kivy interop, or another backend.
8. **Migration is incremental.** Otoe should be able to prove itself beside Wraith before replacing any Wraith screen.

---

## Operating Model

Phases 0-3 are Wraith-first internal R&D. They are successful if Otoe makes Wraith's UI easier to build, test, and improve. Public adoption, GitHub stars, conference talks, and community roadmap goals are not success criteria before Phase 6.

Otoe can start now, but the time budget must be explicit. Phase 1 is not a "small docs cleanup"; the fake-widget runtime with signals, computed values, effects, owners, mounting, events, `Show`, `For`, batching, and tests is a real implementation slice.

Planning estimate:

- **Phase 0:** 8-16 focused hours for ADR-002/ADR-003 and Wraith-shaped component sketches.
- **Phase 1:** 40-60 focused hours for the pure runtime slice and tests.
- **Phase 2:** 40-80 focused hours depending on renderer path.
- **Phase 3:** 20-40 focused hours for the first Wraith surface demo once Phase 2 exists.

At 2-4 hours/week, Phase 1 is a multi-month calendar project. At 8-10 hours/week, it can become a 1-2 month slice. If those hours come from Wraith feature work, that is an explicit priority shift, not background work.

Wraith remains the production app until an isolated Otoe surface proves equivalent behavior and better maintainability. Otoe should not replace a Wraith surface by default; replacement is earned by the Phase 3 comparison.

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
- Baseline tests: `56 passed`.

### Current Sprint

1. Review the Mission Exec live preview visually in a browser against the Wraith source.
2. Tighten Mission Exec spacing, hierarchy, and interaction states until it feels better than the current Wraith UI.
3. Compare a non-trivial Mission Exec change in Otoe versus the Wraith Kivy/front prototype and record the friction points.
4. Decide whether the next Wraith-shaped benchmark is routing/app shell, overlay/modal, or runtime polling.
5. Decide whether Wraith or SaaS should migrate one small surface from browser CSS to portable `css(...)`.
6. Extract shared live-preview/server code after the third live surface proves the duplication is real.
7. Keep snapshots plus live-render tests as the renderer contract while the backend is still moving.

---

## Phase 0 — Case Study and First Slice

**Goal:** turn the ADR into the smallest buildable slice that can attack Wraith's UI pain immediately.

Wraith already proves the domain. It can perform real recon and runtime work; the blocker is that the Kivy UI is too expensive to evolve and does not meet the product bar visually. Otoe work can start now, as long as the first slices stay isolated from Wraith's production runtime until they prove value.

### Scope

- Keep `ADR-001` authoritative for component model, signals, lifecycle, node tree, and events.
- Write Wraith-shaped pseudo-components for:
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
  - Wraith data adapter only after the demo works with fixtures

### Exit Criteria

- At least 10 example components exist and read naturally.
- `TopBar` and `ArsenalView` can be expressed without manual widget mutation, `bind(...)`, or layout bookkeeping in user code.
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

**Goal:** prove that the runtime can create a visible desktop UI without compromising the API.

### Scope

- Choose initial renderer path:
  - primary candidate: Taffy layout + Skia rendering
  - fallback candidate: adapter layer over an existing Python UI backend for validation only
- Implement a minimal layout bridge:
  - flex direction
  - gap
  - padding
  - width / height
  - min / max
  - scroll container
- Implement a minimal widget catalog:
  - `Window`
  - `VStack`
  - `HStack`
  - `Text`
  - `Button`
  - `Input`
  - `ScrollView`
  - `Card` or `Panel`
- Styling baseline:
  - token dictionary
  - `className`
  - utility parser for the small Phase 2 subset
  - deterministic unsupported-class warnings
- Input loop:
  - click
  - text input
  - keyboard
  - focus

### Exit Criteria

- A visible local demo renders without Kivy user-code patterns.
- Props update from signals live.
- Buttons and inputs dispatch through Otoe's event system.
- Styling is expressive enough to build Wraith-like dense operational panels.
- Unsupported styling fails clearly instead of silently.

---

## Phase 3 — Wraith Surface Demo

**Goal:** rebuild one real Wraith surface in Otoe and compare maintainability.

This is the first product milestone. If this phase does not make Wraith feel materially better, Otoe is not succeeding, even if the internals are elegant.

### Scope

- Build a standalone Otoe demo of:
  - app shell
  - top bar
  - status bar
  - `ArsenalView`
  - mission cards
  - search
  - tags
  - pagination
  - empty/loading states
- Use Wraith-like fixture data first.
- Add an optional adapter to read real Wraith mission registry data once the standalone demo is stable.
- Compare against current Kivy implementation:
  - time to implement the same non-trivial UI change
  - files touched for that change
  - tests required to validate the change
  - regressions or visual breakage introduced
  - manual mutation points
  - number of explicit bindings
  - number of custom redraw handlers
  - lines of UI code as a secondary metric only
  - test readability
- Run at least two change benchmarks against both implementations:
  - add or modify a meaningful `ArsenalView` filter or visibility rule
  - add a new mission-card state, top-bar indicator, or status treatment

### Exit Criteria

- `ArsenalView` behavior matches Wraith's current contract.
- UI code is materially smaller and clearer than the Kivy version.
- Non-trivial UI changes are materially faster in Otoe than in Kivy, with fewer mutation points and clearer tests.
- No screen-level canvas/redraw code is needed.
- Tests can assert state and rendered structure without booting the full app.

---

## Phase 4 — Developer Experience

**Goal:** make Otoe pleasant and reliable enough for repeated app development.

This phase is where Otoe starts becoming more than a Wraith support library. The target is a small but coherent framework surface that another Python desktop app could use without knowing Wraith exists.

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
  - Wraith migration examples
  - component cookbook
  - styling subset
  - event signatures
- Dev server or preview runner.
- Snapshot testing for mounted trees.
- Optional watch mode for examples.
- Example corpus:
  - concise idiomatic components
  - bad-to-good Kivy migration examples
  - Wraith case-study examples

### Exit Criteria

- A developer can build a small app without reading the internals.
- Type checking catches common widget mistakes.
- Error messages point to the component and prop/event that caused the issue.

---

## Phase 5 — Wraith Migration Option

**Goal:** decide whether Otoe should become a real Wraith UI dependency.

### Scope

- Do not migrate Wraith wholesale.
- Pick one low-risk Wraith surface after the standalone Otoe demo proves the UI/runtime model.
- Keep service/runtime/data boundaries unchanged.
- Build an adapter that lets Otoe screens consume Wraith services without importing Kivy.
- Run Otoe and Kivy surfaces side by side where possible.
- Preserve Wraith's operational behavior and tests.

### Exit Criteria

- One Wraith surface can be implemented in Otoe without weakening runtime safety.
- The migration reduces maintenance burden enough to justify dependency risk.
- Wraith can still ship without Otoe if Otoe is not ready.

---

## Phase 6 — Optional Framework Extraction

**Goal:** decide whether Otoe should become a reusable public or semi-public framework.

### Scope

- Keep Wraith as the flagship app and regression suite.
- Remove accidental Wraith assumptions from public APIs.
- Stabilize package structure and import paths.
- Write non-Wraith examples:
  - dashboard app
  - settings/admin app
  - local database CRUD app
  - hardware/status monitor
- Optionally test AI-assisted code generation against the documented examples. This is validation of API shape, not a core product promise.
- Define compatibility policy.
- Decide whether the project is personal-only, private reusable, or public.

### Exit Criteria

- At least three non-Wraith examples can be built without new framework primitives.
- Public docs explain Otoe without referencing Wraith as required context.
- The framework remains good for Wraith after generalization.
- The API feels like a Python-native relative of React/Solid, not a clone and not a Kivy wrapper.
- LLM-generated examples, if tested, follow the schema/event/reactivity rules without special prompting.

---

## Non-Goals For Now

- No JSX/transpiler in Phase 1.
- No full Wraith rewrite until one Otoe surface proves better maintainability and equivalent behavior.
- No generic virtual DOM.
- No event bubbling in Phase 1.
- No broad Tailwind clone before a small utility subset works.
- No custom animation system before layout, input, and lifecycle are stable.
- No public branding push before a Wraith-shaped visual demo exists.
- No public framework promises until Wraith proves the core under real use.

---

## Immediate Next Actions

1. Review `preview/wraith.html`.
2. Decide whether the next slice is static visual polish or a thin interactive backend.
3. If static polish wins, generate preview HTML from `examples.wraith.preview` instead of maintaining the convenience artifact by hand.
