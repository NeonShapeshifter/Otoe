# Otoe Design System v0

Design System v0 defines the first visual direction for Otoe hardware
appliances and operator consoles. It is informed by a Wraith-inspired reference
surface, but it is not Wraith-specific: any hardware maker should be able to use
it for dense, dark, tactile interfaces with live data and critical actions.
Otoe examples use fake local data and do not import the Wraith product
repository at runtime.

MissionExec is the priority showcase. The system should first make
`examples/wraith/mission_exec_surface.py` feel like a production appliance
screen, then generalize the same language to hardware control panels,
diagnostic consoles, and local admin surfaces.

## Inputs Reviewed

- `STYLE_GUIDE.md`
- `WIDGET_CONTRACTS.md`
- `examples/wraith_input_console.py`
- `preview/wraith_input_console.css`
- `examples/wraith/mission_exec_surface.py`
- local Wraith checkout: `WraithUI/index.html` static prototype
- supporting docs and CSS for current portable UI, Wraith visual benchmark, and
  hardware previews

## Product Direction

Otoe appliance UI should feel like product hardware, not a web dashboard. The
first viewport is the console. It should show real operating state, live feeds,
readiness checks, and irreversible actions without a marketing layer in front
of the operator.

The v0 language is:

- dark graphite surfaces with shallow depth and clear hairline separation;
- dense but readable information layout;
- restrained semantic color, used for state and risk rather than decoration;
- monospaced numerics, IDs, timers, telemetry, and terminal-like data;
- touch-sized controls that still work with keyboard and mouse;
- critical actions grouped, labeled, and confirmation-gated;
- small radii, hard edges, and appliance-like chrome;
- no Material UI clone, no Tailwind clone, no generic SaaS card stack.

## Otoe CSS Subset Rules

The portable target must respect the current Otoe CSS subset:

- use single class selectors only, such as `.ap-panel`;
- avoid descendant selectors, pseudo-classes, grouped selectors, media queries,
  animations, and general custom-property logic in portable CSS;
- use flat Otoe token names through `css(..., tokens=...)` or raw hex values;
- keep critical layout expressible through widget props, direct class rules, and
  portable properties such as `width`, `height`, `min-height`, `padding`, `gap`,
  `background`, `color`, `border-*`, `border-radius`, `font-size`, and
  `font-weight`;
- treat browser-only polish such as `box-shadow`, `backdrop-filter`,
  `@media`, `:hover`, CSS variables, and animation as optional preview polish.

Recommended portable pattern:

```css
.ap-panel {
  padding: 12px;
  gap: 8px;
  background: ap-surface-1;
  border-width: 1px;
  border-style: solid;
  border-color: ap-line;
  border-radius: 4px;
}

.ap-panel-title {
  color: ap-text;
  font-size: 13px;
  font-weight: 900;
}
```

Avoid:

```css
.ap-panel .title { color: ap-text; }
.ap-button:hover { border-color: ap-signal; }
```

Hover/focus/animation can exist in an HTML preview stylesheet, but the base
appliance identity must survive without them.

## Token Model

Tokens are flat names so they can be used by the portable Otoe parser. CSS
variable aliases may be generated for HTML previews, but the source model
should remain flat.

### Surfaces

| Token | Value | Use |
| --- | --- | --- |
| `ap-bg` | `#080b0f` | outer stage/window background |
| `ap-canvas` | `#0a0d12` | fixed appliance canvas |
| `ap-surface-1` | `#101923` | default panels, top chrome |
| `ap-surface-2` | `#111a24` | nested panels, card bodies |
| `ap-surface-3` | `#17202b` | raised controls and dialogs |
| `ap-surface-4` | `#182433` | active/selected controls |
| `ap-inset` | `#050a0f` | terminal, log feed, deep wells |
| `ap-inset-soft` | `#0d1720` | metadata wells, secondary data panels |
| `ap-overlay` | `#0b1117` | portable modal backdrop fallback |

The Wraith prototype uses a similar ladder (`surface-0` through `surface-3`).
For Otoe v0, keep the ladder general and name it by appliance behavior rather
than by Wraith brand.

### Text

| Token | Value | Use |
| --- | --- | --- |
| `ap-text` | `#f4f8fb` | primary text |
| `ap-text-2` | `#dbe7f3` | normal body text |
| `ap-text-muted` | `#91a4b7` | supporting copy, row metadata |
| `ap-text-quiet` | `#647384` | labels, disabled metadata |
| `ap-text-inverse` | `#080b0f` | text on bright signal buttons |
| `ap-text-danger` | `#fff3f3` | text inside danger overlays |

### Borders

| Token | Value | Use |
| --- | --- | --- |
| `ap-line-soft` | `#1e2d3d` | internal rows and terminal borders |
| `ap-line` | `#273849` | default hairline panel border |
| `ap-line-strong` | `#39536c` | focused or elevated neutral border |
| `ap-line-focus` | `#e8b44a` | keyboard focus, active route, selected rail |
| `ap-line-danger` | `#f47777` | destructive panels and approval modals |

### State Colors

State color should identify status, not decorate the whole product. Prefer a
small colored label, border, rail, or value over a full saturated panel.

| Token | Value | Use |
| --- | --- | --- |
| `ap-signal` | `#e8b44a` | primary operational accent, active command |
| `ap-signal-soft` | `#2b2414` | portable signal background |
| `ap-info` | `#54c7b8` | telemetry, probe, non-critical live data |
| `ap-info-soft` | `#122b43` | portable info background |
| `ap-success` | `#77e8aa` | ok/pass/ready |
| `ap-success-soft` | `#143328` | portable success background |
| `ap-warn` | `#ffd58c` | warning, approval pending, paused |
| `ap-warn-soft` | `#3a2a12` | portable warning background |
| `ap-danger` | `#f06b72` | abort, critical, denial |
| `ap-danger-soft` | `#3a1419` | portable danger background |
| `ap-neutral` | `#c9d7e5` | neutral status text |
| `ap-neutral-soft` | `#172638` | neutral badge/control background |

### Spacing

Use a 4px base. Dense appliance screens should be compact, but not cramped
around touch targets.

| Token | Value | Use |
| --- | --- | --- |
| `ap-space-0` | `0` | reset |
| `ap-space-1` | `4px` | tight row gaps |
| `ap-space-2` | `8px` | row gaps, badge gutters |
| `ap-space-3` | `12px` | panel padding, compact sections |
| `ap-space-4` | `16px` | standard section padding |
| `ap-space-5` | `20px` | major panel gap |
| `ap-space-6` | `24px` | screen gutter |
| `ap-space-8` | `32px` | large stage gutter |
| `ap-space-10` | `40px` | rare wide appliance spacing |
| `ap-space-12` | `48px` | reserved for fixed chrome or large controls |

### Typography

Portable CSS can reliably express size, weight, and color. Font family is a
visual direction for HTML/native profiles that can support it, not a required
portable contract yet.

| Token | Value | Use |
| --- | --- | --- |
| `ap-font-sans` | `Inter, ui-sans-serif, system-ui, sans-serif` | HTML preview body |
| `ap-font-mono` | `"IBM Plex Mono", "JetBrains Mono", ui-monospace, monospace` | telemetry, IDs, timers |
| `ap-fz-10` | `10px` | dense labels |
| `ap-fz-11` | `11px` | chrome labels, timestamps |
| `ap-fz-12` | `12px` | terminal body, badges |
| `ap-fz-13` | `13px` | default appliance body |
| `ap-fz-14` | `14px` | comfortable body copy |
| `ap-fz-16` | `16px` | section titles |
| `ap-fz-20` | `20px` | panel titles |
| `ap-fz-24` | `24px` | mission title, metric value |
| `ap-fz-32` | `32px` | large metric value |
| `ap-fz-40` | `40px` | timer/readout |

Weights:

| Token | Value | Use |
| --- | --- | --- |
| `ap-fw-regular` | `400` | secondary body copy |
| `ap-fw-medium` | `560` | normal UI labels |
| `ap-fw-semibold` | `650` | section values |
| `ap-fw-bold` | `760` | buttons and row titles |
| `ap-fw-heavy` | `900` | critical labels, primary values |

For v0, do not rely on letter spacing for portability. Use clear text, casing,
weight, and spacing instead.

### Radii

The appliance look should be tighter than the current product preview
defaults.

| Token | Value | Use |
| --- | --- | --- |
| `ap-radius-0` | `0` | chrome seams, table grids |
| `ap-radius-1` | `2px` | hairline controls, status chips |
| `ap-radius-2` | `4px` | default panel/control radius |
| `ap-radius-3` | `6px` | larger touch controls |
| `ap-radius-4` | `8px` | legacy/native-safe fallback and large buttons |
| `ap-radius-pill` | `999px` | status pills only |

### Elevation

Elevation is mostly a border and surface ladder. This keeps the system portable
and appliance-like.

| Token | Value | Use |
| --- | --- | --- |
| `ap-shadow-none` | `none` | default portable surfaces |
| `ap-shadow-overlay` | `0 24px 80px rgba(0,0,0,.42)` | HTML-only dialogs |
| `ap-shadow-raised` | `0 18px 42px rgba(0,0,0,.34)` | HTML-only raised panels |

Portable native renders should not require shadows to understand hierarchy.

### Touch Target Sizes

| Token | Value | Use |
| --- | --- | --- |
| `ap-hit-badge` | `28px` | non-interactive status pills |
| `ap-hit-compact` | `40px` | compact toolbar controls |
| `ap-hit-min` | `44px` | minimum interactive target |
| `ap-hit-default` | `48px` | default ActionButton/Input target |
| `ap-hit-critical` | `52px` | destructive/approval controls |
| `ap-hit-keypad` | `64px` | numeric keypad or gloved input |

Do not make critical actions smaller than `48px` high.

## Component Targets

| Component | Current Status | Current Base | v0 Target |
| --- | --- | --- | --- |
| AppFrame | exists, needs improve | `otoe.ui.AppFrame`, `AppShell`, `VStack`, `HStack` | Appliance frame with fixed/dense canvas, optional left rail, top chrome, content well, and bottom `StatusBar`. Current `AppFrame` is more dashboard-like and uses large radii/gutters. |
| TopBar | exists, needs improve | `otoe.ui.TopBar`, `Toolbar`, custom reference-product topbars | Operational chrome: brand/device, mission/campaign context, runtime badges, clock/hardware state, and command affordances. Should support compact 40-64px heights. |
| StatusBar | missing, composable | `Toolbar`, `HStack`, `Text`, `Badge` | Persistent bottom strip for system state, link, CPU/temp, transport, and latest event tail. Should be first-class for appliance shells. |
| Surface/Card | exists, needs improve | `Card`, `Surface`, `Panel` | Default panel with hairline border, small radius, optional compact header, badge/action slot, and tone border. Current `Surface` inherits product-preview spacing/radius. |
| MetricTile | exists, needs improve | `MetricTile`, `StatCard`, custom `MetaTile` | Dense metric/readout tile for timers, counts, voltage/temp, frame numbers, and mission facts. Needs mono/numeric convention and tighter appliance style. |
| DataPanel | missing, composable | `Surface`, `SectionHeader`, `DataTable`, `ScrollView` | Panel for structured data: facts, device state, queue entries, snapshots. Should standardize header, count badge, empty state, and row density. |
| LogFeed/Terminal | missing, composable | `ScrollView`, `For`, `HStack`, `Text` | First-class terminal/log region with timestamp, level, message columns, filter tabs, and deep inset background. MissionExec already proves the shape with custom rows. |
| EventTimeline | missing, composable | `For`, `HStack`, `Text`, `Badge`, `ScrollView` | Chronological event rows with timestamp, tag, severity, and message. Always visible in MissionExec desktop layout. |
| DangerZone | missing, composable; example exists | `Card`, `ActionButton`, custom `exec-danger-panel` | Dedicated destructive-action panel with red border, clear label, full-width action, secondary recovery/pause action, and confirmation handoff. |
| PreFlightChecklist | missing, composable; example exists | custom `PreflightPanel`, `CheckRow`, `Card` | Reusable readiness gate with check status, label, evidence value, and blocked/warn/pass states. Should be portable to hardware setup screens. |
| ActionButton | exists, needs improve | `otoe.ui.ActionButton`, `Button` | Keep as primary control primitive. Needs appliance variants and states: primary/signal, ghost, neutral, info, success, warn, danger, disabled, armed, full-width, compact/default/critical sizes. |
| Dialog/ApprovalModal | Dialog exists, ApprovalModal missing | `Dialog`, `FocusScope`, `Card`, `ActionButton` | `Dialog` remains the base overlay. Add an ApprovalModal pattern for guarded steps: step ID, summary, detail, approve/deny actions, Escape dismissal, and visible danger semantics. |

## Component Detail

### AppFrame

Target anatomy:

- `TopBar` at the top;
- optional side rail or left state column;
- main work surface with fixed regions where possible;
- optional bottom `StatusBar`;
- no nested decorative cards inside page sections.

MissionExec should use a two-column frame: left state/control column, right live
data column. The terminal should remain the largest region.

### TopBar

The appliance topbar is not a page title block. It is chrome. It should carry:

- product/device name;
- active mode or mission/campaign context;
- operator/runtime state;
- transport/link state;
- clock or elapsed indicator;
- one compact command affordance when needed.

### StatusBar

StatusBar should be added as a target component. It should support three zones:

- left: system health and transport;
- middle: latest event/log tail;
- right: CPU, memory, temperature, battery, or local hardware state.

Until it exists, compose it with `HStack`, `Text`, and `Badge`.

### Surface/Card

Use `Surface` for reusable panels and `Card` for lower-level composition.
Appliance panels should prefer:

- `ap-surface-1` or `ap-surface-2` background;
- `ap-line` border;
- `ap-radius-2` radius;
- `12px` or `16px` padding;
- compact section headers;
- tone through border/value accents, not full saturated fills.

### MetricTile

MetricTile should support:

- label;
- primary value;
- detail/subvalue;
- optional tone;
- fixed minimum height;
- numeric/mono treatment where supported.

Examples: elapsed time, frame count, thermal state, link quality, queue depth,
relay state, voltage, packet count.

### DataPanel

DataPanel is the generic appliance data container. It can hold facts, status
rows, tables, or snapshots. It should standardize:

- section heading;
- count/status badge;
- optional actions;
- scrollable body;
- empty or degraded state.

It can be composed from existing primitives now.

### LogFeed/Terminal

Terminal is a priority for MissionExec. It should define:

- deep inset background;
- timestamp column;
- level column using state colors;
- message column with wrapping;
- filter tabs or action row;
- `ScrollView` support;
- readable 12-13px mono-like text.

Portable v0 should not require scanline backgrounds, animation, or custom
scrollbars.

### EventTimeline

EventTimeline is the compact sibling of Terminal. It should be optimized for
scanning important state transitions:

- timestamp;
- severity/tag;
- message;
- optional source/actor;
- rows at `36px` to `44px` high.

### DangerZone

DangerZone is for real consequences: abort, wipe, unlock, power cycle, deploy,
execute, or deny/abort. It should have:

- visible red/danger border;
- short danger label;
- one primary destructive action;
- secondary recovery or pause action when relevant;
- confirmation or approval handoff for irreversible paths.

DangerZone should never be hidden behind hover-only UI.

### PreFlightChecklist

PreFlightChecklist should make readiness explicit before a mission or hardware
action. It should support:

- pass/warn/block states;
- label and evidence value;
- compact rows;
- count badge such as `5/5 READY`;
- blocked reason display;
- rerun/recover action slot.

This component is useful beyond the reference product: hardware makers can use
it for device readiness, calibration, enclosure safety, network checks, and
firmware gates.

### ActionButton

ActionButton remains the core action primitive. Appliance v0 should standardize
these variants:

- `primary` or `signal`: bright operational command;
- `ghost`: secondary chrome action;
- `neutral`: normal low-risk action;
- `info`: telemetry/simulate/recover action;
- `success`: approve/pass action;
- `warn`: pause/pending action;
- `danger`: abort/deny/destructive action.

Sizes:

- `sm`: compact toolbar, at least `40px`;
- `md`: default, at least `48px`;
- `critical`: destructive/approval, at least `52px`;
- `full_width`: required for emergency controls in narrow columns.

### Dialog/ApprovalModal

`Dialog` exists, but approval is a product pattern. ApprovalModal should compose
`Dialog` and `ActionButton` with:

- title;
- step ID or command ID;
- summary;
- evidence/detail copy;
- approve and deny/abort actions;
- strong focus behavior;
- Escape dismissal where safe;
- danger/success state colors.

MissionExec approval should be the first implementation target.

## MissionExec Priority

MissionExec should become the reference appliance screen for v0. The target
layout is:

- top chrome with product, mission, runtime, elapsed, and status;
- left column: mission brief, mission facts, status/timer, preflight checklist,
  and DangerZone;
- right column: capture/probe DataPanel, Terminal, filters/actions, and
  EventTimeline;
- ApprovalModal layered over the screen when a guarded step waits;
- bottom StatusBar when the AppFrame target exists.

First extraction candidates from `examples/wraith/mission_exec_surface.py`:

1. `PreflightPanel` plus `CheckRow` to `PreFlightChecklist`.
2. `LogLine` plus terminal scroll region to `LogFeed`.
3. `EventRow` plus filter header to `EventTimeline`.
4. `exec-danger-panel` to `DangerZone`.
5. `ApprovalDialog` to `ApprovalModal`.

The immediate visual pass should use appliance tokens and portable class rules
before adding more Python APIs. Once MissionExec looks right and still renders
through HTML, native PNG, plan, and build, extract components.

## Implementation Guidance

For v0 examples:

- define a local appliance token map first;
- keep custom CSS to single class selectors for the portable stylesheet;
- use widget props for `gap`, `padding`, and fixed dimensions when they are part
  of the layout contract;
- use current `otoe.ui` components when they fit, then override with appliance
  classes;
- avoid relying on browser-only CSS for mission-critical readability;
- verify MissionExec in HTML and native output after every visual pass.

Suggested future package shape:

```python
from otoe.ui.appliance import (
    ApplianceFrame,
    ApplianceTopBar,
    StatusBar,
    DataPanel,
    LogFeed,
    EventTimeline,
    DangerZone,
    PreFlightChecklist,
    ApprovalModal,
)
```

This should come after the showcase proves the contracts. For now, the design
system can be implemented through `otoe.ui` primitives and appliance classes.

## Non-Goals For v0

- Full browser CSS parity.
- A generic web dashboard theme.
- A complete component catalog.
- Real private/reference product runtime integration.
- Hover-only critical controls.
- Shadows, gradients, animation, or media queries as required semantics.

## Acceptance Bar

Design System v0 is acceptable when:

- MissionExec feels like a credible product appliance console;
- the visual language is reusable for hardware makers beyond the reference
  product;
- the portable CSS remains inside the Otoe subset;
- critical actions are touch-sized and visibly guarded;
- terminal, timeline, status, and preflight patterns are reusable;
- browser-only polish can be removed without destroying hierarchy or meaning.
