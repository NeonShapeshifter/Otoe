from __future__ import annotations

import struct
import zlib
from pathlib import Path
from typing import Any

from otoe import NativePaint


def _write_candidate_png(paint: NativePaint, path: str | Path) -> None:
    image = bytearray([0, 0, 0, 0] * paint.width * paint.height)
    for command in paint.commands:
        if command.kind == "rect":
            _candidate_draw_rect(image, paint.width, paint.height, command)
        elif command.kind == "text":
            _candidate_draw_text(image, paint.width, paint.height, command)
        else:
            raise ValueError(f"Unsupported candidate paint command {command.kind!r}.")
    Path(path).write_bytes(_candidate_encode_png(image, paint.width, paint.height))


def _candidate_draw_rect(
    image: bytearray,
    image_width: int,
    image_height: int,
    command: Any,
) -> None:
    clip_x, clip_y, clip_width, clip_height = _candidate_clip(
        command.clip,
        image_width,
        image_height,
    )
    x1 = max(command.x, 0, clip_x)
    y1 = max(command.y, 0, clip_y)
    x2 = min(command.x + command.width, image_width, clip_x + clip_width)
    y2 = min(command.y + command.height, image_height, clip_y + clip_height)

    if command.fill is not None:
        fill = _candidate_color(command.fill)
        for y in range(y1, y2):
            for x in range(x1, x2):
                _candidate_set_pixel(image, image_width, x, y, fill)

    if command.stroke is None or command.stroke_width <= 0:
        return
    stroke = _candidate_color(command.stroke)
    stroke_width = max(command.stroke_width, 1)
    for y in range(y1, y2):
        for x in range(x1, x2):
            if (
                x < command.x + stroke_width
                or x >= command.x + command.width - stroke_width
                or y < command.y + stroke_width
                or y >= command.y + command.height - stroke_width
            ):
                _candidate_set_pixel(image, image_width, x, y, stroke)


def _candidate_draw_text(
    image: bytearray,
    image_width: int,
    image_height: int,
    command: Any,
) -> None:
    if not command.text:
        return
    color = _candidate_color(command.color or "#111827")
    clip_x, clip_y, clip_width, clip_height = _candidate_clip(
        command.clip,
        image_width,
        image_height,
    )
    glyph_width = max(2, command.font_size // 4)
    glyph_height = max(6, int(command.font_size * 0.75))
    step = glyph_width + 2
    for index, character in enumerate(command.text):
        if character == " ":
            continue
        x = command.x + index * step
        y = command.y + max(0, (command.height - glyph_height) // 2)
        for px in range(
            max(x, 0, clip_x),
            min(x + glyph_width, image_width, clip_x + clip_width),
        ):
            for py in range(
                max(y, 0, clip_y),
                min(y + glyph_height, image_height, clip_y + clip_height),
            ):
                if px in {x, x + glyph_width - 1} or py in {y, y + glyph_height - 1}:
                    _candidate_set_pixel(image, image_width, px, py, color)
                elif (ord(character) + px + py) % 13 == 0:
                    _candidate_set_pixel(image, image_width, px, py, color)


def _candidate_clip(
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


def _candidate_color(value: str) -> tuple[int, int, int, int]:
    if not isinstance(value, str) or not value.startswith("#"):
        raise ValueError(f"Candidate raster only supports hex colors, got {value!r}.")
    raw = value[1:]
    if len(raw) == 6:
        raw = f"{raw}ff"
    if len(raw) != 8:
        raise ValueError(
            f"Candidate raster only supports #rrggbb colors, got {value!r}."
        )
    return tuple(int(raw[index : index + 2], 16) for index in range(0, 8, 2))  # type: ignore[return-value]


def _candidate_set_pixel(
    image: bytearray,
    image_width: int,
    x: int,
    y: int,
    color: tuple[int, int, int, int],
) -> None:
    offset = (y * image_width + x) * 4
    image[offset : offset + 4] = bytes(color)


def _candidate_encode_png(image: bytearray, width: int, height: int) -> bytes:
    rows = []
    stride = width * 4
    for y in range(height):
        start = y * stride
        rows.append(b"\x00" + bytes(image[start : start + stride]))
    raw = b"".join(rows)
    return b"".join(
        [
            b"\x89PNG\r\n\x1a\n",
            _candidate_png_chunk(
                b"IHDR",
                struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0),
            ),
            _candidate_png_chunk(b"IDAT", zlib.compress(raw)),
            _candidate_png_chunk(b"IEND", b""),
        ]
    )


def _candidate_png_chunk(kind: bytes, data: bytes) -> bytes:
    checksum = zlib.crc32(kind)
    checksum = zlib.crc32(data, checksum)
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", checksum)
