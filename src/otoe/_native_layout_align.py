from __future__ import annotations

from typing import Any

from ._native_contracts import LayoutBox, NativeLayoutError


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


def align_stack_children(
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
            offset_box(
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
        offset_box(
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


def validate_alignment_support(
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


def offset_box(box: LayoutBox, *, dx: int = 0, dy: int = 0) -> LayoutBox:
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
        children=tuple(offset_box(child, dx=dx, dy=dy) for child in box.children),
    )


def offset_box_y(box: LayoutBox, delta: int) -> LayoutBox:
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
        children=tuple(offset_box_y(child, delta) for child in box.children),
    )


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
