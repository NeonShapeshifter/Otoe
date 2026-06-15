# Wraith-Inspired Visual Benchmark

This document defines a Wraith-inspired visual benchmark for Otoe examples.

It is not a Wraith migration plan. It must not import Wraith, modify Wraith, or
connect to any Wraith product runtime, vault, mission, hardware, session, or
security APIs. The benchmark uses fake data and Otoe-only components to prove
whether Otoe can render professional appliance/operator screens in the product
family that inspired the framework.

Read-only references:

- local Wraith checkout: `WRAITH_UI.md`
- local Wraith checkout: `WraithUI/` static prototype
- Wraith product repository: `wraith/src/screens/mission_exec.py`
- `examples/wraith/mission_exec_surface.py`
- `examples/wraith_input_console.py`

The `WraithUI/` reference is a static visual prototype, not production Wraith
runtime. The current Wraith product remains Kivy. Otoe should learn from both
without making either one a dependency. Otoe examples must remain standalone:
they do not import Wraith and should run without a local Wraith checkout.

## Benchmark Rule

Every benchmark screen must satisfy these constraints:

- no `import wraith`,
- no file reads from any local Wraith checkout or Wraith product repository path
  at runtime,
- no real mission execution,
- no hardware access,
- no vault/session/secrets access,
- no offensive workflow implementation,
- all state is local fake state owned by the Otoe example,
- all actions are deterministic UI state changes or operator-log entries.

The benchmark should be credible enough to answer one product question:

Can Otoe become a plausible frontend runtime for a Wraith-class private/reference
product without making the browser the required runtime and without accepting
the visual limits of the current Kivy UI?

## Shared Product Shape

All benchmark screens should feel like they belong to the same appliance shell:

- fixed operational canvas first: target `1280x800`, with a smaller
  `1024x600` smoke shape when practical;
- persistent top chrome with campaign, runtime, hardware, clock, battery, lock,
  settings, and notes affordances represented as fake state;
- dense but legible panels with hairline borders and clear section titles;
- dark operational surfaces with restrained semantic color;
- monospaced labels for telemetry, IDs, counts, timers, and state;
- touch-sized primary controls, visible focus, and a keyboard path;
- scroll regions for terminal, lists, event feeds, and detail payloads;
- no critical hover-only actions;
- no marketing layout, mascot dependency, large decorative hero, or browser-only
  visual trick as a required product affordance.

## Screen 1: MissionExec

### Purpose

MissionExec is the live execution surface. It proves that Otoe can render a
professional real-time operator console: mission context, preflight summary,
runtime state, terminal output, event timeline, guarded approvals, and emergency
controls in one dense screen.

This is the first benchmark screen to implement.

### Layout Target

Target a two-column console under the shared top chrome:

- left column around one third of the screen;
- right column around two thirds of the screen;
- left column contains mission brief, mission facts, status/timer, execution
  state, preflight checklist, and emergency controls;
- right column contains capture probe/status strip, terminal telemetry,
  filter/actions row, event timeline, and approval dialog overlay;
- terminal region is the largest visual surface and must remain readable;
- event timeline is secondary but always visible on desktop-size benchmark
  frames;
- approval state appears as a modal or clearly layered panel without hiding
  abort/resume context permanently.

### Components Needed

- `Toolbar` or app shell chrome.
- `Card`/`Surface` panels with tight radius and hairline borders.
- `Badge`/`StatusPill` for runtime, signal, warning, and approval states.
- `ActionButton` for abort, pause/resume, simulate, export, clear, approve, and
  deny.
- `Tabs`/`TabButton` for terminal and event filters.
- `ScrollView` for terminal output and event timeline.
- `Dialog` for guarded approval.
- Reusable rows: mission fact, preflight check, log line, event row.

### Fake Data Needed

- mission name, vector, description, opsec posture;
- target, scope, asset, profile, validation, posture;
- runtime status: staged, running, paused, approval pending, warning, complete;
- elapsed timer string;
- five or six preflight checks: policy guard, hardware, scope, profile,
  tooling, vault;
- terminal lines with IDs, timestamps, levels `info`, `ok`, `warn`, `sig`,
  `cmd`, `crit`;
- event timeline entries with timestamp, tag, severity, and short message;
- pending approval payload with step ID, summary, and detail;
- runtime probe frame with label and last observed event.

### Visual States

- staged/standby before execution;
- running with live signal and elapsed timer;
- paused with timer and capture state visibly distinct;
- approval pending with modal/panel and safe action pair;
- warning/error with terminal and event severity colors;
- aborted/completed summary state as a non-live terminal tail.

### Minimum Interactions

- filter terminal lines by level;
- filter event rows by severity;
- pause/resume capture;
- queue fake approval;
- approve or deny fake approval;
- simulate one frame/log/event append;
- clear visible terminal buffer;
- export action writes a deterministic log entry;
- abort opens or records a deterministic abort state.

### Touch And Keyboard

- all primary controls should be at least 44px high in HTML preview;
- Tab reaches filters, pause/resume, approval actions, terminal controls, and
  abort in a predictable order;
- Enter/Space activates the focused control;
- Escape dismisses approval and any transient panel;
- scrolling works for terminal and event regions;
- no critical action requires hover, right click, or a hidden gesture.

### HTML Preview Requirements

- render statically through `otoe render`;
- run interactively through `otoe dev`;
- use local assets only;
- keep the first viewport as the actual console, not an explanation page;
- show a realistic 1280x800 frame without overlapping text;
- browser-only CSS polish may exist, but critical layout and state must map to
  the portable Otoe subset.

### Native PNG Requirements

- render a deterministic native PNG through `otoe render --native`;
- produce a useful first-frame screenshot at `1280x800`;
- produce a higher-density `--native-scale 2` smoke image;
- keep mission facts, status, primary controls, terminal rows, and event rows
  visible;
- avoid layout features outside native layout v0 unless they are only browser
  polish;
- readable text through the optional Pillow path is preferred for visual review;
  the marker renderer remains acceptable only as a contract baseline.

### Out Of Scope For Now

- importing real mission runners or controllers from the private/reference
  product;
- executing a mission;
- real timer scheduling beyond deterministic fake state;
- real screenshot, lock, settings, notes, or campaign switching behavior;
- terminal virtualization for hundreds of rows;
- animated mascot/chibi state machine as a required UI primitive;
- production native windowing claims.

## Screen 2: PreFlight

### Purpose

PreFlight is the common launch gate before mission execution. It must feel like
an enforcement screen, not a cosmetic confirmation dialog. The benchmark proves
that Otoe can represent target selection, mission parameters, scope evaluation,
policy evaluation, hardware readiness, tooling readiness, and launch gating in a
clear operator workflow.

### Layout Target

Use a three-zone layout under shared chrome:

- left zone: selected mission, target selector/list, profile/asset context;
- center zone: launch checklist with scope, policy, hardware, tooling, vault,
  and parameter readiness;
- right zone: launch summary, risk/posture, blocked reasons, and primary
  `ENGAGE` affordance;
- bottom or side detail drawer for expanded check evidence when selected;
- `ENGAGE` remains disabled or visually guarded until the fake checks allow it.

### Components Needed

- app shell/top chrome;
- mission summary card;
- list rows for targets/assets/profiles;
- form-like controls for fake parameters;
- check rows with status icons and details;
- risk/status badges;
- collapsible or selectable evidence details;
- primary `ENGAGE`, secondary back/cancel, and rerun-checks buttons;
- confirmation dialog when a warning posture is allowed but not clean.

### Fake Data Needed

- mission catalog entry with name, vector, description, lab/deferred posture;
- target list with allowed/denied/in-review scope status;
- mission parameter values and validation messages;
- scope evaluation result;
- policy evaluation result;
- hardware readiness result with device name and mode;
- tooling readiness result;
- selected payload profile and optional workbench asset;
- blocked reason list and launch summary.

### Visual States

- ready: all checks pass and `ENGAGE` is available;
- blocked: one or more checks fail and `ENGAGE` is disabled;
- warning: policy or posture requires operator confirmation;
- missing hardware: hardware row is prominent and recovery action is visible;
- editing: parameter change marks checks stale until rerun;
- launch queued: fake transition state toward MissionExec.

### Minimum Interactions

- select target;
- select profile/asset;
- edit one fake parameter;
- rerun checks;
- expand a check detail;
- toggle warning/blocked demo state;
- press `ENGAGE` only when fake checks allow it;
- cancel/back returns to a neutral operator state.

### Touch And Keyboard

- target/profile rows are reachable by Tab and activatable with Enter/Space;
- parameter input supports text entry and focus-visible styling;
- Arrow keys may move within a selected list if Otoe exposes the pattern;
- Escape closes confirmation/detail overlays;
- `ENGAGE` must not be the first accidental focus target when warnings exist.

### HTML Preview Requirements

- include ready, blocked, warning, and missing-hardware states in the demo model;
- show disabled/enabled launch behavior clearly;
- allow quick state switching in live preview without real backend checks;
- avoid browser-only form controls that cannot map to Otoe native input later.

### Native PNG Requirements

- render at least one ready-state PNG and one blocked-state PNG;
- keep check labels, check states, selected target, and `ENGAGE`/blocked reason
  visible;
- use stack-first geometry that can survive native layout v0;
- represent disabled/blocked controls visibly in native paint.

### Out Of Scope For Now

- real private/reference product policy or scope evaluation;
- actual launch handoff into a Wraith product runtime;
- real hardware detection;
- secret/profile loading from a private/reference product vault;
- destructive parameter persistence;
- full form validation framework.

## Screen 3: Vault/Workbench

### Purpose

Vault/Workbench is the operator memory and preparation benchmark. It proves
that Otoe can handle dense internal-tool UI: search, filters, grouped records,
payload detail, metadata, related findings, reusable assets, profile editing,
validation feedback, and promotion flows.

This benchmark may be one app with two modes rather than two separate screens:
`Vault` for campaign-scoped loot and `Workbench` for reusable profiles/assets.

### Layout Target

Use a split data-workbench layout:

- shared chrome at top;
- left rail or top segmented control for `Vault`, `Profiles`, and `Assets`;
- search and filters near the list;
- main list grouped by target or item type;
- detail pane with payload, metadata, related findings, and state;
- right action rail for copy, mark synced, promote to asset, open asset,
  validate profile, run fake asset tool, and inspect raw data;
- scrollable payload/code block that remains readable in HTML and native PNG.

### Components Needed

- shell/top chrome;
- segmented tabs or mode tabs;
- search `Input`;
- grouped list rows;
- detail card/pane;
- metadata grid;
- payload/code block in `ScrollView`;
- badges for synced, promoted, warning, stale, valid, invalid;
- action rail buttons;
- empty state and no-results state;
- confirmation dialog for destructive-looking fake actions.

### Fake Data Needed

- campaign summary and selected campaign name;
- loot grouped by target with type, timestamp, severity, synced flag, promoted
  flag, and payload preview;
- related findings;
- reusable workbench assets with kind, source, status, and last used time;
- payload profiles with validation result and test output;
- fake raw JSON/detail payload;
- operator log entries for copy/promote/sync/run actions.

### Visual States

- Vault list with selected loot detail;
- no search results;
- unsynced loot requiring action;
- promoted loot linked to an asset;
- Workbench Profiles mode with valid and invalid profiles;
- Workbench Assets mode with selected reusable asset;
- validation warning/error;
- action confirmation open.

### Minimum Interactions

- switch between Vault, Profiles, and Assets;
- search/filter the list;
- select a row and update detail pane;
- copy payload by writing to the operator log;
- mark fake loot as synced;
- promote fake loot to asset;
- open promoted asset in Workbench mode;
- validate a fake profile;
- run a fake asset tool and append result output.

### Touch And Keyboard

- mode tabs and action rail controls are touch-sized;
- search supports text entry;
- Tab order moves from mode tabs to search, list, detail actions, and payload
  region;
- Enter/Space activates selected row/action;
- Escape closes raw/confirm panels;
- scrolling works independently for list and payload/detail regions.

### HTML Preview Requirements

- support realistic dense data without becoming a card gallery;
- show list/detail/action rail in the first viewport;
- keep fake payload text local and deterministic;
- demonstrate no-results, invalid profile, and promoted asset states in live
  preview.

### Native PNG Requirements

- render one Vault-state PNG and one Workbench-state PNG;
- selected row, detail header, payload block, and primary actions must be
  visible;
- use explicit dimensions for list/detail regions where native layout v0 needs
  stable framing;
- avoid relying on CSS grid, absolute positioning, or browser-only overflow
  behavior for the portable contract.

### Out Of Scope For Now

- real private/reference product vault reads or writes;
- cryptographic sealing, unlock, or sync providers;
- actual clipboard integration;
- real payload profile persistence;
- real syntax testing or asset tool execution;
- destructive CRUD;
- importing private/reference product models.

## Professional Visual Criteria

A benchmark screen looks professional when it satisfies all of these:

- The first glance explains the operator state: where am I, what is selected,
  what is live, what is blocked, and what can I safely do next.
- The screen is dense, but not noisy; related information is grouped and visual
  priority is obvious.
- Typography is deliberate: readable body text, monospaced operational values,
  stable tabular numbers for timers/counts, no oversized dashboard vanity text.
- Color is semantic and restrained: signal, ok, warning, critical, info, muted;
  no rainbow status soup and no decorative gradients as the main design move.
- Controls look touchable and behave predictably across click, tap-style
  activation, keyboard focus, and Enter/Space activation.
- Dangerous actions are visually distinct and confirmation-gated where needed.
- Panels align to a clear grid; no overlapping text, clipped buttons, accidental
  wrapping, or layout jumps when state changes.
- Scroll regions are obvious and preserve surrounding context.
- Fake data looks like operator data, not placeholder lorem ipsum.
- HTML preview and native PNG share the same product structure; the browser may
  add polish, but not a different information architecture.
- The native PNG is useful evidence, not merely proof that something rendered.
- The screen is Wraith-inspired without copying Wraith internals.

## First Implementation: MissionExec

MissionExec should ship first because it is the highest-pressure surface and
already has partial Otoe validation in `examples/wraith/mission_exec_surface.py`.
It exercises the hardest product requirements in one screen:

- live terminal density;
- status/timer visibility;
- preflight context;
- emergency controls;
- filters and scroll;
- approval overlays;
- touch and keyboard operation;
- HTML preview plus native PNG evidence.

The first implementation target should produce:

- an Otoe-only example module;
- fake MissionExec model/state;
- portable CSS for native/plan/build;
- optional richer HTML preview CSS only where it does not change the contract;
- static HTML render;
- live preview;
- deterministic native PNG;
- build validation;
- focused tests for filters, approval, pause/resume, abort state, and visible
  native text/layout evidence.

## What Otoe Must Prove For Future Wraith-Class Frontend Use

For Otoe to become a plausible frontend for Wraith-class private/reference
products, these benchmark screens must show that Otoe can provide:

- a professional appliance shell with persistent chrome;
- a component model that can express Wraith-inspired screens without
  app-specific framework hacks;
- a CSS-like style subset strong enough for dense operational UI;
- native render output that is visually credible and testable;
- input behavior that works for touch, mouse, keyboard, focus, scroll, and
  guarded actions;
- offline bundle artifacts that make deployment reviewable;
- fake-provider boundaries that could later be replaced by product-specific
  adapters;
- clear API tiers so future product-specific integration does not depend on
  unstable internals by accident;
- security and trust boundaries that do not imply Otoe is a vault or mission
  sandbox.

The benchmark earns confidence only if it stays independent. Wraith can inspire
the screens, but Otoe must prove the frontend runtime on its own first.
