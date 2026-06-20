"""Experimental internal display-list boundary for native backend spikes."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING

from ._native_contracts import NativeLayout, NativePaint, PaintCommand
from ._native_layout import layout_native
from ._native_paint import paint_native
from .mount import FakeWidget, MountedNode
from .style import StyleSheet

if TYPE_CHECKING:
    from ._native_backend import NativeRendererBackend


DISPLAY_LIST_SCHEMA_VERSION = 0
DISPLAY_LIST_FORMAT = "otoe-display-list"

DisplayListTarget = FakeWidget | MountedNode | NativeLayout | NativePaint


class DisplayListError(ValueError):
    pass


@dataclass(frozen=True)
class DisplayListCommand:
    op: str
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
    font_size: int | None = None
    clip: tuple[int, int, int, int] | None = None
    context: str | None = None

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "op": self.op,
            "path": list(self.path),
            "box": [self.x, self.y, self.width, self.height],
        }
        if self.clip is not None:
            payload["clip"] = list(self.clip)
        if self.fill is not None:
            payload["fill"] = self.fill
        if self.stroke is not None:
            payload["stroke"] = self.stroke
        if self.stroke_width:
            payload["strokeWidth"] = self.stroke_width
        if self.radius:
            payload["radius"] = self.radius
        if self.text is not None:
            payload["text"] = self.text
        if self.color is not None:
            payload["color"] = self.color
        if self.font_size is not None:
            payload["fontSize"] = self.font_size
        if self.context is not None:
            payload["context"] = self.context
        return payload


@dataclass(frozen=True)
class DisplayList:
    width: int
    height: int
    commands: tuple[DisplayListCommand, ...]
    schema_version: int = DISPLAY_LIST_SCHEMA_VERSION
    format: str = DISPLAY_LIST_FORMAT

    def to_dict(self) -> dict[str, object]:
        return display_list_to_dict(self)

    def to_json(self, *, indent: int | None = None) -> str:
        return display_list_to_json(self, indent=indent)


def display_list_from_paint(paint: NativePaint) -> DisplayList:
    return DisplayList(
        width=paint.width,
        height=paint.height,
        commands=tuple(_command_from_paint(command) for command in paint.commands),
    )


def export_native_display_list(
    target: DisplayListTarget,
    *,
    stylesheet: StyleSheet | None = None,
    strict_styles: bool = True,
    background: str = "#ffffff",
    focused_path: tuple[int, ...] | None = None,
    renderer_backend: NativeRendererBackend | None = None,
) -> DisplayList:
    if isinstance(target, NativePaint):
        return display_list_from_paint(target)

    if renderer_backend is not None:
        layout = (
            target
            if isinstance(target, NativeLayout)
            else renderer_backend.layout(
                target,
                stylesheet=stylesheet,
                strict_styles=strict_styles,
            )
        )
        paint = renderer_backend.paint(
            layout,
            background=background,
            focused_path=focused_path,
        )
        return display_list_from_paint(paint)

    layout = (
        target
        if isinstance(target, NativeLayout)
        else layout_native(
            target,
            stylesheet=stylesheet,
            strict_styles=strict_styles,
        )
    )
    return display_list_from_paint(
        paint_native(
            layout,
            background=background,
            focused_path=focused_path,
        )
    )


def display_list_to_dict(display_list: DisplayList) -> dict[str, object]:
    return {
        "schemaVersion": display_list.schema_version,
        "format": display_list.format,
        "width": display_list.width,
        "height": display_list.height,
        "commands": [command.to_dict() for command in display_list.commands],
    }


def display_list_to_json(
    display_list: DisplayList,
    *,
    indent: int | None = None,
) -> str:
    separators = (",", ":") if indent is None else None
    return json.dumps(
        display_list_to_dict(display_list),
        ensure_ascii=True,
        indent=indent,
        separators=separators,
    )


def _command_from_paint(command: PaintCommand) -> DisplayListCommand:
    if command.kind == "rect":
        return DisplayListCommand(
            op="rect",
            path=command.path,
            x=command.x,
            y=command.y,
            width=command.width,
            height=command.height,
            fill=command.fill,
            stroke=command.stroke,
            stroke_width=command.stroke_width,
            radius=command.radius,
            clip=command.clip,
            context=command.context,
        )
    if command.kind == "text":
        return DisplayListCommand(
            op="text",
            path=command.path,
            x=command.x,
            y=command.y,
            width=command.width,
            height=command.height,
            text=command.text or "",
            color=command.color,
            font_size=command.font_size,
            clip=command.clip,
            context=command.context,
        )
    raise DisplayListError(
        f"Cannot export paint command kind {command.kind!r} at path {command.path!r}."
    )


__all__ = [
    "DISPLAY_LIST_FORMAT",
    "DISPLAY_LIST_SCHEMA_VERSION",
    "DisplayList",
    "DisplayListCommand",
    "DisplayListError",
    "DisplayListTarget",
    "display_list_from_paint",
    "display_list_to_dict",
    "display_list_to_json",
    "export_native_display_list",
]
