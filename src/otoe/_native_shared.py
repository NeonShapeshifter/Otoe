from __future__ import annotations

from math import ceil
from typing import Any

from ._native_contracts import LayoutBox, NativeLayout, NativeLayoutError, NativePaintError
from .mount import FakeWidget, MountedNode, root_widget
from .node import Node
from .style import Size, StyleSheet, Token, UnknownStyleClassError


NATIVE_LAYOUT_STYLE_PROPERTIES = frozenset(
    {
        "borderWidth",
        "fontSize",
        "gap",
        "height",
        "alignItems",
        "justifyContent",
        "maxHeight",
        "maxWidth",
        "minHeight",
        "minWidth",
        "padding",
        "scrollY",
        "width",
    }
)
NATIVE_PAINT_STYLE_PROPERTIES = frozenset(
    {
        "background",
        "borderColor",
        "borderRadius",
        "borderWidth",
        "color",
        "fontSize",
    }
)
NATIVE_IGNORED_STYLE_PROPERTIES = frozenset(
    {
        "display",
        "fontWeight",
        "margin",
        "opacity",
    }
)
NATIVE_STYLE_SUPPORT = {
    **{name: "layout" for name in NATIVE_LAYOUT_STYLE_PROPERTIES},
    **{name: "paint" for name in NATIVE_PAINT_STYLE_PROPERTIES},
    **{name: "ignored" for name in NATIVE_IGNORED_STYLE_PROPERTIES},
}
for _name in NATIVE_LAYOUT_STYLE_PROPERTIES & NATIVE_PAINT_STYLE_PROPERTIES:
    NATIVE_STYLE_SUPPORT[_name] = "layout+paint"

NATIVE_TEXT_WIDGETS = frozenset({"Text"})
NATIVE_CONTROL_WIDGETS = frozenset({"Button", "Input"})
NATIVE_CONTAINER_WIDGETS = frozenset(
    {
        "FocusScope",
        "For",
        "HStack",
        "Panel",
        "ScrollView",
        "ShortcutScope",
        "Show",
        "VStack",
    }
)
NATIVE_WIDGET_SUPPORT = {
    **{name: "text" for name in NATIVE_TEXT_WIDGETS},
    **{name: "control" for name in NATIVE_CONTROL_WIDGETS},
    **{name: "container" for name in NATIVE_CONTAINER_WIDGETS},
}
NATIVE_INPUT_SUPPORT = {
    "click": "supported",
    "focus": "supported",
    "input_text": "supported",
    "key_down": "supported",
    "key_input": "supported",
    "shortcut": "supported",
    "tab_focus": "supported",
    "wheel": "supported",
    "caret_movement": "deferred",
    "drag": "deferred",
    "gesture": "deferred",
    "ime": "deferred",
    "inertial_scroll": "deferred",
    "pointer_move": "deferred",
    "text_selection": "deferred",
    "uncontrolled_input": "deferred",
}


def native_surface_target(
    target: Node | FakeWidget | MountedNode,
) -> FakeWidget | MountedNode:
    if isinstance(target, (FakeWidget, MountedNode)):
        return target
    raise TypeError(
        "NativeSurface target must be a Node, FakeWidget, or MountedNode; "
        f"got {type(target).__name__}."
    )


def mounted_or_none(target: FakeWidget | MountedNode) -> MountedNode | None:
    return target if isinstance(target, MountedNode) else None


def surface_root_widget(target: FakeWidget | MountedNode) -> FakeWidget:
    return root_widget(target) if isinstance(target, MountedNode) else target


def walk_widgets(widget: FakeWidget) -> list[FakeWidget]:
    widgets = [widget]
    for child in widget.children:
        widgets.extend(walk_widgets(child))
    return widgets


def tree_revision(widget: FakeWidget) -> tuple[Any, ...]:
    return (
        id(widget),
        widget.revision,
        tuple(tree_revision(child) for child in widget.children),
    )


def resolve_style(
    widget: FakeWidget,
    stylesheet: StyleSheet | None,
    strict_styles: bool,
) -> dict[str, Any]:
    style = {}
    context = widget_context(widget)
    if stylesheet is not None:
        try:
            style.update(
                stylesheet.resolve(
                    optional_string(widget.props.get("className")),
                    strict=strict_styles,
                )
            )
        except UnknownStyleClassError as exc:
            raise NativeLayoutError(_contextual_message(context, str(exc))) from exc
    for prop in ("gap", "padding", "scrollY"):
        if prop in widget.props:
            style[prop] = widget.props[prop]
    if "color" in widget.props:
        style["color"] = widget.props["color"]
    _validate_native_style_keys(style, context=context)
    return resolve_tokens(style, stylesheet.tokens if stylesheet is not None else {})


def native_style_support(name: str) -> str | None:
    return NATIVE_STYLE_SUPPORT.get(name)


def native_widget_support(name: str) -> str:
    return NATIVE_WIDGET_SUPPORT.get(name, "fallback-container")


def native_input_support(name: str) -> str | None:
    return NATIVE_INPUT_SUPPORT.get(name)


def _validate_native_style_keys(style: dict[str, Any], *, context: str | None) -> None:
    unsupported = sorted(name for name in style if name not in NATIVE_STYLE_SUPPORT)
    if unsupported:
        names = ", ".join(repr(name) for name in unsupported)
        raise NativeLayoutError(
            _contextual_message(
                context,
                f"Unsupported native style properties: {names}.",
            )
        )


def resolve_tokens(style: dict[str, Any], tokens: dict[str, Any]) -> dict[str, Any]:
    return {name: resolve_token(value, tokens) for name, value in style.items()}


def resolve_token(value: Any, tokens: dict[str, Any]) -> Any:
    if isinstance(value, Token):
        if value.name not in tokens:
            return value
        return resolve_token(tokens[value.name], tokens)
    return value


def color_value(
    value: Any,
    *,
    default: str | None = None,
    context: str | None = None,
) -> str:
    if value is None:
        if default is None:
            raise NativePaintError(
                _contextual_message(context, "Missing required paint color.")
            )
        return default
    if isinstance(value, Token):
        raise NativePaintError(
            _contextual_message(
                context,
                f"Unresolved paint color token {value.name!r}.",
            )
        )
    if not isinstance(value, str):
        raise NativePaintError(
            _contextual_message(
                context,
                f"Native paint expected color string; got {value!r}.",
            )
        )
    try:
        parse_color(value)
    except NativePaintError as exc:
        raise NativePaintError(_contextual_message(context, str(exc))) from exc
    return value


def dimension(
    style: dict[str, Any],
    name: str,
    *,
    default: int,
    context: str | None = None,
    allow_negative: bool = False,
) -> int:
    if name not in style:
        return default
    value = style[name]
    if isinstance(value, Size):
        if value.unit != "px":
            raise NativeLayoutError(
                _contextual_message(
                    context,
                    f"Native layout only supports px dimensions; {name} used {value.unit!r}.",
                )
            )
        resolved = int(ceil(value.value))
    elif isinstance(value, (int, float)):
        resolved = int(ceil(value))
    else:
        raise NativeLayoutError(
            _contextual_message(
                context,
                f"Native layout expected numeric {name}; got {value!r}.",
            )
        )
    if resolved < 0 and not allow_negative:
        raise NativeLayoutError(
            _contextual_message(
                context,
                f"Native layout expected non-negative {name}; got {resolved}.",
            )
        )
    return resolved


def constrain(
    value: int,
    style: dict[str, Any],
    exact_name: str,
    min_name: str,
    max_name: str,
    *,
    context: str | None = None,
) -> int:
    if exact_name in style:
        value = dimension(style, exact_name, default=value, context=context)
    if max_name in style:
        value = min(value, dimension(style, max_name, default=value, context=context))
    if min_name in style:
        value = max(value, dimension(style, min_name, default=value, context=context))
    return value


def widget_context(widget: FakeWidget) -> str:
    component_stack = getattr(widget, "component_stack", ())
    if not component_stack:
        return widget.name
    return " > ".join((*component_stack, widget.name))


def box_context(box: LayoutBox) -> str:
    return box.context or box.name


def _contextual_message(context: str | None, message: str) -> str:
    if context is None:
        return message
    return f"{context}: {message}"


def style_items(style: dict[str, Any]) -> tuple[tuple[str, Any], ...]:
    return tuple(sorted(style.items()))


def state_items(widget: FakeWidget) -> tuple[str, ...]:
    state = []
    if widget.props.get("disabled"):
        state.append("disabled")
    return tuple(state)


def flatten(box: LayoutBox) -> list[LayoutBox]:
    boxes = [box]
    for child in box.children:
        boxes.extend(flatten(child))
    return boxes


def ancestor_paths(path: tuple[int, ...]) -> list[tuple[int, ...]]:
    return [path[:index] for index in range(len(path), -1, -1)]


def visible_through_scroll_ancestors(
    layout: NativeLayout,
    box: LayoutBox,
    x: int,
    y: int,
) -> bool:
    for path in ancestor_paths(box.path):
        ancestor = layout.by_path(path)
        if ancestor.name == "ScrollView" and not ancestor.contains(x, y):
            return False
    return True


def max_scroll_y(scroll_box: LayoutBox) -> int:
    style = dict(scroll_box.style)
    context = box_context(scroll_box)
    padding = dimension(style, "padding", default=0, context=context)
    scroll_y = dimension(style, "scrollY", default=0, context=context)
    if not scroll_box.children:
        return 0

    content_top = scroll_box.y + padding - scroll_y
    content_bottom = max(child.y + child.height for child in scroll_box.children)
    content_height = max(0, content_bottom - content_top)
    total_height = content_height + padding * 2
    return max(0, total_height - scroll_box.height)


def scroll_y(widget: FakeWidget) -> int:
    value = widget.props.get("scrollY", 0)
    if isinstance(value, (int, float)):
        return max(0, int(ceil(value)))
    raise NativeLayoutError(
        _contextual_message(
            widget_context(widget),
            f"Native layout expected numeric scrollY; got {value!r}.",
        )
    )


def clamp_scroll_y(value: int, *, max_scroll_y: int) -> int:
    return min(max(value, 0), max_scroll_y)


def box_rect(box: LayoutBox) -> tuple[int, int, int, int]:
    return (box.x, box.y, max(box.width, 0), max(box.height, 0))


def intersect_rects(
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


def widget_by_path(widget: FakeWidget, path: tuple[int, ...]) -> FakeWidget:
    current = widget
    for index in path:
        try:
            current = current.children[index]
        except IndexError as exc:
            raise KeyError(f"No widget exists at path {path!r}.") from exc
    return current


def optional_string(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def parse_color(value: str | None) -> tuple[int, int, int, int]:
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
