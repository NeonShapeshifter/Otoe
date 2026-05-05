# Changelog

## Unreleased

- Extracted shared live-preview server infrastructure for Wraith, Mission Exec,
  and SaaS demos.
- Added tests for the shared live-page shell and event script.

## v0.0.1 - Technical Preview

Initial public technical preview of Otoe.

- Reactive Python UI runtime with `signal`, `computed`, `effect`, and batching.
- Component ownership, lifecycle cleanup, explicit widget contracts, and event dispatch.
- `Show` and keyed `For` control-flow primitives.
- Fake-widget mount backend with snapshots and deterministic tests.
- Static and live HTML preview backends.
- Wraith Mission Exec case study with visible runtime mutations.
- SaaS dashboard case study for a softer product UI surface.
- Optional JSX-like `template(...)` syntax.
- Experimental portable `css(...)` / `StyleSheet` prototype.
- MIT license under Forvara.
