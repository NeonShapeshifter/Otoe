# Display List Boundary v0

Status: experimental
Last reviewed: 2026-06-16

Display List v0 is a small serializable boundary between Otoe's current native
layout/paint pipeline and future native backends. It is intentionally not a
stable public API yet.

The current native renderer still works the same way:

1. Otoe mounts a widget tree.
2. `layout_native()` produces `NativeLayout`.
3. `paint_native()` produces `NativePaint`.
4. `write_native_png()` or `PillowNativeRendererBackend` rasterizes the paint
   commands.

Display List v0 sits after `NativePaint`. It translates the existing paint
command stream into a JSON-friendly command list that future Skia, Cairo, SDL3,
or other renderer spikes can consume without depending on the Python PNG writer.

## Scope

The v0 schema covers only the primitives Otoe already emits today:

- `rect` commands for background fills and borders;
- `rect.radius` for existing rounded rectangles;
- `text` commands with color and font size;
- per-command `clip` rectangles when native paint already calculated clipping.

It does not add layout behavior, text shaping, Skia, Yoga, SDL3, Cairo, Pango,
or any dependency.

## Shape

The internal module is `otoe._display_list`. It exposes frozen dataclasses and
pure conversion helpers for tests and backend spikes:

- `DisplayList`
- `DisplayListCommand`
- `display_list_from_paint(paint)`
- `export_native_display_list(target, ...)`
- `display_list_to_dict(display_list)`
- `display_list_to_json(display_list)`

The JSON payload is deterministic and inspectable:

```json
{
  "schemaVersion": 0,
  "format": "otoe-display-list",
  "width": 64,
  "height": 32,
  "commands": [
    {
      "op": "rect",
      "path": [],
      "box": [0, 0, 64, 32],
      "fill": "#ffffff"
    },
    {
      "op": "text",
      "path": [0],
      "box": [8, 9, 48, 14],
      "text": "OK",
      "color": "#111827",
      "fontSize": 14
    }
  ]
}
```

## Why This Boundary

`NativePaint` is useful inside Otoe, but it is still Python-internal. Display
List v0 creates a narrow handoff that backend candidates can inspect, replay,
hash, or serialize without importing the PNG rasterizer. This keeps the next
Skia/Cairo/SDL3 work focused on consuming a stable frame description instead of
re-deriving layout and paint semantics.

For now, treat the display list as an experimental artifact. It may change while
native layout v1, richer text, and backend candidate work settle.

## Non-Goals

- No public stable API.
- No new renderer backend.
- No JSON parser or external ABI contract yet.
- No browser layout parity.
- No full text wrapping, shaping, fallback, or font selection policy.

## Next Consumers

Likely future spikes:

- Skia CPU raster consumer for `rect`, rounded `rect`, and `text`.
- Cairo/Pango consumer if Otoe decides to prove Linux-native shaping.
- SDL3 host experiment that presents frames produced by another raster path.
- Backend package fixtures that compare display-list JSON before raster output.
