# Otoe

Otoe is a pre-alpha Python-first frontend runtime for local operational
interfaces: hardware control panels, kiosks, appliances, dashboards, offline
tools, and operator consoles.

It is for Python developers building controlled product surfaces around local
services, device adapters, diagnostics, workflows, and operator actions. The
goal is to make those interfaces feel modern, testable, and deployable without
making a browser the mandatory runtime or forcing the product into an unrelated
frontend stack.

Otoe is not a stable framework yet. Treat it as an active runtime experiment
with a usable HTML preview path, early portable UI primitives, deterministic
native render evidence, and technical-preview offline bundle tooling.

For the product thesis and anti-goals, read
[Product North Star](docs/product-north-star.md).

## What Works Today

- Python component functions with explicit widget props and event contracts.
- `signal`, `computed`, `effect`, lifecycle cleanup, `Show`, and keyed `For`.
- `otoe.ui` primitives for app frames, cards, badges, action buttons, tabs,
  tables, dialogs, toasts, command palettes, sidebars, menus, selects, lists,
  metrics, and dense operational surfaces.
- Static HTML rendering for fast visual preview.
- Local live HTML preview for development-time interaction checks.
- A documented portable CSS subset through `css(...)`, `StyleSheet`, class
  selectors, selected portable properties, simple values, and style artifacts.
- Headless native layout, paint, PNG output, hit testing, click, focus,
  keyboard, input, and scroll dispatch through `NativeSurface`.
- Offline planning, dependency audit, build, generated runner validation, and
  pack commands for the first constrained Linux hardware profile.
- Experimental renderer/backend evidence tooling for contributors.

## Not Ready Yet

- Stable API guarantees.
- Production native rendering, GPU rendering, retained desktop windowing, or
  complete native text shaping.
- Platform accessibility tree output.
- Full browser CSS compatibility, DOM APIs, or browser extension points.
- A complete native-parity component library.
- Offline bundles as a security sandbox.
- A generic replacement promise for Qt, Flutter, Electron, React, or browser
  apps.

## Quickstart

Use Python 3.11 or newer. Start with the generated app and keep advanced
native/backend surfaces out of your first pass.

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
- `otoe render ... preview.html` is the fastest static visual check. It is a
  usable preview surface, not a production deployment claim.
- `otoe render ... --native` writes a deterministic PNG through the current
  headless native path. Use it for fixtures and evidence, not as a production
  renderer.
- `otoe dev` starts a local live HTML preview for interaction checks. Keep it
  bound to localhost; it is not a public server or sandbox.
- `otoe build ... --validate` writes a minimal offline bundle and runs the
  generated runner's verify/load/layout checks. This is a technical preview,
  not a sandbox or mature deployment platform.

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

## Surface Maturity

| Surface | Status | Use it for | Not for |
| --- | --- | --- | --- |
| Python components and reactivity | Public pre-alpha | Prototypes, local tools, app structure, tests | Stable API commitments |
| `otoe.ui` primitives | Product-preview | Operational layouts, dense panels, reference apps | Guaranteed native parity for every component |
| Static HTML render | Usable preview | Fast screenshots, reviews, simple visual checks | Final runtime proof |
| Live HTML preview | Local dev only | Iterating on interactions on localhost | Public serving, sandboxing, or deployment |
| Portable CSS subset | Public pre-alpha | Styles that can feed HTML, native evidence, and build artifacts | Full browser CSS compatibility |
| Native PNG and `NativeSurface` | Experimental evidence | Layout, paint, input, and fixture validation | Production desktop rendering |
| Offline build/pack | Technical preview | Auditable local bundle experiments for constrained Linux targets | Security sandboxing or mature release packaging |
| Backend evidence tooling | Experimental contributor path | Advanced renderer/backend contract checks | First app-author workflow |

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

Otoe should not be read as a generic replacement for Qt, Flutter, Electron, or
browser apps. Its strongest current niche is Python-first operational software:

- hardware control panels
- kiosks and appliance UIs
- internal dashboards
- offline-testable local tools
- operator consoles and diagnostics
- renderer/backend experiments that need deterministic evidence

Wraith inspired some of the first real constraints, but it is a case study, not
the product identity. Otoe should stand on its own for many appliance-shaped
products.

Use [STYLE_GUIDE.md](STYLE_GUIDE.md) when authoring `--css` files. Otoe accepts
only the current portable CSS subset for native, plan, and build paths. Richer
browser-only preview stylesheets can exist, but they are not part of the
portable contract yet.

Use `otoe portable-core` to inspect the current Portable Core UI v0 support
matrix from the installed package.

The Phase 5 professional reference apps are documented in
[REFERENCE_APP_PATTERNS.md](REFERENCE_APP_PATTERNS.md) and surfaced through the
hardware, admin, data workflow, utility, SaaS, and UI examples.

## Documentation

### App Authors

- [Quick Start](docs/quickstart.md)
- [Concepts](docs/concepts.md)
- [Component Cookbook](COMPONENT_COOKBOOK.md)
- [Widget Contracts](WIDGET_CONTRACTS.md)
- [Style Guide](STYLE_GUIDE.md)
- [Reactive Model](docs/reactive-model.md)
- [Portable Core UI v0](docs/portable-core-ui-v0.md)
- [Portable Input Core v0](docs/portable-input-core-v0.md)
- [API Tiers](docs/api-tiers.md)
- [Compatibility And Versioning](docs/compatibility.md)
- [Testing Guide](TESTING_GUIDE.md)

### Operational UI/Product Demos

- [Hardware Control Panel Demo](docs/hardware-control-panel.md)
- [Reference App Patterns](REFERENCE_APP_PATTERNS.md)
- [Examples Guide](EXAMPLES_GUIDE.md)
- [Mission Exec Showcase](docs/wraith-mission-exec-showcase.md) - Wraith case
  study
- [Wraith Input Console](docs/wraith-input-console.md) - Wraith case study
- [Wraith Visual Benchmark](docs/wraith-visual-benchmark.md) - Wraith case
  study

### Native/Offline Evidence

- [Native Status](docs/native-status.md)
- [Native Layout](docs/native-layout.md)
- [Native Workflows](NATIVE_WORKFLOWS.md)
- [Native Yoga/Skia/SDL3 Roadmap](ADR-021-native-yoga-skia-sdl3-roadmap.md)
- [Offline Build](docs/build-offline.md)
- [Security and Trust Boundaries](docs/security.md)

### Renderer/Backend Contributors

This is the advanced route for backend candidates, RenderTree, styleOps,
coverage declarations, and Path0. App authors do not need this path to start.

- [Backend Candidates](docs/backend-candidates.md)
- [Backend Candidate Guide](BACKEND_CANDIDATE_GUIDE.md)
- [Layout v1 Plan](docs/layout-v1-plan.md)
- [Native Renderer Spike](NATIVE_RENDERER_SPIKE.md)
- [Backend Candidate Acceptance ADR](ADR-012-native-backend-boundary.md)
- [Native Backend Adapter ADR](ADR-015-native-backend-adapter-interface.md)

### Project Process/Release

- [Product North Star](docs/product-north-star.md)
- [Roadmap](ROADMAP.md)
- [Release Checks](docs/release.md)
- [Publication Sync Checklist](docs/publication-sync-checklist.md)
- [API Tiers](docs/api-tiers.md)
- [Changelog](CHANGELOG.md)

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

Current source targets v0.2.0 pre-alpha runtime and release-integrity
hardening. CI enforces strict typing, branch coverage, stub/runtime parity,
reproducible package artifacts, and the full test suite. Pillow remains an
optional runtime dependency; Pillow-specific tests skip when it is unavailable.
See [ROADMAP.md](ROADMAP.md) for the active phase plan.

Readable native PNG text is available through the optional Pillow-backed
renderer path; the default native renderer stays dependency-free and
deterministic.

## License

MIT License. Copyright (c) 2026 Forvara.
