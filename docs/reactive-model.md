# Reactive Model

Otoe's reactive model is explicit: signals hold mutable state, computed values
derive state, effects run side effects, and widgets receive reactive values as
props when you want future updates to flow through the mounted tree.

## Signals

`signal(value)` creates mutable reactive state. Read with `.value` and update
with `.set(...)`.

```python
from otoe import Text, VStack, signal

count = signal(0)
app = VStack(Text(count))
```

Passing the signal itself to `Text(...)` keeps the prop reactive. When `count`
changes, the mounted text can observe the new value.

## Computed Values

`computed(fn)` derives a value from signals or other computed values. It tracks
the dependencies read while `fn` runs.

```python
from otoe import Text, computed, signal

count = signal(0)
label = computed(lambda: f"Count: {count.value}")
node = Text(label)
```

Use `computed` when the widget needs formatted text, branching values, or
derived props that should update later.

## Effects

`effect(fn)` runs `fn` once, tracks the signals it reads, and reruns when those
dependencies change.

```python
from otoe import effect, signal

status = signal("idle")


def log_status():
    print(f"status={status.value}")


status_effect = effect(log_status)
status_effect.dispose()
```

If an effect creates a subscription, timer, or external handle, return a cleanup
callable from the effect body or dispose the effect when it is no longer needed.

## Batching

`batch(...)` groups multiple signal writes so dependents see one coherent update
at the end of the batch.

```python
from otoe import batch, signal

first = signal("Ada")
last = signal("Lovelace")

with batch():
    first.set("Grace")
    last.set("Hopper")
```

Use batching when one user action updates several related signals.

## Reactive Props

Widget props can receive plain values, signals, or computed values. Passing a
reactive object preserves the relationship:

```python
from otoe import Button, Text, VStack, computed, signal

count = signal(0)
label = computed(lambda: f"Count: {count.value}")

app = VStack(
    Text(label),
    Button("Increment", onClick=lambda: count.set(count.value + 1)),
)
```

This is the preferred pattern for text, disabled state, classes, and other props
that should update after mount.

## Show And For

`Show` renders a branch when its condition is true:

```python
from otoe import Show, Text, signal

is_online = signal(True)
node = Show(Text("Online"), when=is_online)
```

`For` renders a keyed list and preserves child identity by key when possible:

```python
from otoe import For, Text, signal

items = signal([
    {"id": "a", "label": "Alpha"},
    {"id": "b", "label": "Beta"},
])

node = For(
    each=items,
    key=lambda item: item["id"],
    children=lambda item: Text(item["label"]),
)
```

Prefer stable keys from your domain model over list indexes.

## Reading .value During Render

Reading `.value` inside component render gives you the current Python value at
that moment. If you put that value into a string, the string is ordinary static
data:

```python
Text(f"Count: {count.value}")
```

That pattern does not create a future reactive relationship for the formatted
string. Use a computed value instead:

```python
Text(computed(lambda: f"Count: {count.value}"))
```

Reading `.value` during render is fine when you intentionally need a one-time
decision or when the control-flow helper tracks it for you. Do not assume every
Python expression that mentions `.value` remains reactive after it becomes a
plain string, number, list, or dict.

## Lifecycle And Mutation Rules

Components render synchronously. Mutating an already-subscribed signal during
render can raise a `ReactiveMutationError` because it creates ambiguous update
ordering. Move mutations to one of these places:

- event handlers such as `onClick`
- `on_mount(...)`
- controlled effects
- explicit setup code before mounting

Use `on_cleanup(...)` or effect cleanup for timers, subscriptions, files, and
other external resources.

## Runtime Thread

Reactive subscribers run synchronously on the thread where they were created.
Do not mutate subscribed signals directly from hardware, network, or worker
threads. Queue the result and drain it from the UI/runtime thread:

```python
from otoe.scheduler import drain_posted, post

# Worker thread:
post(lambda: status.set("ready"))

# UI/runtime thread or custom backend event loop:
drain_posted()
```

The built-in Tk window polls this queue, and the development HTTP server drains
it before rendering or dispatching an event. Custom backends must call
`drain_posted()` from their event loop. A direct cross-thread update raises
`ReactiveThreadError` before changing the signal. Catch it from the normal
app-author surface with `from otoe import ReactiveThreadError`.

## Recommended Patterns

- Pass signals or computed values directly when a prop should keep updating.
- Use `computed` for formatted labels and derived booleans.
- Keep event handlers small and mutate signals from user actions.
- Use `For` with stable keys for lists.
- Use `Show` for conditional branches instead of constructing placeholder
  children manually.
- Use batching when one action updates several related signals.

## Common Mistakes

- Building static strings with `Text(f"...{signal.value}...")` and expecting
  future updates.
- Mutating subscribed signals while a component is rendering.
- Using list indexes as keys for mutable lists.
- Creating effects without cleanup when they own external resources.
- Hiding state changes in helper functions that run during render.
