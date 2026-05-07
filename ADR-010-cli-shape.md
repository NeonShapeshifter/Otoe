# ADR-010: Initial CLI Shape

## Status

Accepted

## Context

Otoe has runtime, HTML preview, native renderer spike, tests, and examples, but
the developer workflow is still module-driven. A framework needs predictable
commands before it adds more backend complexity.

## Decision

The first CLI should stay small and map to current capabilities:

- `otoe check`
  - Runs the local framework health checks.
  - First implementation should compile `src`, `examples`, and `tests`.
  - It may optionally run tests when invoked with `--tests`.
  - It must not require network access.
- `otoe render MODULE:OBJECT --out PATH`
  - Imports a Python object and renders it to an artifact.
  - Initial accepted targets are `Node`, `MountedNode`, and callables returning
    either.
  - Default renderer is HTML; native PNG can come later behind `--native`.
- `otoe dev MODULE:APP`
  - Starts a local live preview app.
  - The app object should expose the same `render_fragment()` and
    `dispatch_event(...)` shape already used by examples.
  - Default host must stay `127.0.0.1`.

## Consequences

- The CLI starts as developer tooling, not a production build system.
- `otoe check` is safe to implement first because it does not need app import
  semantics or a server lifecycle.
- `otoe dev` should reuse the existing live preview server instead of creating
  a second preview stack.
- `otoe render` should be explicit about import targets before supporting
  project scaffolds or config files.
