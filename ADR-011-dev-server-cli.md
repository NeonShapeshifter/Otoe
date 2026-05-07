# ADR-011: Dev Server CLI Semantics

## Status

Accepted

## Context

The live preview server exists in `examples/live_server.py` and several examples
already share its app shape. Before exposing `otoe dev`, the framework needs a
stable command contract that does not depend on one example package.

## Decision

`otoe dev MODULE:APP` should import a local app target and run a live preview
server on `127.0.0.1` by default.

The target may be:

- an app instance exposing `render_fragment()` and `dispatch_event(event_id, *args)`;
- a zero-argument factory returning that app instance.

The initial command shape should be:

```bash
otoe dev MODULE:APP --host 127.0.0.1 --port 8767
```

Defaults:

- `--host` defaults to `127.0.0.1`.
- `--port` defaults to an Otoe-chosen dev port.
- The server must not bind to `0.0.0.0` unless the user asks explicitly.
- The command should print the local URL.
- Browser auto-open should be opt-in later, not default behavior.

## Consequences

- `otoe dev` should reuse the existing live preview protocol instead of
  creating another event transport.
- The shared live server should move from `examples/` into `src/otoe/` before
  the command is implemented.
- Remote exposure remains out of scope until auth/CSRF policy exists.
