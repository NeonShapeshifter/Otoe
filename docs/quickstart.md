# Quick Start

This guide uses only files created by `otoe new`, so it works after installing
the package from PyPI and does not depend on repository examples.

## Install

Use Python 3.11 or newer. Prefer a virtual environment:

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install otoe
```

On Debian/Ubuntu systems with an externally managed Python, do not install Otoe
into the system interpreter. Use a virtual environment.

## Create An App

```bash
otoe new hello_otoe
cd hello_otoe
```

The scaffold contains:

- `app.py` - a small counter surface.
- `styles.css` - portable Otoe style declarations.
- `README.md` - render commands for the generated app.

## Run A Live Preview

```bash
otoe dev app:app --css styles.css
```

This serves the generated app through the live HTML preview adapter. Use it for
quick interaction checks while editing the app.

## Render HTML

```bash
otoe render app:app --out preview.html --css styles.css --pretty
```

This is the fastest static visual check. It proves the target imports and can
render through the HTML adapter.

## Render Native PNG

```bash
otoe render app:app --out preview.png --native --css styles.css
```

This exercises the current headless native renderer. It is deterministic and
useful for fixtures, but it is not a production native renderer.

## Build An Offline Bundle

```bash
otoe build app:app --out dist/cage --css styles.css --validate
```

The build writes:

- `manifest.json`
- `otoe-plan.json`
- `otoe-deps.json`
- `otoe-styles.json`
- `otoe-render-tree.json`
- copied app/runtime files
- copied Otoe runtime files required by the selected backend
- `otoe-run.py`, the generated bundle runner

`--validate` runs the generated runner's verification, load check, and native
layout check inside the bundle directory.

## Optional Readable Native Text

The default native PNG renderer is dependency-free and deterministic. Use
`--native-scale` for higher-density deterministic PNGs without changing layout
units:

```bash
otoe render app:app --out preview@2x.png --native --native-scale 2 --css styles.css
```

For local screenshots with readable text, install the optional text extra:

```bash
python -m pip install "otoe[native-text]"
otoe render app:app --out preview.png --native --native-text pillow --css styles.css
```

Use an explicit font path when the output needs to be repeatable across
machines:

```bash
otoe render app:app --out preview.png --native --native-text pillow --font path/to/font.ttf --css styles.css
```

## Pack The Bundle

```bash
otoe pack dist/cage --out dist/cage.tar.gz
```

`otoe pack` verifies the bundle again before writing the archive.

## Portable UI Matrix

Inspect the packaged Portable Core UI v0 contract before depending on a
primitive across HTML, native PNG, and native-window paths:

```bash
otoe portable-core
otoe portable-core --json
otoe portable-core --format json
```

## Source Checkout Examples

Repository examples are available only from a source checkout because they are
not installed into the wheel:

```bash
PYTHONPATH=src:. python -m otoe render examples.quickstart:app --out preview.html --pretty
PYTHONPATH=src:. python -m otoe render examples.quickstart:app --out preview.png --native
PYTHONPATH=src:. python -m otoe dev examples.live_counter:app --port 8767
```

Use `EXAMPLES_GUIDE.md` to pick the smallest example for a specific runtime,
UI, native, or build behavior. The current product-shaped source demo is
documented in `docs/hardware-control-panel.md`.
