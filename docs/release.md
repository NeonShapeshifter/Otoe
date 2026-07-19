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
distributions, runs `twine check`, and runs the sdist and installed-wheel
cold-start smokes. The test suite includes the supervised `1000+100`
runtime/host soak. It also checks reproducibility and performance budgets. CI
runs the same package checks after building package metadata.

## Build Tooling Policy

Otoe uses the modern SPDX packaging metadata path. `pyproject.toml` declares
`license = "MIT"` plus `license-files = ["LICENSE"]`, so local release tooling,
CI, and publish jobs require:

- `setuptools>=77`
- `wheel>=0.43`
- `build>=1.2`
- `markdown-it-py>=4.2`
- `packaging>=26.2`
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
python3 scripts/runtime_soak.py --cycles 1000 --host-cycles 100
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

## Installed-Wheel Cold Start

The wheel smoke can be run independently:

```bash
scripts/wheel_smoke.sh
```

It builds a wheel from the checkout and delegates the exact artifact to the
cold-start gate. To test an already-built release artifact without rebuilding
it, run:

```bash
scripts/cold_start_smoke.sh dist/otoe-X.Y.Z-py3-none-any.whl
```

Run it from a release-capable checkout installed with `.[release]`; the
standalone identity probe requires `markdown-it-py>=4.2` and `packaging>=26.2`.
The supervised gate currently requires a GNU/Linux release host with GNU
coreutils `timeout` installed as `/usr/bin/timeout` or `/bin/timeout`. The
official CI and publish jobs run on Ubuntu. macOS, Windows, Nix-only utility
layouts, and Homebrew's `gtimeout` are not supported release-gate hosts yet;
unsupported hosts fail explicitly instead of silently running without the
process-group watchdog.

The cold-start gate binds that exact wheel to a controller-computed SHA-256,
copies it into a temporary directory outside the checkout, and installs it into
a clean virtual environment with `--no-index --no-deps`. The copied artifact is
created under a private umask, changed to read-only mode in a non-writable
artifact directory, and rehashed immediately before and after installation in
addition to finalization. It clears `PYTHONPATH`,
`PYTHONHOME`,
the active virtual environment, `BASH_ENV`, user-site packages, and every
inherited `PIP_*` setting by launching each checked command from an empty
environment. It then reintroduces only the required home/cache paths and the
deliberate pip isolation settings, including `PIP_NO_INDEX=1` and
`PIP_CONFIG_FILE=/dev/null`. The controller also starts the supervised worker
itself through absolute system paths and `env -i`, with only a fixed system
`PATH`, its isolated `HOME`, and a validated test hook when applicable. Exported
shell functions and inherited `BASHOPTS`/`SHELLOPTS` therefore cannot intercept
the worker's setup commands. Before installation, it verifies that the package
README embedded in wheel metadata contains exactly one contiguous fenced
`bash` block whose lines are the canonical quickstart. Commands scattered in
prose or comments, reordered, duplicated, or mixed with extra commands do not
satisfy that contract. The fence is parsed as CommonMark rather than searched
as raw text, so backticks nested inside a larger literal fence do not count.
Wheel identity is accepted only when the canonical
distribution and version agree across the PEP 427 filename, the single
`.dist-info` directory, and structured `METADATA`; this validation uses the
release environment's `packaging` build dependency; `markdown-it-py` supplies
the CommonMark parser. An import probe must then
prove that `otoe` came from the temporary venv and that the source checkout is
absent from `sys.path` before the onboarding flow runs:

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
starts on an OS-assigned port and exposes a local health endpoint, and that
`otoe portable-core --format json` matches the legacy `--json` output both as a
structure and as canonically encoded JSON bytes.

For every worker outcome, including command failure and hard timeout, the
controller atomically writes `cold-start-evidence.json` in the temporary
workdir. The machine-readable evidence contains the tested wheel identity,
controller-bound, source, and copied digests with equality results, interpreter
version, render output digests when available,
completed/partial checks, isolation assertions, timing, worker exit status,
outcome, and a bounded error report.
Its timing scope is
`controller-digest-through-generated-app-validation`; the wheel payload exposes
the expected digest plus expected-to-copy, expected-to-source, and source-to-copy
matches.
The copied artifact must match the controller-bound digest before installation.
The pre-install, post-install, and finalization checks require the copied
artifact to remain equal to that digest; finalization also rehashes the source.
These checks and read-only modes prevent accidental replacement and detect
ordinary concurrent mutation. They are not a security boundary against another
process running as the same user, which can change its own permissions and race
path-based opens. Release hosts and their temporary directories remain trusted.

Worker stdout and stderr are drained through bounded FIFO captures. Each stream
retains at most 1 MiB; excess output is discarded with an explicit truncation
marker, makes the gate fail, and cannot grow the log files without bound. The
bounded error reader seeks directly to the final 4000 bytes rather than loading
the complete error log into memory.

The five-minute product-shape budget starts immediately before the controller
hashes the wheel, before it is copied. It therefore includes digesting the source
artifact, clean-venv creation, offline installation, and the complete
generated-app validation through `check`, HTML/native rendering,
`dev`, and bundle validation; it excludes building or downloading the wheel.
GNU `timeout` supervises the whole worker process group; the worker must finish
strictly before 300 seconds. At 300 seconds it sends `TERM` and escalates to
`KILL` five seconds later, so a hung child cannot turn
the budget into a post-hoc assertion. The controller then records monotonic
elapsed time, scope, budget, partial results, and timeout outcome. The script
prints the timing, evidence path, and wheel digest in CI/release logs. Use
`OTOE_COLD_START_WORKDIR` for a deliberate empty output directory; paths inside
the source checkout and nonempty directories are rejected rather than deleted.
`wheel_smoke.sh` exposes the same choice as `OTOE_SMOKE_WORKDIR`.

GitHub Actions fixes that workdir under `${{ runner.temp }}/otoe-cold-start`,
prints both the evidence-file and tested-wheel SHA-256 values into the log and
job summary, and uploads the JSON with `if: always()`. CI matrix artifacts are
named `cold-start-evidence-py<python-version>-attempt<run-attempt>`; the tag
workflow uses `cold-start-evidence-publish-attempt<run-attempt>`. The evidence artifact is separate from
`release/packages`, so the PyPI publisher still receives only the wheel and
sdist.

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

Before creating any release tag, GitHub must have an active tag ruleset targeting
`v*` with both tag updates and tag deletions restricted and no normal bypass.
This is a manual repository-settings gate: the local release script cannot prove
it. Confirm it again immediately before tag creation. The rule must allow a new
tag to be created while preventing a published tag from being moved or deleted.

The build uses the release commit timestamp as `SOURCE_DATE_EPOCH`, the
constrained build backend, and normalized sdist ownership and timestamps. Two
independent rebuilds must match each other and the exact wheel and sdist in
`dist/` byte for byte. The artifact identity gate rejects extra distributions
and requires the canonical project/tag version in both filenames, wheel
`METADATA`, the sdist top directory, and `PKG-INFO`. Those same files that pass
the identity and smoke tests are copied into one
checksummed GitHub artifact, attested with GitHub build provenance, downloaded
by the publish job, checksum-verified, and uploaded without rebuilding.

After the public sync, freeze and verify the public commit before creating a
PyPI tag:

```bash
cd /home/ale/Otoe-public
PUBLIC_COMMIT="$(git rev-parse HEAD)"
git fetch --no-tags origin +refs/heads/main:refs/remotes/origin/main
test "$(git rev-parse refs/remotes/origin/main)" = "$PUBLIC_COMMIT"
```

Wait until the `CI` matrix and `CodeQL` run for `PUBLIC_COMMIT` complete, then
verify their exact workflow runs and jobs through the Actions API:

```bash
RELEASE_CHECK_REPOSITORY="NeonShapeshifter/Otoe" \
RELEASE_CHECK_SHA="$PUBLIC_COMMIT" \
RELEASE_CHECK_TOKEN="$(gh auth token)" \
python3 -I scripts/verify_release_checks.py
```

The verifier binds `CI` and `CodeQL` to their workflow files, the `main` branch,
the `push` event, and the exact SHA. It then requires `tests (3.11)`,
`tests (3.12)`, `tests (3.13)`, `tests (3.14)`, and `Analyze Python` in those exact
workflow attempts. Missing, pending, unsuccessful, ambiguous, malformed, or
unreadable evidence fails closed. The tag workflow repeats this API gate with
`actions: read`
before installing release dependencies or building, so an early tag cannot reach
the artifact or PyPI jobs.

Only after that verifier and all local release checks succeed, create the tag on
the frozen public commit:

```bash
test "$(git rev-parse HEAD)" = "$PUBLIC_COMMIT"
git tag -a vX.Y.Z "$PUBLIC_COMMIT" -m "Release vX.Y.Z" -m "Publish-PyPI: yes"
git push origin vX.Y.Z
```

## Local Build Shadowing

If `python -m build` behaves strangely in a local checkout, remove stale build
artifacts first:

```bash
rm -rf build dist src/*.egg-info ./*.egg-info
```

`scripts/release_check.sh` does that cleanup before running the release flow.
