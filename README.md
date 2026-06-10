# Otoe

Otoe is an experimental Python UI runtime for operational interfaces:
write reactive components, preview them as HTML, test them headlessly, render
deterministic native frames, and build offline bundles for constrained Linux
targets.

The project is still pre-alpha. The core runtime, HTML preview path, headless
native spike, and offline bundle pipeline are active technical-preview surfaces;
Otoe is not yet a stable public framework or production desktop renderer.
Readable native PNG text is available through the optional Pillow-backed
renderer path; the default native renderer stays dependency-free and
deterministic.

## What Works Today

- Python component functions with explicit widget props and event contracts.
- `signal`, `computed`, `effect`, lifecycle cleanup, `Show`, and keyed `For`.
- Static HTML rendering and live HTML preview support for live-preview apps.
- A small portable style layer through `css(...)`, `StyleSheet`, and utilities.
- `otoe.ui` primitives for app frames, cards, badges, action buttons, tabs,
  tables, dialogs, toasts, command palettes, sidebars, menus, selects, lists,
  and metric surfaces.
- Headless native layout, paint, PNG output, hit testing, click, focus,
  keyboard, input, and scroll dispatch through `NativeSurface`.
- Offline planning, dependency audit, build, generated runner validation, and
  pack commands for the first hardware/cage profile.
- Backend-candidate evidence tooling around `RenderTree`, `styleOps`, coverage
  declarations, and an experimental external Path0 JSON runner.

## Not Ready Yet

- Stable API guarantees.
- Production native rendering, GPU rendering, real text shaping, or retained
  desktop windowing.
- Platform accessibility tree output.
- Full browser CSS compatibility.
- A complete native-parity component library.

## Quick Start

Use Python 3.11 or newer.

```bash
python -m pip install otoe
otoe new hello_otoe
cd hello_otoe
otoe render app:app --out preview.html --css styles.css --pretty
otoe render app:app --out preview.png --native --css styles.css
otoe build app:app --out dist/cage --css styles.css --validate
```

`otoe new` writes a small renderable app plus `styles.css`. The HTML render is
the fastest visual check; the native PNG render exercises the current headless
native spike; the build command writes and validates a minimal offline bundle.
For readable native PNG text during local previews, install `otoe[native-text]`
and render with `--native-text pillow`; deterministic offline bundles declare
their font through `[native.text]` in `otoe.profile.toml`.

For local development from a checkout:

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e ".[dev]"
pytest -q
```

Repository examples such as `examples.quickstart:app` are available from a
source checkout, not from the installed wheel:

```bash
PYTHONPATH=src:. python -m otoe render examples.quickstart:app --out preview.html --pretty
PYTHONPATH=src:. python -m otoe render examples.quickstart:app --out preview.png --native
PYTHONPATH=src:. python -m otoe dev examples.live_counter:app --port 8767
```

## Tiny Example

```python
from otoe import Button, Text, VStack, component, computed, mount, signal


@component
def Counter():
    count = signal(0)
    label = computed(lambda: f"Clicked {count.value} times")

    return VStack(
        Text(label),
        Button("Increment", onClick=lambda: count.set(count.value + 1)),
        gap=8,
    )


tree = mount(Counter())
```

## Product Shape

Otoe should not be read as a generic replacement for Qt, Flutter, or browser
apps. The strongest current niche is Python-first operational software:

- hardware control panels
- kiosks and appliance UIs
- internal dashboards
- offline-testable local tools
- renderer/backend experiments that need deterministic evidence

The backend and evidence tooling is intentionally advanced and experimental.
New app authors should start with `otoe new`, HTML/native render, and the
portable UI subset before reaching for backend-candidate commands.
The Phase 5 professional reference apps are documented in
[REFERENCE_APP_PATTERNS.md](REFERENCE_APP_PATTERNS.md) and validated through the
hardware, admin, data workflow, utility, SaaS, and UI examples.

## Documentation

- [Quick Start](docs/quickstart.md)
- [Concepts](docs/concepts.md)
- [API Tiers](docs/api-tiers.md)
- [Portable Core UI v0](docs/portable-core-ui-v0.md)
- [Native Status](docs/native-status.md)
- [Offline Build](docs/build-offline.md)
- [Backend Candidates](docs/backend-candidates.md)
- [Release Checks](docs/release.md)
- [Examples Guide](EXAMPLES_GUIDE.md)
- [Reference App Patterns](REFERENCE_APP_PATTERNS.md)
- [Style Guide](STYLE_GUIDE.md)
- [Testing Guide](TESTING_GUIDE.md)
- [Native Workflows](NATIVE_WORKFLOWS.md)
- [Backend Candidate Guide](BACKEND_CANDIDATE_GUIDE.md)
- [Roadmap](ROADMAP.md)

## Repository Map

- `src/otoe/` - runtime package.
- `tests/` - runtime, renderer, build, and example regression tests.
- `examples/` - source-checkout validation surfaces and case studies.
- `preview/` - generated preview artifacts.
- `docs/` - product-facing guides and support matrices.
- `ADR-*.md` - design decisions.
  `ADR-019-native-pillow-text-backend.md` records the first real native text
  backend choice.

## Status

Current status: post-v0.1.7 workshop hardening. The test baseline is 712
passing tests with optional typing/Pillow tests skipped when those dependencies
are unavailable.
See [ROADMAP.md](ROADMAP.md) for the active phase plan.

## License

MIT License. Copyright (c) 2026 Forvara.
