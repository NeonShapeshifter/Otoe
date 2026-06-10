# Offline Build

The offline build path is Otoe's first hardware/cage workflow. It is meant to
prove that an app can be planned, audited, copied, validated, and packed before
deployment to a constrained target.

## Minimal Build

```bash
otoe build app:app --out dist/cage --css styles.css --validate
```

`--validate` runs generated runner checks from inside the bundle directory:

- `--verify`
- `--check`
- `--layout-check`

## Profile File

For repeatable builds, use `otoe.profile.toml`:

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
# coverage_requirements = "backend-readiness.json"

[native.text]
renderer = "pillow"
font = "fonts/Inter.ttf"

[deps]
packages = ["Pillow"]
extras = []
```

Then run:

```bash
otoe plan app:app --profile-file otoe.profile.toml --out dist/otoe-plan.json
otoe deps app:app --profile-file otoe.profile.toml --json
otoe build app:app --profile-file otoe.profile.toml --out dist/cage --validate
otoe pack dist/cage --out dist/cage.tar.gz
```

## What The Bundle Contains

The build writes core artifacts:

- `manifest.json`
- `otoe-plan.json`
- `otoe-deps.json`
- `otoe-styles.json`
- `otoe-render-tree.json`
- copied `app/` runtime files
- copied `framework/` Otoe runtime files
- copied assets when declared
- copied native text font when `[native.text]` uses Pillow
- optional backend package files
- optional backend coverage reports
- `otoe-run.py`

The generated runner verifies declared files, sizes, SHA-256 hashes, schema
versions, core artifacts, dependency audit metadata, style artifact drift,
RenderTree validity, runtime file policy, and backend coverage traceability
when present.

## Dependency Audit

`otoe deps` is an audit-only check. It does not install packages, download
wheels, or create a lockfile. It reports missing packages, undeclared external
imports, visible dynamic import calls, and visible stdlib network/process usage
according to `[runtime.policy]`.

Use `[runtime] files` for dynamic imports and files the static local import
scanner cannot see.

## Style Artifacts

`otoe-styles.json` records portable class styles, direct widget styles,
diagnostics, backend capability metadata, and low-level `styleOps`. Bundle
runtime checks rehydrate styles from that artifact instead of requiring source
CSS on the target.

## Native Text

Readable native PNG text is currently available through the optional Pillow
renderer path for `otoe render`:

```bash
python -m pip install "otoe[native-text]"
otoe render app:app --out preview.png --native --native-text pillow --font fonts/Inter.ttf --css styles.css
```

Offline bundles use the same renderer boundary through profile configuration:

```toml
[native.text]
renderer = "pillow"
font = "fonts/Inter.ttf"

[deps]
packages = ["Pillow"]
```

The font path must be relative to the profile file. `otoe build` copies it into
`assets/`, records its size and SHA-256 in `manifest.json`, and the generated
`otoe-run.py` uses it for `--layout-check` and `--png`. Do not also list that
same font in `assets`; duplicate bundle paths are rejected during verification.

The generated runner also accepts raster scaling for native PNG evidence:

```bash
dist/cage/otoe-run.py --png preview@2x.png --scale 2
```

The scale multiplies the written PNG dimensions while keeping layout units,
hit testing, and bundled style evidence in logical coordinates.

## Advanced Gates

Backend coverage requirements and backend package manifests are advanced
renderer-candidate features. Keep them out of the first app-authoring workflow
unless you are validating a backend.
