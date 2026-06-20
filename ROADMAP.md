# Otoe Roadmap

**Updated:** June 17, 2026  
**Current phase:** Phase 5 - Product-shape validation  
**Product reference:** [Product North Star](docs/product-north-star.md)  
**Technical history:** [Technical Ledger](docs/technical-ledger.md)

Otoe is a pre-alpha Python-first frontend runtime for local operational
interfaces: hardware panels, kiosks, appliances, dashboards, offline tools, and
operator consoles.

This roadmap is intentionally short. It tracks product direction, current
decisions, and exit criteria. Dense renderer/build/backend history lives in the
technical ledger.

## Status Actual

- Otoe is pre-alpha. It is not a stable framework and should not be sold as one.
- The core Python component/reactive model, HTML render path, live local HTML
  preview, portable style subset, headless native evidence path, and offline
  bundle tooling all exist.
- Phase 5 is active: the project is validating the product shape through
  non-Wraith reference apps and operational UI demos.
- Wraith remains useful evidence and a case study, but it no longer defines the
  product boundary.
- Backend candidates, renderer evidence, build artifacts, and coverage gates are
  valuable contributor paths, not the first app-author story.

## Product Direction

Otoe should help a Python developer building software for a machine create a
polished, testable, offline-capable interface without making a browser the
required runtime and without splitting the product across an unrelated frontend
stack.

The target surfaces are controlled operational environments:

- hardware control panels
- kiosks and appliance UIs
- local dashboards and operator consoles
- offline diagnostic or workflow tools
- private/internal product runtimes with repeatable deployment evidence

The product bet is narrow: Python components, reactive state, portable styling,
deterministic render/input evidence, auditable offline artifacts, and clear
experimental boundaries for future native/backend work.

## Phase Summary

| Phase | Name | Status | Meaning |
| --- | --- | --- | --- |
| 0 | Case Study and First Slice | Done | Initial architecture and validation direction were established. |
| 1 | Pure Python Runtime Core | Done | Components, signals, lifecycle, events, control flow, batching, mounting, snapshots, and HTML render exist. |
| 2A | Headless Native Renderer Spike | Done | Otoe trees can produce deterministic native layout, paint, PNG, hit testing, focus, keyboard, text input, and scroll evidence. |
| 2B | Renderer Backend Hardening | Done | Native/render/backend boundaries, support matrices, diagnostics, and acceptance surfaces exist for contributors. |
| 3 | Interactive Native Demo | Done | `NativeWindowDriver`, optional Tk wrapper, and headless interaction tests prove the window-facing path. |
| 4 | Developer Experience | Done; maintained as needed | CLI, docs, stubs, diagnostics, scaffolding, and testing guides have a usable baseline. |
| 5 | Professional UI Kit and Reference Apps | Active | Product-shape validation through neutral reference apps, portable UI, preview gallery, and operational demos. |
| 6 | Public Framework Extraction/Stabilization | Planned | Public framework extraction/stabilization remains planned once the pre-alpha product surface is coherent. |

## Now

- Keep `README.md`, `preview/`, and core docs aligned with the Product North
  Star: Otoe first, Wraith as case study.
- Make Hardware Control Panel, Portable Core UI, UI Kit, Utility Ops, admin, and
  data workflow examples the main product-shape evidence.
- Keep HTML render and live HTML preview positioned as useful development
  surfaces, not as the definition of the runtime.
- Keep native PNG, `NativeSurface`, and offline build outputs positioned as
  experimental evidence and technical previews.
- Improve app-author docs around the portable subset: components, state,
  styling, input behavior, previews, and tests.
- Keep backend/render/build evidence in contributor-oriented docs instead of the
  first-run app-author path.

## Next

- Tighten the non-Wraith reference apps until a Python developer can understand
  the product direction in minutes.
- Add or refine small examples that show provider/adaptor boundaries for local
  services, devices, and fake test data.
- Make the portable CSS subset easier to inspect, validate, and explain without
  implying browser CSS parity.
- Expand test evidence for touch/mouse/keyboard/focus paths that matter for
  appliance and kiosk interfaces.
- Keep offline bundle validation repeatable from clean checkouts and document
  that it is an audit/deployment contract, not a sandbox.
- Continue backend-candidate work only when it strengthens a clearly documented
  renderer/backend contract.

## Later

- Evaluate a real native backend stack after the current native evidence path
  proves enough layout, text, paint, input, and packaging behavior.
- Decide which product-facing APIs can graduate from pre-alpha preview toward a
  compatibility policy.
- Extract more shared UI primitives only after repeated reference-app usage
  proves they are stable enough.
- Define a fuller CSS track only if it can remain portable and honest about
  constrained runtimes.
- Public framework extraction/stabilization remains planned once the pre-alpha
  product surface is coherent.

## Explicit Non-Goals

- No stable public API guarantee while Otoe is pre-alpha.
- No production desktop renderer promise today.
- No claim of full browser CSS, DOM APIs, or browser layout compatibility.
- No claim that offline bundles are a security sandbox.
- No runtime dependency installation on constrained hardware targets.
- No generic replacement promise for Qt, Flutter, Electron, React, or browser
  apps.
- No Wraith-first product story.
- No migration of private/production application surfaces until Otoe proves a
  better maintainability and deployment story through neutral examples.

## Exit Criteria For Current Phase

Phase 5 can close when:

- A new Python developer can read the README, preview gallery, and quickstart
  and understand what Otoe is for in under five minutes.
- At least three non-Wraith reference apps demonstrate distinct operational
  shapes: hardware/control panel, local admin/settings, and data/table workflow.
- Reference apps use explicit provider or adapter boundaries instead of hidden
  global fixture assumptions.
- Static HTML preview, local live preview, native PNG evidence, and offline
  build validation are documented with honest maturity labels.
- The portable UI/style subset is documented well enough for app authors to use
  it without reading renderer internals.
- Wraith documentation is clearly labeled as case study evidence.
- Backend/render/build contributor paths remain discoverable without dominating
  the first-run product message.

## Risks

- The project could drift back into backend/rendering evidence before the app
  author story is coherent.
- Browser preview polish could accidentally imply production runtime maturity.
- Native layout/text limitations could block credible appliance UI evidence.
- Offline build artifacts could be mistaken for sandboxing or security
  isolation.
- Wraith examples could continue to overdefine the project if neutral reference
  apps are not kept current.
- API surface area could grow faster than the pre-alpha compatibility story.

