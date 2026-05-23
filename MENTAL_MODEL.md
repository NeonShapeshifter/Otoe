# Otoe Mental Model

Otoe is a Python UI runtime built around small, explicit layers. Component
functions describe a tree. `mount(...)` turns that tree into live fake widgets.
Renderers consume the mounted tree through stable boundaries.

The useful way to think about Otoe is:

```text
component function -> Node tree -> mount -> mounted widgets -> renderer
                                      |
                                      v
                              signals and events
```

It is not a direct React clone, a Tk wrapper, or a virtual DOM. The current goal
is a small Python-native component runtime that can feed multiple renderers.

## Nodes Are Descriptions

Calling a widget or component returns a `Node`. A node is inert data: tag, props,
and children.

```python
from otoe import Button, HStack, Text

tree = HStack(
    Text("Ready"),
    Button("Run", onClick=lambda: None),
    gap=8,
)
```

This does not create a button in an OS window. It only describes what should be
mounted later. Renderers do not consume arbitrary Python UI objects; they consume
the mounted widget tree produced from nodes.

## Components Build Nodes

`@component` wraps a Python function so it can participate in the node tree.
The component function returns another node.

```python
from otoe import Button, Text, VStack, component, signal


@component
def Counter():
    count = signal(0)

    return VStack(
        Text(count),
        Button("Increment", onClick=lambda: count.set(count.value + 1)),
        gap=8,
    )
```

When the component is mounted, Otoe runs the function, captures owner/lifecycle
state, and mounts the returned child tree. The component body is not the event
loop. Put state changes in event handlers, `on_mount(...)`, or effects instead
of mutating subscribed signals during render.

## Mount Creates The Live Tree

`mount(...)` resolves components, `Show`, `For`, reactive props, and widget
event handlers into a `MountedNode` tree backed by fake widgets.

```python
from otoe import mount, snapshot_text

mounted = mount(Counter())
print(snapshot_text(mounted))
```

Mounted widgets are the common shape used by snapshots, HTML rendering, native
layout, paint, hit testing, and native surfaces. This shared mount boundary is
why Otoe can keep the component model independent from the renderer.

## Signals Hold Mutable State

`signal(value)` creates a reactive value. Read `signal.value` when you need the
current value, and call `signal.set(next_value)` to change it.

```python
query = signal("")

Input(
    value=query,
    placeholder="Search",
    onChange=lambda value: query.set(value),
)
```

When a signal is passed as a prop, mount subscribes the widget prop to that
signal. Changing the signal updates the mounted prop. Native surfaces also lazily
refresh layout and paint when subscribed props or control-flow children change.

## Computed Values Derive State

`computed(...)` derives a value from signals and other computed values. It tracks
reads automatically and recomputes lazily when dependencies change.

```python
count = signal(0)
label = computed(lambda: f"Clicked {count.value} times")

Text(label)
```

Use computed values for display text, filtered lists, derived counts, labels,
and other state that should not be stored independently.

## Effects Are Side Work

`effect(...)` tracks reactive reads and reruns when dependencies change. Inside a
component, effects are owned by that component and disposed when the component is
unmounted.

Use effects for side work that belongs to component lifetime. Prefer direct
event handlers or computed values for normal UI state.

## Events Are Explicit

Widget events are named props with fixed signatures. Otoe validates event names
at mount time and validates handler arity when the event fires.

```python
Button("Save", onClick=lambda: save())
Input(value=query, onChange=lambda value: query.set(value))
ScrollView(..., scrollY=scroll_y, onScroll=lambda value: scroll_y.set(value))
```

There is no DOM-style bubbling or capture model today. If a parent needs to know
about a child action, pass an explicit callback or write to shared signal state.

## Control Flow Is Declarative

`Show` and `For` are control nodes resolved during mount.

```python
Show(
    Text("Online"),
    when=is_online,
    fallback=Text("Offline"),
)

For(
    each=items,
    key=lambda item: item["id"],
    children=lambda item: Text(item["name"]),
    fallback=Text("No items"),
)
```

`Show` swaps between children and fallback when its condition changes. `For`
keeps keyed children stable where possible and remounts a child when the item for
that key changes. Both subscribe to reactive values when given signals or
computed values.

## Renderers Consume Mounted Trees

Otoe currently has multiple renderer-facing paths:

- `render_html(...)` turns a mounted tree into static HTML.
- live preview serves HTML and dispatches browser events back to mounted widgets.
- `NativeSurface` owns a mounted tree plus native layout, paint, input, scroll,
  focus, and PNG output.
- `NativeWindowDriver` adds window-shaped input events over a `NativeSurface`.
- `run_native(...)` launches an experimental backend adapter for manual smoke
  testing.

Component code should stay renderer-neutral. Components should not import Tk,
Skia, Taffy, platform APIs, or backend modules. Put backend behavior behind
renderer surfaces and adapters.

## Styling Is Portable But Subsetted

`css(...)` and `StyleSheet` describe style in Otoe terms. HTML and native
renderers support different subsets. The native renderer intentionally rejects
unsupported or unknown native style keys instead of pretending to support them.

Use `NATIVE_RENDERER_SPIKE.md` for the current native style/layout/input matrix.
Use `NATIVE_WORKFLOWS.md` to choose a render path.

## Testing Follows The Same Layers

Pick the smallest test surface that proves the behavior:

- `snapshot(...)` for component tree shape and reactive props.
- `render_html(...)` for HTML adapter output.
- `NativeSurface` for native layout, paint, focus, input, scroll, and PNG.
- `NativeWindowDriver` for backend-facing click, wheel, key, and text events.
- backend-replay acceptance tests for future renderer backend parity.

See `TESTING_GUIDE.md` for concrete examples and boundaries.

## Common Mistakes

- Treating a widget call as an OS widget. It is only a node until mounted.
- Mutating subscribed signals during component render. Use an event,
  `on_mount(...)`, or an effect.
- Expecting event bubbling. Pass callbacks or share signals explicitly.
- Using HTML output to prove native behavior.
- Treating Tk manual windows or PNG marker text as production backend promises.
- Adding app-specific assumptions to the runtime instead of keeping case studies
  as regression pressure.

## Tiny App Flow

For a small app, the usual loop is:

1. Write component functions that return widget nodes.
2. Store local UI state in signals.
3. Derive labels, filters, and counts with computed values.
4. Wire user actions through explicit event handlers.
5. Test structure with snapshots and behavior with the smallest renderer surface.
6. Iterate in `otoe dev`.
7. Use native PNG or `NativeSurface` only when checking the native boundary.

That is the current stable mental model for Otoe after `v0.1.1`.
