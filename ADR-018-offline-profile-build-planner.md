# ADR-018: Offline Profile Build Planner

**Status:** Accepted
**Date:** May 28, 2026

## Context

Otoe wants authoring to feel close to modern frontend work: component functions,
tokens, utility classes, custom CSS where needed, and reusable UI presets. The
hardware/cage/OS-style target is different from a browser preview, though. A
small device runtime should not install packages, parse a large CSS universe, or
ship a browser CSS engine just so an app can look polished.

The practical goal is CSS-facing, not browser-CSS-powered. Developers should be
able to write familiar styling, but Otoe should resolve as much as possible on a
development/build machine before anything is deployed to constrained hardware.

## Decision Direction

Introduce an offline profile planner and build path before treating hardware
deployment as a product workflow.

The first slice of this decision is implemented: plan/deps/build/pack, strict
bundle verification, hermetic packable paths, Style IR/styleOps artifacts, and
backend coverage gates exist. The remaining work is turning the renderer
candidate boundary into a stable external ABI and adding stronger offline
dependency closure tooling beyond audit-only package checks.

The first diagnostic slice exists as `otoe plan`. The broader command shape is:

```bash
otoe plan app:app --profile cage
otoe plan app:app --profile cage --backend native-python
otoe deps app:app --profile cage
otoe build app:app --profile cage --out dist/cage
otoe build app:app --profile cage --out dist/cage --validate
otoe pack dist/cage --out dist/cage.tar.gz
```

`otoe plan` is implemented as an import/mount/style diagnostic. It supports a
machine-readable `--json` report, `--out` JSON artifact, and an optional
`otoe.profile.toml` manifest. `otoe deps` is implemented as an audit-only
dependency check for profile-declared packages, Otoe extras, and static external
imports found in discovered local runtime files. It does not install packages,
touch the network, import the app target, or write artifacts when run directly.
It also records audit-only runtime policy findings for visible stdlib network
and process-spawning usage; the policy can warn by default or fail stricter
hardware profiles.
`otoe build` is implemented as a minimal bundle contract that writes
`otoe-plan.json`, `otoe-deps.json`, `otoe-styles.json`, selected
`frameworkFiles`, and `manifest.json`, plus a generated `otoe-run.py` runner.
The first framework copy policy supports the built-in `native` backend only;
future backend candidates must add explicit file sets instead of relying on
import discovery.
`otoe-run.py --verify` checks bundle integrity plus strict Style IR drift
detection through copied runtime code. `otoe pack` is implemented as a
verify-before-archive step that repeats strict Style IR validation, then creates
a portable `.tar.gz` from the generated bundle without local cache directories
or unmanifested files in packable bundle directories.

The initial profile file shape is:

```toml
profile = "cage"
utilities = true
css = ["styles.css"]
assets = ["static/logo.png"]

[styles]
safelist = ["is-danger", "bg-alert"]

[runtime]
allow_runtime_installs = false
files = ["app.py"]

[runtime.policy]
network = "warn"
subprocess = "warn"

[backend]
name = "native"
capability = "native-python"

[deps]
packages = ["pytest"]
extras = ["dev"]
```

Profile CSS, asset, and runtime file paths are relative to the profile file.
Asset and runtime file paths must be relative files and must not contain `.` or
`..`. `[styles].safelist` declares class names that should be compiled even
when they do not appear in the first mounted render. Each entry is one class
name, not a space-separated class list. Explicit CLI flags override the profile
file. `allow_runtime_installs = true` is invalid for `cage`. Dependency package
and extra names are explicit build-machine requirements. Missing packages and
undeclared static external imports are reported by `otoe deps` so the developer
can install or declare them manually before building or deploying. When package
metadata maps an import module to a different distribution name, the declared
dependency should be the distribution package, such as `Pillow` for
`import PIL`; imports with no installed package metadata are reported without package
candidates. `[runtime.policy]` uses `allow`, `warn`, or `error` for `network`
and `subprocess`; it is static source audit, not a runtime sandbox.

Profiles are explicit build targets. A `cage` or hardware profile would declare
the renderer/backend candidate, allowed style surface, asset policy, optional
extras, and runtime constraints. The planner should produce diagnostics before a
deployment artifact is built.

`otoe build` should emit an offline bundle containing:

- app code/runtime files copied from a local target module or package such as
  `app.py` for `app:app` or `workspace_pkg/app.py` for
  `workspace_pkg.app:app`, static local imports such as `import helpers`,
  `from helpers import view`, or `from .views import card`, plus explicit
  `[runtime] files` entries for dynamic import edges and extra files, with
  `runtimeFiles` manifest entries containing source path, bundle path, byte
  size, and SHA-256
- selected backend/runtime framework files copied under `framework/` with
  `frameworkFiles` manifest entries containing source path, bundle path, byte
  size, and SHA-256
- a generated runner entry, initially `otoe-run.py`, that adds the copied
  `app/` and `framework/` directories to `sys.path`, loads the manifest target,
  supports file integrity `--verify`, supports a load-only `--check`, supports
  layout/paint dry-run validation with `--layout-check`, and can render one
  headless PNG frame with `--png` using the bundled compiled styles. Every
  runner mode validates `schemaVersion = 1` for `manifest.json`,
  `otoe-plan.json`, `otoe-deps.json`, and `otoe-styles.json` before loading the
  target or rendering a frame. It also enforces the backend framework policy so
  a `native` bundle must declare and include the expected `frameworkFiles` set.
  Core top-level artifacts must be listed in `manifest.json` `artifacts` with
  size/hash metadata, invalid plan/dependency/style artifact status is rejected
  even after hash updates, `runtimePolicy.mode = "audit-only"` is verified, and
  `runtimeInstallsAllowed = false` remains a runner/pack invariant for hardware
  bundles.
- optional bundle validation through `otoe build --validate`, which runs the
  generated runner in `--verify`, `--check`, and `--layout-check` modes after
  writing artifacts so the copied bundle must be intact, load the manifest
  target, and drive native layout/paint with bundled styles
- a deployment archive step, currently `otoe pack`, that runs the generated
  runner in `--verify` mode, repeats strict Style IR validation, preserves
  declared backend coverage artifacts, rejects unmanifested packable files under
  `app/`, `assets/`, and `framework/`, writes a top-level bundle `.tar.gz`, and
  excludes local cache directories such as `__pycache__/` and `.pytest_cache/`
- assets copied for the profile with manifest entries containing source path,
  bundle path, byte size, and SHA-256
- a compiled portable style plan, initially shaped by the `otoe plan --out`
  JSON artifact and persisted as `otoe-styles.json` with used classes,
  safelisted classes, resolved portable declarations, omitted
  html-only/deferred declarations, diagnostics, tokens, and deterministic
  low-level `styleOps` tied to the selected backend capability profile that
  backend candidates can consume without re-parsing CSS on the target device
- a dependency audit artifact, currently `otoe-deps.json`, proving that
  profile-declared dependencies and static external runtime imports passed on
  the build machine, with `resolution.mode = "audit-only"` and no lockfile or
  wheel closure claim
- an optional backend coverage gate, currently declared with
  `[backend].coverage_requirements` or `--backend-coverage-requirements`, that
  compares the selected backend capability profile against a
  readiness/requirements JSON artifact, validates strict evidence source/gate
  metadata plus Path 0 runtime style proof for each declared support phase, and
  writes
  `otoe-backend-coverage.json` before the bundle manifest is allowed
- diagnostics for portable, html-only, deferred, and invalid styling
- manifest/hash metadata for reproducibility; dependency lockfiles and wheel
  closure remain future work outside the current audit-only gate

No runtime dependency installs are allowed on the hardware target. The current
contract is audit-only: `otoe deps` shows which declared packages or extras are
missing from the development/build environment and which static external
imports are not declared in `[deps] packages`. It also reports visible
`importlib.import_module(...)` and `__import__(...)` dynamic import calls as
warnings, including literal module names when they are statically available.
`otoe-deps.json` records this as `resolution.mode = "audit-only"` with no
lockfile or wheel closure, and records runtime policy as
`runtimePolicy.mode = "audit-only"`. The user decides how to install or declare
them. It should not infer arbitrary dynamic imports, guess unknown distribution
names, sandbox arbitrary Python execution, or install packages on the device
while the app is running.

## Style Compilation

The style path should compile before deployment:

- Parse Otoe's constrained CSS subset and utility classes into `StyleSheet`.
- Resolve tokens and class combinations ahead of runtime when possible.
- Emit low-level `styleOps` for portable declarations so native and hardware
  backends can apply resolved operations instead of interpreting CSS text.
  The generated runner currently rehydrates a `StyleSheet` from that primitive
  stream before calling the Python native renderer; this proves CSS text is not
  required at bundle runtime. Renderer candidates receive a separate
  `RenderTree` IR v0 boundary with normalized props/events/state and
  `ResolvedStyleMap` values rehydrated from `styleOps`; backend readiness
  replays minimal, task board, keyed reorder, and `Show` branch tree shapes.
  The artifact-backed path can verify a bundle, load the target from
  `manifest.json`, and render that target through the same `styleOps` to
  `ResolvedStyleMap` boundary. That tree is not yet a stable Skia/Taffy/Qt ABI.
- Statically extract literal class tokens from local target modules/packages and
  static local imports, including conditional literal branches inside
  `className` expressions.
- Compile profile safelist classes ahead of runtime so dynamic state classes can
  be selected on-device without parsing arbitrary CSS.
- Classify declarations by renderer support: portable, html-only, deferred, or
  invalid for the chosen profile.
- Record the backend capability profile in `otoe-plan.json` and
  `otoe-styles.json` so style, widget, and input support are explicit artifacts
  instead of implicit global runtime assumptions.
- When backend coverage requirements are declared, record the comparison in
  `otoe-plan.json`, persist it as `otoe-backend-coverage.json` during build,
  and reject the bundle manifest when coverage blockers remain.
- Cache repeated class combinations so the runtime can apply compact style ops.
- Keep custom browser CSS available for HTML previews, but do not pretend that
  every browser CSS feature is native behavior.

This keeps the authoring format familiar while preserving a small native
runtime. The device receives a resolved plan; it does not own the full CSS
language.

Dynamic class names for hardware/cage profiles must be statically knowable:
they appear in the initial mounted tree, are literal class tokens in local
`className` expressions that `otoe plan` can extract, or are listed in
`[styles].safelist`. Arbitrary string-built classes such as `bg-${color}` remain
outside the portable contract unless the possible outputs are safelisted.
When `otoe plan` sees a dynamic `className` f-string or string interpolation it
emits a warning with the source file and line so the author can safelist the
possible output classes before building for hardware.

## Consequences

- Otoe can support customization without choosing between beauty and low-level
  deployment.
- The build machine owns dependency resolution, style diagnostics, and bundle
  shape.
- Backend candidates get a clearer acceptance surface: they must document which
  compiled style ops they honor for each profile.
- Browser CSS parity remains a non-goal for hardware profiles.
- The current `utility_css()` and `utility_stylesheet()` APIs are early pieces
  of this direction, not the final profile planner.
