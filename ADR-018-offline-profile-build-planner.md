# ADR-018: Offline Profile Build Planner

**Status:** Proposed
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

The first diagnostic slice exists as `otoe plan`. The broader command shape is:

```bash
otoe plan app:app --profile cage
otoe deps app:app --profile cage
otoe build app:app --profile cage --out dist/cage
otoe build app:app --profile cage --out dist/cage --validate
otoe pack dist/cage --out dist/cage.tar.gz
```

`otoe plan` is implemented as an import/mount/style diagnostic. It supports a
machine-readable `--json` report, `--out` JSON artifact, and an optional
`otoe.profile.toml` manifest. `otoe deps` is implemented as an audit-only
dependency check for profile-declared packages and Otoe extras. It does not
install packages, touch the network, or write artifacts when run directly.
`otoe build` is implemented as a minimal bundle contract that writes
`otoe-plan.json`, `otoe-deps.json`, `otoe-styles.json`, selected
`frameworkFiles`, and `manifest.json`, plus a generated `otoe-run.py` runner.
The first framework copy policy supports the built-in `native` backend only;
future backend candidates must add explicit file sets instead of relying on
import discovery.
`otoe pack` is implemented as a verify-before-archive step that creates a
portable `.tar.gz` from the generated bundle without local cache directories.

The initial profile file shape is:

```toml
profile = "cage"
utilities = true
css = ["styles.css"]
assets = ["static/logo.png"]

[runtime]
allow_runtime_installs = false
files = ["app.py"]

[backend]
name = "native"

[deps]
packages = ["pytest"]
extras = ["dev"]
```

Profile CSS, asset, and runtime file paths are relative to the profile file.
Asset and runtime file paths must be relative files and must not contain `.` or
`..`. Explicit CLI flags override the profile file. `allow_runtime_installs =
true` is invalid for `cage`. Dependency package and extra names are explicit
build-machine requirements. Missing packages are reported by `otoe deps` so the
developer can install them manually before building or deploying.

Profiles are explicit build targets. A `cage` or hardware profile would declare
the renderer/backend candidate, allowed style surface, asset policy, optional
extras, and runtime constraints. The planner should produce diagnostics before a
deployment artifact is built.

`otoe build` should emit an offline bundle containing:

- app code/runtime files copied from a simple local target module such as
  `app.py` for `app:app`, plus explicit `[runtime] files` entries for helper
  modules, package code, and extra files, with `runtimeFiles` manifest entries
  containing source path, bundle path, byte size, and SHA-256
- selected backend/runtime framework files copied under `framework/` with
  `frameworkFiles` manifest entries containing source path, bundle path, byte
  size, and SHA-256
- a generated runner entry, initially `otoe-run.py`, that adds the copied
  `app/` and `framework/` directories to `sys.path`, loads the manifest target,
  supports file integrity `--verify`, supports a load-only `--check`, supports
  layout/paint dry-run validation with `--layout-check`, and can render one
  headless PNG frame with `--png` using the bundled compiled styles
- optional bundle validation through `otoe build --validate`, which runs the
  generated runner in `--verify`, `--check`, and `--layout-check` modes after
  writing artifacts so the copied bundle must be intact, load the manifest
  target, and drive native layout/paint with bundled styles
- a deployment archive step, currently `otoe pack`, that runs the generated
  runner in `--verify` mode, writes a top-level bundle `.tar.gz`, and excludes
  local cache directories such as `__pycache__/` and `.pytest_cache/`
- assets copied for the profile with manifest entries containing source path,
  bundle path, byte size, and SHA-256
- a compiled portable style plan, initially shaped by the `otoe plan --out`
  JSON artifact and persisted as `otoe-styles.json` with used classes, resolved
  portable declarations, omitted html-only/deferred declarations, diagnostics,
  and tokens
- a dependency audit artifact, currently `otoe-deps.json`, proving that
  profile-declared dependencies passed on the build machine
- diagnostics for portable, html-only, deferred, and invalid styling
- lock/manifest metadata for reproducibility

No runtime dependency installs are allowed on the hardware target. The current
contract is audit-only: `otoe deps` shows which declared packages or extras are
missing from the development/build environment, and the user decides how to
install them. It should not infer arbitrary imports or install packages on the
device while the app is running.

## Style Compilation

The style path should compile before deployment:

- Parse Otoe's constrained CSS subset and utility classes into `StyleSheet`.
- Resolve tokens and class combinations ahead of runtime when possible.
- Classify declarations by renderer support: portable, html-only, deferred, or
  invalid for the chosen profile.
- Cache repeated class combinations so the runtime can apply compact style ops.
- Keep custom browser CSS available for HTML previews, but do not pretend that
  every browser CSS feature is native behavior.

This keeps the authoring format familiar while preserving a small native
runtime. The device receives a resolved plan; it does not own the full CSS
language.

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
