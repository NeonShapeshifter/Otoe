# Backend Candidate Guide

This guide is the graduation path for a backend candidate. A candidate starts as
an experiment, proves the current native contract through executable replay, then
declares exactly what it supports through a backend capability profile.

## Ground Rules

- Component code must stay backend-neutral. Widgets should not import Tk, Skia,
  Taffy, Qt, SDL, GPU APIs, or platform APIs.
- Hardware runtimes must not install dependencies. Dependency installs belong
  before deployment; `otoe deps`, `otoe build`, `otoe-run.py --verify`, and
  `otoe pack` audit the bundle instead of installing packages.
- Raw CSS is an authoring/build input, not a hardware runtime dependency.
  Hardware and native candidates should consume compiled `otoe-styles.json`
  through `otoe.style_ops.load_style_ir(...)` and
  `otoe.style_ops.apply_style_ops(...)`; renderer-side tree work should consume
  `ResolvedStyleMap` derived from that primitive stream.
- The current built-in native runner rehydrates a `StyleSheet` from bundled
  `styleOps` before calling the Python native renderer. That proves CSS text is
  not needed at bundle runtime; it is still separate from the renderer-side
  `RenderTree` IR boundary used by backend candidates.
- `Path0RendererCandidate` is the first non-delegating renderer fixture at the
  current SPI: it compiles Otoe targets into `RenderTree` IR v0, then owns
  layout, paint, and raster phases without delegating to the Python renderer.
  When an artifact/map is available it resolves styles through `styleOps` via
  `ResolvedStyleMap`; the current SPI can still derive that map from
  `StyleSheet` as a compatibility bridge.
  It proves replacement pressure on the native renderer; it is not yet the final
  Skia/Taffy/Qt contract.
- Tk is a local manual smoke adapter only. It is not a production backend and
  should not be used as the compatibility model for new candidates.

## Required Artifacts

A candidate should be able to produce or consume these artifacts:

- `backend-profile.json`: a schema-versioned backend capability profile with
  `format: "backend-capability-profile"`, `styles`, `widgets`, and `inputs`.
- `backend-readiness.json`: the replay and audit requirements emitted by
  `examples/native/backend_candidate_skeleton.py --backend-readiness-json`.
  The skeleton module is a stable compatibility facade; the acceptance runner
  and CLI implementation live in focused sibling modules. Command behavior is
  implemented in `backend_candidate_commands.py`, while
  `backend_candidate_cli.py` owns argument parsing and dispatch.
  The report includes `candidate`, which names the backend identity the
  readiness evidence belongs to, and `candidateScope`, which explicitly marks
  the current scope as Path0 `RenderTree` IR v0 fixture evidence and records
  that the external backend ABI is not stable yet.
- `backend-coverage-declaration.json`: the candidate's claimed widget, input,
  style, and omitted-style coverage.
- `otoe-styles.json`: the compiled Style IR artifact from `otoe build`,
  including resolved rules, direct styles, backend capabilities, and `styleOps`.
- `render-tree-contract.json`: the renderer-side `RenderTree` IR v0 replay
  contract produced from mounted widgets, stable `For` keys, normalized
  props/events/state, and style values resolved through `ResolvedStyleMap`.
  With `--render-tree-artifact`, Path0/readiness can load an explicit serialized
  `RenderTree` JSON file. With `--bundle`, the contract verifies the bundle and
  loads the target named in `manifest.json` before adding an `artifactTarget`
  tree.
- `path0-layout-output.json` and `path0-paint-output.json`: the backend-neutral
  Path0 output payloads emitted by either readiness evidence or the
  experimental external JSON runner. They carry schema versions, output hashes,
  layout boxes, paint commands, and semantic shape that can be audited without
  importing native Python layout/paint objects.
- `otoe-backend-coverage.json`: the plan/build gate proving the selected
  backend profile covers the readiness requirements.
- `manifest.json` and `.tar.gz` bundle output: the final offline deployment
  contract with hash-covered artifacts and no runtime-install drift.

## Acceptance Path

1. Prove the minimal backend harness in
   `tests/test_native_backend_contract.py`.
2. Reproduce the app-shaped native task board replay through
   `NativeWindowDriver`.
3. Reproduce the fake adapter replay through `run_native(...)`; future window
   adapters enter through `NativeBackendAdapter` and receive a
   `NativeWindowDriver`, not a component tree.
4. If the candidate replaces layout, paint, or raster behavior, pass
   `tests/test_native_renderer_backend.py`, run the renderer-candidate replay,
   and compare against `Path0RendererCandidate` before generating the renderer
   contract with `--renderer-contract-json` or
   `--composed-renderer-contract-json`.
5. Replay Style IR with `--style-ops-contract-json` so the candidate proves it
   can consume low-level primitive operations without parsing CSS on hardware.
6. Replay RenderTree IR with `--render-tree-contract-json` so the candidate
   proves it can consume the low-level tree boundary across minimal, task board,
   keyed reorder, `Show` branch cases, and bundle artifact targets. Candidates
   should call `validate_render_tree(...)` or `assert_render_tree_valid(...)`
   before layout/paint work so malformed IR fails at the boundary, and use
   `render_tree_from_dict(...)` or `load_render_tree_artifact(...)` when
   consuming serialized RenderTree JSON artifacts.
7. Run the external Path0 JSON backend against an explicit `RenderTree`
   artifact when you need a stricter out-of-process check. This path consumes
   JSON files and emits JSON files; it is intentionally small and rejects
   unknown widgets instead of hiding support gaps behind generic container
   fallback.
8. Emit `--backend-readiness-json` and compare the candidate capability profile
   with `otoe backend-coverage`.
9. Run the same gate through `otoe plan`, `otoe build --validate`,
   `otoe style-ir --strict`, and `otoe pack`.

## Core Commands

```bash
PYTHONPATH=src:. python -m examples.native.backend_candidate_skeleton
PYTHONPATH=src:. python -m examples.native.backend_candidate_skeleton --json
PYTHONPATH=src:. python -m examples.native.backend_candidate_skeleton --renderer-contract-json --contract-out renderer-contract-full.json
PYTHONPATH=src:. python -m examples.native.backend_candidate_skeleton --backend-readiness-json --contract-out backend-readiness.json
PYTHONPATH=src:. python -m examples.native.backend_candidate_skeleton --style-ops-contract-json --contract-out style-ops-contract.json
PYTHONPATH=src:. python -m examples.native.backend_candidate_skeleton --render-tree-contract-json --contract-out render-tree-contract.json
PYTHONPATH=src:. python -m examples.native.backend_candidate_skeleton --path0-render-tree-evidence-json --render-tree-artifact render-tree.json --contract-out path0-evidence.json
PYTHONPATH=src:. python -m examples.native.path0_external_backend --render-tree render-tree.json --styles otoe-styles.json --layout-out path0-layout-output.json --paint-out path0-paint-output.json --contract-out path0-external-report.json
PYTHONPATH=src:. python -m examples.native.backend_candidate_skeleton --backend-readiness-json --render-tree-artifact render-tree.json --contract-out backend-readiness.json
PYTHONPATH=src:. python -m examples.native.backend_candidate_skeleton --render-tree-contract-json --bundle dist/cage --contract-out render-tree-contract.json
PYTHONPATH=src:. python -m examples.native.backend_candidate_skeleton --backend-readiness-json --bundle dist/cage --contract-out backend-readiness.json
PYTHONPATH=src:. python -m examples.native.backend_candidate_skeleton --composed-renderer-contract-json --compact-contract --contract-out renderer-contract.json
PYTHONPATH=src:. python -m otoe backend-profile --backend-capability-profile backend-profile.json --json
PYTHONPATH=src:. python -m otoe backend-profile --backend-capability-profile backend-profile.json --coverage-declaration --out backend-coverage-declaration.json
PYTHONPATH=src:. python -m otoe backend-coverage --requirements backend-readiness.json --backend-capability-profile backend-profile.json --out backend-coverage.json
PYTHONPATH=src:. python -m otoe backend-coverage --requirements backend-readiness.json --backend-capability-profile backend-profile.json --audit
PYTHONPATH=src:. python -m otoe plan app:app --profile cage --backend-capability-profile backend-profile.json --backend-coverage-requirements backend-readiness.json --out dist/otoe-plan.json
PYTHONPATH=src:. python -m otoe build app:app --profile cage --backend-capability-profile backend-profile.json --backend-coverage-requirements backend-readiness.json --out dist/cage --validate
PYTHONPATH=src:. python -m otoe style-ir dist/cage/otoe-styles.json --strict
PYTHONPATH=src:. python -m otoe pack dist/cage --out dist/cage.tar.gz
```

Use `otoe compare-contract` in CI when the candidate has expected JSON fixtures:

```bash
PYTHONPATH=src:. python -m otoe compare-contract examples/native/contracts/backend_readiness_expected.json backend-readiness.json
PYTHONPATH=src:. python -m otoe compare-contract examples/native/contracts/style_ops_expected.json style-ops-contract.json
PYTHONPATH=src:. python -m otoe compare-contract examples/native/contracts/render_tree_expected.json render-tree-contract.json
PYTHONPATH=src:. python -m otoe compare-contract examples/native/contracts/composed_renderer_compact_expected.json renderer-contract.json
```

The native support matrix and renderer spike documentation are part of the same
contract: `tests/test_native_support_matrix.py` keeps `NATIVE_RENDERER_SPIKE.md`
aligned with supported style, widget, input, fallback, ignored, and deferred
entries.
Path0 renderer candidates should enter through `RenderTreeRendererCandidate`:
`layout_render_tree(...)` receives resolved `RenderTree` IR, and
`run_path0_render_tree_evidence(...)` can inject a candidate backend through
that boundary before paint/raster evidence is generated. The readiness artifact
records this as `evidence.path0.renderTreeBoundary` and now also includes
`path0.output.layout` plus `path0.output.paint`, schema-versioned JSON output
payloads with hashes for the layout boxes and paint commands produced from the
RenderTree boundary. Path0 evidence also records whether the supplied
`styleOps` artifact resolves to the same styles embedded in the `RenderTree`;
readiness and coverage reject style runtime proof when that match is missing.
The `evidence.path0` summary stores the corresponding layout/paint output
hashes, so coverage can validate the full output payload without duplicating
it. Path0 readiness also records and recomputes `semanticValidation`, rejecting
layout paths/bounds and paint commands that are structurally incoherent even
when output hashes are refreshed. Coverage rejects Path0 evidence that only
claims generic layout/paint
phases. Coverage also includes a first-class `rendererBoundaries` section,
currently proving `renderTreeLayout` and `paint`, so a candidate profile cannot
claim renderer-boundary support without matching readiness evidence. The
`renderTreeLayout` proof must also carry the input `renderTreeHash`, tying the
layout result to the exact `RenderTree` artifact consumed by Path0.
`NativeRendererBackend` remains the mounted-tree SPI for Otoe's current Python
native renderer and partial layout/paint/raster replacement tests. It receives
Otoe internals such as `FakeWidget`, `MountedNode`, and `StyleSheet`, so passing
only that SPI is not enough to claim an externally replaceable hardware backend.
`examples.native.path0_external_backend` is the first stricter Path0 external
runner. It is deliberately a JSON-in/JSON-out subprocess surface: it reads
`otoe-render-tree`, optionally records `otoe-styles.json` styleOps metadata,
emits `path0-layout-output` and `path0-paint-output`, and does not import Otoe's
mounted-tree renderer, native renderer SPI, or backend-candidate harness
modules. It is still an experimental Path0 runner, not the final external ABI;
the next graduation step is binding this output directly into readiness and
coverage evidence for real backend candidates.

## Capability Profile Contract

The candidate profile is a planning and build artifact. It is not proof by
itself; it is a claim that gets compared against replay requirements. Coverage
reports distinguish required/exercised items from declared/claimed items, and
claims outside the readiness artifact are reported as unproven until a replay
or contract fixture exercises them. Strict readiness artifacts must keep
`schemaVersion = 1`, `format = "backend-readiness-report"`, and a
`candidate.backend` matching the coverage declaration backend. That binding
prevents a profile from reusing another backend's readiness artifact by only
renaming the declaration. Strict readiness artifacts must also carry evidence
metadata: each exercised group needs a source, a passing gate, and
widget/input evidence must match the renderer capability audit hash, item
count, and observed capability names. Style evidence needs runtime Path 0 proof
from `styleOps` plus layout/paint observation hashes for each property's
declared support phase. A `layout+paint` style must appear in both phase
summaries, and declared style omissions must not appear as runtime-applied
layout/paint evidence. Renderer-boundary evidence must carry `boundaryProof`
for `renderTreeLayout` or `paint`, including the Path0 output hash for the
layout or paint artifact it proved; `renderTreeLayout` proofs must also match
the Path0 input `renderTreeHash`. All evidence hashes must use
`sha256:<64 lowercase hex>`; symbolic hashes such as `sha256:test` are
malformed. Malformed or untraced evidence reports as an `*Evidence` blocker and
does not count as
exercised coverage, even when the claimed names otherwise match.
Coverage reports also carry a top-level `trace` summary with
`candidateScope.level`, `path0.renderTreeHash`, `path0.layoutOutputHash`, and
`path0.paintOutputHash`, plus `path0.semanticValidation`. Generated bundle
runners compare covered `rendererBoundaries` proofs against that summary and
require the semantic validation to remain passed with an empty error list, so
tampered coverage artifacts cannot refresh manifest hashes and silently point
boundary evidence at different or structurally invalid Path0 output.
The report includes an `evidenceMap` for every coverage section; each covered
claim points to the source/gate that exercised it, and style claims include the
runtime observation hashes that proved their layout/paint phase.
The report also includes `readiness.evidenceSummary.malformedByBlocker`, and
`--audit` prints those counts so reviewers can separate missing declarations,
declared-but-unproven claims, and evidence that was present but invalid.

```json
{
  "schemaVersion": 1,
  "format": "backend-capability-profile",
  "name": "my-backend-candidate",
  "label": "My backend candidate",
  "styles": {
    "background": "paint",
    "gap": "layout",
    "opacity": "ignored"
  },
  "widgets": {
    "Button": "control",
    "Text": "text",
    "VStack": "container"
  },
  "inputs": {
    "click": "supported",
    "key_down": "supported",
    "ime": "deferred"
  }
}
```

Supported values are intentionally small:

- styles: `layout`, `paint`, `layout+paint`, `ignored`
- widgets: `container`, `control`, `text`
- inputs: `supported`, `deferred`

`ignored` style support is still a declaration. It means the candidate has made
an explicit compatibility decision and the property appears under
`declaredStyleOmissions` in coverage reports.

## Graduation Criteria

A candidate can be treated as equivalent to the current native path only after:

- the minimal harness, task board replay, and fake adapter replay pass
- renderer-specific tests pass for any replaced layout, paint, or raster layer
- Style IR replay passes from both direct `otoe-styles.json` and bundle paths
- `otoe backend-coverage` passes against the emitted readiness requirements and
  does not rely on unproven claims for the supported surface being advertised
- `otoe build --validate` and `otoe pack` pass with no runtime installs
- docs and contract fixtures describe the exact supported backend surface

Until then, keep the candidate as a JSON profile path passed through
`--backend-capability-profile` or `[backend].capability_profile`, not as a
built-in backend profile.

## Common Failure Modes

- A candidate parses CSS at runtime instead of consuming `styleOps`.
- A capability profile claims support that no replay exercised.
- A window adapter receives a component tree instead of a `NativeWindowDriver`.
- `backend-readiness.json` is generated once and then allowed to drift from the
  current task board, Style IR, or renderer contract.
- The offline bundle passes on the development machine but requires network,
  package installation, or untracked files on hardware.
