# Component Cookbook

This cookbook shows small Otoe patterns that are useful for app code. The goal
is not to demonstrate every widget; it is to show how component functions,
signals, computed values, events, control flow, and render targets fit together.

Naming note: core widgets use JSX-style callback props such as `onClick` and
`onChange`. Higher-level helpers in `otoe.ui` use snake_case for domain
callbacks such as `on_action` and `on_navigate`, except when they intentionally
pass through a core event name.

## Static Render Target

Use a plain component when the surface does not need local state yet. Export a
`Node` as `app` when you want `otoe render MODULE:app ...` to work.

```python
from otoe import Button, Text, VStack, component


@component
def QuickstartSurface():
    return VStack(
        Text("Otoe quickstart", className="eyebrow"),
        Text("A small render target for the Otoe CLI."),
        Button("Primary action", onClick=lambda: None),
        className="quickstart-surface",
        gap=12,
        padding=16,
    )


app = QuickstartSurface()
```

Render it:

```bash
otoe render examples.quickstart:app --out preview.html --pretty
```

## Local Counter State

Use `signal(...)` for mutable UI state and `computed(...)` for labels derived
from that state.

```python
from otoe import Button, HStack, Text, VStack, component, computed, signal


@component
def Counter():
    count = signal(0)
    label = computed(lambda: f"Count: {count.value}")

    return VStack(
        Text(label, className="counter-value"),
        HStack(
            Button("Decrement", onClick=lambda: count.set(count.value - 1)),
            Button("Increment", onClick=lambda: count.set(count.value + 1)),
            gap=8,
        ),
        gap=12,
        padding=16,
    )
```

State created inside a component is per mount. Do not mutate subscribed signals
during component render; mutate them from events, `on_mount(...)`, or effects.

## Controlled Input

Inputs are controlled: pass a value and update it through `onChange`.

```python
from otoe import Input, Text, VStack, component, computed, signal


@component
def SearchBox():
    query = signal("")
    summary = computed(lambda: f"Searching for {query.value or 'everything'}")

    return VStack(
        Input(
            value=query,
            placeholder="Search",
            autoFocus=True,
            onChange=lambda value: query.set(value),
        ),
        Text(summary),
        gap=8,
    )
```

Use the same controlled pattern for native input tests. `NativeSurface` and
`NativeWindowDriver` dispatch into `onChange(...)`; they do not mutate app state
behind Otoe's back.

## Filtered Lists With For

Use `computed(...)` to derive filtered data and `For(...)` to render stable
keyed rows.

```python
from otoe import (
    Button,
    For,
    HStack,
    Input,
    Text,
    VStack,
    component,
    computed,
    signal,
)


TASKS = [
    {"id": "runtime", "title": "Runtime bridge", "owner": "Core"},
    {"id": "input", "title": "Input polish", "owner": "Native"},
    {"id": "docs", "title": "Docs pass", "owner": "DX"},
]


@component
def TaskList():
    query = signal("")
    selected_id = signal(None)
    visible_tasks = computed(
        lambda: [
            task
            for task in TASKS
            if query.value.lower() in " ".join(task.values()).lower()
        ]
    )

    def row(task):
        return HStack(
            Text(task["title"]),
            Text(task["owner"]),
            Button(
                "Inspect",
                onClick=lambda task_id=task["id"]: selected_id.set(task_id),
            ),
            gap=8,
        )

    return VStack(
        Input(
            value=query,
            placeholder="Search tasks",
            onChange=lambda value: query.set(value),
        ),
        For(
            each=visible_tasks,
            key=lambda task: task["id"],
            children=row,
            fallback=Text("No tasks match"),
        ),
        gap=8,
    )
```

The `key` should be stable for each logical item. If an item keeps the same key
but changes data, Otoe remounts that keyed child so visible props update.

## Modern Default Surfaces

Use the modern presets when you want a polished app surface without starting
from app-specific CSS:

```python
from otoe import (
    ActionButton,
    AppFrame,
    ListRow,
    MetricGrid,
    MetricTile,
    SidebarFrame,
    SidebarItem,
    Surface,
    TopBar,
)


screen = AppFrame(
    sidebar=SidebarFrame(
        SidebarItem("Overview", detail="Live", tone="success", active=True),
        brand="Otoe",
        subtitle="Utility Ops",
    ),
    topbar=TopBar(
        "Operations",
        subtitle="No custom CSS",
        status="Ready",
        status_tone="success",
        actions=ActionButton("Sync", size="sm"),
    ),
    content=Surface(
        MetricGrid(MetricTile(label="Velocity", value="31 ms", tone="success")),
        ListRow(title="Utility layer smoke", badge="Ready", tone="success"),
        title="Active jobs",
        badge="Preset",
        badge_tone="info",
    ),
)
```

These presets are inspired by utility-first systems and component libraries:
clear slots, tone variants, soft surfaces, compact rows, and responsive shell
classes. They still render as normal Otoe nodes and can be combined with custom
CSS when a product needs a stronger identity.

## Reference App Helpers

Use the shared UI helpers for repeated professional-app markup instead of
rebuilding section headings, empty states, and feedback toasts in every app.

```python
from otoe import EmptyState, FeedbackToast, SectionHeader, VStack, signal


feedback = signal(None)


def run_action():
    feedback.set(
        {
            "title": "Batch approved",
            "detail": "3 records moved to approved.",
            "tone": "success",
        }
    )


surface = VStack(
    FeedbackToast(feedback),
    SectionHeader(
        "Selected records",
        badge="3 rows",
        badge_tone="warn",
        action_label="Approve",
        on_action=run_action,
    ),
    EmptyState(
        "No records selected",
        description="Choose rows from the queue.",
        action_label="Refresh",
        on_action=run_action,
    ),
)
```

`FeedbackToast` expects a feedback object or dict with `title`, `detail`, and
`tone` fields by default. Providers should put feedback in the snapshot so
static previews, live previews, and tests all see the same operator-visible
state. `SectionHeader` and `EmptyState` can build common action buttons directly
with `action_label`/`on_action`; pass an explicit `actions` or `action` node only
when a custom control group is needed.

## Conditional UI With Show

Use `Show(...)` for modal, empty, and detail states. Keep the state in a signal
and derive display text with computed values when useful.

```python
from otoe import Button, Panel, Show, Text, VStack, component, computed, signal


@component
def Inspector():
    selected = signal(None)
    title = computed(
        lambda: "No task" if selected.value is None else f"Task {selected.value}"
    )

    return VStack(
        Button("Open", onClick=lambda: selected.set("runtime")),
        Show(
            Panel(
                Text(title),
                Button("Close", onClick=lambda: selected.set(None)),
                className="modal",
            ),
            when=computed(lambda: selected.value is not None),
        ),
        gap=8,
    )
```

`Show` mounts the active branch and unmounts inactive branch content. Use
`on_cleanup(...)` or owned effects for resources that must be released when a
branch disappears.

## Parent-Owned State And Child Callbacks

Prefer explicit callbacks over hidden event propagation. Children receive state
and callbacks from the parent.

```python
from otoe import Button, Text, VStack, component, computed, signal


@component
def TaskRow(*, title, selected, on_select):
    label = computed(
        lambda: f"{title} [{'selected' if selected.value == title else 'idle'}]"
    )
    return Button(label, onClick=lambda: on_select(title))


@component
def TaskPicker():
    selected = signal("Runtime")

    return VStack(
        Text(computed(lambda: f"Selected: {selected.value}")),
        TaskRow(title="Runtime", selected=selected, on_select=selected.set),
        TaskRow(title="Docs", selected=selected, on_select=selected.set),
        gap=8,
    )
```

This keeps ownership clear: the parent owns `selected`, and children request a
change through `on_select`.

## Lifecycle Cleanup

Use `on_mount(...)` for work that should start after a component mounts and
`on_cleanup(...)` for work that must stop when it unmounts.

```python
from otoe import Text, component, on_cleanup, on_mount, signal


@component
def RuntimeProbe():
    status = signal("starting")

    def start_probe():
        status.set("ready")

    def stop_probe():
        status.set("stopped")

    on_mount(start_probe)
    on_cleanup(stop_probe)

    return Text(status)
```

Keep lifecycle callbacks small. For repeated side work, prefer a dedicated app
service object and feed its state into Otoe through signals.

## Live Preview App Wrapper

`otoe dev` expects an object with `render_fragment()` and
`dispatch_event(event_id, *args)`. A small wrapper can own app state, mount the
surface once, and use `LiveHtmlRenderer` for browser events.

```python
from otoe import (
    Button,
    LiveHtmlRenderer,
    Text,
    VStack,
    component,
    computed,
    mount,
    signal,
)


@component
def CounterSurface(*, label, on_increment):
    return VStack(
        Text(label),
        Button("Increment", onClick=on_increment),
        gap=8,
    )


class CounterPreview:
    def __init__(self):
        self.renderer = LiveHtmlRenderer()
        self.count = signal(0)
        self.label = computed(lambda: f"Count: {self.count.value}")
        self.app = mount(
            CounterSurface(
                label=self.label,
                on_increment=lambda: self.count.set(self.count.value + 1),
            )
        )

    def render_fragment(self):
        self.renderer.clear()
        return self.renderer.render(self.app, pretty=True, indent=4)

    def dispatch_event(self, event_id, *args):
        self.renderer.dispatch(event_id, *args)
        return self.render_fragment()


def app():
    return CounterPreview()
```

Run it:

```bash
otoe dev examples.live_counter:app --port 8767
```

## Native PNG Smoke

Use `NativeSurface` when you need a deterministic native frame from the same
component tree.

```python
from pathlib import Path

from otoe import NativeSurface


def write_frame():
    surface = NativeSurface(Counter())
    output = Path("preview/native/counter.png")
    surface.render_png(output)
    return output
```

This is a renderer-boundary smoke, not a production screenshot system. For
interactive native tests, use `NativeWindowDriver` instead.

## Checklist For New Components

- Keep component props explicit.
- Store mutable UI state in signals.
- Derive display values with computed values.
- Use callbacks for parent-child communication.
- Use `Show` and `For` instead of manual child mutation.
- Keep component code renderer-neutral.
- Add snapshot tests for structure and renderer tests only when crossing a
  renderer boundary.
