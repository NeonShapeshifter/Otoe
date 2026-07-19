# Publication Sync Checklist

This checklist is for manually promoting changes from the working repository
(`/home/ale/Otoe`) into the public repository (`/home/ale/Otoe-public`) when you
decide to publish source. `Otoe-public` is the manual source publication point.
PyPI package publication is a separate release action gated by an annotated tag
with an explicit publish marker.

Use this as a deliberate gate before every public sync. The goal is to publish
reviewed source, docs, tests, and intended examples without copying local
environments, caches, build outputs, or undecided experiments.

## 1. Review the Working Repository

Start in the working repository:

```bash
cd /home/ale/Otoe
git status --short --branch
git diff --stat
git diff --cached --stat
git ls-files --others --exclude-standard
```

Read the actual changes when the stats are not enough:

```bash
git diff
git diff --cached
```

Decide whether the current branch contains one coherent public update. The sync
source will be a commit, never the current working tree. If it contains unrelated
tracked experiments, split them out before creating the promotion commit.

## 2. Decide Experimental Files

Review new or experimental work before it enters the public repository:

```bash
git status --short
git ls-files --others --exclude-standard
find /home/ale/Otoe -maxdepth 3 -type d -name backend_spikes -print
```

Use these categories:

| Category | Action |
| --- | --- |
| Public product/docs direction | Copy when reviewed and consistent with the North Star. |
| Renderer/backend contributor work | Copy only when documented as advanced or experimental. |
| Case studies and generated previews | Copy only when the checked-in HTML/CSS/docs are intentional. |
| Local research notes or scratch spikes | Keep unpublished unless explicitly promoted. |
| Build/test/cache outputs | Never copy. |

## Intentional Unpublished Work

All tracked files in the promotion commit are public. Keep a short note before
syncing if known work remains private or local-only, and keep that work out of
the promotion commit. Examples:

```text
Intentional unpublished work for this sync:
- docs/display-list-v0.md: keep local until the display-list contract is reviewed.
- examples/native/backend_spikes/: keep local research; not part of public examples.
- preview/generated-experiment.html: generated scratch artifact; do not publish.
```

When a file moves from this list into the promotion commit, make the decision
visible in the public commit message or PR description. Do not use rsync
exclusions to create an undocumented second version of a tracked source tree.

## 3. Scan for Files That Must Not Be Copied

These paths and artifacts should never be copied from `Otoe` to `Otoe-public`:

- `.venv/`
- `build/`
- `dist/`
- `dist-wheel-smoke/`
- `.pytest_cache/`
- `.hypothesis/`
- `.ruff_cache/`
- `.mypy_cache/`
- `.coverage`
- `.coverage.*`
- `htmlcov/`
- `preview/native/` when it contains ignored, locally generated frames
- `__pycache__/`
- `*.egg-info/`
- `src/*.egg-info/`
- `.claude/settings.local.json`
- `.agents/`
- `.codex/`

Run a pre-sync scan:

```bash
find /home/ale/Otoe \
  \( -name .venv \
  -o -name build \
  -o -name dist \
  -o -name dist-wheel-smoke \
  -o -name .pytest_cache \
  -o -name .hypothesis \
  -o -name .ruff_cache \
  -o -name .mypy_cache \
  -o -name __pycache__ \
  -o -name "*.egg-info" \
  -o -path "/home/ale/Otoe/src/*.egg-info" \
  -o -name htmlcov \
  -o -path "/home/ale/Otoe/preview/native" \
  -o -name .coverage \
  -o -name ".coverage.*" \
  -o -path "/home/ale/Otoe/.claude/settings.local.json" \
  -o -path "/home/ale/Otoe/.agents" \
  -o -path "/home/ale/Otoe/.codex" \) -print
```

Seeing these paths in the working repo is normal. Seeing them in the sync plan
is a blocker.

## 4. Freeze A Promotion Commit

Commit the coherent source state, then require a clean tree:

```bash
cd /home/ale/Otoe
git add -A
git diff --cached
git commit -m "Prepare public source promotion"
test -z "$(git status --porcelain)"
SOURCE_COMMIT="$(git rev-parse HEAD)"
git show --stat --oneline "$SOURCE_COMMIT"
```

If the clean-tree test fails, stop. Never promote from a dirty tree and never
amend the source commit after recording `SOURCE_COMMIT`.

## 5. Run Release Checks From The Exact Commit

Validation starts only after the promotion commit is frozen. Confirm that `HEAD`
is still the recorded commit and that neither the index nor working tree changed,
then run the local reference command:

```bash
test "$(git rev-parse HEAD)" = "$SOURCE_COMMIT"
test -z "$(git status --porcelain)"
scripts/release_check.sh
test "$(git rev-parse HEAD)" = "$SOURCE_COMMIT"
test -z "$(git status --porcelain)"
```

The release script rejects staged, unstaged, or untracked source changes before
it removes or creates build outputs, fixes `SOURCE_DATE_EPOCH` to the recorded
commit, and revalidates both HEAD and source status before building and after all
checks. It builds reproducible distributions, rejects extra archives, verifies
filename and internal metadata identity, and smoke-tests the exact wheel and
sdist from `SOURCE_COMMIT`; do not substitute a smoke that rebuilds from a
different checkout state.

For a smaller docs-only or planning sync, still run the relevant focused checks
after freezing the commit and record what was intentionally skipped:

```bash
python3 -m compileall -q src examples tests
python3 -m pytest -q
```

If a check requires a source fix, create a new commit, update `SOURCE_COMMIT`,
require a clean tree again, and rerun the checks. Do not amend the recorded commit
or reuse evidence from its predecessor. Build artifacts are validation outputs;
do not copy them into `Otoe-public` without a separate, explicit reason.

The PyPI publish workflow accepts only an annotated `vX.Y.Z` tag whose message
contains this exact marker on its own line:

```text
Publish-PyPI: yes
```

Do not create that tag until the exact source commit has passed these checks and
the public sync is reviewed. Never move or reuse a release tag. If a tag-triggered
workflow reached PyPI, repair forward with a new package version; a rerun against
an existing PyPI version is expected to fail.

## 6. Export And Dry-Run The Commit

Create a temporary export containing only files tracked by that exact commit:

```bash
EXPORT_DIR="$(mktemp -d)"
git archive --format=tar "$SOURCE_COMMIT" | tar -xf - -C "$EXPORT_DIR"
```

Confirm that the public checkout is clean, then dry-run from the export:

```bash
test -z "$(git -C /home/ale/Otoe-public status --porcelain)"
rsync -a --delete --dry-run \
  --exclude='.git/' \
  --exclude='.venv/' \
  --exclude='build/' \
  --exclude='dist/' \
  --exclude='dist-wheel-smoke/' \
  --exclude='.pytest_cache/' \
  --exclude='.hypothesis/' \
  --exclude='.ruff_cache/' \
  --exclude='.mypy_cache/' \
  --exclude='**/__pycache__/' \
  --exclude='*.egg-info/' \
  --exclude='src/*.egg-info/' \
  --exclude='.coverage' \
  --exclude='.coverage.*' \
  --exclude='htmlcov/' \
  --exclude='preview/native/' \
  --exclude='.claude/settings.local.json' \
  --exclude='.agents/' \
  --exclude='.codex/' \
  "$EXPORT_DIR/" /home/ale/Otoe-public/
```

Read every dry-run addition, modification, and deletion. The export has no
`.git`, virtual environment, cache, ignored output, or uncommitted file by
construction.

## 7. Sync The Export To Otoe-public

After the dry run is approved, repeat the command without `--dry-run`:

```bash
rsync -a --delete \
  --exclude='.git/' \
  --exclude='.venv/' \
  --exclude='build/' \
  --exclude='dist/' \
  --exclude='dist-wheel-smoke/' \
  --exclude='.pytest_cache/' \
  --exclude='.hypothesis/' \
  --exclude='.ruff_cache/' \
  --exclude='.mypy_cache/' \
  --exclude='**/__pycache__/' \
  --exclude='*.egg-info/' \
  --exclude='src/*.egg-info/' \
  --exclude='.coverage' \
  --exclude='.coverage.*' \
  --exclude='htmlcov/' \
  --exclude='preview/native/' \
  --exclude='.claude/settings.local.json' \
  --exclude='.agents/' \
  --exclude='.codex/' \
  "$EXPORT_DIR/" /home/ale/Otoe-public/
```

This updates the public working tree from one immutable source commit. It does
not commit or push.

## 8. Review Otoe-public Before Commit

Switch to the public repository and inspect it as the publication artifact:

```bash
cd /home/ale/Otoe-public
git status --short --branch
git diff --stat
git diff --cached --stat
```

Compare the commit export to the public tree while excluding repository metadata
and preserved local artifacts:

```bash
diff -qr \
  --exclude=.git \
  --exclude=.venv \
  --exclude=build \
  --exclude=dist \
  --exclude=dist-wheel-smoke \
  --exclude=.pytest_cache \
  --exclude=.hypothesis \
  --exclude=.ruff_cache \
  --exclude=.mypy_cache \
  --exclude=__pycache__ \
  --exclude='*.egg-info' \
  --exclude='src/*.egg-info' \
  --exclude=.coverage \
  --exclude='.coverage.*' \
  --exclude=htmlcov \
  --exclude=settings.local.json \
  --exclude=.agents \
  --exclude=.codex \
  "$EXPORT_DIR" /home/ale/Otoe-public
```

An ignored local `preview/native/` directory may appear as the only extra path
in this `diff`; it is preserved by the rsync exclusions above and is not part of
the public commit. Any other difference is a blocker.

If the diff shows an unintended tracked file, stop and create a new source
commit without it. Do not edit the promoted source only in `Otoe-public`.

## 9. Commit and Push from Otoe-public

Commit only from the public repository:

```bash
cd /home/ale/Otoe-public
git status --short --branch
git add -A
git diff --cached --stat
git commit -m "Sync public source" -m "Otoe-Source-Commit: $SOURCE_COMMIT"
git push
```

After pushing, preserve `SOURCE_COMMIT` in the PR/release record and remove the
temporary export. The public commit tree must continue to match that export.

Freeze the exact public commit and confirm that `origin/main` resolves to it:

```bash
PUBLIC_COMMIT="$(git rev-parse HEAD)"
git fetch --no-tags origin +refs/heads/main:refs/remotes/origin/main
test "$(git rev-parse refs/remotes/origin/main)" = "$PUBLIC_COMMIT"
```

Wait for the public `CI` and `CodeQL` workflows for `PUBLIC_COMMIT` to finish.
Then query the exact GitHub Actions workflow runs and jobs for that SHA. The token
must be able to read repository Actions; `gh auth token` normally supplies the authenticated CLI
token without putting it in the command arguments:

```bash
RELEASE_CHECK_REPOSITORY="NeonShapeshifter/Otoe" \
RELEASE_CHECK_SHA="$PUBLIC_COMMIT" \
RELEASE_CHECK_TOKEN="$(gh auth token)" \
python3 -I scripts/verify_release_checks.py
```

The verifier binds `ci.yml` and `codeql.yml` to `main`, event `push`, and
`PUBLIC_COMMIT`, then requires successful jobs named `tests (3.11)`,
`tests (3.12)`, `tests (3.13)`, `tests (3.14)`, and `Analyze Python` in those
exact attempts. A missing, pending, unsuccessful, ambiguous, malformed, or
unreadable result is a blocker; fix or rerun the check and execute
the verifier again. Do not substitute checks from another commit.

Do not tag or publish a package unless this remote gate and the release checklist
are complete. Create the annotated PyPI tag on `PUBLIC_COMMIT` only after the
verifier succeeds:

```bash
test "$(git rev-parse HEAD)" = "$PUBLIC_COMMIT"
git tag -a vX.Y.Z "$PUBLIC_COMMIT" -m "Release vX.Y.Z" -m "Publish-PyPI: yes"
git push origin vX.Y.Z
```

The tag workflow repeats the exact-SHA Actions verification before installing
release dependencies or building. It has `actions: read` for that query and
fails closed if a tag is pushed before the required public checks have succeeded.
