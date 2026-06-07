from __future__ import annotations

from typing import Any

from ._native_shared import resolve_style, state_items, widget_context
from ._render_identity import (
    mounted_child_key,
    optional_string,
    render_key_label,
    render_node_id,
)
from .mount import FakeWidget, MountedNode
from .render_ir_types import RenderIRError, RenderNode, RenderTree
from .render_ir_validate import assert_render_tree_valid
from .style import ResolvedStyleMap, StyleSheet


def render_tree_from_target(
    target: FakeWidget | MountedNode,
    *,
    stylesheet: StyleSheet | None = None,
    style_map: ResolvedStyleMap | None = None,
    strict_styles: bool = True,
) -> RenderTree:
    if isinstance(target, MountedNode):
        root = _render_mounted(
            target,
            path=(),
            parent_id=None,
            key=None,
            stylesheet=stylesheet,
            style_map=style_map,
            strict_styles=strict_styles,
        )
    elif isinstance(target, FakeWidget):
        root = _render_widget(
            target,
            path=(),
            parent_id=None,
            key=None,
            stylesheet=stylesheet,
            style_map=style_map,
            strict_styles=strict_styles,
        )
    else:
        raise TypeError(
            "render_tree_from_target expected FakeWidget or MountedNode; "
            f"got {type(target).__name__}."
        )
    tree = RenderTree(root=root)
    assert_render_tree_valid(tree)
    return tree


def _render_mounted(
    mounted: MountedNode,
    *,
    path: tuple[int, ...],
    parent_id: str | None,
    key: Any,
    stylesheet: StyleSheet | None,
    style_map: ResolvedStyleMap | None,
    strict_styles: bool,
) -> RenderNode:
    if mounted.widget is None:
        if len(mounted.children) != 1:
            raise RenderIRError(
                "Mounted component nodes must resolve to exactly one child."
            )
        return _render_mounted(
            mounted.children[0],
            path=path,
            parent_id=parent_id,
            key=key,
            stylesheet=stylesheet,
            style_map=style_map,
            strict_styles=strict_styles,
        )
    return _render_widget(
        mounted.widget,
        path=path,
        parent_id=parent_id,
        key=key,
        stylesheet=stylesheet,
        style_map=style_map,
        strict_styles=strict_styles,
        mounted=mounted,
    )


def _render_widget(
    widget: FakeWidget,
    *,
    path: tuple[int, ...],
    parent_id: str | None,
    key: Any,
    stylesheet: StyleSheet | None,
    style_map: ResolvedStyleMap | None,
    strict_styles: bool,
    mounted: MountedNode | None = None,
) -> RenderNode:
    widget_id = optional_string(widget.props.get("id"))
    class_name = optional_string(widget.props.get("className"))
    key_label = render_key_label(key)
    node_id = render_node_id(
        parent_id=parent_id,
        name=widget.name,
        path=path,
        widget_id=widget_id,
        key_label=key_label,
    )
    children = tuple(
        _render_child(
            child_widget=child_widget,
            child_mounted=child_mounted,
            path=(*path, index),
            parent_id=node_id,
            key=mounted_child_key(mounted, child_mounted),
            stylesheet=stylesheet,
            style_map=style_map,
            strict_styles=strict_styles,
        )
        for index, (child_widget, child_mounted) in enumerate(
            _iter_children(widget, mounted)
        )
    )
    return RenderNode(
        node_id=node_id,
        path=path,
        name=widget.name,
        widget_id=widget_id,
        key=key_label,
        class_name=class_name,
        props=_props(widget),
        events=tuple(sorted(widget.events)),
        state=state_items(widget),
        context=widget_context(widget),
        style=tuple(
            sorted(
                _resolve_render_style(
                    widget,
                    path=path,
                    node_id=node_id,
                    stylesheet=stylesheet,
                    style_map=style_map,
                    strict_styles=strict_styles,
                ).items()
            )
        ),
        children=children,
    )


def _render_child(
    *,
    child_widget: FakeWidget,
    child_mounted: MountedNode | None,
    path: tuple[int, ...],
    parent_id: str,
    key: Any,
    stylesheet: StyleSheet | None,
    style_map: ResolvedStyleMap | None,
    strict_styles: bool,
) -> RenderNode:
    if child_mounted is None:
        return _render_widget(
            child_widget,
            path=path,
            parent_id=parent_id,
            key=key,
            stylesheet=stylesheet,
            style_map=style_map,
            strict_styles=strict_styles,
        )
    return _render_mounted(
        child_mounted,
        path=path,
        parent_id=parent_id,
        key=key,
        stylesheet=stylesheet,
        style_map=style_map,
        strict_styles=strict_styles,
    )


def _iter_children(
    widget: FakeWidget,
    mounted: MountedNode | None,
) -> tuple[tuple[FakeWidget, MountedNode | None], ...]:
    if mounted is None:
        return tuple((child, None) for child in widget.children)
    return tuple(
        (child_widget, child_mounted)
        for child_widget, child_mounted in zip(widget.children, mounted.children)
    )


def _resolve_render_style(
    widget: FakeWidget,
    *,
    path: tuple[int, ...],
    node_id: str,
    stylesheet: StyleSheet | None,
    style_map: ResolvedStyleMap | None,
    strict_styles: bool,
) -> dict[str, Any]:
    if style_map is None:
        return resolve_style(widget, stylesheet, strict_styles)
    style = style_map.resolve(
        optional_string(widget.props.get("className")),
        path=path,
        node_id=node_id,
        strict=strict_styles,
    )
    for name, value in resolve_style(widget, None, strict_styles).items():
        style.setdefault(name, value)
    return style


def _props(widget: FakeWidget) -> tuple[tuple[str, Any], ...]:
    return tuple(
        sorted(
            (name, _prop_value(value))
            for name, value in widget.props.items()
            if _include_prop_value(value)
        )
    )


def _include_prop_value(value: Any) -> bool:
    return isinstance(value, (str, int, float, bool, type(None), list, tuple, dict))


def _prop_value(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, tuple):
        return tuple(_prop_value(item) for item in value if _include_prop_value(item))
    if isinstance(value, list):
        return tuple(_prop_value(item) for item in value if _include_prop_value(item))
    if isinstance(value, dict):
        return tuple(
            sorted(
                (str(key), _prop_value(item))
                for key, item in value.items()
                if _include_prop_value(item)
            )
        )
    return repr(value)
