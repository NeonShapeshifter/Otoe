# Concepts

Otoe is built around a small runtime model and several preview/build surfaces.

## Nodes And Widgets

Widgets declare allowed props, events, and optional event signatures. Calling a
widget creates an immutable `Node`; mounting a node validates props and events
against the widget contract.

```python
from otoe import Button, Text, VStack

view = VStack(
    Text("Queue"),
    Button("Run", onClick=lambda: None),
    gap=8,
)
```

Unknown props and events are errors. Event handler arity is checked when the
event fires, using the declared callback shape.

## Components

Components are Python functions returning nodes:

```python
from otoe import component


@component
def Header():
    return Text("Status")
```

Components get owner cleanup and lifecycle support through `on_mount()` and
`on_cleanup()`.

## Reactivity

`signal`, `computed`, and `effect` provide the current reactive core.

- `signal(value)` stores mutable reactive state.
- `computed(fn)` lazily derives state and tracks dependencies.
- `effect(fn)` reruns side effects when dependencies change.

Mutating an already-subscribed signal during component render is guarded
against; move that work to `on_mount()` or an event handler.

## Control Flow

`Show` toggles a branch based on a boolean value. `For` renders a keyed list and
preserves child identity by key when possible.

## Render Paths

Otoe currently has several render and test paths:

- HTML render for static previews.
- Live HTML preview for apps exposing live event dispatch.
- `NativeSurface` for deterministic native layout, paint, input, and PNG tests.
- `NativeWindowDriver` for headless window-shaped input tests.
- `otoe build` for offline bundle artifacts.

Use HTML/live preview for normal app iteration. Use native surfaces and drivers
to test the native contract. Use backend-candidate tooling only when working on
renderer replacement or coverage evidence.

## Style Layer

`css(...)` is a portable Otoe style subset, not full browser CSS. It supports
class-based declarations that can be compiled into a `StyleSheet` and checked
against backend capability profiles. Browser-only polish can exist in HTML
previews, but constrained targets need portable declarations.
