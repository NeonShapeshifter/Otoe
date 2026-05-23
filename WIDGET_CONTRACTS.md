# Widget Contracts

Otoe widgets have explicit contracts. A widget declares the props and events it
accepts, and `mount(...)` rejects unknown props or event names. Components in
`otoe.ui` are Python wrappers that expand into those core widgets.

The package includes a `py.typed` marker plus initial core widget/control-flow
stubs so editors and type checkers can catch common wrong prop names and event
handler shapes.

## Contract Rules

- A widget call returns a `Node`; it does not create an OS widget.
- Data props are declared by the widget.
- Event props are declared separately and must be callable.
- Some widgets have a `primary_prop`, so positional text becomes a named prop.
- Children must be `Node` instances.
- Reactive values can be passed as data props; mount subscribes the mounted prop
  to the reactive value.
- Event handler arity is checked when the event fires.
- Unknown `on...` names are reported as unknown events; other unknown names are
  reported as unknown props.

## Core Widgets

These are the low-level widgets in `otoe.widgets`.

| Widget | Primary Prop | Data Props | Events |
| --- | --- | --- | --- |
| `VStack` | none | `className`, `gap`, `padding`, `id` | none |
| `HStack` | none | `className`, `gap`, `padding`, `id` | none |
| `Text` | `content` | `content`, `className`, `color`, `id` | none |
| `Button` | `label` | `label`, `className`, `disabled`, `id` | `onClick()`, `onKeyDown(key)`, `onFocus()`, `onBlur()` |
| `Input` | none | `value`, `placeholder`, `className`, `disabled`, `autoFocus`, `id` | `onChange(value)`, `onKeyDown(key)`, `onFocus()`, `onBlur()` |
| `ScrollView` | none | `className`, `id`, `scrollY` | `onScroll(next_scroll_y)` |
| `Panel` | none | `className`, `title`, `id` | none |
| `ShortcutScope` | none | `className`, `id` | `onGlobalKeyDown(event)` |
| `FocusScope` | none | `className`, `trapFocus`, `restoreFocus`, `id` | none |

### Primary Props

`Text("Hello")` is equivalent to `Text(content="Hello")`.
`Button("Save")` is equivalent to `Button(label="Save")`.

Passing both positional primary content and the explicit prop is an error:

```python
Button("Save", label="Duplicate")  # DuplicatePrimaryPropError
```

### Event Shapes

Built-in widget event shapes are:

| Event | Handler |
| --- | --- |
| `Button.onClick` | `lambda: ...` |
| `Button.onKeyDown` | `lambda key: ...` |
| `Button.onFocus`, `Button.onBlur` | `lambda: ...` |
| `Input.onChange` | `lambda value: ...` |
| `Input.onKeyDown` | `lambda key: ...` |
| `Input.onFocus`, `Input.onBlur` | `lambda: ...` |
| `ScrollView.onScroll` | `lambda next_scroll_y: ...` |
| `ShortcutScope.onGlobalKeyDown` | `lambda event: ...` |

`event_signature_for(...)` exposes the same contract programmatically:

```python
from otoe import Button, event_signature_for, format_event_signature

signature = event_signature_for(Button, "onKeyDown")
assert format_event_signature("onKeyDown", signature) == "onKeyDown(key)"
```

## Control Nodes

`Show` and `For` are not visual widgets; they are control nodes resolved during
mount.

| Control | Required Props | Optional Props | Notes |
| --- | --- | --- | --- |
| `Show` | `when` | `fallback` | Mounts children when truthy; otherwise mounts fallback if provided. |
| `For` | `each`, `key`, `children` | `fallback` | Renders keyed children from an iterable. `key` and `children` must be callable. |

`For(each=...)` accepts lists, tuples, and other non-string iterables after
reactive values are resolved. It rejects strings, bytes, dicts, and non-iterable
values.

## UI Components

These components live in `otoe.ui` and are re-exported from `otoe`. They are
implemented as Otoe components, so they expand into the core widget contracts
above.

| Component | Main Props | Callbacks |
| --- | --- | --- |
| `ShortcutScope` | children, `className` | `onKeyDown(event)` |
| `FocusScope` | children, `trapFocus=True`, `restoreFocus=True`, `className` | none |
| `AppShell` | `sidebar`, `content`, optional `header`, `className` | none |
| `Card` | children, `title`, `tone="default"`, `className` | none |
| `Badge` | `label`, `tone="neutral"`, `className` | none |
| `ActionButton` | `label`, `variant="primary"`, `size="md"`, `disabled=False`, `className` | `onClick()` |
| `Toolbar` | children, `gap=8`, `className` | none |
| `Tabs` | children, `gap=6`, `orientation="horizontal"`, `className` | none |
| `TabButton` | `label`, `active=False`, `className` | `onClick()` |
| `StatCard` | `label`, `value`, `detail`, `tone="neutral"`, `className` | none |
| `DataTable` | `columns`, `rows`, `key`, `render_cell`, `empty`, `className` | none |
| `Dialog` | children, `open`, `title`, `description`, `className` | none |
| `Toast` | `title`, `description`, `tone="neutral"`, `className` | none |
| `CommandPalette` | `query`, `commands`, `placeholder`, `empty`, `autoFocus`, `className` | `on_query(value)`, `on_select(command_id)` |
| `Menu` | `items`, `open=True`, `active`, `focused`, `empty`, `className` | `on_select(item_id)`, `on_focus(item_id)`, `on_open_change(open)` |
| `Select` | `options`, `value`, `open`, `placeholder`, `empty`, `className` | `on_change(value)`, `on_open_change(open)` |
| `SidebarNav` | `routes`, `active`, `brand`, `footer`, `empty`, `className` | `on_navigate(route_id)` |
| `NavItem` | `route`, `active`, `className` | `on_navigate(route_id)` |
| `RouteView` | `route`, `routes`, `render`, `fallback`, `className` | none |

UI components may accept reactive values for display/state props when the
underlying implementation reads them with `computed(...)` or passes them to a
core widget prop.

## UI Data Models

The UI layer accepts either model instances or dicts for common collection
props.

| Model | Fields |
| --- | --- |
| `TableColumn` | `key`, `label`, `className=None` |
| `Command` | `id`, `label`, `description=""`, `group=""`, `shortcut=None`, `className=None` |
| `MenuItem` | `id`, `label`, `description=None`, `shortcut=None`, `tone="neutral"`, `disabled=False`, `className=None` |
| `SelectOption` | `value`, `label`, `description=None`, `tone="neutral"`, `disabled=False`, `className=None` |
| `NavRoute` | `id`, `label`, `description=None`, `badge=None`, `tone="neutral"`, `className=None` |

`CommandRegistry` stores normalized commands and provides `commands`,
`visible(query)`, `first(query="")`, `find(command_id)`, and
`find_shortcut(key)`.

## Renderer Notes

Widget contracts are renderer-neutral. Renderer support is a separate question:

- HTML render supports the current core and UI widget output shape.
- Native render supports the current native widget, style, layout, paint, and
  input subset documented in `NATIVE_RENDERER_SPIKE.md`.
- UI components are native-compatible only to the extent that their expanded
  core widget tree and styles fit the native support matrix.
- Tk window behavior is an experimental adapter over the native surface, not a
  new widget contract.

## Failure Examples

Unknown prop:

```python
Button("Run", href="/start")  # UnknownPropError
```

The error includes the widget/component context and the known prop names.

Unknown event:

```python
Button("Run", onSubmit=lambda: None)  # UnknownPropError with known events
```

Wrong handler arity:

```python
Input(value="", onChange=lambda: None)  # EventHandlerError when onChange fires
```

Invalid children:

```python
VStack("not a node")  # TypeError
```

These errors are intentional. Otoe is stricter than ad hoc widget dictionaries
so mistakes appear at component or event boundaries instead of silently leaking
into renderers.
