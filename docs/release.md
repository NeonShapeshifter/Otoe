# Release Checks

Use the release check before tagging or publishing a package:

```bash
scripts/release_check.sh
```

The script removes stale local build artifacts, installs local dev/release plus
`native-text` extras, compiles source files, runs tests, builds distributions,
runs `twine check`, and runs the installed-wheel smoke.

## Installed-Wheel Smoke

The wheel smoke can be run independently:

```bash
scripts/wheel_smoke.sh
```

It builds a wheel from the checkout, installs it into a clean virtual
environment, then verifies the installed-package onboarding flow:

```bash
otoe new app
otoe render app:app --out preview.html --css styles.css --pretty
otoe render app:app --out preview.png --native --css styles.css
otoe build app:app --out dist/cage --css styles.css --validate
otoe portable-core
otoe portable-core --json
```

The `portable-core` checks prove that the installed wheel exposes the packaged
Portable Core UI v0 support matrix as both text and JSON, not only from a source
checkout.

By default, `wheel_smoke.sh` allows normal build isolation. In CI or release
environments where modern build tooling is already installed, use:

```bash
OTOE_SMOKE_NO_BUILD_ISOLATION=1 scripts/wheel_smoke.sh
```

CI runs this smoke after building and checking package metadata. The publish
workflow also runs it before uploading the distribution artifact.

## Local Build Shadowing

If `python -m build` behaves strangely in a local checkout, remove stale build
artifacts first:

```bash
rm -rf build dist src/*.egg-info ./*.egg-info
```

`scripts/release_check.sh` does that cleanup before running the release flow.
