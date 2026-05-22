from __future__ import annotations

from typing import Any

from ._native_contracts import LayoutBox, NativeLayout, NativeLayoutError
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
    widget_context,
)
from ._native_text import measure_native_text
from .mount import FakeWidget, MountedNode, root_widget
from .style import StyleSheet


_ALIGN_ITEMS_VALUES = frozenset(
    {"center", "end", "flex-end", "flex-start", "start", "stretch"}
)
_JUSTIFY_CONTENT_VALUES = frozenset(
    {
        "center",
        "end",
        "flex-end",
        "flex-start",
        "space-around",
        "space-between",
        "space-evenly",
        "start",
    }
)


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
    context = widget_context(widget)
    _validate_alignment_support(name, style, context)

    if name == "Text":
        return _leaf_box(
            widget,
            path=path,
            x=x,
            y=y,
            style=style,
            context=context,
            text=str(widget.props.get("content", "")),
        )
    if name == "Button":
        return _leaf_box(
            widget,
            path=path,
            x=x,
            y=y,
            style=style,
            context=context,
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
            context=context,
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
            context=context,
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
        context=context,
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
    context: str,
    direction: str,
    stylesheet: StyleSheet | None,
    strict_styles: bool,
) -> LayoutBox:
    padding = dimension(style, "padding", default=0, context=context)
    gap = dimension(style, "gap", default=0, context=context)
    scroll_y = (
        dimension(style, "scrollY", default=0, context=context, allow_negative=True)
        if widget.name == "ScrollView"
        else 0
    )
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
    width = constrain(width, style, "width", "minWidth", "maxWidth", context=context)
    height = constrain(height, style, "height", "minHeight", "maxHeight", context=context)
    if widget.name in {"HStack", "VStack"}:
        children = _align_stack_children(
            children,
            direction=direction,
            style=style,
            x=x,
            y=y,
            width=width,
            height=height,
            padding=padding,
            content_width=content_width,
            content_height=content_height,
        )
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
        context=context,
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
    context: str,
    text: str,
    default_padding: int = 0,
    default_width: int | None = None,
) -> LayoutBox:
    padding = dimension(style, "padding", default=default_padding, context=context)
    border_width = dimension(style, "borderWidth", default=0, context=context)
    font_size = dimension(style, "fontSize", default=14, context=context)
    text_metrics = measure_native_text(text, font_size=font_size)

    width = text_metrics.width + padding * 2 + border_width * 2
    height = text_metrics.height + padding * 2 + border_width * 2
    if default_width is not None:
        width = max(width, default_width)

    width = constrain(width, style, "width", "minWidth", "maxWidth", context=context)
    height = constrain(height, style, "height", "minHeight", "maxHeight", context=context)

    return LayoutBox(
        path=path,
        name=widget.name,
        x=x,
        y=y,
        width=width,
        height=height,
        id=optional_string(widget.props.get("id")),
        context=context,
        text=text,
        events=tuple(sorted(widget.events)),
        state=state_items(widget),
        style=style_items(style),
    )


def _align_stack_children(
    children: list[LayoutBox],
    *,
    direction: str,
    style: dict[str, Any],
    x: int,
    y: int,
    width: int,
    height: int,
    padding: int,
    content_width: int,
    content_height: int,
) -> list[LayoutBox]:
    align_items = style.get("alignItems")
    justify_content = style.get("justifyContent")
    if align_items is None and justify_content is None:
        return children
    if not children:
        return children

    inner_width = max(0, width - padding * 2)
    inner_height = max(0, height - padding * 2)

    if direction == "row":
        main_offsets = _main_offsets(
            children,
            justify_content=justify_content,
            available=inner_width,
            content=content_width,
        )
        return [
            _offset_box(
                _stretch_box(child, height=inner_height)
                if align_items == "stretch"
                else child,
                dx=main_offsets[index],
                dy=_cross_offset(
                    align_items,
                    available=inner_height,
                    size=inner_height if align_items == "stretch" else child.height,
                ),
            )
            for index, child in enumerate(children)
        ]

    main_offsets = _main_offsets(
        children,
        justify_content=justify_content,
        available=inner_height,
        content=content_height,
    )
    return [
        _offset_box(
            _stretch_box(child, width=inner_width)
            if align_items == "stretch"
            else child,
            dx=_cross_offset(
                align_items,
                available=inner_width,
                size=inner_width if align_items == "stretch" else child.width,
            ),
            dy=main_offsets[index],
        )
        for index, child in enumerate(children)
    ]


def _main_offsets(
    children: list[LayoutBox],
    *,
    justify_content: Any,
    available: int,
    content: int,
) -> list[int]:
    extra = max(0, available - content)
    if justify_content == "center":
        return [extra // 2 for _ in children]
    if justify_content in {"end", "flex-end"}:
        return [extra for _ in children]
    if justify_content == "space-between" and len(children) > 1:
        gaps = len(children) - 1
        return [(extra * index) // gaps for index, _ in enumerate(children)]
    if justify_content == "space-around":
        count = len(children)
        return [
            (extra * ((index * 2) + 1)) // (count * 2)
            for index, _ in enumerate(children)
        ]
    if justify_content == "space-evenly":
        count = len(children)
        return [
            (extra * (index + 1)) // (count + 1)
            for index, _ in enumerate(children)
        ]
    return [0 for _ in children]


def _cross_offset(value: Any, *, available: int, size: int) -> int:
    extra = max(0, available - size)
    if value == "center":
        return extra // 2
    if value in {"end", "flex-end"}:
        return extra
    return 0


def _validate_alignment_support(
    widget_name: str,
    style: dict[str, Any],
    context: str,
) -> None:
    alignment_props = [
        name for name in ("alignItems", "justifyContent") if name in style
    ]
    if not alignment_props:
        return
    if widget_name not in {"HStack", "VStack"}:
        names = ", ".join(alignment_props)
        raise NativeLayoutError(
            f"{context}: Native layout supports {names} only on HStack and VStack."
        )
    allowed_values = {
        "alignItems": _ALIGN_ITEMS_VALUES,
        "justifyContent": _JUSTIFY_CONTENT_VALUES,
    }
    for name in alignment_props:
        value = style[name]
        if value not in allowed_values[name]:
            supported = ", ".join(repr(item) for item in sorted(allowed_values[name]))
            raise NativeLayoutError(
                f"{context}: Native layout does not support {name}={value!r}; "
                f"supported values are {supported}."
            )


def _offset_box(box: LayoutBox, *, dx: int = 0, dy: int = 0) -> LayoutBox:
    return LayoutBox(
        path=box.path,
        name=box.name,
        x=box.x + dx,
        y=box.y + dy,
        width=box.width,
        height=box.height,
        id=box.id,
        context=box.context,
        text=box.text,
        events=box.events,
        state=box.state,
        style=box.style,
        children=tuple(_offset_box(child, dx=dx, dy=dy) for child in box.children),
    )


def _stretch_box(
    box: LayoutBox,
    *,
    width: int | None = None,
    height: int | None = None,
) -> LayoutBox:
    return LayoutBox(
        path=box.path,
        name=box.name,
        x=box.x,
        y=box.y,
        width=max(0, width) if width is not None else box.width,
        height=max(0, height) if height is not None else box.height,
        id=box.id,
        context=box.context,
        text=box.text,
        events=box.events,
        state=box.state,
        style=box.style,
        children=box.children,
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
        context=box.context,
        text=box.text,
        events=box.events,
        state=box.state,
        style=box.style,
        children=tuple(_offset_box_y(child, delta) for child in box.children),
    )
