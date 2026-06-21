# Release Checks

Use the release check before tagging or publishing a package:

```bash
scripts/release_check.sh
```

When promoting work from `/home/ale/Otoe` into `/home/ale/Otoe-public`, use the
[publication sync checklist](publication-sync-checklist.md). `Otoe-public` is
the manual publication point; this repository does not publish automatically.

The script removes stale local build artifacts, installs local dev/release plus
`native-text` extras, verifies generated Portable Core UI docs, compiles source
files, runs Ruff, mypy, tests, builds distributions, runs `twine check`, and
runs the sdist and installed-wheel smokes. CI runs both smoke tests after
building and checking package metadata.

## Build Tooling Policy

Otoe uses the modern SPDX packaging metadata path. `pyproject.toml` declares
`license = "MIT"` plus `license-files = ["LICENSE"]`, so local release tooling,
CI, and publish jobs require:

- `setuptools>=77`
- `wheel>=0.43`
- `build>=1.2`
- `twine>=6`

Do not downgrade the build backend to support `setuptools<77` unless the license
metadata policy is deliberately revisited. The older
`license = { text = "MIT" }` form is intentionally not used because modern
setuptools treats it as deprecated metadata. There is no release lockfile yet;
the lightweight policy is explicit minimum versions shared by `pyproject.toml`,
the release scripts, and GitHub workflows.

If the Portable Core UI matrix changes, regenerate the docs before release:

```bash
python3 scripts/update_portable_core_docs.py
```

The focused local validation commands are:

```bash
python3 -m compileall -q src examples tests
python3 scripts/update_portable_core_docs.py --check
python3 -m ruff check src tests examples scripts
python3 -m mypy src/otoe
python3 -m pytest -q
```

Coverage is tracked as a diagnostic command, not a release threshold yet:

```bash
python3 -m pytest --cov=otoe --cov-report=term-missing
```

After building distributions, check only package artifacts so unrelated
directories in `dist/` do not break local release validation:

```bash
python3 -m twine check dist/*.whl dist/*.tar.gz
```

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

The smoke also verifies that the generated app works with `otoe check --tests`
outside the Otoe source checkout, that `otoe dev app:app --css styles.css`
starts a local health endpoint, and that `otoe portable-core --format json`
matches the legacy `--json` output.

## Source Distribution Smoke

The source distribution smoke can be run independently after `python -m build`:

```bash
scripts/sdist_smoke.sh
```

It extracts the built `.tar.gz`, verifies that `src/`, `tests/`, `examples/`,
and `docs/` are present, compiles `src examples tests`, and runs focused tests
that import source-checkout examples and backend package fixtures. This keeps
the sdist auditable without duplicating the full test suite in release checks.

By default, `wheel_smoke.sh` allows normal build isolation. In CI or release
environments where modern build tooling is already installed, use:

```bash
OTOE_SMOKE_NO_BUILD_ISOLATION=1 scripts/wheel_smoke.sh
```

CI runs this smoke after building and checking package metadata. The publish
workflow also runs it before uploading the distribution artifact. Publishing
from a tag checks that `vX.Y.Z` matches `project.version` in `pyproject.toml`
before building.

The publish workflow uses PyPI `skip-existing` so rerunning a successful tag
upload does not fail only because the same files are already present. This does
not replace a broken published version; PyPI artifacts are immutable, so a
release that reached PyPI still needs a version bump.

## Local Build Shadowing

If `python -m build` behaves strangely in a local checkout, remove stale build
artifacts first:

```bash
rm -rf build dist src/*.egg-info ./*.egg-info
```

`scripts/release_check.sh` does that cleanup before running the release flow.
