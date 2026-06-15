# Otoe

Otoe is an experimental Python UI runtime for operational interfaces:
write reactive components, preview them as HTML, test them headlessly, render
deterministic native frames, and build offline bundles for constrained Linux
targets.

The project is still pre-alpha. The core runtime, HTML preview path, headless
native spike, and offline bundle pipeline are active technical-preview surfaces;
Otoe is not yet a stable public framework or production desktop renderer.
See [API Tiers](docs/api-tiers.md) for the current split between core public
preview, product-preview UI, and experimental native/backend APIs.
Readable native PNG text is available through the optional Pillow-backed
renderer path; the default native renderer stays dependency-free and
deterministic.

## What Works Today

- Python component functions with explicit widget props and event contracts.
- `signal`, `computed`, `effect`, lifecycle cleanup, `Show`, and keyed `For`.
- Static HTML rendering and live HTML preview support for live-preview apps.
- A small Otoe CSS subset through `css(...)`, `StyleSheet`, and utilities:
  single class selectors, selected portable properties, simple values, and
  build-time Style IR/styleOps artifacts.
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
- Full browser CSS compatibility; the current style system is a documented
  portable subset, not a general CSS engine.
- A complete native-parity component library.

## Happy Path

Use Python 3.11 or newer. Otoe is pre-alpha, so start with the generated app
and the smallest local checks before depending on advanced native/backend
surfaces.

```bash
python -m pip install otoe
otoe new hello_otoe
cd hello_otoe
otoe check
otoe render app:app --out preview.html --css styles.css --pretty
otoe render app:app --out preview.png --native --css styles.css
otoe dev app:app --css styles.css
otoe build app:app --out dist/cage --css styles.css --validate
```

What each step proves:

- `otoe new` writes `app.py`, `styles.css`, and a small app README.
- `otoe check` compiles the scaffold and catches basic Python errors.
- `otoe render ... preview.html` is the fastest static visual check.
- `otoe render ... --native` writes a deterministic PNG through the current
  headless native preview path. It is useful for fixtures, not a production
  desktop renderer.
- `otoe dev` starts a local live HTML preview for interaction checks. Keep it
  bound to localhost; it is not a public server or sandbox.
- `otoe build ... --validate` writes a minimal offline bundle and runs the
  generated runner's verify/load/layout checks.

Use `otoe check --tests` once your generated app has a `tests/` directory.

For local development from a checkout:

```bash
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -e ".[dev]"
python3 -m pytest -q
```

Repository examples such as `examples.quickstart:app` are available from a
source checkout, not from the installed wheel:

```bash
PYTHONPATH=src:. python -m otoe render examples.quickstart:app --out preview.html --pretty
PYTHONPATH=src:. python -m otoe render examples.quickstart:app --out preview.png --native
PYTHONPATH=src:. python -m otoe dev examples.live_counter:app --port 8767
```

## Where To Go Next

- UI components: start with [Component Cookbook](COMPONENT_COOKBOOK.md) and
  [Widget Contracts](WIDGET_CONTRACTS.md). Prefer `otoe.ui` for product-preview
  UI primitives.
- Styles: use [STYLE_GUIDE.md](STYLE_GUIDE.md). Otoe currently supports a
  documented CSS subset, not full browser CSS.
- Native rendering: read [Native Status](docs/native-status.md) before relying
  on native PNG/window behavior. Native is still experimental.
- Offline bundles: use [Offline Build](docs/build-offline.md) after the happy
  path works locally.
- API stability: check [API Tiers](docs/api-tiers.md). There is no stable tier
  yet while Otoe is pre-alpha.
- Backend candidates: read [Backend Candidates](docs/backend-candidates.md)
  only when you are validating renderer/backend experiments.

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

For the product thesis, target users, and explicit anti-goals, read
[Product North Star](docs/product-north-star.md).

The backend and evidence tooling is intentionally advanced and experimental.
New app authors should start with `otoe new`, HTML/native render, and the
portable UI subset before reaching for backend-candidate commands. Use
`otoe portable-core` to inspect the current Portable Core UI v0 support matrix
from the installed package.
Use [STYLE_GUIDE.md](STYLE_GUIDE.md) when authoring `--css` files: Otoe accepts
only the current portable CSS subset for native/plan/build paths. Richer browser
CSS can still be used in browser-only preview stylesheets, but it is not part
of the portable contract yet.
The Phase 5 professional reference apps are documented in
[REFERENCE_APP_PATTERNS.md](REFERENCE_APP_PATTERNS.md) and validated through the
hardware, admin, data workflow, utility, SaaS, and UI examples.

## Documentation

- [Product North Star](docs/product-north-star.md)
- [Quick Start](docs/quickstart.md)
- [Concepts](docs/concepts.md)
- [API Tiers](docs/api-tiers.md)
- [Reactive Model](docs/reactive-model.md)
- [Security and Trust Boundaries](docs/security.md)
- [Portable Core UI v0](docs/portable-core-ui-v0.md)
- [Portable Input Core v0](docs/portable-input-core-v0.md)
- [Hardware Control Panel Demo](docs/hardware-control-panel.md)
- [Native Layout](docs/native-layout.md)
- [Native Status](docs/native-status.md)
- [Native Yoga/Skia/SDL3 Roadmap](ADR-021-native-yoga-skia-sdl3-roadmap.md)
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
  backend choice, and `ADR-020-native-layout-v0-v1-decision.md` records the
  stack-first native layout v0/v1 boundary.

## Status

Current status: post-v0.1.8 workshop hardening. The project maintains broad
test coverage and the suite is expected to pass locally; optional typing and
Pillow tests skip cleanly when those dependencies are unavailable.
See [ROADMAP.md](ROADMAP.md) for the active phase plan.

## License

MIT License. Copyright (c) 2026 Forvara.
