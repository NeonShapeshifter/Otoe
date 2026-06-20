# Publication Sync Checklist

This checklist is for manually promoting changes from the working repository
(`/home/ale/Otoe`) into the public repository (`/home/ale/Otoe-public`) when you
decide to publish. There is no automatic publication path from `Otoe`; the
public repository is the publication point.

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

Decide whether the current branch contains one coherent public update. If it
contains unrelated experiments, document what stays unpublished before syncing.

## 2. Run the Release Checks

For release-ready publication, use the local reference command:

```bash
scripts/release_check.sh
```

For a smaller docs-only or planning sync, still run the relevant focused checks
and record what was intentionally skipped:

```bash
python3 -m compileall -q src examples tests
python3 -m pytest -q
```

If the sync is meant to publish a package tag later, also verify the built
artifacts before copying anything:

```bash
python3 -m build
python3 -m twine check dist/*.whl dist/*.tar.gz
bash scripts/sdist_smoke.sh
OTOE_SMOKE_NO_BUILD_ISOLATION=1 bash scripts/wheel_smoke.sh
```

Build artifacts are validation outputs. They should not be copied into
`Otoe-public` unless there is a separate, explicit reason.

## 3. Decide Experimental Files

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

Keep a short note before syncing if any known work should remain private or
local-only for now. Examples:

```text
Intentional unpublished work for this sync:
- docs/display-list-v0.md: keep local until the display-list contract is reviewed.
- examples/native/backend_spikes/: keep local research; not part of public examples.
- preview/generated-experiment.html: generated scratch artifact; do not publish.
```

When a file moves from this list into the public repo, make the decision visible
in the public commit message or PR description.

## 4. Scan for Files That Must Not Be Copied

These paths and artifacts should never be copied from `Otoe` to `Otoe-public`:

- `.venv/`
- `build/`
- `dist/`
- `dist-wheel-smoke/`
- `.pytest_cache/`
- `.ruff_cache/`
- `.mypy_cache/`
- `.coverage`
- `.coverage.*`
- `htmlcov/`
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
  -o -name .ruff_cache \
  -o -name .mypy_cache \
  -o -name __pycache__ \
  -o -name "*.egg-info" \
  -o -path "/home/ale/Otoe/src/*.egg-info" \
  -o -name htmlcov \
  -o -name .coverage \
  -o -name ".coverage.*" \
  -o -path "/home/ale/Otoe/.claude/settings.local.json" \
  -o -path "/home/ale/Otoe/.agents" \
  -o -path "/home/ale/Otoe/.codex" \) -print
```

Seeing these paths in the working repo is normal. Seeing them in the sync plan
is a blocker.

## 5. Dry-Run the Sync

Run the sync as a dry run first:

```bash
rsync -a --delete --dry-run \
  --exclude='.git/' \
  --exclude='.venv/' \
  --exclude='build/' \
  --exclude='dist/' \
  --exclude='dist-wheel-smoke/' \
  --exclude='.pytest_cache/' \
  --exclude='.ruff_cache/' \
  --exclude='.mypy_cache/' \
  --exclude='**/__pycache__/' \
  --exclude='*.egg-info/' \
  --exclude='src/*.egg-info/' \
  --exclude='.coverage' \
  --exclude='.coverage.*' \
  --exclude='htmlcov/' \
  --exclude='.claude/settings.local.json' \
  --exclude='.agents/' \
  --exclude='.codex/' \
  /home/ale/Otoe/ /home/ale/Otoe-public/
```

Read the dry-run output. Confirm that every added, changed, or deleted path is
intended for public publication.

## 6. Sync to Otoe-public

After the dry run is clean, run the same command without `--dry-run`:

```bash
rsync -a --delete \
  --exclude='.git/' \
  --exclude='.venv/' \
  --exclude='build/' \
  --exclude='dist/' \
  --exclude='dist-wheel-smoke/' \
  --exclude='.pytest_cache/' \
  --exclude='.ruff_cache/' \
  --exclude='.mypy_cache/' \
  --exclude='**/__pycache__/' \
  --exclude='*.egg-info/' \
  --exclude='src/*.egg-info/' \
  --exclude='.coverage' \
  --exclude='.coverage.*' \
  --exclude='htmlcov/' \
  --exclude='.claude/settings.local.json' \
  --exclude='.agents/' \
  --exclude='.codex/' \
  /home/ale/Otoe/ /home/ale/Otoe-public/
```

This updates `Otoe-public`; it does not commit or push.

## 7. Review Otoe-public Before Commit

Switch to the public repository and inspect it as the publication artifact:

```bash
cd /home/ale/Otoe-public
git status --short --branch
git diff --stat
git diff --cached --stat
```

Compare the two trees while excluding repository metadata and local artifacts:

```bash
diff -qr \
  --exclude=.git \
  --exclude=.venv \
  --exclude=build \
  --exclude=dist \
  --exclude=dist-wheel-smoke \
  --exclude=.pytest_cache \
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
  /home/ale/Otoe /home/ale/Otoe-public
```

If the diff shows an unpublished experiment or local artifact, remove it from
`Otoe-public` before committing and update the unpublished-work note.

## 8. Commit and Push from Otoe-public

Commit only from the public repository:

```bash
cd /home/ale/Otoe-public
git status --short --branch
git add -A
git diff --cached --stat
git commit -m "Sync public release updates"
git push
```

Do not tag or publish a package unless the release checklist is also complete.
