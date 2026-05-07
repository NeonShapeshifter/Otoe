from __future__ import annotations

from typing import Any

from ._native_contracts import LayoutBox, NativeLayout
from ._native_shared import (
    clamp_scroll_y,
    constrain,
    dimension,
    flatten,
    NATIVE_CONTAINER_WIDGETS,
    optional_string,
    resolve_style,
    state_items,
    style_items,
)
from ._native_text import measure_native_text
from .mount import FakeWidget, MountedNode, root_widget
from .style import StyleSheet


def layout_native(
    target: FakeWidget | MountedNode,
    *,
    stylesheet: StyleSheet | None = None,
    strict_styles: bool = True,
) -> NativeLayout:
    widget = root_widget(target) if isinstance(target, MountedNode) else target
    root = _layout_widget(
        widget,
        path=(),
        x=0,
        y=0,
        stylesheet=stylesheet,
        strict_styles=strict_styles,
    )
    return NativeLayout(root=root, boxes=tuple(flatten(root)))


def _layout_widget(
    widget: FakeWidget,
    *,
    path: tuple[int, ...],
    x: int,
    y: int,
    stylesheet: StyleSheet | None,
    strict_styles: bool,
) -> LayoutBox:
    style = resolve_style(widget, stylesheet, strict_styles)
    name = widget.name

    if name == "Text":
        return _leaf_box(
            widget,
            path=path,
            x=x,
            y=y,
            style=style,
            text=str(widget.props.get("content", "")),
        )
    if name == "Button":
        return _leaf_box(
            widget,
            path=path,
            x=x,
            y=y,
            style=style,
            text=str(widget.props.get("label", "")),
            default_padding=8,
        )
    if name == "Input":
        return _leaf_box(
            widget,
            path=path,
            x=x,
            y=y,
            style=style,
            text=str(widget.props.get("value") or widget.props.get("placeholder") or ""),
            default_padding=8,
            default_width=180,
        )
    if name in NATIVE_CONTAINER_WIDGETS:
        direction = "row" if name == "HStack" else "column"
        return _container_box(
            widget,
            path=path,
            x=x,
            y=y,
            style=style,
            direction=direction,
            stylesheet=stylesheet,
            strict_styles=strict_styles,
        )
    return _container_box(
        widget,
        path=path,
        x=x,
        y=y,
        style=style,
        direction="column",
        stylesheet=stylesheet,
        strict_styles=strict_styles,
    )


def _container_box(
    widget: FakeWidget,
    *,
    path: tuple[int, ...],
    x: int,
    y: int,
    style: dict[str, Any],
    direction: str,
    stylesheet: StyleSheet | None,
    strict_styles: bool,
) -> LayoutBox:
    padding = dimension(style, "padding", default=0)
    gap = dimension(style, "gap", default=0)
    scroll_y = dimension(style, "scrollY", default=0) if widget.name == "ScrollView" else 0
    scroll_y = max(scroll_y, 0)

    children: list[LayoutBox] = []
    cursor_x = x + padding
    cursor_y = y + padding - scroll_y
    content_width = 0
    content_height = 0

    for index, child in enumerate(widget.children):
        if index:
            if direction == "row":
                cursor_x += gap
            else:
                cursor_y += gap

        child_box = _layout_widget(
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

    width = content_width + padding * 2
    height = content_height + padding * 2
    width = constrain(width, style, "width", "minWidth", "maxWidth")
    height = constrain(height, style, "height", "minHeight", "maxHeight")
    if widget.name == "ScrollView":
        max_scroll_y = max(0, content_height + padding * 2 - height)
        clamped_scroll_y = clamp_scroll_y(scroll_y, max_scroll_y=max_scroll_y)
        if clamped_scroll_y != scroll_y:
            children = [
                _offset_box_y(child, scroll_y - clamped_scroll_y)
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
        id=optional_string(widget.props.get("id")),
        events=tuple(sorted(widget.events)),
        state=state_items(widget),
        style=style_items(style),
        children=tuple(children),
    )


def _leaf_box(
    widget: FakeWidget,
    *,
    path: tuple[int, ...],
    x: int,
    y: int,
    style: dict[str, Any],
    text: str,
    default_padding: int = 0,
    default_width: int | None = None,
) -> LayoutBox:
    padding = dimension(style, "padding", default=default_padding)
    border_width = dimension(style, "borderWidth", default=0)
    font_size = dimension(style, "fontSize", default=14)
    text_metrics = measure_native_text(text, font_size=font_size)

    width = text_metrics.width + padding * 2 + border_width * 2
    height = text_metrics.height + padding * 2 + border_width * 2
    if default_width is not None:
        width = max(width, default_width)

    width = constrain(width, style, "width", "minWidth", "maxWidth")
    height = constrain(height, style, "height", "minHeight", "maxHeight")

    return LayoutBox(
        path=path,
        name=widget.name,
        x=x,
        y=y,
        width=width,
        height=height,
        id=optional_string(widget.props.get("id")),
        text=text,
        events=tuple(sorted(widget.events)),
        state=state_items(widget),
        style=style_items(style),
    )


def _offset_box_y(box: LayoutBox, delta: int) -> LayoutBox:
    return LayoutBox(
        path=box.path,
        name=box.name,
        x=box.x,
        y=box.y + delta,
        width=box.width,
        height=box.height,
        id=box.id,
        text=box.text,
        events=box.events,
        state=box.state,
        style=box.style,
        children=tuple(_offset_box_y(child, delta) for child in box.children),
    )
