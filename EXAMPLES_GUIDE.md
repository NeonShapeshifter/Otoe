# Examples Guide

Otoe examples are validation surfaces. They should stay framework-neutral where
possible and case-study-shaped where useful. Use this guide to pick the smallest
example that proves the behavior you want to inspect.

Repository examples are source-checkout surfaces. They are not installed into
the PyPI wheel. Use `otoe new` for installed-package onboarding, and run these
examples from a checkout with `PYTHONPATH=src:.` unless the package is already
installed in editable mode.

## Choose an example

Start with the smallest row that proves the surface you care about. Static
commands render files and exit. Live commands start a localhost dev server and
are for development only. Native output is experimental evidence, not a
production renderer claim. Backend candidate examples are advanced contributor
paths.

| If you want to... | Example/module | Command | Writes files? | Needs display? | Works from wheel or source checkout? | Maturity/status |
| --- | --- | --- | --- | --- | --- | --- |
| Start from the installed package | Generated app from `otoe new` | `otoe new hello_otoe`<br>`cd hello_otoe`<br>`otoe check` | Yes, creates `hello_otoe/` | No | Wheel or editable checkout | App-author pre-alpha path |
| Do the quickest static render from this repo | `examples.quickstart:app` | `PYTHONPATH=src:. python -m otoe render examples.quickstart:app --out preview.html --pretty` | Yes, `preview.html` | No | Source checkout | Usable static preview |
| Inspect the portable widget/UI matrix | `examples.portable_core_ui:app` | `PYTHONPATH=src:. python -m otoe render examples.portable_core_ui:app --out preview/portable_core_ui.html --css preview/portable_core_ui.css --pretty` | Yes, `preview/portable_core_ui.html` | No | Source checkout | Public pre-alpha support matrix |
| Review shared product UI primitives | `examples.ui.preview` | `PYTHONPATH=src:. python -m examples.ui.preview > preview/ui.html` | Yes, `preview/ui.html` | No | Source checkout | Product-preview reference app |
| Try the main neutral product-facing demo | `examples.hardware.control_panel:app` | `PYTHONPATH=src:. python -m otoe render examples.hardware.control_panel:app --out preview/hardware_cli.html --css preview/hardware_portable.css --pretty` | Yes, `preview/hardware_cli.html` | No | Source checkout | Active Phase 5 product-shape validation |
| See a utility-first operational console | `examples.utility.preview` | `PYTHONPATH=src:. python -m examples.utility.preview > preview/utility_ops.html` | Yes, `preview/utility_ops.html` | No | Source checkout | Product-preview reference app |
| Run the smallest live localhost example | `examples.live_counter:app` | `PYTHONPATH=src:. python -m otoe dev examples.live_counter:app --port 8767` | No persistent files | Browser recommended to interact | Source checkout | Local dev only |
| Produce native/headless evidence | `examples.native.counter_demo` | `PYTHONPATH=src:. python -m examples.native.counter_demo` | Yes, frames under `preview/native/` | No | Source checkout | Experimental native evidence |
| Build and validate an offline bundle | `examples/offline_bundle/` | `cd examples/offline_bundle`<br>`PYTHONPATH=../../src:. python -m otoe build app:app --profile-file otoe.profile.toml --out ../../dist/offline_bundle --validate` | Yes, `dist/offline_bundle/` | No | Source checkout | Technical preview, not a sandbox |
| Compare a non-appliance dashboard shape | `examples.saas.preview` | `PYTHONPATH=src:. python -m examples.saas.preview > preview/saas.html` | Yes, `preview/saas.html` | No | Source checkout | Case study |
| Inspect Wraith as advanced case-study pressure | `examples.wraith.mission_exec_showcase:app` | `PYTHONPATH=src:. python -m otoe render examples.wraith.mission_exec_showcase:app --out preview/wraith_mission_exec.html --css preview/wraith_mission_exec.css --pretty` | Yes, `preview/wraith_mission_exec.html` | No | Source checkout | Advanced case study, not default path |
| Work on renderer/backend contributor contracts | `examples.native.backend_candidate_skeleton` | `PYTHONPATH=src:. python -m examples.native.backend_candidate_skeleton --json` | No by default | No | Source checkout | Advanced/contributor experimental path |

The Phase 5 reference app extraction rules live in
`REFERENCE_APP_PATTERNS.md`. Use that document before adding another broad
example or moving repeated markup into `otoe.ui`. It also documents the
provider/adaptor boundary used by the hardware, admin/settings, and data
workflow reference apps: fake providers by default, explicit `provider=` for
previews and tests, and no hidden global fixture requirement.

## Quickstart

Path: `examples/quickstart.py`

Use this when you need the smallest static render target for the CLI.

```bash
PYTHONPATH=src:. python -m otoe render examples.quickstart:app --out preview.html --pretty
PYTHONPATH=src:. python -m otoe render examples.quickstart:app --out preview.png --native
```

This example proves import-target rendering. It does not prove live events.

## Portable Core UI

Path: `examples/portable_core_ui.py`

Use this when you need runnable examples for every Primitive in Portable Core
UI v0. The module exports one target per matrix row plus a gallery target.

```bash
PYTHONPATH=src:. python -m otoe render examples.portable_core_ui:app --out preview/portable_core_ui.html --css preview/portable_core_ui.css --pretty
PYTHONPATH=src:. python -m otoe render examples.portable_core_ui:app --out preview/portable_core_ui.png --native --css preview/portable_core_ui.css
PYTHONPATH=src:. python -m otoe build examples.portable_core_ui:app --out dist/portable_core_ui_cage --css preview/portable_core_ui.css --validate
```

The support matrix and outside-v0 classifications live in
`docs/portable-core-ui-v0.md` and `docs/portable-core-ui-v0.json`.
`preview/portable_core_ui.css` is the strict portable stylesheet used by the
CLI render, native PNG, plan, and build smoke tests.
Use `otoe portable-core --examples --outside` to inspect the packaged matrix
and source-checkout example targets.

## Live Counter

Path: `examples/live_counter.py`

Use this when you need the smallest live preview app shape:

- app object with `render_fragment()`
- app object with `dispatch_event(event_id, *args)`
- `LiveHtmlRenderer`
- mounted component tree reused across events
- signal-driven rerendering

```bash
PYTHONPATH=src:. python -m otoe dev examples.live_counter:app --port 8767
```

This is the reference for future tiny live-preview examples.

## Offline Bundle

Path: `examples/offline_bundle/`

Use this when changing the low-level build pipeline:

- simple `app:app` target auto-copying
- recursive same-directory import copying
- profile-declared asset copying
- compiled `otoe-styles.json` with profile safelisted dynamic classes
- generated runner validation
- verified `.tar.gz` packing

```bash
cd examples/offline_bundle
PYTHONPATH=../../src:. python -m otoe build app:app --profile-file otoe.profile.toml --out ../../dist/offline_bundle --validate
PYTHONPATH=../../src:. python -m otoe pack ../../dist/offline_bundle --out ../../dist/offline_bundle.tar.gz
```

This example should stay small and hardware-oriented. Its job is to prove that a
user can build, validate, and pack a self-contained bundle before moving it to a
target device.

## Native Counter

Path: `examples/native/counter_demo.py`

Use this when you need the smallest native renderer smoke:

- `NativeSurface`
- before/after PNG frames
- native click dispatch
- state update through an Otoe event

```bash
PYTHONPATH=src:. python -m examples.native.counter_demo
```

This writes native counter frames under `preview/native/`.

## Native Task Board

Path: `examples/native/task_board_demo.py`

Use this as the current framework-neutral native app surface:

- controlled search input
- filtered `For(...)` rows
- empty state
- `Show(...)` modal state
- shortcuts
- controlled `ScrollView(scrollY=..., onScroll=...)`
- PNG frame sequence

```bash
PYTHONPATH=src:. python -m examples.native.task_board_demo
```

This is the main native app-shaped example without Wraith or SaaS coupling.

## Native Portable Core UI

Path: `examples/native/portable_core_ui_demo.py`

Use this when checking the product-facing portable UI subset against native PNG
output. It renders `examples.portable_core_ui:app` with
`preview/portable_core_ui.css` and writes a deterministic marker-text frame,
plus an optional Pillow readable-text frame when requested or available.

```bash
PYTHONPATH=src:. python -m examples.native.portable_core_ui_demo
PYTHONPATH=src:. python -m examples.native.portable_core_ui_demo --marker-only
PYTHONPATH=src:. python -m examples.native.portable_core_ui_demo --pillow --scale 2
```

## Native Window Demo

Path: `examples/native/window_demo.py`

Use this when you need `NativeWindowDriver` or optional `run_native(...)` smoke:

```bash
PYTHONPATH=src:. python -m examples.native.window_demo
PYTHONPATH=src:. python -m examples.native.window_demo --window
```

The `--window` mode requires Tk and a graphical display. It is a manual
experiment, not a production desktop backend.

## Native Backend Candidate Skeleton

Path: `examples/native/backend_candidate_skeleton.py`

Use this before adding Skia, Taffy, or another concrete backend. It provides a
recording backend adapter, `HeadlessCandidateBackend`, and acceptance reports
that drive:

- minimal driver replay
- app-shaped native task board replay
- fake adapter routing through `run_native(...)`
- layout, paint, focus, frame, and visible-text summaries

The skeleton has no external backend dependency and does not open a window.

```bash
PYTHONPATH=src:. python -m examples.native.backend_candidate_skeleton
PYTHONPATH=src:. python -m examples.native.backend_candidate_skeleton --json
```

## UI Kitchen Sink

Paths:

- `examples/ui/kitchen_sink.py`
- `examples/ui/preview.py`
- `examples/ui/live_preview.py`

Use this when changing shared `otoe.ui` primitives:

- app shell
- sidebar navigation
- route view
- command palette
- dialog
- menu
- select
- data table
- cards, badges, tabs, toolbar, toast

```bash
PYTHONPATH=src:. python -m examples.ui.preview > preview/ui.html
PYTHONPATH=src:. python -m examples.ui.live_preview
```

This example is intentionally broader than quickstart; it catches primitive
integration issues.

## Utility Ops Preview

Paths:

- `examples/utility/ops_console.py`
- `examples/utility/preview.py`

Use this when changing `utility_css()`, `utility_stylesheet()`, or modern preset
ergonomics. It is the first utility-first reference app: the screen is composed
with `AppFrame`, `SidebarFrame`, `TopBar`, `Surface`, `MetricGrid`,
`MetricTile`, `ListRow`, `FeedbackToast`, and `ActionButton`, without an
app-specific CSS file.

```bash
PYTHONPATH=src:. python -m examples.utility.preview > preview/utility_ops.html
```

This example should stay small. Its job is to answer whether a new Otoe user can
assemble a polished operational surface without inventing selectors first.

## SaaS Preview

Paths:

- `examples/saas/overview.py`
- `examples/saas/preview.py`
- `examples/saas/live_preview.py`

Use this to validate calmer product-dashboard UI:

- metrics
- account/customer tables
- settings/status surfaces
- shared UI primitives in a less operational visual rhythm

```bash
PYTHONPATH=src:. python -m examples.saas.preview > preview/saas.html
PYTHONPATH=src:. python -m examples.saas.live_preview
```

This is a case study, not a product dependency.

## Hardware Control Panel

Paths:

- `examples/hardware/control_panel.py`
- `examples/hardware/adapters.py`
- `examples/hardware/preview.py`
- `examples/hardware/live_preview.py`
- `preview/hardware.css`
- `preview/hardware_portable.css`

Use this as the first Phase 5 reference app: a professional Python/hardware
surface that is framework-neutral but shaped like something that could later
read serial, USB, GPIO, SQLite, or a local service adapter.
This is the current recommended non-Wraith product demo because it matches
Otoe's strongest niche: local operational UI with deterministic providers,
safe actions, and offline-testable state.

- device status and connection state
- telemetry cards and table
- event stream
- safe operator controls
- provider boundary with fake data and alternate states for tests
- loading, offline, error, and empty telemetry surfaces

Product target:

```bash
PYTHONPATH=src:. python -m otoe render examples.hardware.control_panel:app --out preview/hardware_cli.html --css preview/hardware_portable.css --pretty
PYTHONPATH=src:. python -m otoe render examples.hardware.control_panel:app --out preview/hardware_cli.png --native --css preview/hardware_portable.css
PYTHONPATH=src:. python -m otoe build examples.hardware.control_panel:app --out dist/hardware_cage --css preview/hardware_portable.css --validate
```

Browser/live preview:

```bash
PYTHONPATH=src:. python -m examples.hardware.preview > preview/hardware.html
PYTHONPATH=src:. python -m examples.hardware.live_preview
```

`preview/hardware.css` is the browser presentation stylesheet.
`preview/hardware_portable.css` is the Otoe Style subset used by CLI render,
native PNG, plan, and build smoke tests.

This example uses fake data intentionally. The fake provider is the test
boundary; the component surface should remain ready for a real provider.

Provider contract:

- implement `snapshot() -> DeviceSnapshot` for the first render
- implement `run_command(command_id: str) -> DeviceSnapshot` for operator
  actions
- return disabled commands with a `disabled_reason` instead of hiding unsafe
  controls
- return `last_feedback` after commands so operators see the result or block
  reason outside the event stream
- model connection state explicitly with `status`, `status_detail`,
  `connection`, and `connection_tone`
- use fixture helpers such as `loading_snapshot()`, `offline_snapshot()`,
  `error_snapshot()`, and `empty_snapshot()` to test non-happy paths

Adapter contract:

- implement `HardwareTransport.read_snapshot()` for the latest transport state
- implement `HardwareTransport.write_command(command_id)` for one operator
  action
- adapt transport responses through `TransportHardwareProvider`
- keep unsafe command guards in the provider layer so a disabled command does
  not write to the transport
- use `MemoryHardwareTransport` for deterministic tests before adding serial,
  USB, GPIO, SQLite, or local service adapters

## Local Admin Settings Console

Paths:

- `examples/admin/settings_console.py`
- `examples/admin/preview.py`
- `examples/admin/live_preview.py`

Use this as the second Phase 5 reference app: a local-first admin/settings
surface with editable provider-backed state, validation, safe actions, access
rules, and audit history.

- editable workspace and runtime settings
- validation and blocked saves
- save, reset, and reload actions
- access-rule toggles with audit feedback
- route-driven overview, settings, access, and audit views
- provider boundary with deterministic fixture data for tests

```bash
PYTHONPATH=src:. python -m examples.admin.preview > preview/admin.html
PYTHONPATH=src:. python -m examples.admin.live_preview
```

This example is also fake-data-backed intentionally. The provider is the
boundary between UI and local state; the component surface should remain ready
for a SQLite, file, device, or service-backed provider.

Provider contract:

- implement `snapshot() -> AdminSnapshot` for the first render
- implement `update_setting(setting_id, value)` for controlled drafts and
  validation
- implement `run_action(action_id)` for save, reset, reload, or future local
  actions
- implement `toggle_access_rule(rule_id)` for local permission controls
- return `last_feedback` after edits or actions so operators see the result
  outside the changed row
- model pending and invalid state explicitly with `pending_changes`, `status`,
  and `status_tone`

## Data Workflow Console

Paths:

- `examples/data_workflow/workbench.py`
- `examples/data_workflow/preview.py`
- `examples/data_workflow/live_preview.py`

Use this as the third Phase 5 reference app: a table-first workflow for
reviewing imported records, filtering a queue, selecting a batch, and running
bulk actions.

- search and stage filters over a table-backed record set
- selected-row workflow and batch summary
- blocked bulk approval when invalid rows are selected
- export preparation action for the filtered view
- route-driven queue, selected, and history views
- provider boundary with deterministic records and workflow events

```bash
PYTHONPATH=src:. python -m examples.data_workflow.preview > preview/data_workflow.html
PYTHONPATH=src:. python -m examples.data_workflow.live_preview
```

This example keeps data operations local and deterministic. A real app can
replace the provider with CSV, SQLite, API, or hardware/service-backed data
without changing the component tree.

Provider contract:

- implement `snapshot() -> WorkflowSnapshot` for the first render
- implement `set_query(value)` and `set_stage_filter(value)` for table filters
- implement `toggle_record(record_id)` for row selection
- implement `run_action(action_id)` for approve, clear, export, or future bulk
  actions
- keep invalid-row guards in the provider so the UI cannot approve blocked data
- return `last_feedback` and append workflow events after actions that change
  operator-visible state

## Wraith Previews

Paths:

- `examples/wraith/topbar.py`
- `examples/wraith/arsenal.py`
- `examples/wraith/runtime_status.py`
- `examples/wraith/preview.py`
- `examples/wraith/live_preview.py`
- `examples/wraith/mission_exec_surface.py`
- `examples/wraith/mission_exec_preview.py`
- `examples/wraith/mission_exec_live_preview.py`
- `examples/wraith/mission_exec_showcase.py`

Use these as advanced case studies for dense operational UI pressure:

- topbar/status surfaces
- mission cards
- runtime status polling
- event timelines
- command and approval flows
- recovered snapshot state

```bash
PYTHONPATH=src:. python -m examples.wraith.preview > preview/wraith.html
PYTHONPATH=src:. python -m examples.wraith.live_preview
PYTHONPATH=src:. python -m otoe render examples.wraith.mission_exec_showcase:app --out preview/wraith_mission_exec.html --css preview/wraith_mission_exec.css --pretty
PYTHONPATH=src:. python -m examples.wraith.mission_exec_live_preview
```

Wraith examples should pressure-test Otoe without leaking Wraith-specific
assumptions into the runtime. They are not the default onboarding path.

## Example Rules

- Keep framework-neutral examples free of case-study language.
- Keep case-study examples outside core runtime assumptions.
- Prefer small examples for docs and CLI behavior.
- Prefer app-shaped examples for renderer and UI primitive integration.
- Do not add a new primitive just to make an example prettier.
- When an example exposes a new runtime boundary, add a focused test for that
  boundary.
