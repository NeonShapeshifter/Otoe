# Otoe Roadmap

**Status:** post-v0.1.7 workshop hardening; backend capability gates, bundle hermeticity, dependency audit contract, namespace runtime discovery, RenderTree validation hardening, experimental external Path0 JSON runner, first backend package manifest, and productized Portable Core UI/native layout boundaries
**Updated:** June 10, 2026
**Current baseline:** 752 tests passing, 3 skipped when optional `mypy`/Pillow dependencies are unavailable
**Reference validation surfaces:** native task board, native window demo, UI kit, SaaS preview, utility ops console, hardware control panel, local admin/settings console, data workflow console, Wraith Mission Exec preview

---

## Product Thesis

Otoe is an experimental Python UI framework for building professional desktop-style interfaces with component functions, reactive state, deterministic events, and renderer boundaries that can move beyond HTML previews.

The project is framework-first. Case studies such as Wraith and SaaS previews are validation pressure, not product ownership. They prove whether the API can support dense operational UI, softer dashboard UI, overlays, commands, keyboard handling, and app-shaped state without coupling the core runtime to one application.

The current technical question is no longer whether components, signals, control flow, live previews, headless rendering, and an optional native window smoke can work. They do. The next question is how to turn the proven renderer boundary into repeatable developer workflows and documentation, while future backend candidates remain behind the small adapter contract.

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
| 2B | Renderer Backend Hardening | Done for v0.1.1 | Renderer split, executable support matrices, ADRs, layout policy, overflow policy, API boundary, backend adapter interface, Tk Canvas paint/text/scale proof, stack hardening, backend-replay acceptance, and native diagnostics exist. |
| 3 | Interactive Native Demo | Done | `NativeWindowDriver`, optional Tk wrapper, native window demo, and manual Tk launch smoke are covered; Tk windows now show readable scaled Canvas text while PNG output remains marker-level. |
| 4 | Developer Experience | Done for v0.1.2; maintenance as needed | Docs, diagnostics, stubs, CLI, and app authoring ergonomics have a usable baseline. |
| 5 | Professional UI Kit and Reference Apps | Active | Reference apps, shared UI helpers, and preview theme extraction are the current product-shape validation surface. |
| 6 | Optional Framework Extraction | Planned | Decide whether Otoe becomes a reusable public or semi-public framework. |

### Low-Level Build Direction

Otoe should stay CSS-facing for developer ergonomics without becoming
browser-CSS-powered on constrained targets. `ADR-018` defines the accepted
offline profile planner: `otoe plan`, audit-only `otoe deps`, and the first
`otoe build --profile cage` manifest slice should compile portable styles,
backend selection, and dependency metadata before hardware deployment. Asset,
local target module/package, namespace package target, static local import, and
explicit app runtime file copying now exist as the first file policy. The first
native framework/runtime file copy policy is recorded in `frameworkFiles`.
The bundle now includes a generated `otoe-run.py` integrity verify, load/check,
layout/paint dry-run, and headless PNG entry, plus optional `otoe build
--validate` runner checks.
`otoe plan`, `otoe build`, and `otoe-styles.json` now record a backend
capability profile. The current default is `native-python` (`native` remains an
alias for existing profile files), and the plan artifact records style, widget,
input, and renderer-boundary capability maps so future hardware/backend
candidates can declare their own support surface instead of inheriting one
global native matrix.
Profiles and CLI flags can also attach backend readiness/requirements JSON as a
coverage gate; `otoe plan` reports `backendCoverage`, and `otoe build` writes
`otoe-backend-coverage.json` before refusing manifests for incomplete backend
coverage. Bundle runner verification now rejects backend coverage artifacts
whose `evidenceMap` no longer traces exercised claims back to source/gate and
runtime style proof. `otoe backend-coverage --audit` exposes that same
traceability as a human-readable candidate review report.
`otoe-styles.json` now records compiled class styles and low-level `styleOps`
with the selected capability profile. Runner PNG output rehydrates bundled
styles from that primitive stream instead of workspace CSS, while the current
Python native renderer still receives a `StyleSheet` internally. `RenderTree`
IR v0 now gives backend candidates a mounted-tree boundary with stable `For`
keys, normalized props/events/state, and `ResolvedStyleMap` values rehydrated
from `styleOps` before the renderer. Path0 candidates now expose
`RenderTreeRendererCandidate` so `layout_render_tree(...)` can consume that
resolved IR directly without `FakeWidget`, `MountedNode`, or `StyleSheet` as
the renderer input, and readiness evidence now requires a traced `renderTree`
layout boundary call plus `styleOps`/`RenderTree` style match proof before
`path0RenderTreeEvidence` can pass. It is the first renderer-side IR boundary,
not yet a stable Skia/Taffy/Qt ABI.
`validate_render_tree(...)` and
`assert_render_tree_valid(...)` now reject malformed `RenderTree` IR before
Path0 layout/paint work starts, including boolean schema/path values and empty
identity/event strings, and `render_tree_from_dict(...)` makes the same IR
consumable from serialized JSON artifacts. `load_render_tree_artifact(...)`
and `--render-tree-artifact` now let Path0/readiness render explicit
`RenderTree` JSON files without remounting Otoe targets. Backend readiness now
includes a `RenderTree` replay gate and
checked-in fixture for minimal, task board, keyed reorder, and `Show` branch
cases, and `--bundle` can verify the offline bundle, load the manifest target,
and include an artifact-backed `RenderTree` target in readiness.
`examples.native.path0_external_backend` is the first out-of-process Path0
runner: it consumes serialized `RenderTree` JSON, optionally records
`otoe-styles.json` styleOps metadata, emits schema-versioned layout/paint JSON
outputs, and rejects unsupported widget names instead of hiding them behind a
generic container fallback. This proves the JSON artifact surface is usable
outside the mounted-tree renderer path. `--external-path0-backend` can now bind
that subprocess report into backend readiness and coverage trace as optional
evidence, with validation for process exit, output hashes, semantic shape, and
`renderTreeHash` identity. The runner also has the first
`backend-package-manifest`, and `otoe backend-package` can materialize a hashed
`backend-package.json` descriptor plus declared runner files. Build profiles can
also declare `[backend.package].manifest` so bundles copy that package under
`backend/<name>/` as hash-checked artifacts. Generated bundle runners now also
check the package descriptor's internal file hashes and run a minimal
`--backend-package-check` Path0 JSON-in/JSON-out smoke from inside the bundle.
Builds now also write `otoe-render-tree.json`, and packaged Path0 external
backends can be checked against the app-shaped bundled RenderTree and
`otoe-styles.json` through `--external-backend-check`; `--verify` runs that
check when a backend package is present. Builds with a backend package also
persist that app-shaped run as `otoe-path0-external-backend.json`, and generated
runners verify the report against package identity, RenderTree hash, StyleOps
hash, source binding, and output hashes. That verification lives in copied
runtime helper code instead of expanding the generated runner template further.
It is still an experimental Path0 runner rather than the final external backend
ABI.
The backend-candidate styleOps replay now also covers the real bundle path:
`otoe build --validate`, `--bundle dist/...` runner verification, manifest style
artifact discovery, and styleOps replay from the generated bundle.
Profile `[styles].safelist` now lets the build compile dynamic state classes
that do not appear in the first mounted render, while arbitrary runtime-built
class names remain outside the hardware/cage contract.
`otoe plan` and `otoe build` now also statically extract literal class tokens
from local `className` expressions, including conditional literal branches used
by `class_names(...)`, before falling back to explicit safelists for arbitrary
string interpolation.
Dynamic `className` f-strings and string interpolation now produce plan
warnings with source file and line numbers so missing safelist edges are visible
before deployment.
The generated runner now rejects unsupported artifact schema versions before
verification, layout checks, PNG rendering, or packing.
Native bundle verification now enforces required manifest metadata: declared
bundle files need safe relative paths, size, lowercase SHA-256 hashes, unique
bundle paths, and the required `frameworkFiles` policy. Packable files under
`app/`, `assets/`, `backend/`, and `framework/` must be declared in the
manifest instead of leaking from dirty build directories, and a manifest cannot
omit framework runtime files needed by the selected backend. Dependency audits
also record audit-only runtime policy findings for visible stdlib network and
process usage; strict hardware profiles can raise those findings to errors
without pretending Otoe has a Python sandbox. Generated runners delegate
dependency audit/runtime policy verification to the copied `otoe.bundle_deps`
helper instead of carrying that logic inline.
`NATIVE_RENDERER_SPIKE.md` now names the executable native support matrix,
layout, window, closeout, and backend-candidate replay surfaces that must stay
aligned before backend replacement work starts.
The first backend-candidate skeleton now runs a recording adapter and a
no-window `HeadlessCandidateBackend` through the minimal replay and native task
board replay, then prints text or JSON acceptance reports without adding Skia,
Taffy, Tk, or another concrete backend dependency.
The current Python layout/paint/PNG path is now wrapped by the experimental
`NativeRendererBackend` SPI, so future renderer candidates can be injected into
`NativeSurface`, `NativeWindowDriver.from_target(...)`, `render_native_png(...)`,
and `run_native(...)` before any Skia/Taffy dependency lands.
The backend-candidate skeleton now includes a `RecordingRendererCandidate` and
renderer-candidate acceptance helper, proving the same minimal and task-board
replays can exercise an injected renderer backend and record layout, paint, and
PNG calls.
Those renderer replays now emit a schema-versioned JSON contract snapshot that
locks down SPI call sequence, layout boxes, paint commands, focus, visible text,
and clipping boundaries.
The renderer SPI is now split into layout, paint, and raster capabilities with a
composed backend helper, and the first partial candidate replaces only PNG
raster while leaving Python layout and paint intact.
The second partial candidate replaces paint command generation while preserving
Python layout and raster output, proving the painter can be swapped behind the
same acceptance replays.
The first layout-only candidate now proves widget paths, hit-tested clicks,
focus, text updates, scroll movement, and PNG output for the small replay, plus
static first-frame task-board layout and the interactive app-shaped task board
replay.
The first composed renderer-candidate acceptance now wires layout-only,
paint-only, and raster-only candidates through `ComposedNativeRendererBackend`,
then runs the interactive replays plus a PNG smoke to prove the split
capabilities can be mixed without collapsing back into one monolithic backend.
The composed renderer-candidate contract can now be emitted from the CLI with
`--composed-renderer-contract-json` and an explicit `--composed-renderer-png`
smoke artifact path.
Renderer contract commands now also support `--compact-contract`, producing a
smaller signature-and-hash artifact for candidate comparison without dumping
full layout and paint snapshots.
`otoe compare-contract` now compares expected and actual JSON contract artifacts
with deterministic JSON-pointer diffs and a machine-readable `--json` report,
giving future backend candidates a practical CI gate.
The first expected compact composed-renderer contract fixture now lives under
`examples/native/contracts/`, and the generated candidate contract is compared
against it in tests.
The backend-candidate skeleton can refresh contract fixtures with
`--contract-out`, keeping intentional fixture updates explicit and
redirection-free.
The first bundle-backed styleOps expected contract fixture now covers
`otoe build --validate` plus backend-candidate `--bundle` replay as the
hardware-style contract gate.
The backend-candidate styleOps contract now includes a capability audit that
summarizes applied layout/paint properties, declared omissions, unsupported
properties, and the replay requirements a backend must satisfy.
Renderer contract snapshots now include a widget/input capability audit that
summarizes widget types, input bindings, unsupported entries, and replay
requirements from the minimal and task-board frames.
The backend-candidate skeleton now emits `--backend-readiness-json`, combining
renderer replay, widget/input audit, StyleOps replay, style capability audit,
blockers, and replay requirements into one readiness report.
The skeleton entrypoint is now a compatibility facade over focused acceptance,
CLI dispatch, and command-handler modules, so backend-candidate tooling can keep
growing without turning the example entrypoint back into the contract itself.
The checked-in backend readiness fixture now locks that aggregate report as a
candidate-comparison gate alongside the renderer and StyleOps contract fixtures.
Backend candidates can now derive a coverage declaration from a backend
capability profile and emit `--backend-coverage-json`, so claimed widget,
input, style, and declared omission support is compared against the aggregate
readiness requirements without duplicating the support matrix by hand.
Strict backend-readiness evidence is now validated as part of coverage:
exercised groups must name their source and gate, gate references must be
passing, requirements-only JSON no longer counts as exercised evidence,
widget/input proofs must match the renderer capability audit, and style
evidence must include Path 0 runtime proof from `styleOps` with
layout/paint observation hashes for each property's declared support phase;
declared style omissions must not appear as runtime-applied layout/paint
evidence. Path 0 evidence must also include a traced `renderTree` layout
boundary proof, and coverage now has a first-class `rendererBoundaries` section
that requires `renderTreeLayout` and `paint` boundary proofs before those
claims count as exercised. `renderTreeLayout` proofs now also carry the input
`renderTreeHash`, so Path 0 and renderer-boundary evidence must trace to the
same `RenderTree` artifact before coverage counts the claim. Invalid evidence
groups no longer count toward
exercised/covered support totals, and coverage sections now include an
`evidenceMap` that traces each covered claim back to source/gate metadata,
renderer boundary proof, and runtime style hashes. The coverage artifact now
also carries a top-level `trace` summary for candidate scope, Path0 hashes, and
Path0 `semanticValidation`, and generated runners reject refreshed coverage
artifacts whose covered renderer-boundary proofs do not match that summary or
whose semantic summary is no longer passed with no errors.
Path0 readiness now also recomputes `semanticValidation` from layout/paint
output so duplicate layout paths, invalid bounds, and paint commands pointing
outside layout cannot pass by refreshing hashes.
Backend coverage reports now also summarize malformed evidence by blocker so
candidate audits distinguish invalid proof from missing support and unproven
profile claims.
Backend coverage now also rejects readiness-like payloads without the expected
schema/format contract and binds coverage declarations to
`readiness.candidate.backend`; generated bundle runners repeat that identity
check so packaged coverage cannot drift to a different backend name after
manifest hashes are refreshed.
Backend readiness, coverage evidence, and generated runners now require strict
`sha256:<64 lowercase hex>` hashes for trace, boundary, capability, and runtime
observation proofs.
Candidate-specific JSON capability profiles can run through the same gate
before they graduate into built-in profiles, and `otoe plan/build` now consume
those profiles so bundle artifacts use the same support source as coverage.
`otoe backend-profile` now exposes profile inspection and coverage declaration
generation in the core CLI.
`otoe backend-coverage` now compares backend profiles or declarations against
readiness requirements from core CLI, leaving renderer replay generation in the
native skeleton.
The native skeleton coverage flags are compatibility-only; new backend profile
and coverage artifacts are written through the core CLI.
Style IR validation now rejects malformed serialized value payloads across
compiled rules, direct widget styles, omitted declarations, and low-level
styleOps before backend candidates replay them.
`otoe compare-contract --ignore-path` can now ignore intentional
environment-specific JSON-pointer fields, such as a local PNG smoke filename,
without weakening the rest of the contract comparison.
`otoe pack` verifies those bundle files, rejects failing declared backend
coverage reports, requires top-level artifacts to be hash-covered, rejects
invalid core artifact status or runtime-install drift, preserves
`otoe-backend-coverage.json`, and creates a cache-free `.tar.gz` deployment
archive.
Runtime installs on the target device are a non-goal; no runtime dependency
installs should happen on hardware targets.

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

## Completed Interactive Milestone

### Phase 3 - Interactive Native Demo

**Status:** Done

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
- Phase 3 closeout coverage for driver-driven search, modal, shortcut, scroll,
  repeated stable frames, distinct frames, `run_native(...)` handoff, and no
  app-level renderer pipeline stitching.

Phase 3 is closed for this milestone. The current implementation proves the
path: an Otoe native surface can be driven through a window-facing driver,
opened through `run_native(...)`, refreshed through a Tk wrapper, and tested
headlessly. The default Tk wrapper now presents readable Canvas text and scales
the current surface for manual validation. The headless PNG path still uses
deterministic marker text.

#### Immediate Focus

The next work should converge instead of expanding the framework surface. After
the Phase 3 exit, avoid adding new UI primitives, new CLI commands, or production
backend claims unless they directly support the renderer/backend boundary.

The primary deliverable is one framework-neutral native app surface that can be
driven through `NativeWindowDriver`, opened through `run_native(...)`, tested
without an OS window, and documented without implying that Tk or PNG refresh is a
production backend.

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
- The top-level API clearly marks native/window/backend-adjacent APIs as
  experimental so they do not become accidental compatibility promises.

#### Current Exit Status

Closed:

- The native task board/window demo is driven through `NativeWindowDriver`.
- `run_native(...)` is covered without opening a real OS window.
- Button, input, modal, list, shortcut, scroll, and repeated-frame stability are covered by headless tests.
- App-level demo code uses `NativeSurface` instead of manually stitching mount, layout, paint, hit-testing, and rerender steps.
- Native/window/backend-adjacent exports are marked experimental through the API status boundary.
- Manual Tk launch smoke has been recorded from an uninstalled checkout with
  `PYTHONPATH=src:. python -m examples.native.window_demo --window`.

Remaining:

- Keep Tk documented as optional and non-production while backend adapter work is still undecided.
- Keep production-grade text shaping, font fallback, DPI, and rasterization
  deferred to the backend/text-rendering track.

---

## Current Technical Track

### Phase 2B - Renderer Backend Hardening

**Status:** Done for v0.1.1

**Goal:** make the native renderer contract smaller, clearer, and easier to replace before adopting a real layout, paint, or windowing backend.

This track is the closed `v0.1.1` baseline for future backend work. New backend experiments should reproduce the backend-replay acceptance surface first; near-term DX work should explain and exercise this boundary instead of expanding the public API.

#### Scope

- Split `src/otoe/native.py` into focused modules. **Done:**
  - layout
  - paint
  - hit-testing
  - surface
  - PNG/raster output
  - native errors/contracts
- Preserve the current public imports from `otoe.__init__`. **Done.**
- Make the renderer support matrix executable through tests and documented through `NATIVE_RENDERER_SPIKE.md`. **Done for native style, widget, and input categories.**
- Clarify which style properties are supported, ignored, rejected, or reserved. **Done for current native style subset.**
- Fix the roadmap language around layout: Otoe currently supports stack layout and dimensions, not full flex distribution. **Done.**
- Preserve widget/component debug context in renderer diagnostics. **Done for current layout, paint, strict style, PNG, surface input, and focus failures.**
- Define the next text-rendering plan. **Done in ADR-008:**
  - current marker text is deterministic, not real font rasterization
  - future backend needs text measurement, shaping, font selection, and DPI behavior
- Define accessibility metadata expectations from `LayoutBox` without implementing a full accessibility tree yet. **Done in ADR-009.**
- Define the native layout-hardening boundary before backend adapter work.
  **Done in ADR-013:**
  - next layout spike stays in Python
  - min constraints win over conflicting max constraints
  - initial `alignItems: center` and `justifyContent: center` support on
    `HStack`/`VStack`
  - Taffy/backend work waits until the Python contract is hardened
- Define the native overflow and clipping policy. **Done in ADR-014:**
  - normal containers do not clip overflow
  - overflow from normal containers remains paint-visible and hit-testable
  - `ScrollView` is the current clipping boundary for paint and hit testing
- Define the native backend adapter interface. **Done in ADR-015:**
  - `NativeBackendAdapter` receives a `NativeWindowDriver`
  - `run_native(..., backend=...)` accepts a registered backend name or adapter object
  - invalid backends fail before mounting the target
  - `"tk"` is registered through `TkNativeBackendAdapter`
- Add a Tk Canvas paint/text proof. **Done in ADR-016:**
  - manual Tk windows present `PaintCommand` rectangles and text on a Canvas
  - text commands become readable Tk text items
  - window resize/fullscreen scales geometry up to 2x, keeps fonts logical, and remaps pointer input
  - text commands use layout-box text width to avoid drawing across neighboring widgets
  - headless PNG output remains deterministic marker text
- Add the first post-release Python stack-alignment pass. **Done in ADR-017:**
  - `alignItems` on `HStack`/`VStack` supports `start`, `flex-start`,
    `center`, `end`, `flex-end`, and `stretch`
  - `justifyContent` on `HStack`/`VStack` supports `start`, `flex-start`,
    `center`, `end`, `flex-end`, `space-between`, `space-around`, and
    `space-evenly`
  - unsupported values and alignment on non-stack widgets still fail clearly
- Define the native layout v0/v1 product boundary. **Done in ADR-020:**
  - layout v0 remains Python stack layout
  - flex grow/shrink, wrapping, grid, absolute positioning, percentages, `auto`,
    and margin geometry remain outside the v0 contract
  - layout v1 requires a new decision plus compatibility and feature acceptance
    tests before adding or advertising a layout engine
- Add native layout dimension guardrails. **Done:**
  - negative `width`, `height`, `padding`, `gap`, and `fontSize` fail with
    component-aware `NativeLayoutError`
  - negative `ScrollView(scrollY=...)` clamps to zero before layout proceeds
- Add native strict-style diagnostics. **Done:**
  - missing stylesheet classes in native layout fail as component-aware
    `NativeLayoutError`
- Add a backend-replay acceptance surface. **Done:**
  - one framework-neutral app drives layout, painter order, focused input,
    shortcut dispatch, click hit-testing, controlled scroll, and frame refresh
    through `NativeWindowDriver` and `NativeSurface`
- Evaluate backend candidates only after the contract split is stable.

#### Exit Criteria

- Renderer internals are modular enough to replace layout or paint independently.
- Existing tests still pass through the same public API.
- Unsupported layout/style/text/input features fail or defer clearly.
- `NATIVE_RENDERER_SPIKE.md` matches the actual implementation.
- Future Taffy, Skia, or alternative backend work has a concrete contract to target.

#### Current Exit Status

Closed:

- Native renderer internals are split into focused modules while preserving the public imports.
- The support matrix is executable and documented for current widget, style, layout, input, and overflow behavior.
- ADR-008, ADR-009, ADR-012, ADR-013, ADR-014, ADR-015, ADR-016, ADR-017, and ADR-020 define text, accessibility, backend, layout, overflow, adapter, Tk Canvas proof, stack-alignment, and layout v0/v1 boundaries.
- Layout hardening has deterministic min/max constraints and a stack-only
  alignment subset covering start, center, end, stretch, space-between,
  space-around, and space-evenly.
- Native layout rejects negative dimensions before producing boxes, while
  preserving zero-clamp behavior for negative scroll offsets.
- Native strict stylesheet failures now include the component/widget context.
- Native paint and PNG diagnostics now fail early with surface or command-path
  context for invalid backgrounds, command kinds, and command colors.
- `NativeSurface` input/focus failures now include the component/widget context
  and target path for non-input, disabled, or non-focusable widgets.
- `NativeSurface` focus hit-testing now uses the same depth plus paint/tree-order
  tie-breaker as click dispatch.
- Native hit testing now has deterministic paint/tree-order tie breaking for
  overlapping boxes.
- Native paint command emission has executable painter-order coverage, matching
  hit-test tie breaking.
- The backend-replay acceptance test exercises the driver/surface contract end
  to end without requiring an OS window.
- `ScrollView` is the current clipping boundary for paint and hit-testing; normal containers intentionally do not clip overflow.
- `NativeBackendAdapter`, `TkNativeBackendAdapter`, `native_backend_adapter(...)`, and `native_backend_names()` make backend selection executable.
- Tk Canvas presentation now supports geometry scale-to-fit capped at 2x with logical font sizes and pointer/wheel coordinate mapping back to logical native coordinates.
- Native task board fixed columns fit inside the `ScrollView`, with executable coverage to prevent row overflow regressions.

Remaining:

- Keep the backend-replay acceptance surface small while evaluating future
  layout, paint, or windowing backend candidates.
- Move near-term work to Phase 4 docs, diagnostics, and command ergonomics
  unless a backend candidate starts.

---

## Phase 4 - Developer Experience

**Status:** Done for v0.1.2

**Goal:** make Otoe pleasant and reliable enough for repeated app development.

### Scope

- Typed widget stubs and better editor support. **Expanded with PEP 561 marker,
  core widget/control-flow stubs, current UI component/model stubs, and mypy
  smoke coverage for valid usage plus common mistakes.**
- Better diagnostics:
  - unknown prop **Done with widget/component context and known prop list**
  - wrong event name **Done with widget/component context, known event signatures, and a specific error type**
  - wrong handler arity **Done with widget/event/component context and a specific error type**
  - disposed reactive read **Done for computed values**
  - mutation during mount **Done for subscribed-signal mutation during component render**
  - renderer unsupported feature errors with component context where possible **Done for native layout, paint, and PNG writer diagnostics**
- Documentation:
  - mental model **Done for current runtime and renderer boundaries**
  - component cookbook **Done for current app-state and renderer recipes**
  - widget contracts **Done for core widgets, control nodes, and current UI components**
  - style subset **Done for parser, HTML, and native support matrix**
  - native renderer subset **Done through `NATIVE_RENDERER_SPIKE.md` plus
    workflow/testing/style guides**
  - native workflow guide **Done for current HTML/native/window paths**
  - event signatures **Done for built-in widgets and current UI callback surface**
- CLI:
  - `otoe dev` **Done for app objects/factories, CSS serving, root classes, and CLI validation; reload semantics deferred**
  - `otoe render` **Done for HTML/native output paths, CSS input, and strict-style control**
  - `otoe check` **Done for compile checks, optional pytest, custom paths, and pytest args**
  - `otoe new` **Done for minimal renderable app scaffolds with optional CSS**
- Snapshot and renderer testing guides. **Done for current snapshot, HTML,
  native surface, window driver, PNG, and backend acceptance paths.**
- Example corpus:
  - concise idiomatic components **Indexed in `EXAMPLES_GUIDE.md`**
  - native examples **Indexed in `EXAMPLES_GUIDE.md`**
  - HTML preview examples **Indexed in `EXAMPLES_GUIDE.md`**
  - case-study examples **Indexed in `EXAMPLES_GUIDE.md`**

Phase 4 should not outrun the renderer contract. DX work is highest value when
it explains or tests a boundary that has already been proven by the native demo.

### Exit Criteria

- A developer can build a small app without reading internals.
- Type checking catches common widget mistakes.
- Error messages point to the component, prop, event, or renderer feature that caused the issue.
- The docs explain Otoe without requiring Wraith context.

---

## Phase 5 - Professional UI Kit and Reference Apps

**Status:** Active after v0.1.3; initial reference-app shape landed

**Goal:** make Otoe useful for professional Python apps beyond the author's
private projects while keeping the author as the primary customer.

### Scope

- Keep examples framework-neutral unless they are explicitly case studies.
- Build reference apps that look and feel production-shaped, not toy demos.
- Continue from the professional hardware/control-panel reference app backed by a
  fake provider that can later be swapped for serial, USB, GPIO, SQLite, or a
  local service adapter.
- Add a local admin/settings reference app with editable provider-backed state,
  validation, access controls, and audit history.
- Add a data/table workflow reference app with filtering, row selection, guarded
  bulk actions, and workflow history.
- Improve design-system defaults: variants, tone, spacing, tables, cards,
  shell navigation, command surfaces, settings, telemetry, and status patterns.
- Serve shared reference-app preview CSS explicitly for both static and live
  previews before moving more common styling into the theme layer.
- Keep extracting proven shared preview defaults only after at least two
  reference apps repeat the same selector shape.
- Keep Wraith as pressure, not the next migration target, until a stronger
  layout/paint/window backend exists.
- Preserve the public API's ability to serve users outside the author's own
  projects.

### Current Exit Status

Closed for the first Phase 5 pass:

- Hardware/control panel, local admin/settings, and data/table workflow
  reference apps exist with provider or adapter boundaries.
- Reference apps cover static preview, live preview, provider behavior, guarded
  actions, alternate states, and feedback rendering.
- `SectionHeader`, `EmptyState`, and `FeedbackToast` are extracted into
  `otoe.ui` after appearing across multiple reference apps.
- Static and live previews can serve `reference_theme.css` before app-specific
  CSS, and the shared theme now owns base Otoe selectors, tone variants, and the
  extracted helper styling.

Remaining:

- Do not keep expanding CSS until a repeated app shell/nav/table shape proves it
  needs extraction.
- Use these reference apps as acceptance pressure for the next backend-candidate
  evaluation.

### Exit Criteria

- A new user can build a polished small app from docs and examples without
  reading internals.
- At least three reference apps cover distinct professional app shapes:
  hardware/control panel, local admin/settings, and data/table workflow.
- Reference apps use explicit provider or adapter boundaries instead of global
  fixture data embedded directly in components.
- The UI kit has enough defaults and variants to feel professional before a
  custom stylesheet is written.

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
- No browser CSS engine or runtime dependency installer inside hardware/cage
  targets.
- No custom animation system before layout, input, lifecycle, and renderer invalidation are stable.
- No public branding push before the native demo is credible.
- No public framework stability promises before native layout, paint, input, diagnostics, and backend boundaries are proven.
- No production desktop backend claims for the Tk wrapper.

---

## Immediate Next Actions

1. Keep backend-candidate acceptance coverage anchored on the existing
   `NativeSurface`, `NativeWindowDriver`, native task board replay, and fake
   adapter replay before adding Taffy, Skia, or another backend; use
   `examples/native/backend_candidate_skeleton.py` as the no-dependency
   candidate starting point.
2. Expand the first offline profile/build planner slice from `ADR-018`: keep
   `otoe plan --json/--out`, audit-only `otoe deps`, and `otoe.profile.toml` as
   build inputs, keep `otoe build` manifest-first, and harden the native
   `frameworkFiles` policy plus runtime policy audit while preserving the no runtime dependency installs rule for hardware targets.
3. Keep `NATIVE_RENDERER_SPIKE.md` aligned with the executable support matrices
   and backend-candidate replay surfaces before any backend implementation
   claims parity.
4. Keep `NATIVE_WORKFLOWS.md` aligned whenever render paths or backend adapter
   semantics change.
5. Keep Phase 5 CSS extraction focused on portable utility/style-planner needs
   instead of broad browser CSS parity.
