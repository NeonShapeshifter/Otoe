# Release Checks

Use the release check before tagging or publishing a package:

```bash
scripts/release_check.sh
```

The historical v0.1.9 tag/source mismatch is recorded in
[v0.1.9 Provenance](releases/v0.1.9-provenance.md). Do not move that tag again.

When promoting work from `/home/ale/Otoe` into `/home/ale/Otoe-public`, use the
[publication sync checklist](publication-sync-checklist.md). `Otoe-public` is
the manual source publication point. PyPI package publication is separate and
requires the deliberate tag gate described below.

The script removes stale local build artifacts, installs constrained local
dev/release plus `native-text` extras, verifies generated Portable Core UI docs,
checks installed dependency consistency, compiles source files, runs Ruff,
strict mypy, stub/runtime parity, tests with the coverage gate, builds
distributions, runs `twine check`, and runs the sdist and installed-wheel smokes.
It also checks reproducibility and performance budgets. CI runs the same package
checks after building package metadata.

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
setuptools treats it as deprecated metadata. `pyproject.toml` declares supported
minimums; `requirements/ci-constraints.txt` fixes the direct CI and release
tools. Editable release-test installs use `--no-build-isolation`, and release
builds use `--no-isolation`, so both use the constrained build backend instead
of a separately resolved isolated environment. Transitive dependencies are not
fully locked yet.

If the Portable Core UI matrix changes, regenerate the docs before release:

```bash
python3 scripts/update_portable_core_docs.py
```

The focused local validation commands are:

```bash
python3 -m compileall -q src examples tests
python3 scripts/update_portable_core_docs.py --check
python3 -m ruff check src tests examples scripts
python3 -m mypy --strict src/otoe
python3 -m mypy.stubtest otoe --allowlist tests/stubtest_allowlist.txt
python3 -m pytest -q --cov=otoe --cov-report=term-missing --cov-fail-under=82
```

Coverage must remain at or above the configured release threshold:

```bash
python3 -m pytest --cov=otoe --cov-report=term-missing --cov-fail-under=82
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
from a tag first requires an annotated `vX.Y.Z` tag whose message contains this
exact marker on its own line:

```text
Publish-PyPI: yes
```

The workflow then checks that `vX.Y.Z` matches `project.version` in
`pyproject.toml` before building. A lightweight tag, or an annotated tag without
the marker, fails before building and never reaches the PyPI upload job.

The workflow does not use PyPI `skip-existing`. Reusing or moving a published
version must fail loudly because PyPI artifacts are immutable. A release that
reached PyPI always needs a version bump, even when its tag or source metadata
was wrong.

The build uses the release commit timestamp as `SOURCE_DATE_EPOCH`, the
constrained build backend, and normalized sdist ownership and timestamps. Two
independent rebuilds must match each other and the exact wheel and sdist in
`dist/` byte for byte. Those same files that pass smoke tests are copied into one
checksummed GitHub artifact, attested with GitHub build provenance, downloaded
by the publish job, checksum-verified, and uploaded without rebuilding.

Create the PyPI publish tag only after the release checks and public sync are
complete:

```bash
git tag -a vX.Y.Z -m "Release vX.Y.Z" -m "Publish-PyPI: yes"
git push origin vX.Y.Z
```

## Local Build Shadowing

If `python -m build` behaves strangely in a local checkout, remove stale build
artifacts first:

```bash
rm -rf build dist src/*.egg-info ./*.egg-info
```

`scripts/release_check.sh` does that cleanup before running the release flow.
