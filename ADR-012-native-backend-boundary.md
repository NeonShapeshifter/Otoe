# ADR-012: Native Backend Boundary

## Status

Accepted

## Context

Otoe has enough native infrastructure to render deterministic PNG frames, drive
headless input through `NativeSurface`, and exercise a minimal Tk wrapper. That
is useful for tests and framework-shape validation, but it is not the same as a
production desktop backend.

Without a sharper backend boundary, experimental pieces can accidentally become
API promises. In particular, PNG output, Tk event-loop behavior, fake text
markers, and current layout limitations should not define what "native Otoe"
means long term.

## Decision

Otoe will treat native support as three separable layers:

1. **Headless renderer contract.**
   `NativeSurface`, layout, paint commands, hit testing, focus, input dispatch,
   and PNG output are the current testable contract. The backend-replay
   acceptance test is the executable end-to-end target for this layer.

2. **Backend adapter contract.**
   A backend adapter owns platform windows, event loops, rasterization, text
   shaping, accessibility bridge wiring, and GPU or CPU presentation. Backend
   adapters translate platform events into `NativeWindowDriver` or
   `NativeSurface` operations. ADR-015 defines the current executable
   `NativeBackendAdapter` interface.

3. **Production backend promise.**
   Otoe does not claim a production desktop backend until at least one adapter
   proves window lifecycle, input, accessibility metadata, text rendering,
   clipping, invalidation, packaging constraints, and repeated-frame stability
   outside the headless PNG path.

The current Tk wrapper remains an experiment and manual-test tool. It may inform
the adapter contract, but it is not the backend contract itself.

## Consequences

- `otoe render --native` may write PNG frames because PNG output is already part
  of the headless renderer contract.
- Public docs must describe native support as headless preview/test support
  until a backend adapter meets the production bar.
- Component code must stay backend-neutral. Components should not import Tk,
  Skia, Taffy, SDL, Qt, or platform APIs.
- Backend-specific APIs should live behind adapter modules and should not be
  required for HTML preview, static render, or headless native tests.
- Future Skia/Taffy work should attach below `NativeSurface`/driver boundaries
  instead of changing the component model.
- Future backend spikes should first reproduce the backend-replay acceptance
  test before expanding backend-specific behavior.

## Open Questions

- Whether layout should stay in Python for the next spike or move behind a
  Taffy-backed adapter.
- Whether the first real raster backend should target Skia directly or a
  smaller CPU-backed proof first.
- How much accessibility metadata belongs in `LayoutBox` versus a backend-owned
  accessibility tree.
