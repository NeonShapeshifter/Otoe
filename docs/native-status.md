# Native Status

The native path is currently a deterministic headless renderer spike. It is
useful for tests, fixtures, backend contract work, and early framework API
validation. It is not a production desktop renderer.
The default PNG path still uses deterministic marker text. The first readable
text path is available as an optional Pillow-backed renderer.

## What Works

- Layout of mounted Otoe trees through the current native layout code.
- Paint command generation.
- PNG frame output.
- Hit testing and click dispatch.
- Focus handling.
- Keyboard and text input through `NativeSurface` and `NativeWindowDriver`.
- Controlled `ScrollView(scrollY=..., onScroll=...)` with clipped paint and
  clipped hit testing.
- Lazy `NativeSurface` refresh when reactive state changes outside direct
  surface events.
- Optional Tk wrapper for manual local window experiments.
- Renderer SPI split into layout, paint, and raster capabilities.
- `RenderTree` IR v0 and Path0 evidence for backend-candidate experiments.

## Current Limits

- No GPU renderer.
- No production windowing backend.
- No platform accessibility tree.
- No real text shaping or font fallback in deterministic PNG output.
- No stable Skia, Taffy, Qt, Tk, or other backend ABI.
- Layout is still primarily stack-oriented.
- The Tk wrapper is a smoke/manual adapter, not the final desktop backend.
- The portable style subset is intentionally smaller than browser CSS.

## Recommended Workflow

Use the native path for evidence and testability:

```bash
otoe render app:app --out preview.png --native --css styles.css
otoe render app:app --out preview@2x.png --native --native-scale 2 --css styles.css
```

`--native-scale` is a raster-scale contract: layout, hit testing, and paint
coordinates stay in logical units, while the written PNG dimensions are
multiplied by the positive integer scale.

Use the optional Pillow path when a local native PNG should be readable:

```bash
python -m pip install "otoe[native-text]"
otoe render app:app --out preview.png --native --native-text pillow --css styles.css
otoe render app:app --out preview.png --native --native-text pillow --font path/to/font.ttf --css styles.css
```

The `--font` path is the deterministic option for screenshots. Without
`--font`, Pillow's default font is used for local visual smoke only.

Offline builds declare the same choice in `otoe.profile.toml`:

```toml
[native.text]
renderer = "pillow"
font = "fonts/Inter.ttf"

[deps]
packages = ["Pillow"]
```

The generated bundle runner verifies the copied font and uses
`PillowNativeRendererBackend` for `--layout-check` and `--png`.

Use `NativeSurface` for direct tests:

```python
from otoe.experimental.native import NativeSurface

surface = NativeSurface(App(), stylesheet=styles)
surface.click(24, 32)
surface.input_text("ready")
surface.render_png("frame.png")
```

Use `NativeWindowDriver` when a test should speak in window-shaped events
instead of surface calls.

Use the Portable Core UI native visual demo when checking the current product
surface against the native renderer:

```bash
PYTHONPATH=src:. python -m examples.native.portable_core_ui_demo
PYTHONPATH=src:. python -m examples.native.portable_core_ui_demo --marker-only
PYTHONPATH=src:. python -m examples.native.portable_core_ui_demo --pillow --scale 2
```

The demo writes `preview/native/portable_core_ui_marker.png` every time. The
default mode also writes `preview/native/portable_core_ui_pillow.png` when
Pillow is installed; `--pillow` forces that readable-text path and reports the
install hint if Pillow is missing.

## Chosen Next Step

The next native product milestone is not more widgets. It is visual
credibility, and the first chosen step is the Pillow/FreeType-backed optional
text/PNG path. See `ADR-019-native-pillow-text-backend.md`.

That milestone now:

- add readable text to headless native PNG output
- keep the stdlib marker renderer as the no-dependency deterministic baseline
- require an explicit font policy for deterministic builds
- attach through the renderer backend boundary instead of leaking Pillow into
  component APIs

The remaining native decisions stay separate:

- define the DPI/scaling story
- decide whether stack layout is enough for v0 or whether a layout engine is
  needed later
- keep backend candidates behind the current small adapter and evidence
  contracts

Pango/PangoCairo remains the likely future path for complex shaping and font
fallback on Linux appliances. Skia remains a future candidate for a fuller paint
and raster backend.
