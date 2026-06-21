# Quick Start

This guide uses only files created by `otoe new`, so it works after installing
the package from PyPI and does not depend on repository examples. Otoe is still
pre-alpha: this path shows the intended first workflow, not a stable production
API guarantee.

## Happy Path

The main path for a new user is:

1. Install Otoe in a virtual environment.
2. Create a generated app with `otoe new`.
3. Run `otoe check`.
4. Render HTML.
5. Render a deterministic native PNG.
6. Use `otoe dev` for local interaction.
7. Build and validate a basic offline bundle.

## 1. Install

Use Python 3.11 or newer. Prefer a virtual environment:

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install otoe
```

On Debian/Ubuntu systems with an externally managed Python, do not install Otoe
into the system interpreter. Use a virtual environment.

## 2. Create An App

```bash
otoe new hello_otoe
cd hello_otoe
```

The scaffold contains:

- `app.py` - a small counter surface.
- `styles.css` - portable Otoe style declarations.
- `README.md` - first-run commands and caveats for the generated app.

## 3. Check The App

```bash
otoe check
```

`otoe check` compiles the generated app and catches basic Python errors before
you render or build. Once your app has tests, use:

```bash
otoe check --tests
```

If there is no `tests/` directory yet, `--tests` skips pytest after the compile
check.

## 4. Render HTML

```bash
otoe render app:app --out preview.html --css styles.css --pretty
```

This is the fastest static visual check. It proves the target imports and can
render through the HTML adapter.

## 5. Render Native PNG

```bash
otoe render app:app --out preview.png --native --css styles.css
```

This exercises the current headless native renderer. It is deterministic and
useful for fixtures, but it is not a production native renderer.

## 6. Run A Local Live Preview

```bash
otoe dev app:app --css styles.css
```

This serves the generated app through the live HTML preview adapter. Use it for
quick interaction checks while editing the app. Keep it local; `otoe dev` is a
developer preview server, not a sandboxed public service.

## 7. Build An Offline Bundle

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

## Optional: Pack The Bundle

```bash
otoe pack dist/cage --out dist/cage.tar.gz
```

`otoe pack` verifies the bundle again before writing the archive.

## Where To Go Next

- UI components: use `otoe.ui` primitives such as `ActionButton`, `Card`,
  `Surface`, `DataTable`, `Tabs`, and `Select`. See
  [Component Cookbook](../COMPONENT_COOKBOOK.md) and
  [Widget Contracts](../WIDGET_CONTRACTS.md).
- Styles: use the Otoe CSS subset documented in
  [Style Guide](../STYLE_GUIDE.md). Full browser CSS is a future direction, not
  the current portable contract.
- Native rendering: read [Native Status](native-status.md). Native PNG and
  window paths are useful for evidence and tests, but still experimental.
- Offline bundles: read [Offline Build](build-offline.md) when you need profile
  files, assets, runtime policies, packing, or repeatable native text.
- API stability: read [API Tiers](api-tiers.md). There is no stable tier yet.
- Experimental backend candidates: read [Backend Candidates](backend-candidates.md)
  only when you are validating renderer/backend experiments.

## Optional: Readable Native Text

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

## Optional: Portable UI Matrix

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
