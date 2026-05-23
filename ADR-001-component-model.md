# ADR-001: Component Model, Node Tree, Signals API, Lifecycle, and Events

**Project:** Otoe (working codename)
**Status:** Accepted (Phase 0 / Vision)
**Date:** April 24, 2026
**Author:** Alexander Gagnemyr (Forvara)
**Supersedes:** Partial content of RFC-001 §5.2 (Reactivity)
**Related:** RFC-001 (main document)
**Roadmap:** ROADMAP.md

---

## Context

RFC-001 establishes the vision for a modern component framework for Python desktop UI (working codename TBD). Section 5 of that RFC describes the architecture at a block level — transpiler, reactivity, styling, layout, rendering — but leaves the component model itself underspecified. This ADR closes six foundational decisions needed before Phase 1 implementation can begin:

1. What is a component?
2. What does a component return?
3. How are widgets named and composed?
4. What does the signals API look like?
5. How does the component lifecycle behave?
6. How does the event system work?

These decisions determine the public API of the framework and the implementation surface of the runtime. They cannot be deferred to Phase 1 because every other subsystem (transpiler, layout bridge, renderer) encodes assumptions about them.

The immediate product driver is Wraith: a real Python/Kivy desktop app whose backend and runtime are already useful, but whose UI layer is too expensive to evolve and does not meet the desired visual/product bar. Otoe is a professional framework with Wraith as its flagship case study: Wraith validates the framework under real pressure, while the core API remains general enough to serve other Python desktop apps later.

## Drivers

Two drivers shaped this ADR:

**Primary driver:** Wraith needs a professional UI layer that is easier to build, test, and maintain than Kivy. Otoe should be designed as a framework, not as a one-off Wraith UI rewrite. The framework must feel like writing modern frontend, not like writing legacy desktop.

**Generalization driver:** Python desktop UI has no modern low-level alternative. Tkinter (1991), Qt (1995), and Kivy (2011) all predate the component era and the utility-CSS era. If Otoe solves Wraith cleanly without Wraith-specific shortcuts, it can grow into a broader Python desktop framework.

**Secondary driver (AI-native):** LLMs produce JSX + Tailwind fluently. A framework whose input shape matches that output shape benefits from the training-data asymmetry. This is a consequence of modernizing, not the reason to modernize — if the AI-native thesis weakens, the framework is still valuable.

These drivers together rule out any component model that feels 15–30 years old, and rule in models that match current frontend practice (React, Solid, Svelte, Vue 3).

---

## Decision 1 — Component Model: Function + Fine-Grained Signals

**A component is a function decorated with `@component` that returns a tree of Node objects. State is managed via signals created inside the component body. Dependencies are tracked automatically; when a signal updates, only the widget properties that read it are updated.**

The component function executes once on mount and never again. Updates flow through signal subscriptions, not through re-execution of the component. Lifecycle is handled via `on_mount()` and `on_cleanup()` as functions called inside the component body, not as class methods.

### Alternatives considered

**Model B — Class with lifecycle methods (React classes, PyQt, Flutter StatefulWidget).** Rejected. Verbose, requires explicit lifecycle methods, and modern frontend has moved away from this model. LLMs still write it correctly but it signals "old-style framework" to the target audience.

**Model C — Function + hooks with positional identity (React post-16.8).** Rejected despite matching modern React most closely. Implementation cost in Python is prohibitively high: requires a global dispatcher, per-component slot memory, static verification of hook rules (no conditionals, stable order), and coordination with the GIL for async updates. Building this correctly is a multi-month project by itself and blocks every other subsystem. The user-visible difference between Model A-with-signals and Model C for a developer coming from React is familiarity, not capability. Solid.js demonstrates that signals are a viable and arguably superior alternative.

**Model A — Function returning a tree, signals external (chosen).** Implementation fits in 1–2 weeks. Matches Solid.js, which is a credible reference point for "modern frontend framework." Signals give fine-grained reactivity without the infrastructure cost of hooks.

### Consequences

- Component functions run exactly once. Any code that must re-run when state changes must be placed inside an `effect()` or a reactive prop.
- State declared at the top of a component (via `signal()`) persists for the lifetime of the component instance. There is no concept of "props vs state" re-execution boundary as in React.
- Developers coming from React hooks need a short orientation ("the function body runs once; reactivity happens through signals") but the mental model is simpler once adopted.

---

## Decision 2 — Node Tree: Reactive Nodes with Widget-Schema Prop Classification

**A component returns a tree of `Node` objects. Each Node has a `tag` (the widget class to instantiate), a `props` dict, and a `children` list. Each widget declares which prop names are data props and which prop names are events. At mount time, the framework classifies each entry by the widget schema first, then applies reactivity rules only to data props.**

There is no virtual DOM and no reconciliation. Each reactive prop binds directly to the underlying widget property for the lifetime of the node.

### Alternatives considered

**Option 1 — Component returns real widget instances (Kivy, Qt style).** Rejected. Couples widget construction to reactive bindings awkwardly and makes widgets aware of signals, violating separation of concerns.

**Option 2 — Virtual DOM with descriptors (React style).** Rejected. Contradicts the RFC's "signals, not vDOM" position. Adds reconciliation complexity without benefit when fine-grained reactivity is already available.

**Option 3 — Reactive nodes with stable identity (Solid style, chosen).** The component returns lightweight Node descriptors. On mount, the framework translates the tree to real widgets once and wires reactive props to widget properties directly. No diffing, no re-rendering of subtrees — only property updates.

### Reactivity detection rule

Within Option 3, three sub-approaches exist for signaling "this data prop is reactive":

- **3a — Manual computed wrapping:** `Text(computed(lambda: f"Hello {name.value}"))`. Explicit, works without any magic, but verbose.
- **3b — Transpiler auto-wraps expressions:** `Text(f"Hello {name.value}")` becomes reactive automatically. Depends on the transpiler (Path A, deferred to Phase 2).
- **3c — Widget-schema + reactive-value detection (chosen):** Passing a Signal or Computed as a data prop makes it reactive. Passing `signal.value` makes it static. Raw callables are not reactive by default.

```python
Text(name)                                # reactive — Signal instance passed
Text(name.value)                          # static — value passed
Text(computed(lambda: f"Hello {name.value}"))  # reactive — Computed instance passed
Button("Save", onClick=save)              # event handler — callable is not a reactive prop
```

3c is the Phase 1 baseline because it requires no transpiler and is explicit about reactivity. 3a remains available as an escape hatch for derived expressions. 3b becomes a DX sugar on top once the transpiler lands in Phase 2.

### Prop and event classification

Each widget exposes a small schema:

```python
class Button:
    props = {"label", "className", "disabled"}
    events = {"onClick", "onFocus", "onBlur"}
```

Classification order is mandatory:

1. If the name is in `events`, register it as an event handler. Event values are never treated as reactive data props.
2. If the name is in `props`, assign it as a data prop. Signal and Computed values subscribe reactively; all other values are assigned once.
3. If the name is unknown, raise a developer-facing error instead of silently accepting it.

This keeps `onClick=handler`, `onChange=query.set`, and other callables from colliding with reactive expression handling. It also leaves room for legitimate callable data props (for example, formatter functions) because raw callables are static data unless the widget's documented contract says otherwise.

### Internal representation

```python
class Node:
    tag: type           # widget class (VStack, Text, Button, ...)
    props: dict[str, Any]   # values may be static, Signal, Computed, or event handlers
    children: list[Node]
```

Mounting algorithm:

1. Instantiate the widget corresponding to `tag`.
2. For each `prop`:
   - If the prop name is declared as an event: register the value through the event dispatcher.
   - If the prop name is declared as a data prop and the value is a `Signal` or `Computed`: subscribe and update the widget property on each emission.
   - If the prop name is declared as a data prop and the value is anything else: assign the value to the widget property once.
   - If the prop name is unknown: raise an error.
3. Recursively mount each child.

### Consequences

- No virtual DOM implementation needed in Phase 1.
- Reconciliation is not a concept in the framework — subtrees are never compared.
- Dynamic children lists (rendering a list of items whose length changes) require an explicit primitive (`For` or similar) to be defined in Phase 1 because naive Python list comprehensions inside a component body would execute only once.
- Widgets need explicit prop and event schemas from the beginning. This is extra upfront work, but it prevents typo-driven bugs and avoids ambiguous callable behavior.

---

## Decision 3 — Widget Naming and Composition: CamelCase Classes, Hybrid Args

**Widgets are classes named in CamelCase (`VStack`, `Text`, `Button`, `Input`). Their constructor accepts `*args` for children/primary content and `**kwargs` for props. In plain Python, positional children must appear before prop kwargs. This matches JSX mental models as closely as Python call syntax allows.**

### Example

```python
VStack(
    Text("Hello"),
    Button("Click", onClick=handler),
    className="p-4 gap-2",
)
```

### Alternatives considered

**Lowercase factory functions (`vstack(text("hello"))`).** Rejected despite PEP 8 alignment. The target audience comes from React, Vue, and Solid, where CamelCase component names are universal. Matching that convention outweighs the minor PEP 8 deviation, which PEP 8 itself permits for this kind of case (a component is closer to a class than a function).

**Explicit `children=[]` kwarg.** Rejected as primary syntax. Too verbose for nested trees. The hybrid form reads closer to JSX and Python's argument model supports it natively without ambiguity.

### Consequences

- Widget classes must provide a constructor/factory path that normalizes `args` into `children: list[Node]` and `kwargs` into `props: dict`. The prototype may implement this through `__new__` returning `Node` descriptors; the public contract is the call syntax, not the internal hook.
- Tooling (type checkers, IDEs) will not autocomplete children positional args, but will autocomplete props kwargs. This is an acceptable trade-off because children types are constrained (they must be Nodes) and common.
- A small set of widgets that accept primary content (e.g., `Text("Hello")`, `Button("Click")`) declare a `primary_prop` in their widget schema. The first positional argument maps to that prop before mount-time classification. Container widgets treat all positionals as children.
- Plain Python syntax requires positional children before kwargs (`VStack(Text(...), className="...")`). A future transpiler may support JSX-like prop-first syntax as source sugar, but the Phase 1 Python API uses valid Python ordering.

Example:

```python
class Text:
    primary_prop = "content"
    props = {"content", "className"}
    events = set()

class Button:
    primary_prop = "label"
    props = {"label", "className", "disabled"}
    events = {"onClick"}
```

---

## Decision 4 — Signals API: `signal`, `computed`, `effect`

**Three primitives form the reactive core. `signal(initial)` creates writable reactive state. `computed(fn)` creates a derived read-only value that memoizes based on its dependencies. `effect(fn)` runs a side-effectful function immediately and re-runs it whenever any signal it reads changes.**

### Reading and writing

```python
count = signal(0)
print(count.value)       # read
count.value = 1          # write (direct assignment)
count.set(1)             # write (method form, usable inside lambdas)
```

Reading is done via the `.value` property. Writing is done either by assignment (`count.value = 1`) or by `set()` (`count.set(1)`). Both forms exist because Python lambdas do not accept assignment statements — without `.set()`, every writer inside an `onClick` handler would have to be a named function.

### Derived values

```python
first = signal("Ale")
last = signal("Gagnemyr")

full = computed(lambda: f"{first.value} {last.value}")
print(full.value)   # "Ale Gagnemyr"
```

`computed` tracks its dependencies automatically by observing which signals are read during its function. The result is memoized until any dependency changes.

### Side effects

```python
theme = signal("dark")

def persist():
    save_to_disk(theme.value)

effect(persist)
```

`effect` runs its function once immediately and again whenever any signal read during its last execution changes. It is the primitive for I/O, logging, DOM-adjacent updates, and anything that must react to state changes but does not return a value for rendering.

### Lifecycle

```python
@component
def Counter():
    count = signal(0)

    on_mount(lambda: print("mounted"))
    on_cleanup(lambda: print("unmounted"))

    return Button(label="+", onClick=lambda: count.set(count.value + 1))
```

`on_mount` and `on_cleanup` register callbacks for the component's lifecycle. They are functions called during the component function's execution, not decorators or methods.

### Alternatives considered

**Solid-style call syntax (`count()` to read, `setCount(v)` to write).** Rejected. Function-call-to-read-an-int is unusual in Python and breaks developer intuition about what parentheses mean. The property form (`count.value`) is more idiomatic without losing any capability.

**Vue-style `ref` + `watch` with explicit dependency declarations.** Rejected for Phase 1. Automatic dependency tracking is simpler to use and matches the Solid reference implementation. An explicit `watch(signal, callback)` can be added in Phase 2 as a convenience for cases where explicit dependency lists are preferred.

### Consequences

- The reactive runtime must implement a dependency-tracking context (a stack or context-variable) that tracks which signals are read during the execution of a `computed` or `effect`.
- `computed` values must be lazy and memoized — they should not re-execute unless a dependency has actually changed.
- Cleanup semantics for `effect` (what happens when an effect runs a second time) must be defined: the old subscription is disposed before the new one is established. This is standard Solid/SolidJS behavior and should be replicated.

---

## Decision 5 — Component Lifecycle: Bottom-Up Mount, Auto-Cleanup, No Update Hook

**Components have two lifecycle hooks: `on_mount(callback)` runs after the component and all its children have mounted and rendered for the first time. `on_cleanup(callback)` runs before the component is destroyed, after all its children have already been cleaned up. There is no `on_update` hook — reactivity to state changes is expressed exclusively through `effect()`.**

### Mount timing

`on_mount` runs **after** the first render, not before. The widget is in the layout tree, has computed geometry, and has been painted. This matches Solid's `onMount` and React's `useEffect` (not `useLayoutEffect`).

### Mount and unmount order

Lifecycle traverses the tree **bottom-up**: children mount before their parent's `on_mount` runs, and children unmount before their parent's `on_cleanup` runs. When a parent's `on_mount` fires, all descendants are guaranteed to be live. This matches React, Vue, and Solid conventions and means that parent components can safely reference child state at mount time.

### Automatic disposal of effects and computeds

Effects and computeds created inside a component's body are owned by that component. When the component unmounts, all owned reactives are disposed automatically — their subscriptions are removed and their cleanup functions (if any) are invoked. The developer never has to manually dispose effects.

Implementation: when `@component` executes the function, it establishes an "owner context" (a context variable). Any `effect()` or `computed()` created while that context is active registers itself with the owner. On unmount, the owner walks its registered reactives and disposes them.

This is Solid's owner model. It is the difference between a framework that feels effortless and one that leaks subscriptions.

### No update lifecycle

There is no `on_update` hook. In Model A, the component function executes exactly once — there are no re-renders to hook into. Code that should run when state changes goes inside an `effect()`. This keeps the API surface minimal and makes the data flow obvious: state changes propagate through signals, period.

### Full lifecycle order

For a component being mounted:

1. Component function executes, returning a Node tree.
2. Framework instantiates widgets recursively for the tree.
3. Signal subscriptions are created for every reactive prop.
4. Children complete their full mount sequence (recursively).
5. The component's `effect()` callbacks run for the first time.
6. The component's `on_mount` callbacks run.

For the same component being unmounted:

7. Unmount is triggered (parent destruction, conditional render, etc.).
8. Children complete their full unmount sequence (recursively).
9. The component's `on_cleanup` callbacks run.
10. All effects and computeds owned by the component are disposed.
11. The widget is removed from the layout tree.

### Alternatives considered

**Mount before first render (`useLayoutEffect`-style as default).** Rejected. The 95% case is "do something after the user can see the component" — focus an input, start an animation, fetch data that does not need to block the paint. Pre-render mount is occasionally needed (measuring geometry to avoid layout shift) but rare enough to defer to a Phase 2 `on_layout` primitive.

**Top-down mount order (parent first).** Rejected. Universal convention across React, Vue, and Solid is bottom-up because it ensures children are live when the parent runs its mount logic. Inverting this would surprise every developer coming from frontend.

**Manual effect disposal.** Rejected. Forgetting to dispose effects is the #1 source of memory leaks in reactive frameworks. Automatic ownership is non-negotiable for a framework that wants to feel modern.

**`on_update` hook.** Rejected. Redundant with `effect()`. Adding it would introduce two ways to react to state changes, which violates "one obvious way to do it."

### Consequences

- The framework runtime must implement context-variable-based owner tracking for effects and computeds.
- `effect()` callbacks may optionally return a cleanup function that runs before the next execution and on disposal — standard Solid behavior.
- Conditional rendering primitives (`Show`, `For`) must integrate with the owner system so that components inside them are correctly disposed when the condition flips or list items are removed. This is a Phase 1 implementation concern, not an API concern.
- The lack of an `on_update` hook is a documentation challenge: developers from React class-based backgrounds will look for it. The migration guide must explain why `effect()` covers the case.

---

## Decision 6 — Event System: Per-Widget Signatures, camelCase, No Bubbling, Async-Aware

**Each widget declares its event names and documents the exact signature each event handler receives. There is no generic Event object passed to all handlers. Event handler kwargs use camelCase (`onClick`, `onChange`, `onKeyDown`) for consistency with the rest of the API. Events do not bubble — they are consumed by the widget where they originate. Handlers may be sync or async; the framework detects coroutine functions and coroutine return values and schedules them on the event loop automatically.**

### Handler signatures

Each widget defines what its handlers receive. There is no generic `Event` object. Examples:

```python
Button(onClick=lambda: ...)                       # no args
Input(onChange=lambda value: ...)                 # (value: str)
Input(onKeyDown=lambda key, mods: ...)            # (key: str, mods: set[str])
Slider(onChange=lambda value: ...)                # (value: float)
Window(onResize=lambda width, height: ...)        # (width: int, height: int)
```

The event name and signature are part of the widget's documented contract.
Type stubs and docs describe them, and the runtime raises
`EventHandlerArityError` when a handler cannot accept the delivered event
arguments.

Event handlers are classified before data-prop reactivity. A callable assigned to a declared event name is always a handler, never a reactive expression:

```python
Button(onClick=save)                 # handler
Input(onChange=query.set)            # handler
Text(computed(lambda: query.value))   # reactive text
```

Unknown `on*` names should raise an error just like any other unknown prop. This catches typos such as `onCLick` immediately instead of creating inert props.

### Naming convention

All event handlers are camelCase: `onClick`, `onChange`, `onKeyDown`, `onMouseEnter`, `onFocus`. This matches the prop naming established by Decision 3 (`className`, `placeholder`) and by JSX/React convention. Mixing camelCase props with snake_case events would be inconsistent.

### No event bubbling

When a Button inside a VStack is clicked, only the Button's `onClick` handler fires. The VStack's `onClick` (if any) does not. Each widget consumes its own events.

This intentionally diverges from web/DOM conventions. Desktop UI does not have the same need for delegation that the web does (which evolved bubbling primarily for performance with large numbers of similar elements). The patterns where bubbling is genuinely useful — "click outside to close," global keyboard shortcuts — are better expressed as dedicated primitives (`ClickOutside` widget, global key bindings) than as an implicit bubbling system.

If real-world usage during Phase 1 reveals friction, bubbling can be added in Phase 2 without breaking existing handlers.

### Async handlers

Handlers may be sync or async. The framework detects both cases:

```python
async def search():
    data = await api.search(query.value)
    results.set(data)

Button(onClick=search)                              # async function, scheduled on event loop
Button(onClick=lambda: search())                    # sync function returning a coroutine, also scheduled
Button(onClick=lambda: count.set(count.value + 1))  # plain sync, runs inline
```

Detection logic:

1. If `inspect.iscoroutinefunction(handler)` is true → schedule on event loop.
2. Otherwise call the handler synchronously, then check if the return value is a coroutine via `asyncio.iscoroutine(result)` → if yes, schedule on event loop.
3. Otherwise discard the return value.

The two-step check handles the case where a handler is sync but accidentally returns a coroutine (e.g., `lambda: search() if key == "Enter" else None` where `search()` is async). Without the second check, the coroutine would silently never run and produce a runtime warning at GC time.

### Alternatives considered

**Generic Event object passed to every handler.** Rejected. Most handlers (90%+) do not need event metadata. Forcing every handler to declare an unused `e` parameter is friction. The cases that do need metadata (key codes, mouse coordinates) are better served by widget-specific signatures.

**Signature inspection (Option C in the design discussion).** Rejected. `inspect.signature()` magic produces flexible but unpredictable behavior, confusing error messages, and runtime overhead. With widget-specific args (`value`, `key`, `mods`), inspection-based dispatch becomes a complex matching system rather than the simple "pass event or not" pattern that makes it appealing in single-arg-event frameworks.

**snake_case event names (`on_click`, `on_change`).** Rejected. Decision 3 established camelCase for props (`className`). Mixing conventions within the same call site is worse than full camelCase consistency.

**Bubbling with stopPropagation.** Rejected for Phase 1. Requires a mutable Event object that travels the tree, contradicting the no-Event-object decision above. The use cases that justify bubbling on the web are weaker on desktop and have cleaner alternatives.

**Sync-only handlers.** Rejected. Async-first is the 2026 default for Python. Manual `asyncio.create_task` wrapping is friction the framework should eliminate.

### Consequences

- Every widget class must document its event handler signatures explicitly. The widget catalog needs a consistent format for this.
- Every widget class must declare its data props and event names explicitly so mount-time classification is deterministic.
- The framework runtime needs a small dispatcher that handles the sync/async detection and event-loop scheduling.
- Type stubs become important: a developer writing `onChange=lambda value: ...` should get autocompletion and type checking for `value`. This requires careful typing of the widget classes.
- Documentation must explain why there is no generic `Event` object for developers coming from React, where `SyntheticEvent` is universal.
- The "no bubbling" decision must be visible in the docs. Developers will assume bubbling by default; the docs need to address this directly and provide alternative patterns for common cases.

---

## Full Example

Consolidating all six decisions:

```python
from pyx import component, signal, computed, effect, on_mount, on_cleanup
from pyx.ui import VStack, HStack, Text, Button, Input

@component
def ScanPanel(title: str, on_launch):
    query = signal("")
    launches = signal(0)

    status = computed(
        lambda: f"{launches.value} scans launched"
    )

    def log_changes():
        print(f"query changed to: {query.value}")
    effect(log_changes)

    on_mount(lambda: print("ScanPanel mounted"))

    async def handle_launch():
        await on_launch(query.value)
        launches.set(launches.value + 1)

    return VStack(
        Text(title, className="text-2xl font-bold text-emerald-400"),
        Input(
            className="bg-slate-800 text-white px-3 py-2 rounded",
            placeholder="Target CIDR...",
            value=query,
            onChange=query.set
        ),
        Text(status, className="text-sm text-slate-400"),
        HStack(
            Button(
                label="Launch Scan",
                className="bg-red-600 hover:bg-red-700 px-4 py-2 rounded",
                onClick=handle_launch
            ),
            className="gap-2 justify-end",
        ),
        className="p-6 gap-4 bg-slate-900 rounded-lg",
    )
```

Notes on what this example exercises:

- **Decision 1:** Component is a function returning a tree; runs once on mount.
- **Decision 2:** Reactive props by type — `value=query` passes the signal directly; `Text(status, ...)` passes a computed.
- **Decision 3:** CamelCase widgets, hybrid args/kwargs (children positional, props as kwargs).
- **Decision 4:** `signal`, `computed`, `effect` all in use.
- **Decision 5:** `on_mount` registered; effect will be auto-disposed when component unmounts.
- **Decision 6:** `onChange`, `onClick` in camelCase; `handle_launch` is async and the framework schedules it.

This example is the reference surface against which Phase 1 must be built.

---

## Open Questions Deferred

These were identified during the session but not resolved. They are tracked here as inputs to later ADRs:

1. **Transpiler: import hook vs build step** (RFC §10). Affects DX but not runtime correctness. Decide before Path A ships.
2. **Threading and ownership model across Python ↔ Taffy (Rust) ↔ Skia (C++).** Highest technical risk in the project. Needs a dedicated research ADR before Phase 1 begins.
3. **Dynamic children primitives (`For`, `Show`, keyed reconciliation for lists).** Decision 2 noted this needs a Phase 1 primitive but did not specify its API. Separate ADR needed.
4. **Batch updates and scheduling.** If multiple signals update in the same tick, should effects run once or per-update? Solid batches by default; decide before Phase 1 API freezes.
5. **Public name of the framework.** Internal codename is "Otoe" (a Panamanian tuber — low-level, foundational, grows from below). Public name decision deferred until Phase 1 is visually demoable. Codename may or may not become the public name depending on how it feels after building against it for several months.

---

## Status and Next Actions

This ADR is accepted as of the date above and will be treated as the authoritative reference for the component model, node tree shape, widget composition, and signals API for Phase 1.

Immediate next steps are tracked in `ROADMAP.md`. The current critical path is:

- Choose the explicit Otoe time budget and whether it is a side lane or a deliberate priority shift from Wraith feature work.
- Write ADR-002 for `Show`, `For`, keyed identity, and disposal semantics.
- Write ADR-003 for batching, scheduling, timers, and async UI ownership.
- Implement the first isolated runtime slice: `Node`, widget schema (`props`, `events`, `primary_prop`), `Signal`, `Computed`, `Effect`, and fake-widget mount. No production Wraith integration yet — just the reactive core and prop/event classification.
- Write Wraith-shaped components in this syntax to stress-test the ergonomics before any renderer commitment.
- Open a tracking issue for each deferred open question above.

Otoe can start now. Wraith already proves the product domain; the integration gate is not a future Wraith version, it is whether an isolated Otoe surface can match Wraith behavior while being easier to build, test, and maintain.
