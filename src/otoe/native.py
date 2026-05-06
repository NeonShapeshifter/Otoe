from __future__ import annotations

from dataclasses import dataclass
from math import ceil
from typing import Any

from .mount import FakeWidget, MountedNode, root_widget
from .style import Size, StyleSheet, Token


class NativeLayoutError(ValueError):
    pass


@dataclass(frozen=True)
class LayoutBox:
    path: tuple[int, ...]
    name: str
    x: int
    y: int
    width: int
    height: int
    id: str | None = None
    text: str | None = None
    events: tuple[str, ...] = ()
    style: tuple[tuple[str, Any], ...] = ()
    children: tuple["LayoutBox", ...] = ()

    def contains(self, x: int, y: int) -> bool:
        return self.x <= x < self.x + self.width and self.y <= y < self.y + self.height


@dataclass(frozen=True)
class NativeLayout:
    root: LayoutBox
    boxes: tuple[LayoutBox, ...]

    def by_path(self, path: tuple[int, ...]) -> LayoutBox:
        for box in self.boxes:
            if box.path == path:
                return box
        raise KeyError(f"No layout box exists at path {path!r}.")


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
    return NativeLayout(root=root, boxes=tuple(_flatten(root)))


def _layout_widget(
    widget: FakeWidget,
    *,
    path: tuple[int, ...],
    x: int,
    y: int,
    stylesheet: StyleSheet | None,
    strict_styles: bool,
) -> LayoutBox:
    style = _resolve_style(widget, stylesheet, strict_styles)
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
    if name in {"HStack", "VStack", "Panel", "ScrollView", "FocusScope", "ShortcutScope"}:
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
    if name in {"Show", "For"}:
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
    padding = _dimension(style, "padding", default=0)
    gap = _dimension(style, "gap", default=0)

    children: list[LayoutBox] = []
    cursor_x = x + padding
    cursor_y = y + padding
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
    width = _constrain(width, style, "width", "minWidth", "maxWidth")
    height = _constrain(height, style, "height", "minHeight", "maxHeight")

    return LayoutBox(
        path=path,
        name=widget.name,
        x=x,
        y=y,
        width=width,
        height=height,
        id=_optional_string(widget.props.get("id")),
        events=tuple(sorted(widget.events)),
        style=_style_items(style),
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
    padding = _dimension(style, "padding", default=default_padding)
    border_width = _dimension(style, "borderWidth", default=0)
    font_size = _dimension(style, "fontSize", default=14)
    text_width = ceil(len(text) * font_size * 0.55)
    text_height = ceil(font_size * 1.25)

    width = text_width + padding * 2 + border_width * 2
    height = text_height + padding * 2 + border_width * 2
    if default_width is not None:
        width = max(width, default_width)

    width = _constrain(width, style, "width", "minWidth", "maxWidth")
    height = _constrain(height, style, "height", "minHeight", "maxHeight")

    return LayoutBox(
        path=path,
        name=widget.name,
        x=x,
        y=y,
        width=width,
        height=height,
        id=_optional_string(widget.props.get("id")),
        text=text,
        events=tuple(sorted(widget.events)),
        style=_style_items(style),
    )


def _resolve_style(
    widget: FakeWidget,
    stylesheet: StyleSheet | None,
    strict_styles: bool,
) -> dict[str, Any]:
    style = {}
    if stylesheet is not None:
        style.update(
            stylesheet.resolve(
                _optional_string(widget.props.get("className")),
                strict=strict_styles,
            )
        )
    for prop in ("gap", "padding"):
        if prop in widget.props:
            style[prop] = widget.props[prop]
    if "color" in widget.props:
        style["color"] = widget.props["color"]
    return _resolve_tokens(style, stylesheet.tokens if stylesheet is not None else {})


def _resolve_tokens(style: dict[str, Any], tokens: dict[str, Any]) -> dict[str, Any]:
    return {name: _resolve_token(value, tokens) for name, value in style.items()}


def _resolve_token(value: Any, tokens: dict[str, Any]) -> Any:
    if isinstance(value, Token):
        if value.name not in tokens:
            return value
        return _resolve_token(tokens[value.name], tokens)
    return value


def _dimension(style: dict[str, Any], name: str, *, default: int) -> int:
    if name not in style:
        return default
    value = style[name]
    if isinstance(value, Size):
        if value.unit != "px":
            raise NativeLayoutError(
                f"Native layout only supports px dimensions; {name} used {value.unit!r}."
            )
        return int(ceil(value.value))
    if isinstance(value, (int, float)):
        return int(ceil(value))
    raise NativeLayoutError(f"Native layout expected numeric {name}; got {value!r}.")


def _constrain(
    value: int,
    style: dict[str, Any],
    exact_name: str,
    min_name: str,
    max_name: str,
) -> int:
    if exact_name in style:
        value = _dimension(style, exact_name, default=value)
    if min_name in style:
        value = max(value, _dimension(style, min_name, default=value))
    if max_name in style:
        value = min(value, _dimension(style, max_name, default=value))
    return value


def _style_items(style: dict[str, Any]) -> tuple[tuple[str, Any], ...]:
    return tuple(sorted(style.items()))


def _flatten(box: LayoutBox) -> list[LayoutBox]:
    boxes = [box]
    for child in box.children:
        boxes.extend(_flatten(child))
    return boxes


def _optional_string(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)
