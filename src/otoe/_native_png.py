from __future__ import annotations

import struct
import zlib
from pathlib import Path
from typing import TYPE_CHECKING

from ._native_contracts import NativeLayout, NativePaint, NativePaintError, PaintCommand
from ._native_layout import layout_native
from ._native_paint import paint_native
from ._native_shared import parse_color
from .mount import FakeWidget, MountedNode
from .style import StyleSheet

if TYPE_CHECKING:
    from ._native_backend import NativeRendererBackend


def write_native_png(
    paint: NativePaint,
    path: str | Path,
    *,
    scale: int = 1,
) -> None:
    raster_paint = _scale_paint(paint, scale=scale)
    image = _new_image(raster_paint.width, raster_paint.height)
    for command in raster_paint.commands:
        if command.kind == "rect":
            _draw_rounded_rect(image, raster_paint.width, raster_paint.height, command)
        elif command.kind == "text":
            _draw_text_marker(image, raster_paint.width, raster_paint.height, command)
        else:
            raise NativePaintError(
                f"Unknown paint command kind {command.kind!r}"
                f"{_command_location(command)}."
            )
    Path(path).write_bytes(_encode_png(image, raster_paint.width, raster_paint.height))


def render_native_png(
    target: FakeWidget | MountedNode | NativeLayout,
    path: str | Path,
    *,
    stylesheet: StyleSheet | None = None,
    strict_styles: bool = True,
    background: str = "#ffffff",
    focused_path: tuple[int, ...] | None = None,
    renderer_backend: NativeRendererBackend | None = None,
    scale: int = 1,
) -> NativePaint:
    _validate_scale(scale)
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
        renderer_backend.write_png(_scale_paint(paint, scale=scale), path)
        return paint

    layout = (
        target
        if isinstance(target, NativeLayout)
        else layout_native(target, stylesheet=stylesheet, strict_styles=strict_styles)
    )
    paint = paint_native(layout, background=background, focused_path=focused_path)
    write_native_png(paint, path, scale=scale)
    return paint


def _scale_paint(paint: NativePaint, *, scale: int) -> NativePaint:
    _validate_scale(scale)
    if scale == 1:
        return paint
    return NativePaint(
        width=paint.width * scale,
        height=paint.height * scale,
        commands=tuple(_scale_command(command, scale=scale) for command in paint.commands),
    )


def _scale_command(command: PaintCommand, *, scale: int) -> PaintCommand:
    clip = command.clip
    if clip is not None:
        clip = (clip[0] * scale, clip[1] * scale, clip[2] * scale, clip[3] * scale)
    return PaintCommand(
        kind=command.kind,
        path=command.path,
        x=command.x * scale,
        y=command.y * scale,
        width=command.width * scale,
        height=command.height * scale,
        fill=command.fill,
        stroke=command.stroke,
        stroke_width=command.stroke_width * scale,
        radius=command.radius * scale,
        text=command.text,
        color=command.color,
        font_size=command.font_size * scale,
        clip=clip,
        context=command.context,
    )


def _validate_scale(scale: int) -> None:
    if isinstance(scale, bool) or not isinstance(scale, int) or scale < 1:
        raise NativePaintError(
            f"Native PNG scale must be a positive integer; got {scale!r}."
        )


def _new_image(width: int, height: int) -> bytearray:
    return bytearray([0, 0, 0, 0] * width * height)


def _draw_rounded_rect(
    image: bytearray,
    image_width: int,
    image_height: int,
    command: PaintCommand,
) -> None:
    fill = _command_color(command, "fill") if command.fill is not None else None
    stroke = _command_color(command, "stroke") if command.stroke is not None else None
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
            if border_pixel and stroke is not None:
                _set_pixel(image, image_width, x, y, stroke)
            elif fill is not None:
                _set_pixel(image, image_width, x, y, fill)


def _draw_text_marker(
    image: bytearray,
    image_width: int,
    image_height: int,
    command: PaintCommand,
) -> None:
    color = _command_color(command, "color")
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


def _command_color(command: PaintCommand, field: str) -> tuple[int, int, int, int]:
    value = getattr(command, field)
    try:
        return parse_color(value)
    except NativePaintError as exc:
        raise NativePaintError(
            f"Paint command {command.kind!r}{_command_location(command)} "
            f"has invalid {field}: {exc}"
        ) from exc


def _command_location(command: PaintCommand) -> str:
    if command.context:
        return f" for {command.context} at path {command.path!r}"
    return f" at path {command.path!r}"


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
