from __future__ import annotations

from typing import Any

from otoe import NativeLayout, NativePaint, PaintCommand

from .backend_candidate_renderer_utils import (
    _candidate_intersect_rects,
    _candidate_style_color,
    _candidate_style_dimension,
)


def _paint_candidate_layout(
    layout: NativeLayout,
    *,
    background: str,
    focused_path: tuple[int, ...] | None,
) -> NativePaint:
    commands = [
        PaintCommand(
            kind="rect",
            path=(),
            x=0,
            y=0,
            width=max(layout.root.width, 1),
            height=max(layout.root.height, 1),
            fill=_candidate_style_color(background, default="#ffffff"),
            context="PaintOnlyRendererCandidate surface",
        )
    ]
    commands.extend(
        _paint_candidate_box(
            layout.root,
            focused_path=focused_path,
            clip=None,
        )
    )
    return NativePaint(
        width=max(layout.root.width, 1),
        height=max(layout.root.height, 1),
        commands=tuple(commands),
    )


def _paint_candidate_box(
    box: Any,
    *,
    focused_path: tuple[int, ...] | None,
    clip: tuple[int, int, int, int] | None,
) -> list[PaintCommand]:
    style = dict(box.style)
    commands: list[PaintCommand] = []
    rect = _paint_candidate_rect(box, style, clip=clip)
    if rect is not None:
        commands.append(rect)
    focus_ring = _paint_candidate_focus_ring(
        box,
        style,
        focused_path=focused_path,
        clip=clip,
    )
    if focus_ring is not None:
        commands.append(focus_ring)
    if box.text:
        commands.append(_paint_candidate_text(box, style, clip=clip))

    child_clip = (
        _candidate_intersect_rects(clip, (box.x, box.y, box.width, box.height))
        if box.name == "ScrollView"
        else clip
    )
    for child in box.children:
        commands.extend(
            _paint_candidate_box(
                child,
                focused_path=focused_path,
                clip=child_clip,
            )
        )
    return commands


def _paint_candidate_rect(
    box: Any,
    style: dict[str, Any],
    *,
    clip: tuple[int, int, int, int] | None,
) -> PaintCommand | None:
    fill = _paint_candidate_fill(box, style)
    stroke = _paint_candidate_stroke(box, style)
    stroke_width = _candidate_style_dimension(
        style,
        "borderWidth",
        default=1 if box.name in {"Button", "Input"} else 0,
    )
    radius = _candidate_style_dimension(
        style,
        "borderRadius",
        default=8 if box.name in {"Button", "Input"} else 0,
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
        context=f"PaintOnlyRendererCandidate {box.name}",
    )


def _paint_candidate_focus_ring(
    box: Any,
    style: dict[str, Any],
    *,
    focused_path: tuple[int, ...] | None,
    clip: tuple[int, int, int, int] | None,
) -> PaintCommand | None:
    if box.path != focused_path or box.name not in {"Button", "Input"}:
        return None
    if "disabled" in box.state:
        return None
    return PaintCommand(
        kind="rect",
        path=box.path,
        x=box.x - 2,
        y=box.y - 2,
        width=box.width + 4,
        height=box.height + 4,
        stroke="#38bdf8",
        stroke_width=2,
        radius=_candidate_style_dimension(
            style,
            "borderRadius",
            default=8 if box.name in {"Button", "Input"} else 0,
        )
        + 2,
        clip=clip,
        context=f"PaintOnlyRendererCandidate {box.name}",
    )


def _paint_candidate_text(
    box: Any,
    style: dict[str, Any],
    *,
    clip: tuple[int, int, int, int] | None,
) -> PaintCommand:
    font_size = _candidate_style_dimension(style, "fontSize", default=14)
    padding = _candidate_text_padding(box)
    height = max(8, int(font_size * 0.85))
    width = max(1, box.width - (padding * 2))
    text = _candidate_text_for_width(
        box.text or "",
        width=width,
        font_size=font_size,
        style=style,
    )
    return PaintCommand(
        kind="text",
        path=box.path,
        x=box.x + padding,
        y=box.y + max(0, (box.height - height) // 2),
        width=width,
        height=height,
        text=text,
        color=_paint_candidate_text_color(box, style),
        font_size=font_size,
        clip=_candidate_text_clip(box, style, padding=padding, clip=clip),
        context=f"PaintOnlyRendererCandidate {box.name}",
    )


def _candidate_text_for_width(
    text: str,
    *,
    width: int,
    font_size: int,
    style: dict[str, Any],
) -> str:
    if style.get("textOverflow") != "ellipsis":
        return text
    if _candidate_text_width(text, font_size=font_size) <= width:
        return text
    ellipsis = "..."
    if _candidate_text_width(ellipsis, font_size=font_size) > width:
        return ""
    candidate = text
    while candidate:
        candidate = candidate[:-1]
        rendered = candidate.rstrip() + ellipsis
        if _candidate_text_width(rendered, font_size=font_size) <= width:
            return rendered
    return ellipsis


def _candidate_text_width(text: str, *, font_size: int) -> int:
    return max(1, int(len(text) * font_size * 0.55))


def _candidate_text_clip(
    box: Any,
    style: dict[str, Any],
    *,
    padding: int,
    clip: tuple[int, int, int, int] | None,
) -> tuple[int, int, int, int] | None:
    if style.get("overflow") != "hidden":
        return clip
    return _candidate_intersect_rects(
        clip,
        (
            box.x + padding,
            box.y + padding,
            max(1, box.width - padding * 2),
            max(1, box.height - padding * 2),
        ),
    )


def _paint_candidate_fill(box: Any, style: dict[str, Any]) -> str | None:
    if "background" in style:
        return _candidate_style_color(style["background"], default="#ffffff")
    if "disabled" in box.state:
        if box.name == "Button":
            return "#d1d5db"
        if box.name == "Input":
            return "#f3f4f6"
    if box.name == "Button":
        return "#1f2937"
    if box.name == "Input":
        return "#ffffff"
    return None


def _paint_candidate_stroke(box: Any, style: dict[str, Any]) -> str | None:
    if "borderColor" in style:
        return _candidate_style_color(style["borderColor"], default="#d1d5db")
    if box.name == "Button":
        return "#111827"
    if box.name == "Input":
        return "#94a3b8"
    return None


def _paint_candidate_text_color(box: Any, style: dict[str, Any]) -> str:
    if "color" in style:
        return _candidate_style_color(style["color"], default="#111827")
    if "disabled" in box.state:
        return "#64748b"
    if box.name == "Button":
        return "#ffffff"
    return "#111827"


def _candidate_text_padding(box: Any) -> int:
    if box.name in {"Button", "Input"}:
        return min(8, max(0, box.width // 4))
    return 0
