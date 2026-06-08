# Otoe

Otoe is an experimental Python UI runtime for building desktop-style
interfaces with component functions, reactive state, explicit events, and a
renderer boundary that can evolve beyond the current HTML proof backend.

The project is early. The current repository is a technical preview for the
runtime model, visual case studies, and live preview loop. It is not yet a
stable public framework or a production desktop renderer.

## What Works Today

- Python component functions with typed widget contracts.
- `signal`, `computed`, `effect`, owner cleanup, and lifecycle hooks.
- `Show` and keyed `For` control flow.
- Fake-widget mounting and deterministic snapshots.
- Static HTML preview rendering.
- Shared live HTML preview server with click/input event dispatch.
- Optional JSX-like `template(...)` syntax that returns the same `Node` tree.
- Experimental portable `css(...)` / `StyleSheet` API plus low-level
  `utility_css()` / `utility_stylesheet()` helpers for app styling.
- `otoe plan` diagnostics for checking an app against the first offline
  hardware/cage profile before any deployment bundle exists, including static
  extraction of literal `className` state classes for simple local targets.
- First `otoe.ui` primitives: cards, badges, action buttons, tabs, toolbars,
  stat cards, data tables, dialogs, toasts, command palettes, app shells,
  sidebar navigation, route views, command registries, shortcut scopes, menus,
  controlled selects, section headers, empty states, and feedback toasts.
- Modern default presets for no-custom-CSS app surfaces: app frames, sidebars,
  topbars, surfaces, metric grids, metric tiles, status pills, and list rows.
- Keyboard handling for command palettes, menus, selects, and button-backed
  controls in the live preview backend.
- `FocusScope` support for live focus trapping and focus restoration in dialogs
  and popovers.
- Live autofocus support for command overlays and other focused inputs.
- Wraith-shaped and SaaS-shaped case studies using the same UI primitives.
- UI kit kitchen-sink preview for validating primitives outside one product shape.
- Utility-first reference app for validating low-level styling ergonomics.
- Headless native layout, paint, PNG output, hit-testing, and click dispatch
  for the first renderer spike.
- `NativeSurface` for mounting a tree, rendering PNG frames, dispatching
  clicks, and refreshing the headless native frame from one object.
- `NativeWindowDriver` for testable native-window event dispatch over a
  `NativeSurface`, plus an optional Tk wrapper for local experiments.
- `run_native(...)` as the experimental native app entry point, currently backed
  by the optional Tk wrapper.
- Driver-level `key_input(...)` text editing for printable keys, Backspace,
  Delete, Enter/Tab fallback, and shortcut fallback.
- Controlled native `ScrollView(scrollY=..., onScroll=...)` support with
  clipped paint, clipped hit-testing, and wheel dispatch through the native
  window driver.
- Headless native focus and keyboard handling for autofocus, click-to-focus,
  Tab traversal, focused keydown handlers, button submit keys, and global
  shortcut payloads.
- Headless controlled input text dispatch through `NativeSurface.input_text(...)`.
- Framework-neutral native task board demo with search, filtered rows, empty
  state, modal state, shortcuts, controlled scroll, and PNG frame output.
- Lazy `NativeSurface` refresh when reactive props or control-flow branches
  change outside direct surface events.
- Disabled widgets are skipped for native focus and click dispatch.
- `ScrollView` bounds clip native paint output and hit-tested clicks.
- Native paint includes disabled control defaults and focused control rings.

## What Is Not Ready Yet

- Production desktop rendering/windowing.
- GPU rendering, layout engine integration, or accessibility tree output.
- Stable public API guarantees.
- Full component library or shadcn/Horizon-style UI kit.
- Packaging for production apps.

## Native Renderer Status

The native path is currently a deterministic headless renderer spike. It can
layout mounted Otoe trees, emit paint commands, write PNG preview frames, and
exercise click, focus, keyboard, input, and scroll dispatch through
`NativeSurface`. Backend candidates can now consume `RenderTree` IR v0, which
normalizes mounted widgets into stable node IDs, serializable props/events/state,
and `ResolvedStyleMap` values rehydrated from `styleOps` before candidate
layout runs. Path0 evidence verifies that any supplied `styleOps` artifact
resolves to the same styles embedded in that `RenderTree` before readiness can
count the style runtime as proven, and Path0 layout proofs carry the input
`renderTreeHash` so renderer-boundary evidence cannot be reused against a
different tree. Readiness also records `path0.semanticValidation` and
recomputes it from the Path0 layout/paint output, rejecting duplicate layout
paths, invalid bounds, and paint commands that do not reference layout boxes.
`validate_render_tree(...)` and
`assert_render_tree_valid(...)` check that boundary before Path0 layout/paint
work starts, and
`render_tree_from_dict(...)` plus `load_render_tree_artifact(...)` load
serialized `RenderTree` JSON back into the validated IR. Backend readiness also
includes a `RenderTree` contract fixture for minimal, task board, keyed reorder,
and `Show` branch shapes, plus artifact-backed paths that can load explicit
`--render-tree-artifact` JSON files or verify a bundle and load the target from
`manifest.json`.
The experimental `examples.native.path0_external_backend` runner takes the next
small step: it runs out-of-process, reads serialized `RenderTree` JSON,
optionally binds `otoe-styles.json` styleOps metadata, and writes
`path0-layout-output` plus `path0-paint-output` JSON without importing Otoe's
mounted-tree renderer or native renderer SPI. Add
`--external-path0-backend` to backend-readiness/coverage compatibility commands
when that subprocess report should be included under `path0.externalBackend`
and validated for process exit, output hashes, semantic shape, and
`renderTreeHash` binding. The same runner now has
`examples/native/path0_external_backend.package.json`; inspect or materialize it
with `otoe backend-package ... --package-out dist/path0-external-backend` to get
a hashed `backend-package.json` descriptor plus declared runner files. A profile
can also point `[backend.package].manifest` at that manifest so `otoe build`
copies the package under `backend/<name>/` as declared, hashed artifacts. It is
a Path0 proof surface, not a stable external backend ABI yet.

This is enough for renderer tests, visual fixtures, and early framework API
validation. It is not yet a production desktop backend: there is no GPU
renderer, platform accessibility tree, text shaping engine, retained windowing
backend, stable Skia/Taffy/Qt ABI, or production backend compatibility promise.
See
`ADR-012-native-backend-boundary.md` for the backend boundary and
`ADR-013-native-layout-hardening.md` for the current layout-hardening contract.
`ADR-014-native-overflow-clipping.md` defines the current overflow policy:
normal containers do not clip, while `ScrollView` clips paint and hit testing.
For day-to-day workflow choices, see `NATIVE_WORKFLOWS.md`.

Native and window-facing exports are intentionally marked as experimental. The
imports remain available for examples and tests, but they are not backend
compatibility promises:

```python
from otoe import api_status

assert api_status("NativeSurface").category == "experimental-native"
```

## Quick Start

Use Python 3.11 or newer.

Install the latest published package from PyPI:

```bash
python -m pip install otoe
```

For local development:

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e ".[dev]"
pytest -q
```

On Debian/Ubuntu systems that report an externally managed Python environment,
do not install Otoe into the system Python. Use the virtual environment above,
or run examples directly from a checkout with `PYTHONPATH=src:.`.

Run the local framework health check:

```bash
python -m otoe check
python -m otoe check --tests
python -m otoe check --tests -- tests/test_cli.py -k new
python -m otoe new my_app
```

After installation, the same commands are available through the `otoe` console
script:

```bash
otoe check
otoe new my_app
otoe render examples.quickstart:app --out preview.html --pretty
otoe render examples.quickstart:app --out preview.png --native
otoe plan examples.quickstart:app --profile cage --no-strict-styles
otoe build examples.quickstart:app --out dist/cage --no-strict-styles
otoe compare-contract expected.json actual.json
otoe dev examples.live_counter:app --port 8767
```

`otoe new my_app` writes a small renderable app plus `styles.css`; pass
`--no-css` when you want only the Python scaffold.

Render the generated app with its stylesheet:

```bash
cd my_app
otoe render app:app --out preview.html --css styles.css --pretty
otoe render app:app --out preview.png --native --css styles.css
```

Render an importable Otoe node or zero-argument factory to HTML:

```bash
python -m otoe render examples.quickstart:app --out preview.html --pretty
```

Apply an Otoe CSS file inline while rendering:

```bash
python -m otoe render examples.quickstart:app --out preview.html --css path/to/styles.css --pretty
```

Render the same target through the native PNG path:

```bash
python -m otoe render examples.quickstart:app --out preview.png --native
```

Check an app against the first offline hardware/cage profile:

```bash
python -m otoe plan app:app --profile cage --css styles.css
python -m otoe plan app:app --profile cage --backend native-python --css styles.css
python -m otoe plan app:app --profile cage --backend-capability-profile backend-profile.json --css styles.css
python -m otoe plan app:app --profile cage --backend-coverage-requirements backend-readiness.json
python -m otoe plan app:app --profile cage --utilities
python -m otoe plan app:app --profile cage --utilities --out dist/otoe-plan.json
python -m otoe plan app:app --profile cage --utilities --json
python -m otoe plan app:app --profile-file otoe.profile.toml --out dist/otoe-plan.json
python -m otoe build app:app --profile cage --backend-capability-profile backend-profile.json --css styles.css --out dist/cage
python -m otoe build app:app --profile cage --backend-coverage-requirements backend-readiness.json --out dist/cage
python -m otoe backend-profile native-python
python -m otoe backend-profile --backend-capability-profile backend-profile.json --json
python -m otoe backend-profile --backend-capability-profile backend-profile.json --coverage-declaration --out backend-coverage-declaration.json
python -m otoe backend-coverage --requirements examples/native/contracts/backend_readiness_expected.json --backend native-python
python -m otoe backend-coverage --requirements examples/native/contracts/backend_readiness_expected.json --backend native-python --audit
python -m otoe backend-coverage --requirements examples/native/contracts/backend_readiness_expected.json --backend-capability-profile backend-profile.json --out backend-coverage.json
python -m otoe deps app:app --profile-file otoe.profile.toml --json
```

`otoe plan` is diagnostic only. It imports and mounts the target, checks used
classes against the selected style sources and backend capability profile, then
reports portable, html-only, deferred, and invalid style work before building
or deploying a bundle.
`--json` emits the same report as machine-readable JSON, and `--out` writes that
JSON as the first plan artifact.
`otoe backend-profile` inspects the built-in `native-python` profile or a
candidate JSON profile and can emit the matching coverage declaration without
running a renderer replay. `otoe backend-coverage` compares that profile or an
explicit coverage declaration against a backend-readiness JSON artifact. This is
a declaration/evidence report, not proof of a production backend by itself:
required items must be exercised by readiness evidence, declared support is
treated as claimed by the profile, and extra claims are reported as unproven
until a replay artifact exercises them. Requirements-only JSON is not evidence,
and readiness-like artifacts must keep `schemaVersion = 1` plus
`format = "backend-readiness-report"` before executed evidence can count.
Coverage declarations are also bound to `readiness.candidate.backend`, so a
profile cannot reuse another backend's readiness artifact by only changing the
declared backend name.
Coverage validates the evidence contract: exercised groups need source/gate
metadata, their gates must be passing, widget/input proofs must match the
renderer capability audit, and style evidence must carry runtime Path 0 proof
from `styleOps` plus layout/paint observations for each property's declared
support phase. Declared style omissions must stay omitted from runtime
layout/paint style evidence. Invalid evidence groups do not count as exercised
coverage, so malformed proof cannot inflate `covered` support counts.
Evidence hashes must use the strict `sha256:<64 lowercase hex>` form; symbolic
or uppercase hash strings are treated as malformed evidence.
Each coverage section also carries an `evidenceMap` keyed by capability name so
audits can trace a covered renderer boundary, widget, input, style, or omission
back to its source/gate and, for renderer/style entries, boundary proof or
runtime observation hashes. The machine-readable coverage artifact also carries
a top-level `trace` summary with the candidate scope level, Path0
render-tree/layout/paint hashes, and Path0 `semanticValidation`; generated
bundle runners verify that covered renderer-boundary proofs match that trace
and that the semantic summary still passed with no errors.
Coverage artifacts also include `readiness.evidenceSummary`, so JSON reports
and audit output distinguish malformed evidence from missing support or
declared-but-unproven claims.
`--audit` prints that traceability as a text report for humans; `--json` and
`--out` keep writing the machine-readable coverage artifact.
See `BACKEND_CANDIDATE_GUIDE.md` for the full backend-candidate graduation path
from `RenderTree`/replay artifacts through capability profiles, build gates,
and offline bundle packaging.
When a profile or CLI flag declares backend coverage requirements, `otoe plan`
embeds a `backendCoverage` report and exits nonzero if the selected backend
capability profile misses required coverage. `otoe build` writes the same gate
as `otoe-backend-coverage.json` and refuses to write `manifest.json` when it
fails.

When `otoe.profile.toml` exists in the current directory, `otoe plan` uses it by
default. CSS paths are relative to the profile file:

```toml
profile = "cage"
utilities = true
css = ["styles.css"]
assets = ["static/logo.png"]

[runtime]
allow_runtime_installs = false
files = ["app.py"]

[runtime.policy]
# Audit-only source checks for hardware/cage surfaces: allow, warn, or error.
network = "warn"
subprocess = "warn"

[backend]
name = "native"
capability = "native-python"
# Optional backend coverage gate:
# coverage_requirements = "backend-readiness.json"
# Or, for experimental backend candidates:
# capability_profile = "backend-profile.json"

[backend.package]
# Optional experimental backend package copied into the build bundle.
manifest = "path0_external_backend.package.json"

[deps]
packages = ["pytest"]
extras = ["dev"]
```

Explicit CLI flags override the profile file. For example, `--css custom.css`
replaces the profile `css` list, and `--no-utilities` disables profile-enabled
utilities.

`otoe deps` audits declared `[deps]` entries and static external imports found
in discovered local runtime files against the current build environment. It
reports installed and missing packages, known and unknown Otoe extras, and
undeclared external imports. It reads local Python files but does not install
anything, download anything, import the app target, or write files; missing
packages must be installed manually before a hardware/cage deployment. This is
an audit-only gate, not a lockfile, wheel closure, or reproducible offline
dependency resolver. When installed package metadata maps an import module to a
different distribution name, declare the distribution package, for example
`Pillow` for `import PIL`; imports with no installed package metadata are
reported as unknown candidates. It also reports visible stdlib network and
subprocess/process usage under `runtimePolicy`; `[runtime.policy]` can keep
those findings as warnings or raise them to errors for stricter hardware
profiles. This is still static source audit, not a Python sandbox. During
`otoe build`, the same audit is written as `otoe-deps.json`, including
machine-readable `resolution.mode = "audit-only"` and
`runtimePolicy.mode = "audit-only"` contracts, and invalid dependency audits
stop the build before `manifest.json` is written.

Write the first minimal offline bundle contract:

```bash
python -m otoe build app:app --profile-file otoe.profile.toml --out dist/cage
python -m otoe build app:app --profile-file otoe.profile.toml --out dist/cage --validate
python -m otoe pack dist/cage --out dist/cage.tar.gz
```

`otoe build` currently writes `dist/cage/otoe-plan.json`,
`dist/cage/otoe-deps.json`, `dist/cage/otoe-styles.json`, and, when backend
coverage requirements are declared, `dist/cage/otoe-backend-coverage.json`.
It then writes `dist/cage/manifest.json`, copies declared assets under
`dist/cage/assets/`, copies selected Otoe framework/runtime files under
`dist/cage/framework/`, copies the local target module/package under
`dist/cage/app/`, preserving package paths for targets such as
`workspace_pkg.app:app`, supports namespace package targets without requiring a
package `__init__.py`, follows static local imports including package-relative
imports such as `from .views import card`, and copies declared extra runtime
files under `dist/cage/app/`.
When `[backend.package].manifest` is declared, the validated backend package is
copied under `dist/cage/backend/<name>/`, and every package file plus
`backend-package.json` is listed in `manifest.json.artifacts`.
It fails when the plan, dependency audit, backend coverage gate, or backend
selection is invalid, allows warning plans, and does not install dependencies,
or download anything. It reports visible `importlib.import_module(...)` and
`__import__(...)` dynamic import calls as dependency warnings, but does not
auto-copy arbitrary dynamic imports. It reports visible stdlib network imports
and process-spawning APIs such as `socket`, `urllib`, `subprocess`, and
`os.system(...)` through the audit-only runtime policy.
`[runtime] files` remains the explicit place for dynamic import edges, external
app files, and anything the static local import scanner cannot see. The manifest
references `otoe-deps.json`, records copied framework files in `frameworkFiles`,
and records copied app files in `runtimeFiles`. The style artifact records used
classes, resolved portable declarations, direct widget style props, omitted
html-only/deferred declarations, diagnostics, tokens, backend capability
metadata, and low-level `styleOps` that backend candidates can apply without
re-parsing CSS on the target. Backend tooling can consume the artifact with
`otoe.style_ops.load_style_ir(...)` and `otoe.style_ops.apply_style_ops(...)`
instead of indexing the JSON shape directly. The same artifact can be inspected
from the CLI with `otoe style-ir dist/cage/otoe-styles.json --summary` or
`otoe style-ir dist/cage/otoe-styles.json --json`; add `--strict` to fail when
`styleOps` drift from compiled `rules` or `directStyles`.
`directStyles` records include stable `nodeId` values in addition to legacy
widget paths, so backend candidates can match direct widget styles across keyed
reorders and use paths only as a fallback/debug view. Path 0 backend readiness
requires evidence that `styleOps` resolve to the `RenderTree` styles and that
layout/paint style properties affect rendered output, not just that the
resolved declarations exist.

The bundle also includes `otoe-run.py`, a minimal generated runner. It adds the
copied `app/` and `framework/` directories to `sys.path`, loads the manifest
target, supports `--check` for import/load validation, and supports `--png
frame.png` for a single headless native PNG frame using styles rehydrated from
the bundled `styleOps` primitive stream. The current native renderer still
receives a `StyleSheet` internally; the important runtime boundary is that the
bundle runner no longer needs source CSS text or workspace styles to reconstruct
that stylesheet. It also supports `--verify` to check referenced bundle files,
sizes, SHA-256 hashes, schema versions, declared backend coverage reports,
backend coverage `evidenceMap` traceability, unmanifested packable files, and
strict Style IR drift through the copied `otoe.style_ops` runtime module. When
the manifest declares `backendPackage`, `--verify` also checks the package
descriptor file hashes against the copied files and runs a Path0 JSON-in/JSON-out
smoke through the backend package entrypoint. Use
`otoe-run.py --backend-package-check` to run only that bundled package smoke.
Builds also emit `otoe-render-tree.json`; when a backend package is declared,
`--verify` runs that package against the bundled `otoe-render-tree.json` and
`otoe-styles.json`, and `otoe-run.py --external-backend-check` runs just that
app-shaped JSON-in/JSON-out backend check. Core bundle artifacts declared
through `plan`, `deps`, `styles`, `renderTree`, and `backendCoverage` must also
appear in `artifacts` with size/hash metadata, and all declared file entries
must use safe relative paths, size metadata, lowercase SHA-256 hashes, and
unique bundle paths. The runner rejects invalid plan, dependency, style, or
RenderTree artifacts even if the manifest hash entries were updated after
tampering. Hardware bundles also keep the
`runtimeInstallsAllowed = false` runner/pack invariant.
`--layout-check` runs native layout/paint validation without writing a PNG.
Runtime style rehydration also validates the same contract by default when
loading `otoe-styles.json`. Pass `otoe build --validate` to run the generated
runner's `--verify`, `--check`, and `--layout-check` modes after writing the
bundle; this confirms the copied files are intact, the target loads from the
bundle instead of only from the workspace, declared backend coverage still
passes with traceable evidence, dependency/style artifacts remain valid, and
compiled styles can drive native rendering.

`otoe pack` verifies the bundle with `otoe-run.py --verify`, repeats strict
Style IR drift detection against `otoe-styles.json`, preserves
`otoe-backend-coverage.json` when the manifest declares it, and writes a
portable `.tar.gz` archive for deployment. The pack step keeps the bundle rooted
at the archive top level, rejects unmanifested files under packable directories
such as `app/`, `framework/`, and `assets/`, and excludes local cache
directories such as `__pycache__/` and `.pytest_cache/`.

Compare JSON contract artifacts:

```bash
python -m otoe compare-contract expected.json actual.json
python -m otoe compare-contract expected.json actual.json --json
python -m otoe compare-contract expected.json actual.json --max-diffs 5
python -m otoe compare-contract expected.json actual.json --ignore-path /pngSmoke/path --ignore-path /calls/raster/signature/0/subject --ignore-path /calls/raster/hash
PYTHONPATH=src:. python -m examples.native.backend_candidate_skeleton --composed-renderer-contract-json --compact-contract --composed-renderer-png /tmp/composed_renderer_candidate.png --contract-out examples/native/contracts/composed_renderer_compact_expected.json
PYTHONPATH=src:. python -m examples.native.backend_candidate_skeleton --backend-readiness-json --contract-out examples/native/contracts/backend_readiness_expected.json
PYTHONPATH=src:. python -m otoe backend-profile native-python --coverage-declaration --out examples/native/contracts/backend_coverage_full_declaration.json
PYTHONPATH=src:. python -m otoe backend-coverage --requirements examples/native/contracts/backend_readiness_expected.json --backend-capability-profile examples/native/contracts/backend_candidate_partial_profile.json
PYTHONPATH=src:. python -m examples.native.backend_candidate_skeleton --style-ops-contract-json --bundle dist/cage --contract-out actual-style-ops-contract.json
```

`otoe compare-contract` performs a deterministic deep JSON comparison, exits
zero only when the contracts match, and reports JSON-pointer paths for
differences. Use `--ignore-path` for intentionally environment-specific JSON
pointer fields. If the composed renderer PNG smoke filename differs from the
fixture, ignore `/pngSmoke/path`, `/calls/raster/signature/0/subject`, and
`/calls/raster/hash` together. Use it with compact renderer contracts when
checking backend candidates in CI. The native backend candidate fixtures at
`examples/native/contracts/composed_renderer_compact_expected.json` and
`examples/native/contracts/backend_readiness_expected.json` are the current
expected compact composed-renderer contract and aggregate readiness report. The
`examples/native/contracts/backend_coverage_full_declaration.json` fixture is
generated from the `native-python` capability profile and records widgets,
inputs, styles, and declared style omissions that profile claims to cover
against the readiness report. Candidate-specific declarations can still be
passed with `--coverage-declaration`, and candidate-specific JSON capability
profiles can be passed with `--backend-capability-profile`. The
bundle-backed StyleOps fixture at
`examples/native/contracts/bundle_style_ops_expected.json` is the expected
contract for the hardware-style `--bundle` path. Refresh these fixtures only
for intentional contract changes, using `--contract-out` instead of shell
redirection.

Run an importable live preview app locally:

```bash
python -m otoe dev examples.live_counter:app --port 8767
```

Generate the static Wraith Mission Exec preview:

```bash
PYTHONPATH=src:. python -m examples.wraith.mission_exec_preview > preview/wraith_mission_exec.html
```

Run the live Wraith Mission Exec preview:

```bash
PYTHONPATH=src:. python -m examples.wraith.mission_exec_live_preview
```

Then open <http://127.0.0.1:8767>. Use `SIMULATE FRAME` to verify that
signals, events, and rerendering are actually changing visible state.

Run the live SaaS preview:

```bash
PYTHONPATH=src:. python -m examples.saas.live_preview
```

Then open <http://127.0.0.1:8766>.

Generate the static UI kit preview:

```bash
PYTHONPATH=src:. python -m examples.ui.preview > preview/ui.html
```

Run the live UI kit preview:

```bash
PYTHONPATH=src:. python -m examples.ui.live_preview
```

Then open <http://127.0.0.1:8768>. Use the sidebar, command launcher,
`Ctrl+K`/`Meta+K`, command search, Enter key, `Escape`, and single-key command
shortcuts to verify the live command overlay and route switching.

Generate the framework-neutral native counter PNG frames through
`NativeSurface`:

```bash
PYTHONPATH=src:. python -m examples.native.counter_demo
```

This writes `preview/native/native_counter_before.png` and
`preview/native/native_counter_after.png`.

Generate the framework-neutral native task board PNG frames:

```bash
PYTHONPATH=src:. python -m examples.native.task_board_demo
```

This writes initial, filtered, and modal frames under `preview/native/`.

Generate native-window driver PNG frames, or open the optional Tk wrapper:

```bash
PYTHONPATH=src:. python -m examples.native.window_demo
PYTHONPATH=src:. python -m examples.native.window_demo --window
```

The `--window` command requires Python's Tk bindings and a graphical display. On
Debian/Ubuntu, install the OS package with:

```bash
sudo apt install python3-tk
```

The `--window` mode uses the experimental native entry point:

```python
from otoe import run_native

run_native(App(), stylesheet=styles, title="Otoe")
```

`run_native(...)` routes through the experimental `NativeBackendAdapter`
boundary. The only built-in backend name today is `"tk"`; it is a manual-test
adapter, not a production desktop backend. The `"tk"` adapter presents native
paint commands on a Tk Canvas so manual windows can show readable text. The
Canvas scales geometry up to 2x for larger windows while keeping font sizes in
logical native units; this is a presentation proof, not responsive layout
reflow. The headless PNG output path remains deterministic and still uses marker
text.

## Tiny Example

```python
from otoe import Button, Text, VStack, component, computed, mount, signal


@component
def Counter():
    count = signal(0)
    label = computed(lambda: f"Clicked {count.value} times")

    return VStack(
        Text(label),
        Button("Increment", onClick=lambda: count.set(count.value + 1)),
        gap=8,
    )


tree = mount(Counter())
```

## Event Signatures

Built-in widget event handlers are plain callables. Otoe validates the handler
arity when the event fires and includes the widget/event contract in developer
errors. Arity mismatches raise `EventHandlerArityError`, which remains an
`EventHandlerError` for compatibility.

| Widget | Event | Handler shape |
| --- | --- | --- |
| `Button` | `onClick` | `lambda: ...` |
| `Button` | `onKeyDown` | `lambda key: ...` |
| `Button` | `onFocus`, `onBlur` | `lambda: ...` |
| `Input` | `onChange` | `lambda value: ...` |
| `Input` | `onKeyDown` | `lambda key: ...` |
| `Input` | `onFocus`, `onBlur` | `lambda: ...` |
| `ScrollView` | `onScroll` | `lambda next_scroll_y: ...` |
| `ShortcutScope` | `onGlobalKeyDown` | `lambda event: ...` |

The same contracts are available programmatically:

```python
from otoe import Button, event_signature_for, format_event_signature

signature = event_signature_for(Button, "onKeyDown")
assert format_event_signature("onKeyDown", signature) == "onKeyDown(key)"
```

The current `otoe.ui` callback surface follows the same style: `onClick()`,
`on_query(value)`, `on_select(command_id | item_id)`, `on_change(value)`,
`on_open_change(open)`, and `on_navigate(route_id)`.

## Project Shape

Otoe is intentionally split into layers:

- **Core runtime:** nodes, components, signals, effects, events, owners, control flow.
- **Renderer boundary:** fake widgets, HTML preview, `NativeSurface`, and an
  early headless native layout/paint/input spike.
- **Style system:** portable style representation and CSS preview adapter.
- **UI kits:** current `otoe.ui` primitives, growing toward libraries inspired by systems like shadcn or Horizon UI.
- **Case studies:** Wraith validates dense operational UI; SaaS validates softer product UI.

## Repository Map

- `src/otoe/` - runtime package.
- `examples/native/` - framework-neutral native renderer spike demos.
- `examples/hardware/`, `examples/admin/`, and `examples/data_workflow/` -
  Phase 5 professional reference apps.
- `examples/wraith/` - Wraith-shaped components and live previews.
- `examples/saas/` - SaaS-shaped generality case study.
- `examples/ui/` - shared UI primitive kitchen-sink preview.
- `preview/` - generated HTML/CSS preview artifacts, including the shared
  `reference_theme.css` base used by the Phase 5 reference apps.
- `tests/` - runtime and preview regression tests.
- `ADR-*.md` - design decisions.
- `BENCHMARKS.md` - concrete Otoe-vs-Wraith UI change benchmarks.
- `COMPONENT_COOKBOOK.md` - small component, state, control-flow, live preview,
  and native smoke recipes.
- `EXAMPLES_GUIDE.md` - current quickstart, live, native, UI kit, SaaS, and
  Wraith example surfaces.
- `REFERENCE_APP_PATTERNS.md` - Phase 5 reference app boundaries, provider
  contracts, and extraction rules.
- `MENTAL_MODEL.md` - how nodes, components, signals, events, control flow,
  mounting, and renderers fit together.
- `NATIVE_WORKFLOWS.md` - when to use HTML render, native PNG,
  `NativeSurface`, `NativeWindowDriver`, and `run_native(...)`.
- `NATIVE_RENDERER_SPIKE.md` - current native renderer support and deferred work.
- `STYLE_GUIDE.md` - supported style parser, token, HTML, and native style
  subset behavior.
- `TESTING_GUIDE.md` - snapshot, HTML, native surface, window driver, PNG, and
  backend acceptance testing guidance.
- `WIDGET_CONTRACTS.md` - core widget, control node, UI component, callback,
  and model contracts.
- `ROADMAP.md` - current status and phase plan.

## Fixture Data

Preview data is fictitious and sanitized. The Wraith examples are design and
runtime case studies; they do not run recon, touch network interfaces, or
perform security operations.

## Status

Current status: post-v0.1.7 workshop hardening. Backend coverage gates,
hardware bundle verification, Style IR packaging hardening, Path0 evidence
hashing, and renderer-boundary cleanup are in the workshop branch. See
`ROADMAP.md` for the active plan and the current public-sync baseline.

## License

MIT License. Copyright (c) 2026 Forvara.
