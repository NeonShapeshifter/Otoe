# ADR-015: Native Backend Adapter Interface

## Status

Accepted

## Date

May 22, 2026

## Context

Phase 3 proved that the native task board can run through `NativeSurface`,
`NativeWindowDriver`, `run_native(...)`, and the optional Tk wrapper. The manual
Tk smoke also made the current limitation visible: the window shows the
headless PNG marker renderer, including marker text, not a production text or
windowing backend.

The next backend work needs a smaller attachment point than "replace whatever
`run_native(...)` does today". Without an adapter contract, a Skia, Taffy, Qt,
SDL, or CPU paint experiment could leak backend details into component code or
make Tk behavior the accidental reference implementation.

## Decision

Otoe defines a minimal `NativeBackendAdapter` protocol:

```python
class NativeBackendAdapter(Protocol):
    name: str

    def run(self, driver: NativeWindowDriver, *, title: str = "Otoe") -> None:
        ...
```

`run_native(...)` resolves a backend before mounting the target. A backend may be
either:

- a registered backend name such as `"tk"`
- an object implementing `NativeBackendAdapter`

The built-in `TkNativeBackendAdapter` is registered as `"tk"` and delegates to
`TkNativeWindow`. It remains a manual-test adapter only.

The adapter receives a `NativeWindowDriver`, not a component tree. That keeps
component code backend-neutral and preserves the existing testable boundary for
layout, paint, hit-testing, focus, text input, scroll, and frame refresh.

## Contract

A backend adapter owns:

- platform window creation and destruction
- event-loop blocking or integration policy
- translating platform pointer, wheel, keyboard, and text events into
  `NativeWindowDriver`
- presenting refreshed frames
- any backend-specific text, accessibility, DPI, raster, GPU, or packaging work

A backend adapter must not:

- require Otoe component code to import backend APIs
- replace the signal/component/mount model
- bypass `NativeWindowDriver` for app-level input dispatch
- make `TkNativeWindow`, PNG marker text, or stdlib raster details part of the
  production compatibility promise

## Consequences

- Backend selection is now executable through `native_backend_adapter(...)`,
  `native_backend_names()`, and `run_native(..., backend=...)`.
- Unknown or invalid backends fail before the target is mounted.
- Future backend spikes can attach at the adapter boundary first, then decide
  whether layout, paint, and text should remain behind the existing
  `NativeSurface` contract or move behind a deeper backend-specific interface.
- The next production-quality backend decision should start by implementing this
  protocol, not by changing widgets or app examples.
