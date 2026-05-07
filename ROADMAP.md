# Otoe Roadmap

**Status:** Phase 3 started / renderer hardening and DX diagnostics started
**Updated:** May 7, 2026
**Current baseline:** 220 tests passing
**Reference validation surfaces:** native task board, native window demo, UI kit, SaaS preview, Wraith Mission Exec preview

---

## Product Thesis

Otoe is an experimental Python UI framework for building professional desktop-style interfaces with component functions, reactive state, deterministic events, and renderer boundaries that can move beyond HTML previews.

The project is framework-first. Case studies such as Wraith and SaaS previews are validation pressure, not product ownership. They prove whether the API can support dense operational UI, softer dashboard UI, overlays, commands, keyboard handling, and app-shaped state without coupling the core runtime to one application.

The current technical question is no longer whether components, signals, control flow, live previews, and headless rendering can work. They do. The next question is whether Otoe can turn the headless renderer and optional window wrapper into a coherent native framework demo while keeping the renderer contract small enough to replace the backend later.

---

## Roadmap Principles

1. **Professional framework first.** Otoe's core API should stand on its own.
2. **Case-study-shaped, not case-study-coupled.** Wraith, SaaS, and framework-neutral examples should pressure-test the API without leaking app assumptions into the runtime.
3. **Runtime before syntax sugar.** Signals, owners, lifecycle, events, `Show`, `For`, batching, and renderer boundaries matter more than authoring shortcuts.
4. **Deterministic widget contracts.** Widgets declare `props`, `events`, and optional `primary_prop`; unknown props are errors.
5. **No hidden event magic.** Handlers are classified by widget schema before data-prop reactivity.
6. **Renderer boundary before renderer lock-in.** Public APIs describe layout, paint, input, and accessibility contracts; Taffy, Skia, Tk, or other backends are implementation candidates.
7. **Migration is earned later.** Otoe should prove native layout, paint, input, diagnostics, and maintainability before replacing any production app surface.

---

## Phase Summary

| Phase | Name | Status | Meaning |
| --- | --- | --- | --- |
| 0 | Case Study and First Slice | Done | Architecture and validation direction are established. |
| 1 | Pure Python Runtime Core | Done | Core reactivity, components, mounting, lifecycle, events, control flow, batching, and tests are implemented. |
| 2A | Headless Native Renderer Spike | Done | Otoe trees can produce deterministic layout, paint commands, PNG output, hit-tested input, focus, keyboard, text input, and scroll in tests. |
| 2B | Renderer Backend Hardening | Started | Split and harden the native renderer contract before choosing real layout/paint/window backends. |
| 3 | Interactive Native Demo | Started | `NativeWindowDriver`, optional Tk wrapper, and native window demo exist; the demo still needs framework-level polish and backend contract clarity. |
| 4 | Developer Experience | Started | Improve docs, diagnostics, stubs, CLI, and app authoring ergonomics. |
| 5 | Case Study Migration Option | Planned | Decide whether one real app surface should adopt Otoe. |
| 6 | Optional Framework Extraction | Planned | Decide whether Otoe becomes a reusable public or semi-public framework. |

---

## Completed Milestones

### Phase 0 - Case Study and First Slice

**Status:** Done

Otoe has enough examples and design notes to justify the framework direction:

- ADRs cover component model, control flow, scheduling, template syntax, style system, and native renderer boundary.
- Wraith-shaped examples validate dense operational UI.
- SaaS-shaped examples validate calmer product dashboard UI.
- UI kit examples validate primitives outside one app shape.
- Framework-neutral native examples validate renderer work without Wraith coupling.

The useful conclusion from Phase 0 is that Otoe should stay framework-first, with case studies as regression pressure.

### Phase 1 - Pure Python Runtime Core

**Status:** Done

Implemented and tested:

- `Node` descriptors and widget call syntax.
- Widget schemas with `props`, `events`, and `primary_prop`.
- Unknown prop, duplicate primary prop, and invalid event errors.
- `signal`, `computed`, `effect`, dependency tracking, cleanup, and batching.
- Component ownership with `on_mount`, `on_cleanup`, and automatic disposal.
- Fake-widget mounting with static props, reactive props, event registration, child trees, and unmount cleanup.
- Sync and async event dispatch.
- `Show` and keyed `For` control flow.
- Deterministic snapshots and HTML rendering.

Phase 1 is considered closed unless future renderer work reveals a core contract bug.

### Phase 2A - Headless Native Renderer Spike

**Status:** Done

Implemented and tested:

- `layout_native(...)` with deterministic `LayoutBox` output.
- `paint_native(...)` with deterministic `PaintCommand` output.
- Standard-library PNG output.
- `NativeSurface` as the framework-facing headless surface.
- Coordinate hit-testing and click dispatch through Otoe events.
- Lazy surface refresh after external reactive prop and control-flow updates.
- Native focus, autofocus, blur/focus events, Tab traversal, button submit keys, and shortcut payloads.
- Controlled native input text dispatch.
- Controlled `ScrollView(scrollY=..., onScroll=...)`, wheel dispatch, scroll clamping, clipped paint, and clipped hit-testing.
- Disabled control semantics for focus and click.
- Native task board demo with shell, search, filtered rows, empty state, modal state, shortcuts, controlled input, and PNG frames.

The Phase 2A success criterion is satisfied: an Otoe tree can leave the HTML preview path and produce layout, pixels, input dispatch, and rerendered state in a headless native pipeline.

---

## Current Milestone

### Phase 3 - Interactive Native Demo

**Status:** Started

**Goal:** turn the headless renderer spike into a small interactive native app that feels like a framework demo rather than a screenshot generator.

Already landed:

- `NativeWindowDriver` as the testable window-facing wrapper over `NativeSurface`.
- `NativeWindowEvent` for high-level click, wheel, key-down, key-input, and text-input dispatch.
- `TkNativeWindow` as an optional local manual-test wrapper.
- `run_native(...)` as the experimental framework-facing native entry point.
- Native window demo frame generation through the task board surface.
- Driver-level key editing for printable text, Backspace, Delete, Enter/Tab fallback, and shortcut fallback.
- Driver-level wheel events for controlled scroll views.
- Native task board behavior parity tests against the HTML render path for text
  content and controlled input values after native event dispatch.

Phase 3 is not complete yet. The current implementation proves the path, but it is still an experimental wrapper over a headless surface.

#### Scope

- Keep the demo framework-neutral.
- Make the native task board/window demo the primary Phase 3 validation surface.
- Support click, keyboard, focus, text input, shortcuts, modal state, list filtering, and scroll through the same Otoe event system.
- Compare behavior against the HTML preview only for state/event parity, not exact visuals.
- Use `ADR-007` as the backend ownership note for `run_native(...)`, event loop ownership, window lifetime, and future backend replacement.
- Keep Tk explicitly optional and non-production.

#### Exit Criteria

- The demo runs outside a browser through `run_native(...)`.
- Button, input, modal, list, shortcut, and scroll interactions work through Otoe events.
- Tests can assert state, focus, rendered structure, and distinct frames without opening a real window.
- No app-level code manually stitches mount, layout, paint, hit-testing, and rerender.
- Backend-specific details remain outside component code.
- The remaining native limitations are documented clearly enough that future backend work has a stable target.

---

## Next Technical Track

### Phase 2B - Renderer Backend Hardening

**Status:** Started

**Goal:** make the native renderer contract smaller, clearer, and easier to replace before adopting a real layout, paint, or windowing backend.

This track can run alongside Phase 3, but it should not expand the public API until the current contract is cleaned up.

#### Scope

- Split `src/otoe/native.py` into focused modules. **Done:**
  - layout
  - paint
  - hit-testing
  - surface
  - PNG/raster output
  - native errors/contracts
- Preserve the current public imports from `otoe.__init__`. **Done.**
- Make the renderer support matrix executable through tests and documented through `NATIVE_RENDERER_SPIKE.md`. **Started for native style, widget, and input categories.**
- Clarify which style properties are supported, ignored, rejected, or reserved. **Done for current native style subset.**
- Fix the roadmap language around layout: Otoe currently supports stack layout and dimensions, not full flex distribution. **Done.**
- Preserve widget/component debug context in `LayoutBox` for renderer diagnostics. **Started for layout and paint errors.**
- Define the next text-rendering plan. **Done in ADR-008:**
  - current marker text is deterministic, not real font rasterization
  - future backend needs text measurement, shaping, font selection, and DPI behavior
- Define accessibility metadata expectations from `LayoutBox` without implementing a full accessibility tree yet. **Done in ADR-009.**
- Evaluate backend candidates only after the contract split is stable.

#### Exit Criteria

- Renderer internals are modular enough to replace layout or paint independently.
- Existing tests still pass through the same public API.
- Unsupported layout/style/text/input features fail or defer clearly.
- `NATIVE_RENDERER_SPIKE.md` matches the actual implementation.
- Future Taffy, Skia, or alternative backend work has a concrete contract to target.

---

## Phase 4 - Developer Experience

**Status:** Started

**Goal:** make Otoe pleasant and reliable enough for repeated app development.

### Scope

- Typed widget stubs and better editor support.
- Better diagnostics:
  - unknown prop
  - wrong event name **Started with widget/component context**
  - wrong handler arity **Started with widget/event/component context**
  - disposed reactive read **Done for computed values**
  - mutation during mount **Done for subscribed-signal mutation during component render**
  - renderer unsupported feature errors with component context where possible **Started**
- Documentation:
  - mental model
  - component cookbook
  - widget contracts
  - style subset
  - native renderer subset
  - event signatures **Done for built-in widgets and current UI callback surface**
- CLI:
  - `otoe dev` **Started through `python -m otoe dev MODULE:APP` and the installed `otoe` console script**
  - `otoe render` **Started through HTML and native PNG output paths**
  - `otoe check` **Started through `python -m otoe check` and the installed `otoe` console script**
  - optional `otoe new`
- Snapshot and renderer testing guides.
- Example corpus:
  - concise idiomatic components
  - native examples
  - HTML preview examples
  - case-study examples

### Exit Criteria

- A developer can build a small app without reading internals.
- Type checking catches common widget mistakes.
- Error messages point to the component, prop, event, or renderer feature that caused the issue.
- The docs explain Otoe without requiring Wraith context.

---

## Phase 5 - Case Study Migration Option

**Status:** Planned

**Goal:** decide whether Otoe should become a real dependency for one existing app surface.

### Scope

- Do not migrate any app wholesale.
- Pick one low-risk surface only after the standalone native demo proves the runtime and renderer model.
- Keep service/runtime/data boundaries unchanged.
- Build an adapter that lets Otoe screens consume app services without importing the legacy UI backend.
- Run Otoe and legacy surfaces side by side where possible.
- Preserve operational behavior and tests.

### Exit Criteria

- One real app surface can be implemented in Otoe without weakening runtime safety.
- The migration reduces maintenance burden enough to justify dependency risk.
- The app can still ship without Otoe if Otoe is not ready.

---

## Phase 6 - Optional Framework Extraction

**Status:** Planned

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
- Define compatibility policy.
- Decide whether the project is personal-only, private reusable, or public.
- Optionally test AI-assisted code generation against documented examples. This validates API shape; it is not a core product promise.

### Exit Criteria

- At least three framework-neutral examples can be built without new framework primitives.
- Public docs explain Otoe without referencing any one case study as required context.
- The framework remains useful for the original case studies after generalization.
- The API feels Python-native, not like a Kivy wrapper and not like a direct React clone.

---

## Non-Goals For Now

- No production app rewrite before one Otoe surface proves better maintainability and equivalent behavior.
- No generic virtual DOM.
- No DOM-style event bubbling/capture before native input ownership is clearer.
- No broad Tailwind clone before the current style subset hardens.
- No custom animation system before layout, input, lifecycle, and renderer invalidation are stable.
- No public branding push before the native demo is credible.
- No public framework stability promises before native layout, paint, input, diagnostics, and backend boundaries are proven.
- No production desktop backend claims for the Tk wrapper.

---

## Immediate Next Actions

1. Decide whether `otoe dev` should accept app factories lazily per reload cycle.
2. Add first-class CLI help text examples if the command surface grows past these three commands.
3. Add a public native renderer status note that separates PNG preview support from production backend claims.
