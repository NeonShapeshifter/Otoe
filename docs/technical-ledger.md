# Technical Ledger

This ledger preserves the dense technical history that used to live in
`ROADMAP.md`. It is contributor-oriented. The short roadmap now lives at
[ROADMAP.md](../ROADMAP.md), and the product direction lives at
[Product North Star](product-north-star.md).

Otoe's technical work should support the product goal: a Python-first runtime
for local operational interfaces, with honest pre-alpha boundaries.

## Current Baseline

Status before the roadmap split: post-v0.1.8 workshop hardening. The test suite
is expected to pass locally; optional `mypy` and Pillow checks skip cleanly when
those dependencies are unavailable.

Reference validation surfaces include the native task board, native window
demo, UI kit, SaaS preview, utility ops console, hardware control panel, local
admin/settings console, data workflow console, Wraith input console, and Wraith
Mission Exec showcase.

## Low-Level Build Direction

Otoe should stay CSS-facing for developer ergonomics without becoming
browser-CSS-powered on constrained targets. `ADR-018` defines the accepted
offline profile planner: `otoe plan`, audit-only `otoe deps`, and the first
`otoe build --profile cage` manifest slice should compile portable styles,
backend selection, and dependency metadata before hardware deployment. Asset,
local target module/package, namespace package target, static local import, and
explicit app runtime file copying now exist as the first file policy. The first
native framework/runtime file copy policy is recorded in `frameworkFiles`.
Historical command landmarks for this track include `otoe plan --json/--out`,
`otoe.profile.toml`, manifest-first `otoe build --profile cage`, `otoe build
--validate`, `otoe pack`, `.tar.gz` packaging, and the no runtime dependency installs rule for hardware targets.

The bundle includes a generated `otoe-run.py` integrity verify, load/check,
layout/paint dry-run, and headless PNG entry, plus optional `otoe build
--validate` runner checks. `otoe plan`, `otoe build`, and `otoe-styles.json`
record a backend capability profile. The current default is `native-python`
(`native` remains an alias for existing profile files), and the plan artifact
records style, widget, input, and renderer-boundary capability maps so future
hardware/backend candidates can declare their own support surface instead of
inheriting one global native matrix.

Profiles and CLI flags can attach backend readiness/requirements JSON as a
coverage gate. `otoe plan` reports `backendCoverage`, and `otoe build` writes
`otoe-backend-coverage.json` before refusing manifests for incomplete backend
coverage. Bundle runner verification rejects backend coverage artifacts whose
`evidenceMap` no longer traces exercised claims back to source/gate and runtime
style proof. `otoe backend-coverage --audit` exposes that same traceability as a
human-readable candidate review report.

`otoe-styles.json` records compiled class styles and low-level `styleOps` with
the selected capability profile. Runner PNG output rehydrates bundled styles
from that primitive stream instead of workspace CSS, while the current Python
native renderer still receives a `StyleSheet` internally.

`RenderTree` IR v0 gives backend candidates a mounted-tree boundary with stable
`For` keys, normalized props/events/state, and `ResolvedStyleMap` values
rehydrated from `styleOps` before the renderer. Path0 candidates expose
`RenderTreeRendererCandidate` so `layout_render_tree(...)` can consume that
resolved IR directly without `FakeWidget`, `MountedNode`, or `StyleSheet` as
the renderer input. Readiness evidence requires a traced `renderTree` layout
boundary call plus `styleOps`/`RenderTree` style match proof before
`path0RenderTreeEvidence` can pass. This is the first renderer-side IR
boundary, not yet a stable Skia/Taffy/Qt ABI.

`validate_render_tree(...)` and `assert_render_tree_valid(...)` reject
malformed `RenderTree` IR before Path0 layout/paint work starts, including
boolean schema/path values and empty identity/event strings.
`render_tree_from_dict(...)` makes the same IR consumable from serialized JSON
artifacts. `load_render_tree_artifact(...)` and `--render-tree-artifact` let
Path0/readiness render explicit `RenderTree` JSON files without remounting Otoe
targets. Backend readiness includes a `RenderTree` replay gate and checked-in
fixtures for minimal, task board, keyed reorder, and `Show` branch cases.
`--bundle` can verify the offline bundle, load the manifest target, and include
an artifact-backed `RenderTree` target in readiness.

`examples.native.path0_external_backend` is the first out-of-process Path0
runner. It consumes serialized `RenderTree` JSON, optionally records
`otoe-styles.json` styleOps metadata, emits schema-versioned layout/paint JSON
outputs, and rejects unsupported widget names instead of hiding them behind a
generic container fallback. This proves the JSON artifact surface is usable
outside the mounted-tree renderer path.

`--external-path0-backend` binds that subprocess report into backend readiness
and coverage trace as optional evidence, with validation for process exit,
output hashes, semantic shape, and `renderTreeHash` identity. The runner also
has the first `backend-package-manifest`, and `otoe backend-package` can
materialize a hashed `backend-package.json` descriptor plus declared runner
files. Build profiles can declare `[backend.package].manifest` so bundles copy
that package under `backend/<name>/` as hash-checked artifacts.

Generated bundle runners check the package descriptor's internal file hashes
and run a minimal `--backend-package-check` Path0 JSON-in/JSON-out smoke from
inside the bundle. Builds write `otoe-render-tree.json`, and packaged Path0
external backends can be checked against the app-shaped bundled RenderTree and
`otoe-styles.json` through `--external-backend-check`; `--verify` runs that
check when a backend package is present.

Builds with a backend package persist that app-shaped run as
`otoe-path0-external-backend.json`, and generated runners verify the report
against package identity, RenderTree hash, StyleOps hash, source binding, and
output hashes. That verification lives in copied runtime helper code instead of
expanding the generated runner template further. It is still an experimental
Path0 runner rather than the final external backend ABI.

The backend-candidate styleOps replay covers the real bundle path:
`otoe build --validate`, `--bundle dist/...` runner verification, manifest style
artifact discovery, and styleOps replay from the generated bundle.

Profile `[styles].safelist` lets the build compile dynamic state classes that
do not appear in the first mounted render, while arbitrary runtime-built class
names remain outside the hardware/cage contract. `otoe plan` and `otoe build`
statically extract literal class tokens from local `className` expressions,
including conditional literal branches used by `class_names(...)`, before
falling back to explicit safelists for arbitrary string interpolation. Dynamic `className` f-strings and string interpolation produce plan warnings with
source file and line numbers so missing safelist edges are visible before
deployment.

The CSS parser remains intentionally narrow: single class selectors, selected
portable properties, simple tokens, and Style IR/styleOps output. A future
fuller CSS track should add a real parser, cascade, specificity, media queries,
pseudo-classes, inheritance, variables, and explicit portable/native layout
mapping without pretending constrained runtimes have a browser CSS engine.

The generated runner rejects unsupported artifact schema versions before
verification, layout checks, PNG rendering, or packing. Native bundle
verification enforces required manifest metadata: declared bundle files need
safe relative paths, size, lowercase SHA-256 hashes, unique bundle paths, and
the required `frameworkFiles` policy. Packable files under `app/`, `assets/`,
`backend/`, and `framework/` must be declared in the manifest instead of
leaking from dirty build directories, and a manifest cannot omit framework
runtime files needed by the selected backend.

Dependency audits record audit-only runtime policy findings for visible stdlib
network and process usage; strict hardware profiles can raise those findings to
errors without pretending Otoe has a Python sandbox. Generated runners delegate
dependency audit/runtime policy verification to the copied `otoe.bundle_deps`
helper instead of carrying that logic inline.

`otoe pack` verifies bundle files, rejects failing declared backend coverage
reports, requires top-level artifacts to be hash-covered, rejects invalid core
artifact status or runtime-install drift, preserves
`otoe-backend-coverage.json`, and creates a cache-free `.tar.gz` deployment
archive. Runtime installs on target devices are a non-goal; no runtime
dependency installs should happen on hardware targets.

## Native Renderer And Backend Ledger

`NATIVE_RENDERER_SPIKE.md` names the executable native support matrix, layout,
window, closeout, and backend-candidate replay surfaces that must stay aligned
before backend replacement work starts.

The current Python layout/paint/PNG path is wrapped by the experimental
`NativeRendererBackend` SPI, so future renderer candidates can be injected into
`NativeSurface`, `NativeWindowDriver.from_target(...)`,
`render_native_png(...)`, and `run_native(...)` before any Skia/Taffy
dependency lands.

The first backend-candidate skeleton runs a recording adapter and a no-window
`HeadlessCandidateBackend` through minimal replay and native task board replay,
then prints text or JSON acceptance reports without adding Skia, Taffy, Tk, or
another concrete backend dependency.

The backend-candidate skeleton includes a `RecordingRendererCandidate` and
renderer-candidate acceptance helper, proving the same minimal and task-board
replays can exercise an injected renderer backend and record layout, paint, and
PNG calls. Renderer replays emit schema-versioned JSON contract snapshots that
lock down SPI call sequence, layout boxes, paint commands, focus, visible text,
and clipping boundaries.

The renderer SPI is split into layout, paint, and raster capabilities with a
composed backend helper. Partial candidates have replaced only PNG raster,
paint command generation, and layout in isolation while preserving the other
Python-native stages. Composed renderer-candidate acceptance wires layout-only,
paint-only, and raster-only candidates through `ComposedNativeRendererBackend`,
then runs interactive replays plus a PNG smoke to prove split capabilities can
be mixed without collapsing back into one monolithic backend.

Renderer contract commands support:

- `--composed-renderer-contract-json`
- `--composed-renderer-png`
- `--compact-contract`
- `otoe compare-contract`
- `otoe compare-contract --ignore-path`
- `--contract-out` fixture refreshes in the backend-candidate skeleton

The first expected compact composed-renderer contract fixture lives under
`examples/native/contracts/`, and generated candidate contracts are compared
against it in tests.

The first bundle-backed styleOps expected contract fixture covers
`otoe build --validate` plus backend-candidate `--bundle` replay as the
hardware-style contract gate. The backend-candidate styleOps contract includes
a capability audit summarizing applied layout/paint properties, declared
omissions, unsupported properties, and replay requirements a backend must
satisfy.

Renderer contract snapshots include a widget/input capability audit summarizing
widget types, input bindings, unsupported entries, and replay requirements from
minimal and task-board frames.

The backend-candidate skeleton emits `--backend-readiness-json`, combining
renderer replay, widget/input audit, StyleOps replay, style capability audit,
blockers, and replay requirements into one readiness report. The skeleton
entrypoint is a compatibility facade over focused acceptance, CLI dispatch, and
command-handler modules, so backend-candidate tooling can grow without turning
the example entrypoint back into the contract itself. The checked-in backend
readiness fixture locks that aggregate report as a candidate-comparison gate
alongside renderer and StyleOps contract fixtures.

Backend candidates can derive a coverage declaration from a backend capability
profile and emit `--backend-coverage-json`, so claimed widget, input, style,
and declared omission support is compared against aggregate readiness
requirements without duplicating the support matrix by hand.

Strict backend-readiness evidence is validated as part of coverage: exercised
groups must name their source and gate, gate references must be passing,
requirements-only JSON no longer counts as exercised evidence, widget/input
proofs must match the renderer capability audit, and style evidence must
include Path 0 runtime proof from `styleOps` with layout/paint observation
hashes for each property's declared support phase. Declared style omissions
must not appear as runtime-applied layout/paint evidence.

Path 0 evidence must include a traced `renderTree` layout boundary proof, and
coverage has a first-class `rendererBoundaries` section that requires
`renderTreeLayout` and `paint` boundary proofs before those claims count as
exercised. `renderTreeLayout` proofs carry the input `renderTreeHash`, so Path0
and renderer-boundary evidence must trace to the same `RenderTree` artifact
before coverage counts the claim.
Strict backend-readiness evidence also records layout/paint observation hashes
for runtime Path0 proof, declared support phase, and declared style omissions
so runtime-applied layout/paint evidence cannot accidentally satisfy an
unsupported style claim.

Invalid evidence groups no longer count toward exercised/covered support
totals. Coverage sections include an `evidenceMap` that traces each covered
claim back to source/gate metadata, renderer boundary proof, and runtime style
hashes. The coverage artifact carries a top-level `trace` summary for candidate
scope, Path0 hashes, and Path0 `semanticValidation`; generated runners reject
refreshed coverage artifacts whose covered renderer-boundary proofs do not
match that summary or whose semantic summary is no longer passed with no
errors.

Path0 readiness recomputes `semanticValidation` from layout/paint output so
duplicate layout paths, invalid bounds, and paint commands pointing outside
layout cannot pass by refreshing hashes.

Backend coverage reports summarize malformed evidence by blocker so candidate
audits distinguish invalid proof from missing support and unproven profile
claims. Backend coverage rejects readiness-like payloads without the expected
schema/format contract and binds coverage declarations to
`readiness.candidate.backend`; generated bundle runners repeat that identity
check so packaged coverage cannot drift to a different backend name after
manifest hashes are refreshed.

Backend readiness, coverage evidence, and generated runners require strict
`sha256:<64 lowercase hex>` hashes for trace, boundary, capability, and runtime
observation proofs. Candidate-specific JSON capability profiles can run through
the same gate before they graduate into built-in profiles, and
`otoe plan/build` consume those profiles so bundle artifacts use the same
support source as coverage.

`otoe backend-profile` exposes profile inspection and coverage declaration
generation in the core CLI. `otoe backend-coverage` compares backend profiles
or declarations against readiness requirements from the core CLI, leaving
renderer replay generation in the native skeleton. Native skeleton coverage
flags are compatibility-only; new backend profile and coverage artifacts are
written through the core CLI.

Style IR validation rejects malformed serialized value payloads across compiled
rules, direct widget styles, omitted declarations, and low-level styleOps before
backend candidates replay them.

## Completed Technical Milestones

### Phase 0 - Case Study and First Slice

Architecture and validation direction were established. ADRs covered component
model, control flow, scheduling, template syntax, style system, and native
renderer boundary. Wraith-shaped examples validated dense operational UI,
SaaS-shaped examples validated calmer dashboard UI, UI kit examples validated
primitives outside one app shape, and framework-neutral native examples
validated renderer work without Wraith coupling.

### Phase 1 - Pure Python Runtime Core

Implemented and tested:

- `Node` descriptors and widget call syntax.
- Widget schemas with `props`, `events`, and `primary_prop`.
- Unknown prop, duplicate primary prop, and invalid event errors.
- `signal`, `computed`, `effect`, dependency tracking, cleanup, and batching.
- Component ownership with `on_mount`, `on_cleanup`, and automatic disposal.
- Fake-widget mounting with static props, reactive props, event registration,
  child trees, and unmount cleanup.
- Sync and async event dispatch.
- `Show` and keyed `For` control flow.
- Deterministic snapshots and HTML rendering.

Phase 1 is closed unless future renderer work reveals a core contract bug.

### Phase 2A - Headless Native Renderer Spike

Implemented and tested:

- `layout_native(...)` with deterministic `LayoutBox` output.
- `paint_native(...)` with deterministic `PaintCommand` output.
- Standard-library PNG output.
- `NativeSurface` as the framework-facing headless surface.
- Coordinate hit-testing and click dispatch through Otoe events.
- Lazy surface refresh after external reactive prop and control-flow updates.
- Native focus, autofocus, blur/focus events, Tab traversal, button submit
  keys, and shortcut payloads.
- Controlled native input text dispatch.
- Controlled `ScrollView(scrollY=..., onScroll=...)`, wheel dispatch, scroll
  clamping, clipped paint, and clipped hit-testing.
- Disabled control semantics for focus and click.
- Native task board demo with shell, search, filtered rows, empty state, modal
  state, shortcuts, controlled input, and PNG frames.

The Phase 2A success criterion is satisfied: an Otoe tree can leave the HTML
preview path and produce layout, pixels, input dispatch, and rerendered state in
a headless native pipeline.

### Phase 2B - Renderer Backend Hardening

Closed for v0.1.1. The track made the native renderer contract smaller,
clearer, and easier to replace before adopting a real layout, paint, or
windowing backend.

Closed work includes:

- Splitting renderer internals into focused layout, paint, hit-testing,
  surface, PNG/raster, and native error/contract modules while preserving
  public imports.
- Executable native support matrices for widget, style, layout, input, and
  overflow behavior.
- ADR-008, ADR-009, ADR-012, ADR-013, ADR-014, ADR-015, ADR-016, ADR-017, and
  ADR-020 for text, accessibility, backend, layout, overflow, adapter, Tk
  Canvas proof, stack alignment, and layout v0/v1 boundaries.
- Deterministic min/max constraints and stack-only alignment subset covering
  start, center, end, stretch, space-between, space-around, and space-evenly.
- Native layout rejection for negative dimensions while preserving zero-clamp
  behavior for negative scroll offsets.
- Component/widget context in native strict stylesheet, layout, paint, PNG,
  input, and focus failures.
- Deterministic paint/tree-order tie breaking for hit testing and paint command
  emission.
- Backend-replay acceptance through `NativeWindowDriver` and `NativeSurface`
  without requiring an OS window.
- `ScrollView` as the clipping boundary for paint and hit testing.
- `NativeBackendAdapter`, `TkNativeBackendAdapter`,
  `native_backend_adapter(...)`, and `native_backend_names()`.
- Tk Canvas geometry scale-to-fit capped at 2x with logical font sizes and
  pointer/wheel coordinate mapping back to logical native coordinates.

Remaining from this track: keep backend-replay small while evaluating future
layout, paint, or windowing backend candidates.

### Phase 3 - Interactive Native Demo

Closed. The goal was to turn the headless renderer spike into a small
interactive native app that feels like a framework demo rather than a
screenshot generator.

Landed:

- `NativeWindowDriver` as the testable window-facing wrapper over
  `NativeSurface`.
- `NativeWindowEvent` for high-level click, wheel, key-down, key-input, and
  text-input dispatch.
- `TkNativeWindow` as an optional local manual-test wrapper.
- `run_native(...)` as the experimental framework-facing native entry point.
- Native window demo frame generation through the task board surface.
- Driver-level key editing for printable text, Backspace, Delete, Enter/Tab
  fallback, and shortcut fallback.
- Driver-level wheel events for controlled scroll views.
- Native task board behavior parity tests against the HTML render path for text
  content and controlled input values after native event dispatch.
- Phase 3 closeout coverage for driver-driven search, modal, shortcut, scroll,
  repeated stable frames, distinct frames, `run_native(...)` handoff, and no
  app-level renderer pipeline stitching.

The current implementation proves that an Otoe native surface can be driven
through a window-facing driver, opened through `run_native(...)`, refreshed
through a Tk wrapper, and tested headlessly. Tk remains optional and
non-production.

### Phase 4 - Developer Experience

Closed for v0.1.2 and maintained as needed.

Landed:

- PEP 561 marker, widget/control-flow stubs, current UI component/model stubs,
  and mypy smoke coverage.
- Better diagnostics for unknown props, wrong event names, handler arity,
  disposed reactive reads, subscribed-signal mutation during render, and native
  renderer unsupported feature errors with component context where possible.
- Documentation for mental model, component cookbook, widget contracts, style
  subset, native renderer subset, native workflows, and event signatures.
- CLI baseline: `otoe dev`, `otoe render`, `otoe check`, and `otoe new`.
- Snapshot and renderer testing guides.
- Example corpus indexed in `EXAMPLES_GUIDE.md`.

### Phase 5 - Professional UI Kit And Reference Apps

Active product-shape validation.

Closed for the first Phase 5 pass:

- Hardware/control panel, local admin/settings, and data/table workflow
  reference apps exist with provider or adapter boundaries.
- Reference apps cover static preview, live preview, provider behavior, guarded
  actions, alternate states, and feedback rendering.
- `SectionHeader`, `EmptyState`, and `FeedbackToast` are extracted into
  `otoe.ui` after appearing across multiple reference apps.
- Static and live previews can serve `reference_theme.css` before app-specific
  CSS, and the shared theme owns base Otoe selectors, tone variants, and the
  extracted helper styling.
- Otoe preview gallery now leads with neutral Otoe surfaces and keeps Wraith as
  case-study evidence.

Remaining:

- Do not keep expanding CSS until a repeated app shell/nav/table shape proves it
  needs extraction.
- Use reference apps as acceptance pressure for backend-candidate evaluation,
  not as an excuse to move backend work back to the first app-author path.

### Phase 6 - Public Framework Extraction/Stabilization

Planned after Phase 5 product-shape validation.

The old question was whether Otoe should become public at all. The current
North Star is clearer: public framework extraction/stabilization remains
planned once the pre-alpha product surface is coherent. Future work should:

- keep case studies as regression suites;
- remove accidental app assumptions from public APIs;
- stabilize package structure and import paths;
- define a compatibility policy;
- preserve framework-neutral examples for dashboard, settings/admin, local
  data workflow, and hardware/status surfaces;
- optionally test AI-assisted code generation against documented examples as an
  API-shape check, not a product promise.
