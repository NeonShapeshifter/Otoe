from __future__ import annotations

import struct
import zlib
from dataclasses import dataclass
from math import ceil
from pathlib import Path
from typing import Any

from .mount import FakeWidget, MountedNode, mount, root_widget, unmount
from .node import Node
from .style import Size, StyleSheet, Token


class NativeLayoutError(ValueError):
    pass


class NativePaintError(ValueError):
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


@dataclass(frozen=True)
class PaintCommand:
    kind: str
    path: tuple[int, ...]
    x: int
    y: int
    width: int
    height: int
    fill: str | None = None
    stroke: str | None = None
    stroke_width: int = 0
    radius: int = 0
    text: str | None = None
    color: str | None = None
    font_size: int = 14
    clip: tuple[int, int, int, int] | None = None


@dataclass(frozen=True)
class NativePaint:
    width: int
    height: int
    commands: tuple[PaintCommand, ...]

    def by_path(self, path: tuple[int, ...]) -> tuple[PaintCommand, ...]:
        return tuple(command for command in self.commands if command.path == path)


class NativeSurface:
    def __init__(
        self,
        target: Node | FakeWidget | MountedNode,
        *,
        stylesheet: StyleSheet | None = None,
        strict_styles: bool = True,
        background: str = "#ffffff",
    ) -> None:
        self.stylesheet = stylesheet
        self.strict_styles = strict_styles
        self.background = background
        self.frame = 0
        self.focused_path: tuple[int, ...] | None = None
        self._owns_mount = isinstance(target, Node)
        self._mounted = mount(target) if self._owns_mount else None
        self._target: FakeWidget | MountedNode = (
            self._mounted
            if self._mounted is not None
            else _native_surface_target(target)
        )
        self._layout: NativeLayout | None = None
        self._paint: NativePaint | None = None
        self._tree_revision: tuple[Any, ...] | None = None
        self.refresh()
        self.focused_path = self._first_autofocus_path()

    @property
    def mounted(self) -> MountedNode | None:
        return (
            self._mounted
            if self._mounted is not None
            else _mounted_or_none(self._target)
        )

    @property
    def target(self) -> FakeWidget | MountedNode:
        return self._target

    @property
    def layout(self) -> NativeLayout:
        self._ensure_fresh()
        assert self._layout is not None
        return self._layout

    @property
    def paint(self) -> NativePaint:
        self._ensure_fresh()
        assert self._paint is not None
        return self._paint

    @property
    def focused_box(self) -> LayoutBox | None:
        if self.focused_path is None:
            return None
        try:
            return self.layout.by_path(self.focused_path)
        except KeyError:
            return None

    def refresh(self) -> NativePaint:
        self._layout = layout_native(
            self._target,
            stylesheet=self.stylesheet,
            strict_styles=self.strict_styles,
        )
        self._paint = paint_native(self._layout, background=self.background)
        self._tree_revision = _tree_revision(_surface_root_widget(self._target))
        self._sync_focus_after_refresh()
        self.frame += 1
        return self._paint

    def render_png(self, path: str | Path) -> NativePaint:
        paint = self.refresh()
        write_native_png(paint, path)
        return paint

    def hit_test(
        self,
        x: int,
        y: int,
        *,
        event: str = "onClick",
    ) -> LayoutBox | None:
        return hit_test_native(self.layout, x, y, event=event)

    def click(self, x: int, y: int) -> Any:
        focus_hit = self._hit_test_focusable(x, y)
        if focus_hit is not None:
            self.focus(focus_hit.path)
        result = dispatch_native_click(self._target, self.layout, x, y)
        self.refresh()
        return result

    def focus(self, path: tuple[int, ...] | None) -> None:
        if path == self.focused_path:
            return
        if path is not None and not self._is_focusable_path(path):
            raise KeyError(f"No focusable native box exists at path {path!r}.")

        previous_path = self.focused_path
        self.focused_path = path
        if previous_path is not None:
            self._trigger_path_event(previous_path, "onBlur")
        if path is not None:
            self._trigger_path_event(path, "onFocus")
        self.refresh()

    def focus_next(self, *, reverse: bool = False) -> LayoutBox | None:
        focusable = self._focusable_paths()
        if not focusable:
            self.focus(None)
            return None

        if self.focused_path not in focusable:
            next_path = focusable[-1] if reverse else focusable[0]
        else:
            index = focusable.index(self.focused_path)
            step = -1 if reverse else 1
            next_path = focusable[(index + step) % len(focusable)]
        self.focus(next_path)
        return self.focused_box

    def key_down(
        self,
        key: str,
        *,
        shift: bool = False,
        ctrl: bool = False,
        meta: bool = False,
        alt: bool = False,
    ) -> Any:
        if key == "Tab":
            return self.focus_next(reverse=shift)

        if self.focused_path is None:
            self.focus_next()

        result = None
        if self.focused_path is not None:
            result = self._trigger_path_event(self.focused_path, "onKeyDown", key)
            widget = _widget_by_path(
                _surface_root_widget(self._target),
                self.focused_path,
            )
            if widget.name == "Button" and key in {"Enter", " ", "Spacebar"}:
                result = self._trigger_path_event(self.focused_path, "onClick")

        if self._should_send_global_key(key, shift=shift, ctrl=ctrl, meta=meta, alt=alt):
            global_result = self._trigger_global_key_down(
                {
                    "key": key,
                    "ctrlKey": ctrl,
                    "metaKey": meta,
                    "altKey": alt,
                    "shiftKey": shift,
                }
            )
            if global_result is not None:
                result = global_result

        self.refresh()
        return result

    def input_text(self, value: str, *, path: tuple[int, ...] | None = None) -> Any:
        target_path = self.focused_path if path is None else path
        if target_path is None:
            raise KeyError("NativeSurface has no focused input for text entry.")
        widget = _widget_by_path(_surface_root_widget(self._target), target_path)
        if widget.name != "Input" or widget.props.get("disabled"):
            raise KeyError(f"No enabled native input exists at path {target_path!r}.")

        if target_path != self.focused_path:
            self.focus(target_path)
        result = self._trigger_path_event(target_path, "onChange", value)
        self.refresh()
        return result

    def box(self, path: tuple[int, ...]) -> LayoutBox:
        return self.layout.by_path(path)

    def dispose(self) -> None:
        if self._owns_mount and self._mounted is not None:
            unmount(self._mounted)
        self._layout = None
        self._paint = None
        self._tree_revision = None
        self.focused_path = None

    def _ensure_fresh(self) -> None:
        current_revision = _tree_revision(_surface_root_widget(self._target))
        if self._layout is None or self._paint is None or current_revision != self._tree_revision:
            self.refresh()

    def _sync_focus_after_refresh(self) -> None:
        if self.focused_path is None:
            return
        if self._is_focusable_path(self.focused_path):
            return
        self.focused_path = self._first_autofocus_path()

    def _first_autofocus_path(self) -> tuple[int, ...] | None:
        widget = _surface_root_widget(self._target)
        for box in self.layout.boxes:
            candidate = _widget_by_path(widget, box.path)
            if candidate.props.get("autoFocus") and self._is_focusable_widget(candidate):
                return box.path
        return None

    def _focusable_paths(self) -> list[tuple[int, ...]]:
        widget = _surface_root_widget(self._target)
        return [
            box.path
            for box in self.layout.boxes
            if self._is_focusable_widget(_widget_by_path(widget, box.path))
        ]

    def _hit_test_focusable(self, x: int, y: int) -> LayoutBox | None:
        widget = _surface_root_widget(self._target)
        containing = [
            box
            for box in self.layout.boxes
            if box.contains(x, y)
            and _visible_through_scroll_ancestors(self.layout, box, x, y)
            and self._is_focusable_widget(_widget_by_path(widget, box.path))
        ]
        if not containing:
            return None
        return max(containing, key=lambda box: len(box.path))

    def _is_focusable_path(self, path: tuple[int, ...]) -> bool:
        try:
            widget = _widget_by_path(_surface_root_widget(self._target), path)
        except KeyError:
            return False
        return self._is_focusable_widget(widget)

    def _is_focusable_widget(self, widget: FakeWidget) -> bool:
        if widget.props.get("disabled"):
            return False
        return widget.name in {"Button", "Input"}

    def _trigger_path_event(self, path: tuple[int, ...], event: str, *args: Any) -> Any:
        try:
            widget = _widget_by_path(_surface_root_widget(self._target), path)
        except KeyError:
            return None
        if event not in widget.events:
            return None
        return widget.trigger(event, *args)

    def _trigger_global_key_down(self, payload: dict[str, Any]) -> Any:
        for widget in _walk_widgets(_surface_root_widget(self._target)):
            if "onGlobalKeyDown" in widget.events:
                return widget.trigger("onGlobalKeyDown", payload)
        return None

    def _should_send_global_key(
        self,
        key: str,
        *,
        shift: bool,
        ctrl: bool,
        meta: bool,
        alt: bool,
    ) -> bool:
        has_global = any(
            "onGlobalKeyDown" in widget.events
            for widget in _walk_widgets(_surface_root_widget(self._target))
        )
        if not has_global:
            return False
        if ctrl or meta or key == "Escape":
            return True
        if len(key) != 1:
            return False
        if self.focused_path is None:
            return True
        focused = _widget_by_path(_surface_root_widget(self._target), self.focused_path)
        if focused.name == "Input":
            return False
        return True


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


def paint_native(
    layout: NativeLayout,
    *,
    background: str = "#ffffff",
) -> NativePaint:
    commands = [
        PaintCommand(
            kind="rect",
            path=(),
            x=0,
            y=0,
            width=max(layout.root.width, 1),
            height=max(layout.root.height, 1),
            fill=background,
        )
    ]
    commands.extend(_paint_box(layout.root))
    return NativePaint(
        width=max(layout.root.width, 1),
        height=max(layout.root.height, 1),
        commands=tuple(commands),
    )


def write_native_png(paint: NativePaint, path: str | Path) -> None:
    image = _new_image(paint.width, paint.height)
    for command in paint.commands:
        if command.kind == "rect":
            _draw_rounded_rect(image, paint.width, paint.height, command)
        elif command.kind == "text":
            _draw_text_marker(image, paint.width, paint.height, command)
        else:
            raise NativePaintError(f"Unknown paint command kind {command.kind!r}.")
    Path(path).write_bytes(_encode_png(image, paint.width, paint.height))


def render_native_png(
    target: FakeWidget | MountedNode | NativeLayout,
    path: str | Path,
    *,
    stylesheet: StyleSheet | None = None,
    strict_styles: bool = True,
    background: str = "#ffffff",
) -> NativePaint:
    layout = (
        target
        if isinstance(target, NativeLayout)
        else layout_native(target, stylesheet=stylesheet, strict_styles=strict_styles)
    )
    paint = paint_native(layout, background=background)
    write_native_png(paint, path)
    return paint


def hit_test_native(
    layout: NativeLayout,
    x: int,
    y: int,
    *,
    event: str = "onClick",
) -> LayoutBox | None:
    containing = [
        box
        for box in layout.boxes
        if box.contains(x, y) and _visible_through_scroll_ancestors(layout, box, x, y)
    ]
    if not containing:
        return None

    deepest = max(containing, key=lambda box: len(box.path))
    for path in _ancestor_paths(deepest.path):
        box = layout.by_path(path)
        if event in box.events:
            return box
    return None


def dispatch_native_click(
    target: FakeWidget | MountedNode,
    layout: NativeLayout,
    x: int,
    y: int,
) -> Any:
    hit = hit_test_native(layout, x, y, event="onClick")
    if hit is None:
        return None
    widget = root_widget(target) if isinstance(target, MountedNode) else target
    target_widget = _widget_by_path(widget, hit.path)
    if target_widget.props.get("disabled"):
        return None
    return target_widget.trigger("onClick")


def _native_surface_target(
    target: Node | FakeWidget | MountedNode,
) -> FakeWidget | MountedNode:
    if isinstance(target, (FakeWidget, MountedNode)):
        return target
    raise TypeError(
        "NativeSurface target must be a Node, FakeWidget, or MountedNode; "
        f"got {type(target).__name__}."
    )


def _mounted_or_none(target: FakeWidget | MountedNode) -> MountedNode | None:
    return target if isinstance(target, MountedNode) else None


def _surface_root_widget(target: FakeWidget | MountedNode) -> FakeWidget:
    return root_widget(target) if isinstance(target, MountedNode) else target


def _walk_widgets(widget: FakeWidget) -> list[FakeWidget]:
    widgets = [widget]
    for child in widget.children:
        widgets.extend(_walk_widgets(child))
    return widgets


def _tree_revision(widget: FakeWidget) -> tuple[Any, ...]:
    return (
        id(widget),
        widget.revision,
        tuple(_tree_revision(child) for child in widget.children),
    )


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


def _paint_box(
    box: LayoutBox,
    *,
    clip: tuple[int, int, int, int] | None = None,
) -> list[PaintCommand]:
    style = dict(box.style)
    commands: list[PaintCommand] = []
    rect = _rect_command(box, style, clip=clip)
    if rect is not None:
        commands.append(rect)

    if box.text:
        commands.append(_text_command(box, style, clip=clip))

    child_clip = (
        _intersect_rects(clip, _box_rect(box))
        if box.name == "ScrollView"
        else clip
    )
    for child in box.children:
        commands.extend(_paint_box(child, clip=child_clip))
    return commands


def _rect_command(
    box: LayoutBox,
    style: dict[str, Any],
    *,
    clip: tuple[int, int, int, int] | None,
) -> PaintCommand | None:
    fill = _box_fill(box, style)
    stroke = _box_stroke(box, style)
    stroke_width = _dimension(style, "borderWidth", default=_default_border_width(box))
    radius = _dimension(style, "borderRadius", default=_default_radius(box))

    if fill is None and (stroke is None or stroke_width <= 0):
        return None
    return PaintCommand(
        kind="rect",
        path=box.path,
        x=box.x,
        y=box.y,
        width=box.width,
        height=box.height,
        fill=fill,
        stroke=stroke,
        stroke_width=stroke_width,
        radius=radius,
        clip=clip,
    )


def _text_command(
    box: LayoutBox,
    style: dict[str, Any],
    *,
    clip: tuple[int, int, int, int] | None,
) -> PaintCommand:
    font_size = _dimension(style, "fontSize", default=14)
    padding = _text_padding(box, style)
    width = max(1, ceil(len(box.text or "") * font_size * 0.55))
    height = max(1, ceil(font_size * 1.25))
    return PaintCommand(
        kind="text",
        path=box.path,
        x=box.x + padding,
        y=box.y + max(padding, (box.height - height) // 2),
        width=width,
        height=height,
        text=box.text or "",
        color=_color_value(style.get("color"), default=_default_text_color(box)),
        font_size=font_size,
        clip=clip,
    )


def _box_fill(box: LayoutBox, style: dict[str, Any]) -> str | None:
    if "background" in style:
        return _color_value(style["background"])
    if box.name == "Button":
        return "#2563eb"
    if box.name == "Input":
        return "#ffffff"
    return None


def _box_stroke(box: LayoutBox, style: dict[str, Any]) -> str | None:
    if "borderColor" in style:
        return _color_value(style["borderColor"])
    if box.name == "Button":
        return "#1d4ed8"
    if box.name == "Input":
        return "#d1d5db"
    return None


def _default_border_width(box: LayoutBox) -> int:
    return 1 if box.name in {"Button", "Input"} else 0


def _default_radius(box: LayoutBox) -> int:
    return 6 if box.name in {"Button", "Input"} else 0


def _default_text_color(box: LayoutBox) -> str:
    if box.name == "Button":
        return "#ffffff"
    return "#111827"


def _text_padding(box: LayoutBox, style: dict[str, Any]) -> int:
    if "padding" in style:
        return _dimension(style, "padding", default=0)
    return 8 if box.name in {"Button", "Input"} else 0


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


def _color_value(value: Any, *, default: str | None = None) -> str:
    if value is None:
        if default is None:
            raise NativePaintError("Missing required paint color.")
        return default
    if isinstance(value, Token):
        raise NativePaintError(f"Unresolved paint color token {value.name!r}.")
    if not isinstance(value, str):
        raise NativePaintError(f"Native paint expected color string; got {value!r}.")
    _parse_color(value)
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


def _ancestor_paths(path: tuple[int, ...]) -> list[tuple[int, ...]]:
    return [path[:index] for index in range(len(path), -1, -1)]


def _visible_through_scroll_ancestors(
    layout: NativeLayout,
    box: LayoutBox,
    x: int,
    y: int,
) -> bool:
    for path in _ancestor_paths(box.path):
        ancestor = layout.by_path(path)
        if ancestor.name == "ScrollView" and not ancestor.contains(x, y):
            return False
    return True


def _box_rect(box: LayoutBox) -> tuple[int, int, int, int]:
    return (box.x, box.y, max(box.width, 0), max(box.height, 0))


def _intersect_rects(
    first: tuple[int, int, int, int] | None,
    second: tuple[int, int, int, int],
) -> tuple[int, int, int, int]:
    if first is None:
        return second
    x1 = max(first[0], second[0])
    y1 = max(first[1], second[1])
    x2 = min(first[0] + first[2], second[0] + second[2])
    y2 = min(first[1] + first[3], second[1] + second[3])
    return (x1, y1, max(0, x2 - x1), max(0, y2 - y1))


def _widget_by_path(widget: FakeWidget, path: tuple[int, ...]) -> FakeWidget:
    current = widget
    for index in path:
        try:
            current = current.children[index]
        except IndexError as exc:
            raise KeyError(f"No widget exists at path {path!r}.") from exc
    return current


def _optional_string(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def _new_image(width: int, height: int) -> bytearray:
    return bytearray([0, 0, 0, 0] * width * height)


def _draw_rounded_rect(
    image: bytearray,
    image_width: int,
    image_height: int,
    command: PaintCommand,
) -> None:
    fill = _parse_color(command.fill) if command.fill is not None else None
    stroke = _parse_color(command.stroke) if command.stroke is not None else None
    stroke_width = max(command.stroke_width, 0)
    radius = max(command.radius, 0)
    clip_x, clip_y, clip_width, clip_height = _clip_bounds(
        command.clip,
        image_width,
        image_height,
    )
    x1 = max(command.x, 0, clip_x)
    y1 = max(command.y, 0, clip_y)
    x2 = min(command.x + command.width, image_width, clip_x + clip_width)
    y2 = min(command.y + command.height, image_height, clip_y + clip_height)

    for y in range(y1, y2):
        for x in range(x1, x2):
            if not _inside_rounded_rect(
                x,
                y,
                command.x,
                command.y,
                command.width,
                command.height,
                radius,
            ):
                continue
            border_pixel = False
            if stroke is not None and stroke_width:
                border_pixel = not _inside_rounded_rect(
                    x,
                    y,
                    command.x + stroke_width,
                    command.y + stroke_width,
                    command.width - stroke_width * 2,
                    command.height - stroke_width * 2,
                    max(radius - stroke_width, 0),
                )
            if border_pixel:
                _set_pixel(image, image_width, x, y, stroke)
            elif fill is not None:
                _set_pixel(image, image_width, x, y, fill)


def _draw_text_marker(
    image: bytearray,
    image_width: int,
    image_height: int,
    command: PaintCommand,
) -> None:
    color = _parse_color(command.color)
    clip = _clip_bounds(command.clip, image_width, image_height)
    glyph_width = max(2, command.font_size // 3)
    glyph_height = max(6, int(command.font_size * 0.85))
    step = glyph_width + 2
    for index, character in enumerate(command.text or ""):
        if character == " ":
            continue
        x = command.x + index * step
        y = command.y + max(0, (command.height - glyph_height) // 2)
        _draw_text_glyph(
            image,
            image_width,
            image_height,
            x,
            y,
            glyph_width,
            glyph_height,
            color,
            ord(character),
            clip,
        )


def _draw_text_glyph(
    image: bytearray,
    image_width: int,
    image_height: int,
    x: int,
    y: int,
    width: int,
    height: int,
    color: tuple[int, int, int, int],
    seed: int,
    clip: tuple[int, int, int, int],
) -> None:
    clip_x, clip_y, clip_width, clip_height = clip
    for px in range(max(x, 0, clip_x), min(x + width, image_width, clip_x + clip_width)):
        for py in range(max(y, 0, clip_y), min(y + height, image_height, clip_y + clip_height)):
            local_x = px - x
            local_y = py - y
            if (
                py in {y, y + height - 1}
                or px in {x, x + width - 1}
                or (seed + local_x * 3 + local_y * 5) % 11 == 0
            ):
                _set_pixel(image, image_width, px, py, color)


def _clip_bounds(
    clip: tuple[int, int, int, int] | None,
    image_width: int,
    image_height: int,
) -> tuple[int, int, int, int]:
    if clip is None:
        return (0, 0, image_width, image_height)
    x, y, width, height = clip
    x1 = max(x, 0)
    y1 = max(y, 0)
    x2 = min(x + width, image_width)
    y2 = min(y + height, image_height)
    return (x1, y1, max(0, x2 - x1), max(0, y2 - y1))


def _inside_rounded_rect(
    x: int,
    y: int,
    rect_x: int,
    rect_y: int,
    width: int,
    height: int,
    radius: int,
) -> bool:
    if width <= 0 or height <= 0:
        return False
    if radius <= 0:
        return rect_x <= x < rect_x + width and rect_y <= y < rect_y + height
    radius = min(radius, width // 2, height // 2)
    left = rect_x + radius
    right = rect_x + width - radius - 1
    top = rect_y + radius
    bottom = rect_y + height - radius - 1
    if left <= x <= right or top <= y <= bottom:
        return True
    corner_x = left if x < left else right
    corner_y = top if y < top else bottom
    return (x - corner_x) ** 2 + (y - corner_y) ** 2 <= radius**2


def _set_pixel(
    image: bytearray,
    image_width: int,
    x: int,
    y: int,
    color: tuple[int, int, int, int],
) -> None:
    offset = (y * image_width + x) * 4
    image[offset : offset + 4] = bytes(color)


def _encode_png(image: bytearray, width: int, height: int) -> bytes:
    rows = []
    stride = width * 4
    for y in range(height):
        start = y * stride
        rows.append(b"\x00" + bytes(image[start : start + stride]))
    raw = b"".join(rows)
    return b"".join(
        [
            b"\x89PNG\r\n\x1a\n",
            _png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)),
            _png_chunk(b"IDAT", zlib.compress(raw)),
            _png_chunk(b"IEND", b""),
        ]
    )


def _png_chunk(kind: bytes, data: bytes) -> bytes:
    checksum = zlib.crc32(kind)
    checksum = zlib.crc32(data, checksum)
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", checksum)


def _parse_color(value: str | None) -> tuple[int, int, int, int]:
    if value is None:
        raise NativePaintError("Missing paint color.")
    normalized = value.strip().lower()
    named = {
        "black": "#000000",
        "blue": "#0000ff",
        "green": "#008000",
        "red": "#ff0000",
        "transparent": "#00000000",
        "white": "#ffffff",
    }
    normalized = named.get(normalized, normalized)
    if normalized.startswith("#") and len(normalized) == 4:
        return (
            int(normalized[1] * 2, 16),
            int(normalized[2] * 2, 16),
            int(normalized[3] * 2, 16),
            255,
        )
    if normalized.startswith("#") and len(normalized) == 7:
        return (
            int(normalized[1:3], 16),
            int(normalized[3:5], 16),
            int(normalized[5:7], 16),
            255,
        )
    if normalized.startswith("#") and len(normalized) == 9:
        return (
            int(normalized[1:3], 16),
            int(normalized[3:5], 16),
            int(normalized[5:7], 16),
            int(normalized[7:9], 16),
        )
    raise NativePaintError(f"Unsupported paint color {value!r}.")
