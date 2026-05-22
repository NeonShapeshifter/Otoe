from __future__ import annotations

from typing import Any

from ._native_contracts import LayoutBox, NativeLayout, NativePaint, PaintCommand
from ._native_shared import (
    box_context,
    box_rect,
    color_value,
    dimension,
    intersect_rects,
)
from ._native_text import measure_native_text


def paint_native(
    layout: NativeLayout,
    *,
    background: str = "#ffffff",
    focused_path: tuple[int, ...] | None = None,
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
    commands.extend(_paint_box(layout.root, focused_path=focused_path))
    return NativePaint(
        width=max(layout.root.width, 1),
        height=max(layout.root.height, 1),
        commands=tuple(commands),
    )


def _paint_box(
    box: LayoutBox,
    *,
    clip: tuple[int, int, int, int] | None = None,
    focused_path: tuple[int, ...] | None = None,
) -> list[PaintCommand]:
    style = dict(box.style)
    commands: list[PaintCommand] = []
    rect = _rect_command(box, style, clip=clip)
    if rect is not None:
        commands.append(rect)
    focus_ring = _focus_ring_command(box, style, clip=clip, focused_path=focused_path)
    if focus_ring is not None:
        commands.append(focus_ring)

    if box.text:
        commands.append(_text_command(box, style, clip=clip))

    child_clip = (
        intersect_rects(clip, box_rect(box))
        if box.name == "ScrollView"
        else clip
    )
    for child in box.children:
        commands.extend(_paint_box(child, clip=child_clip, focused_path=focused_path))
    return commands


def _rect_command(
    box: LayoutBox,
    style: dict[str, Any],
    *,
    clip: tuple[int, int, int, int] | None,
) -> PaintCommand | None:
    context = box_context(box)
    fill = _box_fill(box, style)
    stroke = _box_stroke(box, style)
    stroke_width = dimension(
        style,
        "borderWidth",
        default=_default_border_width(box),
        context=context,
    )
    radius = dimension(
        style,
        "borderRadius",
        default=_default_radius(box),
        context=context,
    )

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


def _focus_ring_command(
    box: LayoutBox,
    style: dict[str, Any],
    *,
    clip: tuple[int, int, int, int] | None,
    focused_path: tuple[int, ...] | None,
) -> PaintCommand | None:
    if box.path != focused_path or box.name not in {"Button", "Input"}:
        return None
    if _is_disabled(box):
        return None
    context = box_context(box)
    return PaintCommand(
        kind="rect",
        path=box.path,
        x=box.x - 2,
        y=box.y - 2,
        width=box.width + 4,
        height=box.height + 4,
        stroke="#38bdf8",
        stroke_width=2,
        radius=dimension(
            style,
            "borderRadius",
            default=_default_radius(box),
            context=context,
        )
        + 2,
        clip=clip,
    )


def _text_command(
    box: LayoutBox,
    style: dict[str, Any],
    *,
    clip: tuple[int, int, int, int] | None,
) -> PaintCommand:
    context = box_context(box)
    font_size = dimension(style, "fontSize", default=14, context=context)
    padding = _text_padding(box, style)
    metrics = measure_native_text(box.text or "", font_size=font_size)
    available_width = max(1, box.width - (padding * 2))
    return PaintCommand(
        kind="text",
        path=box.path,
        x=box.x + padding,
        y=box.y + max(padding, (box.height - metrics.height) // 2),
        width=available_width,
        height=metrics.height,
        text=box.text or "",
        color=color_value(
            style.get("color"),
            default=_default_text_color(box),
            context=context,
        ),
        font_size=font_size,
        clip=clip,
    )


def _box_fill(box: LayoutBox, style: dict[str, Any]) -> str | None:
    if "background" in style:
        return color_value(style["background"], context=box_context(box))
    if _is_disabled(box):
        if box.name == "Button":
            return "#e5e7eb"
        if box.name == "Input":
            return "#f3f4f6"
    if box.name == "Button":
        return "#2563eb"
    if box.name == "Input":
        return "#ffffff"
    return None


def _box_stroke(box: LayoutBox, style: dict[str, Any]) -> str | None:
    if "borderColor" in style:
        return color_value(style["borderColor"], context=box_context(box))
    if _is_disabled(box) and box.name in {"Button", "Input"}:
        return "#d1d5db"
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
    if _is_disabled(box):
        if box.name == "Button":
            return "#6b7280"
        if box.name == "Input":
            return "#9ca3af"
    if box.name == "Button":
        return "#ffffff"
    return "#111827"


def _text_padding(box: LayoutBox, style: dict[str, Any]) -> int:
    if "padding" in style:
        return dimension(style, "padding", default=0, context=box_context(box))
    return 8 if box.name in {"Button", "Input"} else 0


def _is_disabled(box: LayoutBox) -> bool:
    return "disabled" in box.state
