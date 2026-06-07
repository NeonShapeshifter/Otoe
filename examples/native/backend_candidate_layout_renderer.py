from __future__ import annotations

from math import ceil
from typing import Any

from otoe import LayoutBox, NativeLayout

from .backend_candidate_layout_styles import _layout_candidate_style
from .backend_candidate_layout_utils import (
    _candidate_flatten,
    _candidate_optional_string,
    _candidate_root_widget,
    _candidate_widget_context,
    _candidate_widget_state,
    _layout_candidate_offset,
    _layout_candidate_offset_y,
    _layout_candidate_text,
)
from .backend_candidate_renderer_utils import (
    _candidate_style_constrain,
    _candidate_style_dimension,
)


def _layout_candidate_target(
    target: Any,
    *,
    stylesheet: Any,
    strict_styles: bool,
) -> NativeLayout:
    widget = _candidate_root_widget(target)
    root = _layout_candidate_widget(
        widget,
        path=(),
        x=0,
        y=0,
        stylesheet=stylesheet,
        strict_styles=strict_styles,
    )
    return NativeLayout(root=root, boxes=tuple(_candidate_flatten(root)))


def _layout_candidate_widget(
    widget: Any,
    *,
    path: tuple[int, ...],
    x: int,
    y: int,
    stylesheet: Any,
    strict_styles: bool,
) -> LayoutBox:
    style = _layout_candidate_style(
        widget,
        stylesheet=stylesheet,
        strict_styles=strict_styles,
    )
    name = widget.name
    if name in {"Text", "Button", "Input"}:
        return _layout_candidate_leaf(widget, path=path, x=x, y=y, style=style)
    direction = "row" if name == "HStack" else "column"
    return _layout_candidate_container(
        widget,
        path=path,
        x=x,
        y=y,
        style=style,
        direction=direction,
        stylesheet=stylesheet,
        strict_styles=strict_styles,
    )


def _layout_candidate_leaf(
    widget: Any,
    *,
    path: tuple[int, ...],
    x: int,
    y: int,
    style: dict[str, Any],
) -> LayoutBox:
    text = _layout_candidate_text(widget)
    font_size = _candidate_style_dimension(style, "fontSize", default=14)
    default_padding = 8 if widget.name in {"Button", "Input"} else 0
    padding = _candidate_style_dimension(style, "padding", default=default_padding)
    border_width = _candidate_style_dimension(style, "borderWidth", default=0)
    width = max(1, ceil(len(text) * font_size * 0.55))
    height = max(1, ceil(font_size * 1.25))
    width += padding * 2 + border_width * 2
    height += padding * 2 + border_width * 2
    if widget.name == "Input":
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
        path=path,
        name=widget.name,
        x=x,
        y=y,
        width=width,
        height=height,
        id=_candidate_optional_string(widget.props.get("id")),
        context=_candidate_widget_context(widget),
        text=text,
        events=tuple(sorted(widget.events)),
        state=_candidate_widget_state(widget),
        style=tuple(sorted(style.items())),
    )


def _layout_candidate_container(
    widget: Any,
    *,
    path: tuple[int, ...],
    x: int,
    y: int,
    style: dict[str, Any],
    direction: str,
    stylesheet: Any,
    strict_styles: bool,
) -> LayoutBox:
    padding = _candidate_style_dimension(style, "padding", default=0)
    gap = _candidate_style_dimension(style, "gap", default=0)
    scroll_y = (
        _candidate_style_dimension(style, "scrollY", default=0)
        if widget.name == "ScrollView"
        else 0
    )
    cursor_x = x + padding
    cursor_y = y + padding - scroll_y
    content_width = 0
    content_height = 0
    children = []
    for index, child in enumerate(widget.children):
        if index:
            if direction == "row":
                cursor_x += gap
            else:
                cursor_y += gap
        child_box = _layout_candidate_widget(
            child,
            path=(*path, index),
            x=cursor_x,
            y=cursor_y,
            stylesheet=stylesheet,
            strict_styles=strict_styles,
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
    if widget.name == "HStack":
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
    if widget.name == "ScrollView":
        max_scroll = max(0, content_height + padding * 2 - height)
        clamped_scroll_y = min(max(scroll_y, 0), max_scroll)
        if clamped_scroll_y != scroll_y:
            children = [
                _layout_candidate_offset_y(child, scroll_y - clamped_scroll_y)
                for child in children
            ]
        style = {**style, "scrollY": clamped_scroll_y}

    return LayoutBox(
        path=path,
        name=widget.name,
        x=x,
        y=y,
        width=width,
        height=height,
        id=_candidate_optional_string(widget.props.get("id")),
        context=_candidate_widget_context(widget),
        events=tuple(sorted(widget.events)),
        state=_candidate_widget_state(widget),
        style=tuple(sorted(style.items())),
        children=tuple(children),
    )


def _layout_candidate_align_row(
    children: list[LayoutBox],
    *,
    x: int,
    y: int,
    width: int,
    height: int,
    padding: int,
    content_width: int,
    style: dict[str, Any],
) -> list[LayoutBox]:
    if not children:
        return children
    extra = max(0, width - padding * 2 - content_width)
    justify_content = style.get("justifyContent")
    align_items = style.get("alignItems")
    if justify_content == "space-between" and len(children) > 1:
        main_offsets = [
            (extra * index) // (len(children) - 1)
            for index, _child in enumerate(children)
        ]
    elif justify_content == "center":
        main_offsets = [extra // 2 for _child in children]
    elif justify_content in {"end", "flex-end"}:
        main_offsets = [extra for _child in children]
    else:
        main_offsets = [0 for _child in children]
    return [
        _layout_candidate_offset(
            child,
            dx=main_offsets[index],
            dy=max(0, (height - padding * 2 - child.height) // 2)
            if align_items == "center"
            else 0,
        )
        for index, child in enumerate(children)
    ]
