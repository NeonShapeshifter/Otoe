# Native Workflow Guide

This guide explains which Otoe render path to use while the native renderer is
still experimental. The short rule: use HTML and live preview for app iteration;
use native surfaces and drivers to test the renderer contract; use
`run_native(...)` only for local manual smoke testing.

## Choosing A Path

| Need | Use | Why |
| --- | --- | --- |
| Static app markup or docs screenshots | `otoe render TARGET --out preview.html` | Fast HTML output for an importable `Node` or zero-argument app factory. |
| Interactive browser iteration | `otoe dev TARGET --port 8767` | Local live preview with browser events, signals, rerendering, and app-level workflows. |
| Deterministic native image fixture | `otoe render TARGET --out frame.png --native` | Headless native layout, paint commands, and PNG output without an OS window. |
| Renderer contract test | `NativeSurface` | One mounted tree with layout, paint, hit testing, focus, input, scroll, PNG output, and refresh from a testable object. |
| Window-level input contract test | `NativeWindowDriver` | High-level click, key, text input, and wheel events over the same `NativeSurface` path future backends must drive. |
| Local native window smoke | `run_native(...)` | Optional Tk-backed manual experiment. It is useful for seeing a window, not for production backend claims. |

## HTML Render

Use HTML render when you need a quick static preview of an importable component
tree. It is the least surprising output path and the right first check for docs,
examples, and simple visual snapshots.

```bash
otoe render examples.quickstart:app --out preview.html --pretty
```

HTML render does not prove native layout, paint, input, or backend behavior. It
only proves that the target can be imported and rendered through the HTML
adapter.

## Live Preview

Use `otoe dev` when you are building normal app flows: buttons, forms, route
switching, dialogs, command palettes, and repeated state changes.

```bash
otoe dev examples.live_counter:app --port 8767
```

This is the best workflow for component authoring because it exercises the
browser event path and live rerendering. Keep app code backend-neutral here:
components should not import native modules, Tk, Skia, Taffy, or platform APIs.

## Native PNG

Use native PNG output when you need a deterministic file artifact from the
headless native renderer.

```bash
otoe render examples.quickstart:app --out preview.png --native
```

Native PNG output proves that Otoe can mount the target, compute native layout,
emit paint commands, and rasterize a non-empty frame through the current stdlib
PNG writer. It is not a production raster backend. Text in PNG output remains
deterministic marker output rather than real font shaping.

The current implementation is exposed as `PYTHON_NATIVE_RENDERER_BACKEND`, an
experimental `NativeRendererBackend` that wraps Python layout, paint, and PNG
writing. Future renderer candidates should attach at this boundary before they
claim parity with the headless native path.
The SPI is split by capability (`NativeLayoutBackend`, `NativePaintBackend`, and
`NativeRasterBackend`), and `ComposedNativeRendererBackend` can combine them.
Use that split when a candidate only replaces one layer.

## NativeSurface

Use `NativeSurface` in tests or examples when you need direct access to the
headless renderer state:

- inspect `surface.layout`, `surface.paint`, or `surface.box(path)`
- render a PNG frame
- dispatch click, key, text input, focus, and scroll behavior
- assert frame changes after state updates
- test native behavior without opening an OS window

```python
from otoe import NativeSurface

surface = NativeSurface(App(), stylesheet=styles)
surface.click(24, 32)
surface.input_text("search")
surface.render_png("frame.png")
```

This is the lowest-level framework-facing native workflow. Use it before
reaching for a window driver. Renderer experiments can pass
`renderer_backend=...` here to prove their layout, paint, and PNG behavior while
keeping input and focus on the existing surface contract.

## NativeWindowDriver

Use `NativeWindowDriver` when the test needs window-shaped events rather than
direct surface calls. It maps click, wheel, key-down, and key-input events to
the current `NativeSurface` behavior while staying headless.

```python
from otoe import NativeWindowDriver

driver = NativeWindowDriver.from_target(App(), stylesheet=styles)
driver.click(20, 20)
driver.key_input("a")
driver.wheel(80, 120, 40)
```

Future backend adapters should drive this same contract. If a backend cannot
replay the current backend acceptance surface through `NativeWindowDriver`, it
is not equivalent to the current native path yet.

Renderer experiments can also pass `renderer_backend=...` to
`NativeWindowDriver.from_target(...)` to test a new renderer behind the same
window-shaped input replay.

The current backend-candidate acceptance bar has three replay surfaces:

- the minimal harness in `tests/test_native_backend_contract.py`
- the app-shaped native task board replay
- the fake adapter replay through `run_native(...)`

New candidates should reproduce those surfaces before adding backend-specific
layout, paint, text, GPU, or packaging behavior.
Use `BACKEND_CANDIDATE_GUIDE.md` as the candidate graduation checklist when an
experiment needs to move from replay proof to capability profile, build gate,
and offline bundle packaging.
`examples/native/backend_candidate_skeleton.py` is the first no-dependency
starting point for that work: it records a candidate adapter run, provides a
`HeadlessCandidateBackend`, includes a no-dependency `RecordingRendererCandidate`,
drives the minimal replay and task board replay through `run_native(...)`, and
returns small acceptance reports with layout, paint, focus, frame,
renderer-backend, and visible-text summaries. The file is now a compatibility
facade; acceptance orchestration lives in `backend_candidate_acceptance.py` and
CLI argument handling lives in `backend_candidate_cli.py`, with command
implementations in `backend_candidate_commands.py`, while the historical import
path and `python -m examples.native.backend_candidate_skeleton` entrypoint
remain stable. The
`run_renderer_candidate_acceptance()` helper runs those same replays through the
renderer SPI and records `layout`, `paint`, and `write_png` calls. The
`renderer_contract_snapshot_to_dict(...)` helper and
`--renderer-contract-json` CLI flag produce the schema-versioned JSON snapshot
used as the golden renderer contract. `RasterOnlyRendererCandidate` is the first
partial candidate: it keeps Python layout and paint but replaces `write_png`
with a separate no-dependency raster path. `PaintOnlyRendererCandidate` keeps
Python layout and raster but replaces `paint(...)` with an alternate compatible
paint command stream. `LayoutOnlyRendererCandidate` currently covers the
minimal replay, static task-board layout acceptance, and interactive task-board
replay while preserving Python paint and raster output. The
`run_composed_renderer_candidate_acceptance(...)` helper wires
`LayoutOnlyRendererCandidate`, `PaintOnlyRendererCandidate`, and
`RasterOnlyRendererCandidate` into `ComposedNativeRendererBackend`, then runs
the interactive replays plus a PNG smoke so every capability is exercised.
Path0 now also exposes the `RenderTreeRendererCandidate` boundary:
`layout_render_tree(...)` consumes already-resolved `RenderTree` IR directly,
while `run_path0_render_tree_evidence(...)` can inject any backend that
implements that boundary. This is the first replaceable backend-candidate path
that does not need `FakeWidget`, `MountedNode`, or `StyleSheet` as the renderer
input. Backend readiness records that boundary as `renderTreeBoundary`, and
`path0RenderTreeEvidence` fails if the layout proof only shows a generic
layout phase without the `renderTree` boundary marker. It also fails when a
supplied `styleOps` artifact does not resolve to the same styles already
embedded in the `RenderTree`, or when Path0/renderTreeLayout proofs do not
carry the input `renderTreeHash`. Path0 readiness also recomputes
`semanticValidation` from the layout/paint output so structurally incoherent
output cannot pass by refreshing hashes. Backend coverage carries that
semantic summary in its top-level trace, and generated bundle runners require
it to stay passed with no errors. The same readiness artifact now emits
`rendererBoundaries` evidence for `renderTreeLayout` and
`paint`, and backend coverage treats those as first-class claims with their own
`evidenceMap` entries.
For a stricter subprocess check, use
`examples.native.path0_external_backend`: it reads serialized `RenderTree` JSON,
optionally records `otoe-styles.json` styleOps metadata, and writes
`path0-layout-output` plus `path0-paint-output` JSON without importing the
mounted-tree renderer or native renderer SPI. This is the current external
Path0 proof surface; it is intentionally smaller than a real hardware backend
and rejects unsupported widget names instead of falling back silently. Add
`--external-path0-backend` to `--backend-readiness-json` or
`--backend-coverage-json` when that subprocess report should become optional
readiness evidence and coverage trace data. Use `otoe backend-package` on
`examples/native/path0_external_backend.package.json` when you need the runner
and its hashed `backend-package.json` descriptor materialized as a package
directory. Build profiles can declare that package too:

```toml
[backend.package]
manifest = "examples/native/path0_external_backend.package.json"
```

`otoe build` then copies it under `backend/<name>/` and lists the descriptor
plus runner files as hash-checked artifacts.
`--composed-renderer-contract-json` prints that composed contract, and
`--composed-renderer-png` chooses the PNG smoke path. Add
`--compact-contract` to either renderer contract command when the desired
artifact is a smaller signature-and-hash contract instead of the full
layout/paint snapshot. Renderer contracts also include a `capabilityAudit`
section that summarizes widget instances/types, input bindings/capabilities,
unsupported entries, and replay requirements from the minimal and task-board
frames. `--backend-readiness-json` combines that renderer audit with the
StyleOps replay/audit into one blocker-oriented report for backend candidates.
`--backend-coverage-declaration-json` derives a coverage declaration from a
backend capability profile. `--backend-coverage-json` compares that profile
declaration, a candidate JSON profile passed with `--backend-capability-profile`,
or an explicit `--coverage-declaration`, against the readiness requirements.
Use the profile path when the candidate owns a capability profile; use the
explicit declaration path while a candidate is still narrower than the profile
it is working toward.
`run_style_ops_candidate_acceptance(...)` and
`--style-ops-contract-json` replay the generated `otoe-styles.json`
`styleOps` artifact into low-level declarations and compare those declarations,
direct widget style operations, omitted operations, support categories, and
missing-class flags against the compiled `rules` and `directStyles` sections.
The same JSON includes `capabilityAudit`, which summarizes applied style
properties by layout/paint support, declared omissions by status/support,
unsupported properties, and the support categories a backend must replay.
`directStyles` entries carry both the legacy widget `path` and a stable
`nodeId`; backend candidates must use `nodeId` for matching direct widget
styles and treat `path` as a debug/legacy fallback. Path 0 readiness also checks
that `styleOps` match the resolved `RenderTree` styles and that layout and
paint style properties produce observable effects in the candidate output, not
just that the properties appear in the artifact.
Known UI-kit dynamic classes are added to plan/build only when the target uses
the UI kit and the stylesheet already defines a matching portable rule; this
keeps reactive variants from disappearing in hardware builds without turning
strict styles into a broad, missing-rule safelist.
Use `--bundle` to point the candidate at an offline build directory; it runs
`otoe-run.py --verify`, reads `manifest.json`, and replays the generated style
artifact. Use `--style-artifact` only when you want to bypass bundle
verification and point directly at an existing `otoe-styles.json`; otherwise it
builds the skeleton app artifact directly.

Backend tooling should load that artifact through `otoe.style_ops.load_style_ir`
and apply the primitive stream with `otoe.style_ops.apply_style_ops`; this keeps
backend candidates from depending on raw CSS or duplicating the Style IR JSON
shape by hand. Use `otoe style-ir dist/cage/otoe-styles.json --summary`,
`--json`, or `--strict` for a quick local inspection before running a backend
replay.

```bash
PYTHONPATH=src:. python -m examples.native.backend_candidate_skeleton
PYTHONPATH=src:. python -m examples.native.backend_candidate_skeleton --json
PYTHONPATH=src:. python -m examples.native.backend_candidate_skeleton --renderer-contract-json
PYTHONPATH=src:. python -m examples.native.backend_candidate_skeleton --renderer-contract-json --compact-contract
PYTHONPATH=src:. python -m examples.native.backend_candidate_skeleton --backend-readiness-json
PYTHONPATH=src:. python -m examples.native.backend_candidate_skeleton --backend-readiness-json --contract-out examples/native/contracts/backend_readiness_expected.json
PYTHONPATH=src:. python -m otoe backend-profile native-python --coverage-declaration --out examples/native/contracts/backend_coverage_full_declaration.json
PYTHONPATH=src:. python -m otoe backend-coverage --requirements examples/native/contracts/backend_readiness_expected.json --backend-capability-profile examples/native/contracts/backend_candidate_partial_profile.json
PYTHONPATH=src:. python -m examples.native.backend_candidate_skeleton --style-ops-contract-json
PYTHONPATH=src:. python -m examples.native.backend_candidate_skeleton --style-ops-contract-json --bundle dist/cage
PYTHONPATH=src:. python -m examples.native.backend_candidate_skeleton --style-ops-contract-json --style-artifact dist/cage/otoe-styles.json
PYTHONPATH=src:. python -m examples.native.backend_candidate_skeleton --style-ops-contract-json --contract-out examples/native/contracts/style_ops_expected.json
PYTHONPATH=src:. python -m examples.native.path0_external_backend --render-tree render-tree.json --styles otoe-styles.json --layout-out path0-layout-output.json --paint-out path0-paint-output.json --contract-out path0-external-report.json
PYTHONPATH=src:. python -m otoe backend-package examples/native/path0_external_backend.package.json --package-out dist/path0-external-backend --json
PYTHONPATH=src:. python -m examples.native.backend_candidate_skeleton --backend-readiness-json --external-path0-backend --render-tree-artifact render-tree.json
PYTHONPATH=src:. python -m examples.native.backend_candidate_skeleton --composed-renderer-contract-json --composed-renderer-png preview/native/composed_renderer_candidate.png
PYTHONPATH=src:. python -m examples.native.backend_candidate_skeleton --composed-renderer-contract-json --compact-contract --composed-renderer-png preview/native/composed_renderer_candidate.png
PYTHONPATH=src:. python -m examples.native.backend_candidate_skeleton --composed-renderer-contract-json --compact-contract --composed-renderer-png /tmp/composed_renderer_candidate.png --contract-out examples/native/contracts/composed_renderer_compact_expected.json
PYTHONPATH=src:. python -m otoe compare-contract examples/native/contracts/composed_renderer_compact_expected.json actual-contract.json
PYTHONPATH=src:. python -m otoe compare-contract examples/native/contracts/backend_readiness_expected.json actual-backend-readiness.json
PYTHONPATH=src:. python -m otoe compare-contract examples/native/contracts/style_ops_expected.json actual-style-ops-contract.json
PYTHONPATH=src:. python -m otoe compare-contract examples/native/contracts/bundle_style_ops_expected.json actual-bundle-style-ops-contract.json
PYTHONPATH=src:. python -m otoe compare-contract examples/native/contracts/composed_renderer_compact_expected.json actual-contract.json --ignore-path /pngSmoke/path --ignore-path /calls/raster/signature/0/subject --ignore-path /calls/raster/hash
```

Use `otoe compare-contract` for candidate contract comparisons in CI. It exits
zero only when the JSON artifacts match, reports JSON-pointer paths for human
diffs, can emit a machine-readable report with `--json`, and can ignore
intentional environment-specific fields with `--ignore-path`. If the composed
renderer PNG smoke filename differs from the fixture, ignore `/pngSmoke/path`,
`/calls/raster/signature/0/subject`, and `/calls/raster/hash` together. The
checked-in `examples/native/contracts/composed_renderer_compact_expected.json`
fixture is the current expected compact composed-renderer contract,
`examples/native/contracts/backend_readiness_expected.json` is the aggregate
backend-readiness gate, `examples/native/contracts/backend_coverage_full_declaration.json`
is the full coverage declaration fixture generated from the `native-python`
capability profile,
`examples/native/contracts/backend_candidate_partial_profile.json` is a partial
candidate profile fixture that intentionally reports coverage blockers, and
`examples/native/contracts/style_ops_expected.json` is the current expected
in-memory low-level style operations contract. The
`examples/native/contracts/bundle_style_ops_expected.json` fixture is the
bundle-backed hardware workflow gate. Refresh these only when an intentional
contract change lands, using `--contract-out` so the update command does not
depend on shell redirection.

The native support matrix and renderer spike documentation are also executable
drift checks: `tests/test_native_support_matrix.py` keeps `NATIVE_RENDERER_SPIKE.md`
aligned with supported style, widget, input, fallback, ignored, and deferred
entries.

Backend capability profiles are the build/planning view of that same support
surface. `native-python` is the current default profile, and `native` remains a
profile-file alias. `otoe plan --backend native-python` records style, widget,
input, and renderer-boundary capabilities in `otoe-plan.json`; `otoe plan/build
--backend-capability-profile path/to/profile.json` does the same for
experimental JSON candidate profiles. `otoe build` carries the selected
capability profile into `manifest.json` and `otoe-styles.json`; and `styleOps`
records support categories from that profile so hardware candidates do not need
to infer support from Python internals.
`otoe backend-profile native-python` or `otoe backend-profile
--backend-capability-profile path/to/profile.json --json` inspects that support
surface from the core CLI; add `--coverage-declaration` when the output should
feed a backend coverage comparison.
`otoe backend-coverage --requirements backend-readiness.json --backend-capability-profile
path/to/profile.json` runs that comparison from core CLI, leaving the skeleton
focused on generating readiness/replay artifacts.
Readiness-like payloads must keep `schemaVersion = 1`,
`format = "backend-readiness-report"`, and `candidate.backend` equal to the
coverage declaration backend; otherwise coverage reports
`backendReadinessContract` or `backendIdentity` blockers instead of counting
the evidence.
Add `--audit` when the candidate needs a human-readable trace of every covered,
missing, or unproven renderer boundary/widget/input/style back to its source,
gate, boundary proof, and runtime style proof.
Those proof hashes are strict `sha256:<64 lowercase hex>` values; symbolic or
uppercase hashes are reported as malformed evidence.
The JSON coverage artifact also includes a top-level `trace` summary for
`candidateScope.level`, Path0 render-tree/layout/paint hashes, and Path0
`semanticValidation`; bundle runners verify covered renderer-boundary proofs
and semantic pass/fail state against that summary. Coverage artifacts also
include an evidence summary that counts malformed evidence by blocker so audit
output can distinguish missing support from claims that were declared but not
validly exercised.
The requirements path should be a backend-readiness report with executed
`evidence`; requirements-only JSON is treated as insufficient because declared
coverage is not proof.
Profiles can make that comparison a normal plan/build gate with
`[backend].coverage_requirements = "backend-readiness.json"`, or the same path
can be passed with `--backend-coverage-requirements`. `otoe plan` embeds the
result as `backendCoverage`; `otoe build` persists it as
`otoe-backend-coverage.json` and refuses to write `manifest.json` when the
selected capability profile misses required coverage.
The skeleton's `--backend-coverage-json` and
`--backend-coverage-declaration-json` flags remain compatibility-only; use the
core `otoe backend-profile` / `otoe backend-coverage` commands for new flows.
That keeps the support matrix, planner, bundle, and candidate contract aligned.

`otoe pack` is the final bundle gate before deployment archives: it runs the
bundle runner verification, including copied-runtime Style IR drift detection,
checks declared backend coverage reports and their per-capability `evidenceMap`
traceability, repeats strict Style IR validation, requires top-level artifacts
to be covered by manifest hash entries, rejects invalid plan/dependency/style
artifacts or runtime-install/runtime-policy drift, and includes
`otoe-backend-coverage.json` when the manifest declares it before writing the
`.tar.gz`. Runtime policy remains static audit: set `[runtime.policy]` entries
to `error` for hardware profiles that must fail on visible stdlib network or
process-spawning usage. When the manifest declares `backendPackage`,
verification also checks the package descriptor's internal file hashes and runs
the bundled Path0 JSON backend smoke; `otoe-run.py --backend-package-check`
exposes that smoke directly.

## run_native

Use `run_native(...)` only for local manual experiments:

```python
from otoe import run_native

run_native(App(), stylesheet=styles, title="Otoe", backend="tk")
```

When `run_native(...)` receives a raw target, renderer experiments may pass
`renderer_backend=...`; when they already pass a `NativeSurface` or
`NativeWindowDriver`, that object must already have the intended renderer
backend attached.

The built-in `"tk"` backend is optional and requires Python's Tk bindings plus a
graphical display. On Debian/Ubuntu:

```bash
sudo apt install python3-tk
```

The Tk wrapper presents the current paint command stream on a Canvas with
readable text items and scale-to-fit geometry. It is a manual-test adapter, not
a production desktop backend or model for future production backends. Do not
treat Tk window behavior, PNG marker text, or current scaling as compatibility
promises.

## Backend Rules

- Component code stays backend-neutral.
- Renderer tests should prefer `NativeSurface` or `NativeWindowDriver`.
- Partial renderer candidates may implement `NativeRendererBackend` to replace
  one mounted-tree capability behind the current Python native path.
- Externally replaceable backend candidates should implement the Path0
  `RenderTreeRendererCandidate` boundary and prove they consume resolved
  `RenderTree` IR rather than `FakeWidget`, `MountedNode`, or raw `StyleSheet`
  internals.
- Renderer candidates still need to pass through the minimal harness, native
  task board replay, fake adapter replay, renderer-candidate replay, and
  `tests/test_native_renderer_backend.py` while the current mounted-tree SPI
  remains part of the acceptance surface.
- Partial renderer candidates should use the layout/paint/raster capability
  split and prove which capability they replace.
- Layout-only candidates must start with the minimal replay, then static
  task-board layout acceptance, then the interactive app-shaped task board
  replay.
- Manual OS windows should go through `run_native(...)`, not custom app-level
  mounting/layout/paint wiring.
- New backend candidates must reproduce the minimal harness, native task board
  replay, and fake adapter replay before expanding backend-specific behavior.
- Public docs should keep native support framed as headless preview/test support
  until a production backend meets the bar in `ADR-012-native-backend-boundary.md`.
