# Backend Candidates

Backend-candidate tooling is advanced and experimental. It exists so renderer
work can be evaluated with repeatable evidence instead of informal screenshots.

Most app authors do not need these commands.

## Current Boundary

The current replacement boundary centers on:

- `RenderTree` IR v0
- `ResolvedStyleMap`
- `styleOps`
- layout, paint, and raster backend capabilities
- backend capability profiles
- readiness and coverage evidence
- external Path0 JSON runner experiments
- backend package manifests

Path0 is a proof surface, not a stable external backend ABI.

New code that intentionally uses RenderTree/style evidence helpers should use
the experimental facade:

```python
from otoe.experimental.backend import RenderTree, render_tree_from_target
```

Top-level aliases remain for compatibility while Otoe is pre-alpha.

## Useful Commands

Inspect a backend profile:

```bash
otoe backend-profile native-python
otoe backend-profile --backend-capability-profile backend-profile.json --json
```

Compare readiness requirements against a backend profile or coverage
declaration:

```bash
otoe backend-coverage --requirements examples/native/contracts/backend_readiness_expected.json --backend native-python
otoe backend-coverage --requirements examples/native/contracts/backend_readiness_expected.json --backend native-python --audit
```

Compare JSON contract artifacts:

```bash
otoe compare-contract expected.json actual.json
otoe compare-contract expected.json actual.json --json
```

Materialize an experimental backend package:

```bash
otoe backend-package examples/native/path0_external_backend.package.json --package-out dist/path0-external-backend
```

## Graduation Bar

A backend candidate should prove:

- it can consume the intended input boundary
- layout and paint outputs are schema-valid
- hashes bind evidence to the exact RenderTree/style input
- widget/input/style support is observed by replay, not only declared
- unsupported behavior is explicit
- generated bundle verification still passes

Use `BACKEND_CANDIDATE_GUIDE.md` for the full checklist and
`examples/native/backend_candidate_skeleton.py` as the no-dependency starting
point.
