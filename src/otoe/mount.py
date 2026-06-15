from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Protocol, cast

from .component import is_component_tag
from .control import is_control_tag, is_for_tag, is_show_tag, list_from_value, resolve_value
from .errors import EventHandlerError, UnknownEventError, UnknownPropError
from .events import dispatch_event, event_signature_for, format_event_catalog
from .node import Node
from .owner import CURRENT_MOUNT_PHASE, CURRENT_OWNER, Owner, current_owner
from .reactive import ReactiveValue, is_reactive


class FakeWidget:
    def __init__(self, tag: Any, *, component_stack: tuple[str, ...] = ()):
        self.tag = tag
        self.name = _tag_name(tag)
        self.component_stack = component_stack
        self.props: dict[str, Any] = {}
        self.events: dict[str, Callable[..., Any]] = {}
        self.children: list["FakeWidget"] = []
        self.revision = 0

    def set_prop(self, name: str, value: Any) -> None:
        missing = object()
        previous = self.props.get(name, missing)
        if previous is not missing and previous == value:
            return
        self.props[name] = value
        self.revision += 1

    def set_event(self, name: str, handler: Callable[..., Any]) -> None:
        self.events[name] = handler
        self.revision += 1

    def trigger(self, name: str, *args: Any) -> Any:
        if name not in self.events:
            raise KeyError(f"{self.name} has no event handler for {name!r}.")
        return dispatch_event(
            self.events[name],
            *args,
            context=_event_context(widget=self, event_name=name),
            event_signature=event_signature_for(self.tag, name),
        )


@dataclass
class MountedNode:
    node: Node
    widget: FakeWidget | None = None
    children: list["MountedNode"] = field(default_factory=list)
    owner: Owner | None = None
    cleanups: list[Callable[[], None]] = field(default_factory=list)
    _keyed_children: dict[Any, "MountedNode"] = field(default_factory=dict, init=False, repr=False)
    _keyed_items: dict[Any, Any] = field(default_factory=dict, init=False, repr=False)
    _fallback_mounted: "MountedNode | None" = field(default=None, init=False, repr=False)

    def root_widget(self) -> FakeWidget:
        return root_widget(self)


class _ReadableReactive(Protocol):
    @property
    def value(self) -> Any: ...

    def subscribe(self, callback: Callable[[], None]) -> Any: ...


def mount(node: Node) -> MountedNode:
    return _mount(node)


def _mount(node: Node, *, component_stack: tuple[str, ...] = ()) -> MountedNode:
    if is_component_tag(node.tag):
        return _mount_component(node, component_stack=component_stack)
    if is_control_tag(node.tag):
        return _mount_control(node, component_stack=component_stack)
    return _mount_widget(node, component_stack=component_stack)


def _mount_component(
    node: Node,
    *,
    component_stack: tuple[str, ...],
) -> MountedNode:
    owner = Owner(_tag_name(node.tag))
    mounted = MountedNode(node=node, owner=owner)
    token = CURRENT_OWNER.set(owner)
    try:
        phase_token = CURRENT_MOUNT_PHASE.set("render")
        try:
            child_node = node.tag.fn(*node.props["args"], **node.props["kwargs"])
        finally:
            CURRENT_MOUNT_PHASE.reset(phase_token)
        child_mounted = _mount(
            child_node,
            component_stack=component_stack + (owner.name,),
        )
        mounted.children.append(child_mounted)
        owner.run_mount()
    finally:
        CURRENT_OWNER.reset(token)
    return mounted


def _mount_widget(
    node: Node,
    *,
    component_stack: tuple[str, ...],
) -> MountedNode:
    widget = FakeWidget(node.tag, component_stack=component_stack)
    mounted = MountedNode(node=node, widget=widget)

    data_props = set(getattr(node.tag, "props", set()))
    events = set(getattr(node.tag, "events", set()))

    for name, value in node.props.items():
        if name in events:
            _register_event(widget, name, value)
        elif name in data_props:
            _assign_prop(mounted, widget, name, value)
        else:
            kind = "event" if name.startswith("on") else "prop"
            if kind == "event":
                raise UnknownEventError(_unknown_event_message(widget, name, events))
            raise UnknownPropError(_unknown_prop_message(widget, name, data_props))

    for child in node.children:
        child_mounted = _mount(child, component_stack=component_stack)
        mounted.children.append(child_mounted)
        child_widget = root_widget(child_mounted)
        widget.children.append(child_widget)

    return mounted


def _mount_control(node: Node, *, component_stack: tuple[str, ...]) -> MountedNode:
    if is_show_tag(node.tag):
        return _mount_show(node, component_stack=component_stack)
    if is_for_tag(node.tag):
        return _mount_for(node, component_stack=component_stack)
    raise RuntimeError(f"Unknown control node {_tag_name(node.tag)}.")


def _mount_show(node: Node, *, component_stack: tuple[str, ...]) -> MountedNode:
    widget = FakeWidget(node.tag, component_stack=component_stack)
    mounted = MountedNode(node=node, widget=widget)

    def refresh() -> None:
        for child in reversed(mounted.children):
            unmount(child)
        mounted.children.clear()
        widget.children.clear()

        branch_nodes = node.children if bool(resolve_value(node.props["when"])) else []
        if not branch_nodes and node.props.get("fallback") is not None:
            branch_nodes = [node.props["fallback"]]

        for branch_node in branch_nodes:
            child_mounted = _mount(branch_node, component_stack=component_stack)
            mounted.children.append(child_mounted)
            widget.children.append(root_widget(child_mounted))

    refresh()
    _subscribe_control_value(mounted, node.props["when"], refresh)
    return mounted


def _mount_for(node: Node, *, component_stack: tuple[str, ...]) -> MountedNode:
    widget = FakeWidget(node.tag, component_stack=component_stack)
    mounted = MountedNode(node=node, widget=widget)
    mounted._keyed_children = {}
    mounted._keyed_items = {}
    mounted._fallback_mounted = None

    key_fn = node.props["key"]
    render = node.props["render"]
    fallback = node.props.get("fallback")

    def refresh() -> None:
        items = list_from_value(node.props["each"])
        keyed_children: dict[Any, MountedNode] = mounted._keyed_children
        keyed_items: dict[Any, Any] = mounted._keyed_items
        next_keys = [key_fn(item) for item in items]
        next_key_set = _validated_key_set(widget, next_keys)

        fallback_mounted = mounted._fallback_mounted
        if items and fallback_mounted is not None:
            unmount(fallback_mounted)
            mounted._fallback_mounted = None
        if not items:
            for existing in keyed_children.values():
                unmount(existing)
            keyed_children.clear()
            keyed_items.clear()
            mounted.children.clear()
            widget.children.clear()
            if fallback is not None:
                if mounted._fallback_mounted is None:
                    mounted._fallback_mounted = _mount(
                        fallback,
                        component_stack=component_stack,
                    )
                fallback_mounted = mounted._fallback_mounted
                mounted.children = [fallback_mounted]
                widget.children = [root_widget(fallback_mounted)]
            return

        for existing_key in list(keyed_children):
            if existing_key not in next_key_set:
                unmount(keyed_children.pop(existing_key))
                keyed_items.pop(existing_key, None)

        for item, item_key in zip(items, next_keys):
            if item_key not in keyed_children:
                keyed_children[item_key] = _mount(
                    render(item),
                    component_stack=component_stack,
                )
                keyed_items[item_key] = item
            elif not _items_equal(keyed_items.get(item_key), item):
                unmount(keyed_children[item_key])
                keyed_children[item_key] = _mount(
                    render(item),
                    component_stack=component_stack,
                )
                keyed_items[item_key] = item

        mounted.children = [keyed_children[item_key] for item_key in next_keys]
        widget.children = [root_widget(child) for child in mounted.children]

    refresh()
    _subscribe_control_value(mounted, node.props["each"], refresh)
    return mounted


def _subscribe_control_value(mounted: MountedNode, value: Any, refresh: Callable[[], None]) -> None:
    if is_reactive(value):
        source = value
        assert isinstance(source, ReactiveValue)
        subscription = source.subscribe(refresh)
        mounted.cleanups.append(subscription.dispose)

        owner = current_owner()
        if owner is not None:
            owner.add_cleanup(subscription.dispose)


def _register_event(widget: FakeWidget, name: str, value: Any) -> None:
    if not callable(value):
        raise EventHandlerError(f"{widget.name}.{name} must be callable.")
    widget.set_event(name, value)


def _unknown_event_message(widget: FakeWidget, name: str, events: set[str]) -> str:
    message = f"{_widget_context(widget)} received unknown event {name!r}."
    if not events:
        return message
    signatures = getattr(widget.tag, "event_signatures", {})
    return f"{message} Known events: {format_event_catalog(events, signatures)}."


def _unknown_prop_message(widget: FakeWidget, name: str, props: set[str]) -> str:
    message = f"{_widget_context(widget)} received unknown prop {name!r}."
    if not props:
        return message
    return f"{message} Known props: {', '.join(sorted(props))}."


def _event_context(*, widget: FakeWidget, event_name: str) -> str:
    return _join_context(widget, f"{widget.name}.{event_name}")


def _widget_context(widget: FakeWidget) -> str:
    return _join_context(widget, widget.name)


def _join_context(widget: FakeWidget, leaf: str) -> str:
    if not widget.component_stack:
        return leaf
    return " > ".join((*widget.component_stack, leaf))


def _assign_prop(mounted: MountedNode, widget: FakeWidget, name: str, value: Any) -> None:
    if is_reactive(value):
        source = cast(_ReadableReactive, value)

        def update() -> None:
            widget.set_prop(name, source.value)

        update()
        subscription = source.subscribe(update)
        mounted.cleanups.append(subscription.dispose)

        owner = current_owner()
        if owner is not None:
            owner.add_cleanup(subscription.dispose)
    else:
        widget.set_prop(name, value)


def _items_equal(left: Any, right: Any) -> bool:
    try:
        result = left == right
    except Exception:
        return left is right
    return result if isinstance(result, bool) else left is right


def _validated_key_set(widget: FakeWidget, keys: list[Any]) -> set[Any]:
    seen: set[Any] = set()
    for key in keys:
        try:
            if key in seen:
                raise ValueError(
                    f"{_widget_context(widget)} received duplicate key {key!r}. "
                    "For keys must be unique."
                )
            seen.add(key)
        except TypeError as exc:
            raise TypeError(
                f"{_widget_context(widget)} received unhashable key {key!r}. "
                "For keys must be hashable."
            ) from exc
    return seen


def unmount(mounted: MountedNode) -> None:
    for child in reversed(mounted.children):
        unmount(child)

    for cleanup in reversed(mounted.cleanups):
        cleanup()
    mounted.cleanups.clear()

    if mounted.owner is not None:
        mounted.owner.dispose()


def root_widget(mounted: MountedNode) -> FakeWidget:
    if mounted.widget is not None:
        return mounted.widget
    if not mounted.children:
        raise RuntimeError("Mounted component has no root widget.")
    return root_widget(mounted.children[0])


def _tag_name(tag: Any) -> str:
    return getattr(tag, "__name__", getattr(tag, "name", tag.__class__.__name__))
