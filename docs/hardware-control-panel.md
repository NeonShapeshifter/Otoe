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

## Five-Minute Evidence Path

Run these from a source checkout with `PYTHONPATH=src:.`. The path shows the
public Otoe story for a realistic app without entering backend internals.

1. Render the checked-in browser preview:

   ```bash
   PYTHONPATH=src:. python -m examples.hardware.preview > preview/hardware.html
   ```

   This proves the product-shaped HTML surface with the richer browser
   stylesheet. It does not prove native rendering or offline bundle behavior.

2. Open the gallery:

   ```bash
   xdg-open preview/index.html
   ```

   This is a review convenience for the checked-in preview gallery. Opening
   the gallery does not run the app or validate live events.

3. Run the live localhost preview:

   ```bash
   PYTHONPATH=src:. python -m examples.hardware.live_preview
   ```

   This proves provider-backed local interaction through an in-memory transport.
   The live preview is localhost-only development tooling, not a public server
   and not a sandbox.

4. Render native PNG evidence:

   ```bash
   PYTHONPATH=src:. python -m otoe render examples.hardware.control_panel:app --out /tmp/otoe-hardware.png --native --css preview/hardware_portable.css
   ```

   This proves the current deterministic headless native layout/paint/PNG path
   for the app. It is evidence, not a production renderer claim.

5. Build and validate the offline bundle:

   ```bash
   PYTHONPATH=src:. python -m otoe build examples.hardware.control_panel:app --out /tmp/otoe-hardware-bundle --css preview/hardware_portable.css --validate
   ```

   This proves plan, dependency audit, style artifact, render-tree artifact,
   manifest, copied runtime/framework files, and generated runner checks. The
   offline build path is a technical preview and is not a security sandbox.

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

## Offline Evidence

The hardware bundle flow is technical-preview evidence, not a security sandbox
or a production deployment promise. It is useful for reviewing exactly what a
realistic provider-backed app would ship: plan output, dependency audit, style
artifact, render-tree artifact, manifest, copied runtime files, and generated
runner checks.

Use `/tmp` or another disposable output directory when collecting evidence:

```bash
PYTHONPATH=src:. python -m otoe plan examples.hardware.control_panel:app --css preview/hardware_portable.css --out /tmp/otoe-hardware-plan.json
PYTHONPATH=src:. python -m otoe build examples.hardware.control_panel:app --out /tmp/otoe-hardware-bundle --css preview/hardware_portable.css --validate
```

The bundle should contain:

- `manifest.json`
- `otoe-run.py`
- `otoe-plan.json`
- `otoe-deps.json`
- `otoe-styles.json`
- `otoe-render-tree.json`
- copied runtime files under `app/`
- copied framework files under `framework/`

The generated runner can be checked directly:

```bash
cd /tmp/otoe-hardware-bundle
python otoe-run.py --verify
python otoe-run.py --check
python otoe-run.py --layout-check
python otoe-run.py --png /tmp/otoe-hardware-frame.png
```

Those commands use the default fake hardware provider. They do not talk to a
device, open a network connection, or install dependencies at runtime.

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
