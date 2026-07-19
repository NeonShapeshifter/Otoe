from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, Callable, Protocol, cast

from ._widget_contracts import widget_event_signatures, widget_events, widget_props
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
        self.focus_identity: object | None = None
        self.focus_identities: set[object] = set()

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
    _activated: bool = field(default=False, init=False, repr=False)
    _unmounted: bool = field(default=False, init=False, repr=False)

    def root_widget(self) -> FakeWidget:
        return root_widget(self)


class _ReadableReactive(Protocol):
    @property
    def value(self) -> Any: ...

    def subscribe(self, callback: Callable[[], None]) -> Any: ...


def mount(node: Node) -> MountedNode:
    return _mount(node)


def _mount(
    node: Node,
    *,
    component_stack: tuple[str, ...] = (),
    activate: bool = True,
) -> MountedNode:
    if is_component_tag(node.tag):
        return _mount_component(node, component_stack=component_stack, activate=activate)
    if is_control_tag(node.tag):
        return _mount_control(node, component_stack=component_stack, activate=activate)
    return _mount_widget(node, component_stack=component_stack, activate=activate)


def _mount_component(
    node: Node,
    *,
    component_stack: tuple[str, ...],
    activate: bool,
) -> MountedNode:
    owner = Owner(_tag_name(node.tag))
    mounted = MountedNode(node=node, owner=owner)
    token = CURRENT_OWNER.set(owner)
    try:
        try:
            phase_token = CURRENT_MOUNT_PHASE.set("render")
            try:
                child_node = node.tag.fn(*node.props["args"], **node.props["kwargs"])
            finally:
                CURRENT_MOUNT_PHASE.reset(phase_token)
            child_mounted = _mount(
                child_node,
                component_stack=component_stack + (owner.name,),
                activate=activate,
            )
            mounted.children.append(child_mounted)
            if activate:
                owner.run_mount()
                mounted._activated = True
        except BaseException as primary_error:
            _run_failure_cleanup(
                primary_error,
                lambda: unmount(mounted),
                message=f"{owner.name}: mount and cleanup both failed.",
            )
            raise
    finally:
        CURRENT_OWNER.reset(token)
    return mounted


def _mount_widget(
    node: Node,
    *,
    component_stack: tuple[str, ...],
    activate: bool,
) -> MountedNode:
    widget = FakeWidget(node.tag, component_stack=component_stack)
    mounted = MountedNode(node=node, widget=widget)

    data_props = set(widget_props(node.tag))
    events = set(widget_events(node.tag))

    try:
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
            child_mounted = _mount(
                child,
                component_stack=component_stack,
                activate=activate,
            )
            mounted.children.append(child_mounted)
            child_widget = root_widget(child_mounted)
            widget.children.append(child_widget)
        if activate:
            mounted._activated = True
    except BaseException as primary_error:
        _run_failure_cleanup(
            primary_error,
            lambda: unmount(mounted),
            message=f"{_tag_name(node.tag)}: mount and cleanup both failed.",
        )
        raise

    return mounted


def _mount_control(
    node: Node,
    *,
    component_stack: tuple[str, ...],
    activate: bool,
) -> MountedNode:
    if is_show_tag(node.tag):
        return _mount_show(node, component_stack=component_stack, activate=activate)
    if is_for_tag(node.tag):
        return _mount_for(node, component_stack=component_stack, activate=activate)
    raise RuntimeError(f"Unknown control node {_tag_name(node.tag)}.")


def _mount_show(
    node: Node,
    *,
    component_stack: tuple[str, ...],
    activate: bool,
) -> MountedNode:
    widget = FakeWidget(node.tag, component_stack=component_stack)
    mounted = MountedNode(node=node, widget=widget)
    selected_truthiness: bool | None = None

    def refresh() -> None:
        nonlocal selected_truthiness
        next_truthiness = bool(resolve_value(node.props["when"]))
        if selected_truthiness is next_truthiness:
            return
        branch_nodes = node.children if next_truthiness else []
        if not branch_nodes and node.props.get("fallback") is not None:
            branch_nodes = [node.props["fallback"]]

        next_children = _mount_children(
            branch_nodes,
            component_stack=component_stack,
            activate=False,
        )
        previous_children = mounted.children
        previous_widgets = widget.children
        previous_truthiness = selected_truthiness
        try:
            next_widgets = [root_widget(child) for child in next_children]
        except BaseException as primary_error:
            _run_failure_cleanup(
                primary_error,
                lambda: _unmount_children(next_children),
                message="Show branch preparation and cleanup both failed.",
            )
            raise

        mounted.children = next_children
        widget.children = next_widgets
        selected_truthiness = next_truthiness
        try:
            if mounted._activated:
                _activate_children(next_children)
        except BaseException as primary_error:
            staged_state_is_current = mounted.children is next_children
            if staged_state_is_current:
                mounted.children = previous_children
                widget.children = previous_widgets
                selected_truthiness = previous_truthiness
            cleanup_candidates = list(next_children)
            if not staged_state_is_current:
                cleanup_candidates.extend(previous_children)
            orphaned_children = _unretained_children(
                cleanup_candidates,
                retained=mounted.children,
            )
            _run_failure_cleanup(
                primary_error,
                lambda: _unmount_children(orphaned_children),
                message="Show branch activation and cleanup both failed.",
            )
            raise

        _unmount_children(
            _unretained_children(previous_children, retained=mounted.children)
        )

    try:
        refresh()
        _subscribe_control_value(mounted, node.props["when"], refresh)
        if activate:
            _activate_mounted(mounted)
    except BaseException as primary_error:
        _run_failure_cleanup(
            primary_error,
            lambda: unmount(mounted),
            message="Show mount and cleanup both failed.",
        )
        raise
    return mounted


def _mount_children(
    nodes: Sequence[Node],
    *,
    component_stack: tuple[str, ...],
    activate: bool,
) -> list[MountedNode]:
    mounted_children: list[MountedNode] = []
    try:
        for child_node in nodes:
            mounted_children.append(
                _mount(
                    child_node,
                    component_stack=component_stack,
                    activate=activate,
                )
            )
    except BaseException as primary_error:
        _run_failure_cleanup(
            primary_error,
            lambda: _unmount_children(mounted_children),
            message="Child mount and cleanup both failed.",
        )
        raise
    return mounted_children


def _unmount_children(children: list[MountedNode]) -> None:
    errors: list[BaseException] = []
    for child in reversed(children):
        try:
            unmount(child)
        except BaseException as exc:
            errors.append(exc)
    if errors:
        raise BaseExceptionGroup("Errors while unmounting children.", errors)


def _activate_children(children: list[MountedNode]) -> None:
    for child in children:
        _activate_mounted(child)


def _activate_mounted(mounted: MountedNode) -> None:
    if mounted._activated or mounted._unmounted:
        return
    mounted._activated = True
    _activate_children(mounted.children)
    if mounted.owner is not None and not mounted._unmounted:
        mounted.owner.run_mount()


def _mount_for(
    node: Node,
    *,
    component_stack: tuple[str, ...],
    activate: bool,
) -> MountedNode:
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
        _validated_key_set(widget, next_keys)

        fallback_mounted = mounted._fallback_mounted
        if not items:
            next_fallback = fallback_mounted
            created_fallback = False
            if fallback is not None:
                if next_fallback is None:
                    next_fallback = _mount(
                        fallback,
                        component_stack=component_stack,
                        activate=False,
                    )
                    created_fallback = True
                try:
                    next_widgets = [root_widget(next_fallback)]
                except BaseException as primary_error:
                    if created_fallback:
                        _run_failure_cleanup(
                            primary_error,
                            lambda: unmount(next_fallback),
                            message="For fallback preparation and cleanup both failed.",
                        )
                    raise
                next_children = [next_fallback]
            else:
                next_widgets = []
                next_children = []

            empty_previous_children = list(keyed_children.values())
            empty_previous_fallback = fallback_mounted
            empty_previous_keyed_children = keyed_children
            empty_previous_keyed_items = keyed_items
            empty_previous_mounted_children = mounted.children
            empty_previous_widgets = widget.children
            mounted._fallback_mounted = next_fallback if fallback is not None else None
            mounted._keyed_children = {}
            mounted._keyed_items = {}
            mounted.children = next_children
            widget.children = next_widgets
            try:
                if mounted._activated and next_fallback is not None:
                    _activate_mounted(next_fallback)
            except BaseException as primary_error:
                staged_state_is_current = mounted.children is next_children
                if staged_state_is_current:
                    mounted._fallback_mounted = empty_previous_fallback
                    mounted._keyed_children = empty_previous_keyed_children
                    mounted._keyed_items = empty_previous_keyed_items
                    mounted.children = empty_previous_mounted_children
                    widget.children = empty_previous_widgets
                cleanup_candidates = [
                    child
                    for child in [next_fallback]
                    if child is not None and created_fallback
                ]
                if not staged_state_is_current:
                    cleanup_candidates.extend(empty_previous_children)
                orphaned_children = _unretained_children(
                    cleanup_candidates,
                    retained=mounted.children,
                )
                _run_failure_cleanup(
                    primary_error,
                    lambda: _unmount_children(orphaned_children),
                    message="For fallback activation and cleanup both failed.",
                )
                raise

            _unmount_children(
                _unretained_children(
                    empty_previous_children,
                    retained=mounted.children,
                )
            )
            return

        next_keyed_children: dict[Any, MountedNode] = {}
        next_keyed_items: dict[Any, Any] = {}
        created_children: list[MountedNode] = []
        try:
            for item, item_key in zip(items, next_keys, strict=True):
                if item_key in keyed_children and _items_equal(
                    keyed_items.get(item_key), item
                ):
                    child_mounted = keyed_children[item_key]
                else:
                    child_mounted = _mount(
                        render(item),
                        component_stack=component_stack,
                        activate=False,
                    )
                    created_children.append(child_mounted)
                next_keyed_children[item_key] = child_mounted
                next_keyed_items[item_key] = item
        except BaseException as primary_error:
            _run_failure_cleanup(
                primary_error,
                lambda: _unmount_children(created_children),
                message="For child mount and cleanup both failed.",
            )
            raise

        next_children = [next_keyed_children[item_key] for item_key in next_keys]
        try:
            next_widgets = [root_widget(child) for child in next_children]
            for item_key, child_widget in zip(next_keys, next_widgets, strict=True):
                _assign_keyed_focus_identity(
                    child_widget,
                    control_widget=widget,
                    item_key=item_key,
                )
        except BaseException as primary_error:
            _run_failure_cleanup(
                primary_error,
                lambda: _unmount_children(created_children),
                message="For child preparation and cleanup both failed.",
            )
            raise

        previous_children: list[MountedNode] = []
        if fallback_mounted is not None:
            previous_children.append(fallback_mounted)
        for existing_key, existing_child in keyed_children.items():
            if next_keyed_children.get(existing_key) is not existing_child:
                previous_children.append(existing_child)

        previous_keyed_children = keyed_children
        previous_keyed_items = keyed_items
        previous_mounted_children = mounted.children
        previous_widgets = widget.children
        mounted._fallback_mounted = None
        mounted._keyed_children = next_keyed_children
        mounted._keyed_items = next_keyed_items
        mounted.children = next_children
        widget.children = next_widgets
        try:
            if mounted._activated:
                _activate_children(next_children)
        except BaseException as primary_error:
            staged_state_is_current = mounted._keyed_children is next_keyed_children
            if staged_state_is_current:
                mounted._fallback_mounted = fallback_mounted
                mounted._keyed_children = previous_keyed_children
                mounted._keyed_items = previous_keyed_items
                mounted.children = previous_mounted_children
                widget.children = previous_widgets
            cleanup_candidates = list(created_children)
            if not staged_state_is_current:
                cleanup_candidates.extend(previous_children)
            orphaned_children = _unretained_children(
                cleanup_candidates,
                retained=mounted.children,
            )
            _run_failure_cleanup(
                primary_error,
                lambda: _unmount_children(orphaned_children),
                message="For child activation and cleanup both failed.",
            )
            raise

        _unmount_children(
            _unretained_children(previous_children, retained=mounted.children)
        )

    try:
        refresh()
        _subscribe_control_value(mounted, node.props["each"], refresh)
        if activate:
            _activate_mounted(mounted)
    except BaseException as primary_error:
        _run_failure_cleanup(
            primary_error,
            lambda: unmount(mounted),
            message="For mount and cleanup both failed.",
        )
        raise
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
    signatures = widget_event_signatures(widget.tag)
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


def _assign_keyed_focus_identity(
    widget: FakeWidget,
    *,
    control_widget: FakeWidget,
    item_key: Any,
    relative_path: tuple[int, ...] = (),
) -> None:
    identity = (
        "for-key",
        control_widget,
        item_key,
        relative_path,
    )
    widget.focus_identity = identity
    widget.focus_identities.add(identity)
    for index, child in enumerate(widget.children):
        _assign_keyed_focus_identity(
            child,
            control_widget=control_widget,
            item_key=item_key,
            relative_path=(*relative_path, index),
        )


def _run_failure_cleanup(
    primary_error: BaseException,
    cleanup: Callable[[], None],
    *,
    message: str,
) -> None:
    try:
        cleanup()
    except BaseException as cleanup_error:
        raise BaseExceptionGroup(
            message,
            [primary_error, cleanup_error],
        ) from primary_error


def _unretained_children(
    candidates: Sequence[MountedNode],
    *,
    retained: Sequence[MountedNode],
) -> list[MountedNode]:
    retained_ids = {id(child) for child in retained}
    seen_ids: set[int] = set()
    result: list[MountedNode] = []
    for child in candidates:
        child_id = id(child)
        if child_id in retained_ids or child_id in seen_ids:
            continue
        seen_ids.add(child_id)
        result.append(child)
    return result


def unmount(mounted: MountedNode) -> None:
    if mounted._unmounted:
        return
    mounted._unmounted = True

    errors: list[BaseException] = []
    for child in reversed(mounted.children):
        try:
            unmount(child)
        except BaseException as exc:
            errors.append(exc)

    cleanups = list(reversed(mounted.cleanups))
    mounted.cleanups.clear()
    for cleanup in cleanups:
        try:
            cleanup()
        except BaseException as exc:
            errors.append(exc)

    if mounted.owner is not None:
        try:
            mounted.owner.dispose()
        except BaseException as exc:
            errors.append(exc)

    if errors:
        raise BaseExceptionGroup(
            f"{_tag_name(mounted.node.tag)}: errors while unmounting.",
            errors,
        )


def root_widget(mounted: MountedNode) -> FakeWidget:
    if mounted.widget is not None:
        return mounted.widget
    if not mounted.children:
        raise RuntimeError("Mounted component has no root widget.")
    return root_widget(mounted.children[0])


def _tag_name(tag: Any) -> str:
    return cast(
        str,
        getattr(tag, "__name__", getattr(tag, "name", tag.__class__.__name__)),
    )
