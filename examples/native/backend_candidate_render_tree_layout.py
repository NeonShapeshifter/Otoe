from __future__ import annotations

from math import ceil
from typing import Any

from otoe import LayoutBox, NativeLayout
from otoe.render_ir import RenderNode, RenderTree

from .backend_candidate_layout_renderer import (
    _candidate_flatten,
    _layout_candidate_align_row,
    _layout_candidate_offset_y,
)
from .backend_candidate_renderer_utils import (
    _candidate_style_constrain,
    _candidate_style_dimension,
)


def _layout_candidate_render_tree(tree: RenderTree) -> NativeLayout:
    root = _layout_candidate_render_node(tree.root, x=0, y=0)
    return NativeLayout(root=root, boxes=tuple(_candidate_flatten(root)))


def _layout_candidate_render_node(
    node: RenderNode,
    *,
    x: int,
    y: int,
) -> LayoutBox:
    style = node.style_dict()
    name = node.name
    props = node.prop_dict()
    if name in {"Text", "Button", "Input"}:
        return _layout_candidate_render_leaf(
            node,
            props=props,
            x=x,
            y=y,
            style=style,
        )
    direction = "row" if name == "HStack" else "column"
    return _layout_candidate_render_container(
        node,
        x=x,
        y=y,
        style=style,
        direction=direction,
    )


def _layout_candidate_render_leaf(
    node: RenderNode,
    *,
    props: dict[str, Any],
    x: int,
    y: int,
    style: dict[str, Any],
) -> LayoutBox:
    text = _layout_candidate_render_text(node, props)
    font_size = _candidate_style_dimension(style, "fontSize", default=14)
    default_padding = 8 if node.name in {"Button", "Input"} else 0
    padding = _candidate_style_dimension(style, "padding", default=default_padding)
    border_width = _candidate_style_dimension(style, "borderWidth", default=0)
    width = max(1, ceil(len(text) * font_size * 0.55))
    height = max(1, ceil(font_size * 1.25))
    width += padding * 2 + border_width * 2
    height += padding * 2 + border_width * 2
    if node.name == "Input":
        width = max(width, 180)
    width = _candidate_style_dimension(style, "width", default=width)
    height = _candidate_style_dimension(style, "height", default=height)
    width = _candidate_style_constrain(
        width,
        style,
        min_name="minWidth",
        max_name="maxWidth",
    )
    height = _candidate_style_constrain(
        height,
        style,
        min_name="minHeight",
        max_name="maxHeight",
    )
    return LayoutBox(
        path=node.path,
        name=node.name,
        x=x,
        y=y,
        width=width,
        height=height,
        id=node.widget_id,
        context=node.context,
        text=text,
        events=node.events,
        state=node.state,
        style=tuple(sorted(style.items())),
    )


def _layout_candidate_render_container(
    node: RenderNode,
    *,
    x: int,
    y: int,
    style: dict[str, Any],
    direction: str,
) -> LayoutBox:
    padding = _candidate_style_dimension(style, "padding", default=0)
    gap = _candidate_style_dimension(style, "gap", default=0)
    scroll_y = (
        _candidate_style_dimension(style, "scrollY", default=0)
        if node.name == "ScrollView"
        else 0
    )
    cursor_x = x + padding
    cursor_y = y + padding - scroll_y
    content_width = 0
    content_height = 0
    children = []
    for index, child in enumerate(node.children):
        if index:
            if direction == "row":
                cursor_x += gap
            else:
                cursor_y += gap
        child_box = _layout_candidate_render_node(
            child,
            x=cursor_x,
            y=cursor_y,
        )
        children.append(child_box)
        if direction == "row":
            cursor_x += child_box.width
            content_width += child_box.width + (gap if index else 0)
            content_height = max(content_height, child_box.height)
        else:
            cursor_y += child_box.height
            content_width = max(content_width, child_box.width)
            content_height += child_box.height + (gap if index else 0)

    width = _candidate_style_dimension(
        style,
        "width",
        default=content_width + padding * 2,
    )
    height = _candidate_style_dimension(
        style,
        "height",
        default=content_height + padding * 2,
    )
    width = _candidate_style_constrain(
        width,
        style,
        min_name="minWidth",
        max_name="maxWidth",
    )
    height = _candidate_style_constrain(
        height,
        style,
        min_name="minHeight",
        max_name="maxHeight",
    )
    if node.name == "HStack":
        children = _layout_candidate_align_row(
            children,
            x=x,
            y=y,
            width=width,
            height=height,
            padding=padding,
            content_width=content_width,
            style=style,
        )
    if node.name == "ScrollView":
        max_scroll = max(0, content_height + padding * 2 - height)
        clamped_scroll_y = min(max(scroll_y, 0), max_scroll)
        if clamped_scroll_y != scroll_y:
            children = [
                _layout_candidate_offset_y(child, scroll_y - clamped_scroll_y)
                for child in children
            ]
        style = {**style, "scrollY": clamped_scroll_y}

    return LayoutBox(
        path=node.path,
        name=node.name,
        x=x,
        y=y,
        width=width,
        height=height,
        id=node.widget_id,
        context=node.context,
        events=node.events,
        state=node.state,
        style=tuple(sorted(style.items())),
        children=tuple(children),
    )


def _layout_candidate_render_text(
    node: RenderNode,
    props: dict[str, Any],
) -> str:
    if node.name == "Button":
        return str(props.get("label", ""))
    if node.name == "Input":
        return str(props.get("value") or props.get("placeholder") or "")
    return str(props.get("content", ""))
