# Otoe Roadmap

**Updated:** July 11, 2026\
**Current program gate:** G0-G2 runtime and release stabilization\
**Product reference:** [Product North Star](docs/product-north-star.md)\
**Native track:** [ADR-021](ADR-021-native-yoga-skia-sdl3-roadmap.md)\
**Layout track:** [Layout v1 Plan](docs/layout-v1-plan.md)\
**Technical history:** [Technical Ledger](docs/technical-ledger.md)

Otoe is a pre-alpha Python-first UI runtime for local operational interfaces:
hardware panels, kiosks, appliances, dashboards, offline tools, and operator
consoles. It has a credible Python authoring model and deterministic evidence
tooling. It does not yet have the SDL3/Skia/Yoga production runtime described by
the native target architecture.

This file is the master dependency graph. ADRs describe design decisions and
technical phases, but they do not override the status or exit gates here.

## Current Truth

- Components, signals, effects, lifecycle, keyed control flow, HTML rendering,
  live preview, portable styles, deterministic native layout/paint/PNG evidence,
  input simulation, and offline bundle verification exist.
- Tk is an optional development host. The current native path is headless/Tk
  evidence, not a production desktop or appliance backend.
- Display List v0 is an inspectable projection after current native paint. A
  standalone scene builder feeding Skia does not yet exist.
- Skia CPU rendering, an SDL3 host, Yoga layout, an SDL end-to-end counter,
  MissionExec SDL smoke, Raspberry Pi/Cage evidence, and native wheel packaging
  are not implemented.
- Otoe is already public and published on PyPI. The remaining framework phase is
  runtime/API stabilization, not deciding whether to extract a public project.
- Wraith is a case study and contract source. It is not an Otoe dependency or a
  production migration target today.

## Historical Workstreams

These labels describe work that landed; “landed” does not imply production
readiness.

| Workstream | Status | What is actually proven |
| --- | --- | --- |
| Case study and first slice | Landed | Initial component architecture and validation direction. |
| Pure Python runtime core | Landed; stabilization active | Core APIs exist; lifecycle, rollback, batching, thread handoff, and keyed-focus invariants now have regression/property coverage. |
| Headless native renderer | Landed | Deterministic Python layout, paint, PNG, hit testing, focus, keyboard, text input, and scroll evidence. |
| Renderer/backend evidence | Landed; freeze expansion | Contracts, support matrices, artifacts, and contributor acceptance paths exist. More evidence work requires a delivery-gate need. |
| Interactive native demo | Prototype | `NativeWindowDriver` and optional Tk prove host wiring. They do not prove SDL3 or hardware readiness. |
| Developer experience | Baseline | Scaffolding, CLI, docs, typing metadata, diagnostics, and testing guides exist; first-run validation remains open. |
| Professional UI/reference apps | Active | Hardware, admin, and data workflow apps validate product shape and provider boundaries. |
| Runtime/API stabilization | Active | Strict typing, compatibility policy, API reduction, release candidates, and stable import boundaries. |
| SDL3/Skia/Yoga native V0 | Planned | ADR-021 Phase A is partial, B is partial, and C-I are not implemented. |

## Delivery Gates

Gates are ordered by dependency. Later work may be researched in parallel, but
it cannot be called complete before its prerequisites pass.

### G0 - Source And Release Integrity

**Status:** Active; implementation hardened locally, public promotion pending.

Exit criteria:

- one Git commit is the source of every public source sync and package artifact;
- no release is copied from an uncommitted working tree;
- annotated immutable `vX.Y.Z` tags target a commit reachable from `main`;
- CI, strict typing, coverage, package metadata, exact wheel/sdist smoke,
  reproducibility, and performance budgets pass before publication;
- one checksummed, attested artifact is promoted to PyPI without rebuilding;
- existing PyPI versions fail loudly rather than using `skip-existing`;
- the historical `v0.1.9` discrepancy is documented with immutable PyPI hashes
  and an additive provenance ref to the actual published-source commit.

### G1 - Runtime Correctness

**Status:** Active; fixes and focused/property tests pass locally.

Exit criteria:

- owner lifecycle has explicit created/mounting/mounted/disposing/disposed states;
- resources created during dynamic activation belong to the correct owner;
- effects created in `on_mount()` run and dispose correctly;
- every cleanup is attempted exactly once and multiple failures are aggregated;
- direct and batched failed updates restore signal and rendered state;
- all subscribers are attempted in deterministic registration order;
- `Show` changes branches only when condition truthiness changes;
- keyed identity retains child ownership and native focus across reorder/rebuild;
- state-machine/property tests cover mount, update, reorder, failure, and unmount;
- the full supported-Python CI matrix passes these invariants.

### G2 - Runtime Thread And Host Contract

**Status:** Active; single-thread enforcement and posted-callback queue landed
locally, integration soak remains.

Exit criteria:

- subscribed reactive values reject direct cross-thread mutation before state
  changes;
- workers use a documented thread-safe `post()` handoff;
- built-in hosts drain posted callbacks on the owning runtime thread;
- hardware/provider examples use the same handoff for background results;
- repeated start, update, failure, unmount, and restart tests show no lost work or
  leaked resources.

### G3 - Phase 5 Product-Shape Closure

**Status:** Active; the strict MissionExec baseline is landed, while external
cold-start validation remains open.

Exit criteria:

- three neutral reference apps remain green: hardware/control, admin/settings,
  and data/table workflow;
- every reference app exposes a provider or adapter boundary and fake test data;
- an unfamiliar Python developer can complete README -> `otoe new` -> `otoe
  dev` -> `otoe check` in under five minutes without renderer internals;
- the default CLI/help and docs lead with app-author workflows;
- portable UI/style/input behavior is usable without reading backend modules;
- the landed MissionExec showcase remains green as strict portable native/build
  acceptance evidence; the rich legacy surface and browser-only CSS remain
  clearly separate;
- Wraith and all backend-candidate material are labeled contributor/case-study
  evidence rather than the product entry point.

### G4 - Native V0 Vertical Slice

**Status:** Planned. ADR-021 A/B partial; C-I not started.

Required order:

1. Stabilize a scene/display-list input independent of the current painter.
2. Add an optional Skia CPU consumer with explicit font input and clean missing
   dependency behavior.
3. Add a minimal SDL3 host that presents the pixel buffer and reports close,
   click, key, text, and wheel events.
4. Run the existing layout v0 through app -> display list -> Skia -> SDL3 for a
   counter before adding Yoga.
5. Render a strict-portable MissionExec snapshot in that host.
6. Add Yoga only for demonstrated layout gaps, with differential tests against
   layout v0 for the supported subset.

Exit criteria:

- counter click, Tab, Shift+Tab, Enter/Space, Escape, text, and scroll work in an
  SDL3 window;
- MissionExec snapshot content, disabled controls, focus, dialog representation,
  and log scrolling work without importing Wraith;
- default installation and existing HTML/headless paths remain dependency-light;
- optional dependency absence produces actionable errors;
- automated screenshots plus manual window evidence are recorded on x86_64.

Do not implement Yoga, Skia, and SDL3 as one undifferentiated change. Do not
stabilize a backend API before this slice shows which boundary is real.

### G5 - Appliance Hardware Evidence

**Status:** Planned; depends on G4.

Exit criteria:

- x86_64 Linux soak passes before Raspberry Pi work;
- Raspberry Pi/aarch64 runs under Wayland with Weston or Cage at the target
  fullscreen resolution;
- touch/click, keyboard focus/activation, text input, wheel/touch scrolling,
  offline boot, process restart, and repeated runtime restart are exercised;
- commands, OS image/package versions, limitations, logs, and visual evidence are
  reproducible from a clean device;
- no production Wraith migration is claimed from a smoke test.

### G6 - Runtime/API Stabilization

**Status:** Active groundwork; graduation depends on G4/G5 feedback.

Exit criteria:

- app-author, product-preview, experimental-native, and contributor-backend APIs
  have explicit import boundaries;
- the top-level export set is reduced deliberately with deprecation shims rather
  than silently broken;
- compatibility, deprecation, and SemVer policies are documented and tested;
- public stubs match runtime behavior for the supported API tier;
- framework-neutral examples cover dashboard, settings, local data workflow, and
  hardware/status surfaces;
- backend evidence commands are grouped away from the primary author workflow;
- one release-candidate cycle validates downstream apps before stable claims.

### G7 - Release Candidate And Promotion

**Status:** Planned; depends on the gates required by the release scope.

Exit criteria:

- build an RC once from a clean commit;
- test that exact wheel/sdist and publish the same attested bytes to the selected
  index;
- run downstream app and hardware acceptance against the RC artifact;
- promote by versioned artifact policy without rebuilding or moving a tag;
- record known limitations and rollback/forward-fix instructions.

## Immediate Sequence

1. Finish G0 by committing a coherent private source state, reviewing its diff,
   syncing from that commit, and repairing/documenting `v0.1.9` provenance.
2. Finish G1/G2 with the full matrix, coverage, package, and soak verification.
3. Run an external cold-start Phase 5 test and keep the landed strict portable
   MissionExec baseline green.
4. Freeze new backend-evidence formats and UI primitives unless a gate requires
   them.
5. Implement G4 as Skia CPU -> SDL3 counter -> MissionExec -> Yoga-on-demand.
6. Run G5 on x86_64, then Raspberry Pi/Cage, before API graduation.

## Explicit Non-Goals

- No stable public API guarantee while Otoe remains pre-alpha.
- No production native renderer claim before G4/G5 pass.
- No full browser CSS, DOM, flexbox, or grid compatibility claim.
- No claim that offline bundles or backend packages are a security sandbox.
- No required native dependencies in the default installation.
- No direct Wayland, DRM/KMS, Skia GPU, complex shaping, IME, full accessibility,
  advanced gesture, animation, or generic Qt/Flutter/Electron replacement in V0.
- No Wraith production migration until neutral evidence and hardware gates prove
  a better maintainability and deployment story.

## Program Risks

- Manual source promotion can still destroy provenance until G0 is operational,
  not merely documented.
- A large top-level API can freeze accidental abstractions before the real native
  slice tests them.
- Browser preview polish can be mistaken for native runtime maturity.
- Layout, text shaping, native dependency packaging, and aarch64 distribution are
  the largest unknowns in the remaining effort.
- More evidence schemas can create work without reducing product risk.
- Hardware success on one image/device can be overgeneralized without soak and
  restart evidence.
