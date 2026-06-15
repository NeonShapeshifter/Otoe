# Layout v1 Plan

Layout v1 is the next native layout step for Otoe appliance UIs. The goal is to
make dense professional consoles possible without turning Otoe into a browser
CSS engine.

MissionExec is the guide surface. It exposes the layout pressure that simple
stacking cannot solve: a fixed state column, a growing live-data column,
toolbars that need to wrap, terminal regions that need stable scroll viewports,
and approval layers that should not become another row in the document.

## Inputs Reviewed

- `examples/wraith/mission_exec_surface.py`
- `preview/wraith.css`
- `src/otoe/_native_layout.py`
- `src/otoe/_native_layout_align.py`
- `docs/native-layout.md`
- `STYLE_GUIDE.md`
- `src/otoe/style.py`
- `src/otoe/plan.py`
- `src/otoe/capabilities.py`
- `src/otoe/style_ir.py`
- `src/otoe/style_ops.py`
- `src/otoe/render_ir.py`
- `src/otoe/render_ir_target.py`
- `src/otoe/render_ir_types.py`
- current native layout, style IR, RenderTree, and MissionExec tests

## MissionExec Findings

MissionExec currently proves the desired product shape, but much of the layout
is browser-only CSS. That is useful as a visual target, not as a portable
layout contract.

Current hacks and limitations:

- `preview/wraith.css` is a rich browser stylesheet, not an Otoe CSS subset
  stylesheet. It uses `:root`, descendant selectors, pseudo-classes, media
  queries, `calc(...)`, `min(...)`, `var(...)`, `position: fixed`, CSS grid,
  flex shorthands, transitions, and `@media`.
- MissionExec has no strict portable stylesheet equivalent to
  `preview/wraith_input_console.css`, so it cannot yet be treated as a native
  layout/build acceptance surface.
- The two-column console depends on browser flex behavior:
  `.exec-left { width: 380px; flex: 0 0 380px; }` and
  `.exec-right { min-width: 0; flex: 1; }`.
- The mission facts and terminal rows depend on CSS grid:
  `.mission-facts { grid-template-columns: repeat(2, minmax(0, 1fr)); }` and
  `.log-line { grid-template-columns: 72px 48px minmax(0, 1fr); }`.
- Filter/action rows depend on wrapping through `.exec-filters { flex-wrap:
  wrap; }`.
- The approval dialog depends on fixed overlay CSS through
  `.ui-dialog-backdrop { position: fixed; inset: 0; ... }`. Native layout
  currently treats the dialog tree as normal stacked content.
- Several rows depend on natural browser shrink behavior with `min-width: 0`.
  Native layout currently measures children first and does not distribute
  available space back into children.
- Some class names are data-driven, such as `is-{line["level"]}` and
  `is-{event["severity"]}`. Portable plan/build needs safelisting or explicit
  enumerable state classes.
- The HTML preview tests validate content and live interactions, but they do
  not validate native layout, RenderTree layout evidence, or offline bundle
  output for MissionExec.

These findings are the reason Layout v1 should start with appliance stack
semantics: bounded sizes, grow/shrink, wrapping, scroll viewports, and a limited
overlay model.

## Current Layout Contract

Native layout v0 is stack-first:

- `VStack` and `HStack` place children sequentially.
- `Panel`, `ScrollView`, `Show`, `For`, `FocusScope`, and `ShortcutScope` are
  native containers.
- `width`, `height`, `min-width`, `min-height`, `max-width`, `max-height`,
  `padding`, `gap`, `align-items`, `justify-content`, and `scrollY` are the
  main geometry inputs.
- Only non-negative pixel dimensions are portable for native layout.
- `align-items: stretch` resizes the child box on the cross axis, but does not
  rerun child layout.
- `ScrollView` clips paint and hit testing, clamps `scrollY`, and offsets
  children, but it does not reflow content into a viewport.

The core implementation is in `src/otoe/_native_layout.py`. It lays out each
child at natural size, computes container content size, applies constraints,
then offsets children for alignment. That order is deterministic and simple,
but it cannot answer "how much space is left for the right column?" before it
has already laid out the right column.

## Style, IR, RenderTree, And Bundle Impact

Any Layout v1 property must flow through the full portable pipeline:

- `src/otoe/style.py` parses class declarations and serializes style values.
- `src/otoe/capabilities.py` declares native support categories.
- `src/otoe/plan.py` classifies values as `portable`, `html-only`,
  `deferred`, or `invalid`.
- `src/otoe/style_ir.py` emits compiled rules and low-level `styleOps`.
- `src/otoe/style_ops.py` replays and validates style operations.
- `src/otoe/render_ir_target.py` records resolved styles in RenderTree nodes.
- `otoe build` and bundle runners validate styleOps, RenderTree, and native
  layout/paint.

RenderTree v0 does not store final geometry. That is acceptable for Layout v1:
new layout properties can appear in each node's resolved `style` without a
RenderTree schema bump, as long as `styleOps` and capability profiles classify
them deterministically. A schema bump is only needed if RenderTree begins
storing layout constraints or computed boxes.

## Non-Goals

Layout v1 must not promise full browser flexbox or CSS grid parity.

Not planned for Layout v1:

- browser cascade/specificity parity;
- `@media` layout behavior in native;
- CSS grid;
- `calc(...)`, arbitrary CSS functions, or CSS variables as native layout
  inputs;
- `auto` and percentage dimensions as general native layout semantics;
- floats;
- baseline alignment;
- browser text shaping and automatic line wrapping parity;
- arbitrary absolute/fixed positioning;
- z-index stacking contexts;
- transform-based layout;
- margin-collapsing or full CSS margin geometry.

These can stay HTML-only or future-engine topics.

## Phase 0: MissionExec Portable Baseline

Purpose: create the real acceptance surface before changing layout semantics.

Work:

- add a strict portable MissionExec stylesheet or portable mode separate from
  `preview/wraith.css`;
- keep it inside single class selectors and portable properties;
- safelist enumerable dynamic classes for log levels, event severity, tab
  active state, status tones, and dialog state;
- render MissionExec through HTML, native PNG, `otoe plan`, `otoe build`, and
  bundle validation;
- document the exact places where the portable version must use explicit sizes
  before Layout v1 features exist.

Implementable now in Python layout:

- explicit pixel widths/heights/min/max;
- fixed left column and fixed terminal viewport;
- stack-based rows using explicit timestamp/level widths;
- `ScrollView` terminal clipping and scroll clamping;
- normal-flow approval panel as an interim native fallback.

Needs bigger engine later:

- responsive breakpoint behavior from `@media`;
- percentage/calc sizing;
- real overlay/fixed positioning.

Not planned:

- carrying browser-only `preview/wraith.css` into native as-is.

## Phase 1: Size Constraints And Direct Geometry

Purpose: tighten the current size model before adding grow/shrink.

Current support already exists for class-based pixel:

- `width`
- `height`
- `minWidth`
- `minHeight`
- `maxWidth`
- `maxHeight`

Work:

- make MissionExec portable CSS use these properties explicitly;
- consider whether direct widget style props should include width/height/min/max
  in addition to `gap`, `padding`, `scrollY`, and `color`;
- keep non-pixel units classified as `deferred`;
- keep negative dimensions invalid;
- document how constraints interact when `min > max`.

Implementable now in Python layout:

- stronger tests around existing `constrain(...)` behavior;
- MissionExec explicit panel and viewport dimensions;
- `AppFrame` or appliance examples that target `1280x800` and `1024x600`;
- plan/styleOps tests for accepted and omitted dimensions.

Needs bigger engine later:

- percentage dimensions;
- `auto` dimensions;
- intrinsic sizing loops between parent and child.

Not planned:

- `calc(...)` for native v1.

## Phase 2: Flex Grow And Shrink

Purpose: support the common appliance pattern "fixed rail, remaining content"
without browser flexbox parity.

Proposed portable properties:

- `flex-grow`: numeric, default `0`;
- `flex-shrink`: numeric, default `1` for normal children, but exact default
  should be chosen deliberately and tested;
- `flex-basis`: pixel size or `0`, no percentages in v1;
- do not support the `flex` shorthand in the portable subset.

Proposed semantics:

- only applies to immediate children of `HStack` and `VStack`;
- only applies on the stack main axis;
- only distributes space when the parent has a definite main-axis size from
  `width`, `height`, or min/max-constrained explicit layout;
- natural child size is measured first;
- remaining positive space is distributed by `flexGrow`;
- negative space is removed by `flexShrink` down to each child's min main size;
- child boxes never become negative;
- cross-axis behavior remains governed by `alignItems`;
- no browser intrinsic min-content/max-content algorithm.

MissionExec target:

- `exec-left` remains `width: 380px; flex-shrink: 0`;
- `exec-right` uses `flex-grow: 1; min-width: 0`;
- probe copy, terminal panel, and event panel can fill the right column without
  hardcoding every nested width.

Implementable now in Python layout:

- add longhand properties to `SUPPORTED_PROPERTIES`;
- add native capability entries as `layout`;
- extend stack layout to distribute available main-axis space;
- update `LayoutBox` sizes deterministically;
- initially support grown containers by resizing their box, then decide whether
  recursive re-layout is required for a useful MissionExec result.

Needs bigger engine later:

- true CSS flex item intrinsic sizing;
- flex-basis `auto`;
- percentage flex-basis;
- text wrapping/reflow caused by assigned width;
- multi-pass layout for every nested dependency.

Not planned:

- `flex` shorthand parity;
- order changes through CSS `order`.

## Phase 3: Wrapping

Purpose: let toolbar actions and filter tabs wrap within a known width.

Proposed portable property:

- `flex-wrap`: `nowrap` or `wrap`;
- only on `HStack` for v1.

Proposed semantics:

- children are placed left to right until the next child would exceed the
  available inner width;
- a new line starts at `x + padding`;
- row height is the max child height in that line;
- `gap` applies both between items and between rows;
- no `row-gap`/`column-gap` split in v1;
- `justify-content` applies inside each line only if straightforward;
- `align-items` applies per line.

MissionExec target:

- terminal filters plus `CLEAR` and `EXPORT` wrap at smaller console widths;
- approval action buttons can wrap without overlapping;
- topbar badges can wrap in compact previews if needed.

Implementable now in Python layout:

- simple row wrapping for `HStack` with definite width;
- deterministic line metrics;
- tests that wrapped rows increase container height.

Needs bigger engine later:

- `wrap-reverse`;
- per-line `align-content`;
- grid-like equal columns;
- responsive breakpoints driven by media queries.

Not planned:

- CSS grid replacement through wrapping.

## Phase 4: Justify And Align Refinements

Purpose: make the existing alignment subset reliable with the new sizing model.

Current native support:

- `align-items`: `start`, `flex-start`, `center`, `end`, `flex-end`, `stretch`;
- `justify-content`: `start`, `flex-start`, `center`, `end`, `flex-end`,
  `space-between`, `space-around`, `space-evenly`.

Work:

- define whether `stretch` only resizes boxes or also triggers child re-layout;
- add `align-self` only if MissionExec needs per-child cross-axis behavior;
- ensure grow/shrink happens before justify offsets;
- ensure wrapping computes line placement before per-line justify offsets.

MissionExec target:

- status/timer row aligns timer to the end;
- probe panel uses `justify-content: space-between`;
- check rows keep label/value alignment without manual fixed widths everywhere.

Implementable now in Python layout:

- reorder internal layout phases for stack containers;
- add tests for grow/shrink combined with `space-between`;
- add tests for `stretch` with fixed cross-axis parent size.

Needs bigger engine later:

- baseline alignment;
- CSS `align-content`;
- automatic text wrapping based on assigned width.

Not planned:

- browser pixel-perfect alignment parity.

## Phase 5: Overflow And Scroll

Purpose: make live data regions stable when content grows.

Current support:

- `ScrollView` has `scrollY`, child offsetting, paint clipping, hit-test
  clipping, and scroll clamping;
- `overflow: hidden`, `text-overflow: ellipsis`, and `white-space: nowrap`
  affect native text paint in a narrow way.

Work:

- keep `ScrollView` as the portable overflow primitive;
- do not treat generic `overflow: auto` as a native scroll container;
- allow `ScrollView` to receive grown height from parent stacks;
- keep max scroll calculations correct after grow/shrink;
- document that generic `overflow` is paint/text clipping, not layout.

MissionExec target:

- terminal consumes remaining right-column height or a stable explicit height;
- event timeline remains visible below terminal;
- long terminal lines clip/ellipsis or remain horizontally readable according
  to the chosen terminal contract;
- filtering lines updates scroll bounds deterministically.

Implementable now in Python layout:

- better tests for scroll clamping after container size changes;
- fixed or grown terminal viewport;
- event timeline viewport if content exceeds its panel.

Needs bigger engine later:

- scrollbars as first-class layout affordances;
- horizontal scroll;
- virtualized terminal rows;
- automatic multiline text wrapping.

Not planned:

- generic browser `overflow: auto` parity.

## Phase 6: Overlay And Fixed Panels

Purpose: support approval dialogs and operator overlays without turning them
into normal stacked rows.

MissionExec needs a guarded approval layer. The current HTML preview uses
`position: fixed`, but native layout has no fixed/absolute model.

Proposed v1 direction:

- add a constrained Otoe overlay primitive or UI pattern rather than supporting
  CSS `position: fixed`;
- overlay children are laid out relative to the root viewport;
- overlay does not contribute to parent stack size;
- initial placement options should be small: `center`, `top`, `bottom`, maybe
  `right`;
- overlay should preserve focus behavior through `FocusScope`;
- hit testing should prefer overlay boxes above normal content.

Implementable now in Python layout:

- a dedicated `Overlay`/`Layer` widget contract, or a native-recognized
  component output shape for `Dialog`;
- centered modal placement with explicit width and natural height;
- layout/painter order that draws overlays after normal content.

Needs bigger engine later:

- arbitrary absolute positioning;
- anchor positioning/popovers;
- nested stacking contexts and z-index;
- viewport resize policies;
- collision avoidance.

Not planned:

- raw CSS `position`, `inset`, and `z-index` semantics in native v1.

## Cross-Cutting Plan

Property additions should be incremental and capability-gated.

For every new layout property:

- add parser support in `src/otoe/style.py`;
- add native capability support in `src/otoe/capabilities.py`;
- add plan validation in `src/otoe/plan.py`;
- emit and replay it through `styleOps`;
- preserve it in RenderTree resolved styles;
- add native layout behavior or classify it as `deferred`;
- update `docs/native-layout.md`, `STYLE_GUIDE.md`, and support matrix tests.

Do not add utility classes as the source of truth. Utilities may expose the new
properties after the core property contract exists.

## Suggested Implementation Order

1. Make MissionExec portable enough for native/plan/build smoke with explicit
   sizes.
2. Add `flex-grow`, `flex-shrink`, and `flex-basis` parser/capability/plan
   support behind strict tests.
3. Implement grow/shrink for definite-size stacks.
4. Update MissionExec to replace hardcoded right-column widths with grow.
5. Add `flex-wrap: wrap` for definite-width `HStack`.
6. Update MissionExec filters and approval actions to use wrapping.
7. Tighten alignment tests with grow/wrap.
8. Improve `ScrollView` tests for grown viewports.
9. Decide whether approval needs a new `Overlay` primitive or a Dialog-specific
   native path.

## Test Plan

MissionExec acceptance tests:

- render static MissionExec HTML from an Otoe target;
- render native MissionExec PNG with the portable stylesheet;
- run `otoe plan` for MissionExec with strict styles and no missing classes;
- run `otoe build --validate` for MissionExec;
- verify bundle runner layout check succeeds;
- assert terminal, event timeline, preflight, danger controls, and approval
  content are visible in native layout boxes;
- assert dynamic severity classes are either statically enumerable or
  safelisted.

Native layout unit tests:

- fixed left column plus growing right column in `HStack`;
- grow distribution among multiple children;
- shrink distribution with `min-width` or `min-height`;
- `flex-basis` pixel value overriding natural main size;
- no grow when parent main-axis size is indefinite;
- `justify-content` after grow/shrink does not double-count space;
- `align-items: stretch` with grown children is deterministic;
- wrapped `HStack` line breaks at known widths;
- wrapped toolbar height increases by expected line height plus `gap`;
- `ScrollView` clamps `scrollY` after height changes;
- overlay/dialog does not increase root stack height once overlay exists.

Style parser and plan tests:

- `flex-grow`, `flex-shrink`, `flex-basis`, and `flex-wrap` parse into canonical
  style keys;
- numeric grow/shrink values are portable;
- negative grow/shrink values are invalid;
- non-px `flex-basis` is deferred;
- unsupported wrap values are invalid;
- new properties appear in backend capability profiles as `layout`;
- ignored/deferred values remain visible in diagnostics.

Style IR/styleOps tests:

- compiled rules include new layout properties;
- omitted declarations are emitted for deferred values;
- styleOps replay applies the new properties;
- styleOps validation detects drift for changed grow/shrink/basis values;
- runtime stylesheet from styleOps produces the same native layout as source
  stylesheet for supported values.

RenderTree tests:

- RenderTree nodes include resolved v1 layout styles;
- RenderTree schema stays at v1 unless computed geometry is added;
- node IDs remain stable when layout props change;
- direct style node IDs still match RenderTree node IDs.

Bundle and backend-candidate tests:

- bundle manifest includes style artifact and RenderTree for a layout-v1
  surface;
- generated bundle runner verifies styleOps and layout check;
- backend capability coverage reports new layout properties;
- path0 RenderTree evidence includes layout phase proof for new properties;
- existing backend candidate contract fixtures are updated only when intended.

Regression tests:

- existing stack layout snapshots remain unchanged when no v1 properties are
  used;
- percent dimensions remain deferred;
- CSS grid remains invalid or HTML-only according to the existing parser
  boundary;
- generic browser `position`, `calc`, and media queries remain unsupported by
  the portable CSS parser.

## Decision Gates

Layout v1 should be considered ready for public documentation when:

- MissionExec passes strict plan/build/native checks through a portable
  stylesheet;
- grow/shrink solves the fixed-left/growing-right appliance layout without
  hardcoded right-column widths;
- wrapping solves filter/tool rows without browser media queries;
- scroll regions remain stable as live data changes;
- any overlay support is explicitly an Otoe primitive or Dialog behavior, not a
  promise of CSS fixed positioning;
- docs and capability profiles make clear that this is flexbox-like stack
  layout, not browser flexbox parity.
