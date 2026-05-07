# ADR-007: Native Window Ownership and Backend Replacement

**Status:** Proposed
**Date:** May 7, 2026

## Context

Otoe now has a headless native renderer path:

```text
Node tree -> NativeSurface -> layout -> paint -> input dispatch -> rerender
```

It also has `NativeWindowDriver`, `TkNativeWindow`, and `run_native(...)`.
Without a clear ownership boundary, the temporary Tk wrapper could accidentally
become the framework contract and make future Skia, Taffy, Qt, SDL, or other
backends harder to adopt.

The framework needs to separate three concerns:

- The Otoe tree and renderer state.
- The window-facing input/frame driver.
- The actual OS window and event loop.

## Decision

Otoe will treat `NativeSurface` as the renderer owner, `NativeWindowDriver` as
the backend-neutral window driver, and concrete window backends as replaceable
adapters.

1. **`NativeSurface` owns one mounted tree and its headless frame state.**
   It owns layout/paint caching, focus path, lazy refresh, input dispatch, and
   PNG frame output. It does not create OS windows, run an event loop, or expose
   backend-specific objects.

2. **`NativeWindowDriver` owns high-level window input dispatch.**
   It translates click, wheel, key-down, key-input, and text-input events into
   `NativeSurface` calls. It is testable without a real window and exposes frame,
   focus, paint, size, and PNG output for assertions.

3. **Window backends own OS resources and event loops.**
   A backend adapter may create windows, bind platform events, manage the event
   loop, and translate platform payloads into driver calls. Backends must not
   require component code to import backend APIs.

4. **`TkNativeWindow` is a manual-test adapter, not the production backend.**
   It is allowed to be blocking, minimal, and PNG-backed. Its purpose is to prove
   the interactive path outside a browser while the renderer contract hardens.

5. **`run_native(...)` is an experimental convenience entry point.**
   Today it launches the optional Tk adapter and blocks until the window closes.
   Unsupported backend names must fail before constructing a window. Future
   backends may add explicit backend names without changing component code.

6. **Production app integration can bypass `run_native(...)`.**
   Apps or tests that already own an event loop should use `NativeWindowDriver`
   or `NativeSurface` directly until Otoe defines a non-blocking app lifecycle
   API.

## Consequences

The renderer path remains test-first and backend-neutral. A future backend can
replace windowing, layout, paint, or raster output without changing component
functions, widget declarations, signals, or event handlers.

The public contract remains small: components produce Otoe nodes; the renderer
produces layout/paint/input behavior; backend adapters translate platform events
into driver calls.

This deliberately postpones production concerns that need a real backend:

- native accessibility tree integration
- IME and text composition
- platform text selection/caret movement
- async event loop integration
- multiple windows
- GPU swapchain ownership
- packaging and window security policy

Those features should attach to the driver/backend boundary, not leak into user
components.
