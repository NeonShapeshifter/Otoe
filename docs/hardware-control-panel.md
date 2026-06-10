# Hardware Control Panel Demo

The hardware control panel is the recommended non-Wraith product demo for a
source checkout. It shows Otoe's intended niche: Python-first operational UI,
safe provider-backed actions, deterministic state, HTML preview, native PNG,
and an offline bundle path.

Paths:

- `examples/hardware/control_panel.py`
- `examples/hardware/adapters.py`
- `examples/hardware/preview.py`
- `examples/hardware/live_preview.py`
- `preview/hardware.css`
- `preview/hardware_portable.css`

## Static Product Target

`examples.hardware.control_panel:app` is the CLI/build target. It uses a fake
hardware provider by default so the same target can render without a device:

```bash
PYTHONPATH=src:. python -m otoe render examples.hardware.control_panel:app --out preview/hardware_cli.html --css preview/hardware_portable.css --pretty
PYTHONPATH=src:. python -m otoe render examples.hardware.control_panel:app --out preview/hardware_cli.png --native --css preview/hardware_portable.css
PYTHONPATH=src:. python -m otoe build examples.hardware.control_panel:app --out dist/hardware_cage --css preview/hardware_portable.css --validate
```

The build command writes a bundle and validates the generated runner's verify,
load, and native layout checks.

## Browser Preview

The browser preview uses the richer browser stylesheet:

```bash
PYTHONPATH=src:. python -m examples.hardware.preview > preview/hardware.html
```

Use `preview/hardware.css` for browser presentation. It intentionally contains
browser-only CSS such as media queries.

## Live Preview

The live preview uses `TransportHardwareProvider` over an in-memory transport
so command handling follows the same provider boundary a serial, USB, GPIO,
SQLite, or local service adapter would use:

```bash
PYTHONPATH=src:. python -m examples.hardware.live_preview
```

## Portable Style Contract

Use `preview/hardware_portable.css` for Otoe CLI render, native PNG, plan, and
build. It stays inside the Otoe Style subset: single class selectors,
portable properties, and native-safe dimensions.

The regression tests cover:

- static HTML render through `otoe render`
- native PNG render through `otoe render --native`
- offline `otoe build --validate`
- generated runner PNG output
- live command dispatch through the transport-backed preview
