from __future__ import annotations

from dataclasses import dataclass
from math import ceil
from pathlib import Path
from typing import Any

from ._native_contracts import NativeLayout, NativePaint, NativePaintError, PaintCommand
from ._native_layout import layout_native
from ._native_paint import paint_native
from ._native_shared import parse_color
from ._native_text import NativeTextMetrics
from .mount import FakeWidget, MountedNode
from .style import StyleSheet


_PILLOW_INSTALL_HINT = "Install it with `python -m pip install 'otoe[native-text]'`."


@dataclass(frozen=True)
class PillowNativeRendererBackend:
    font_path: str | Path | None = None
    name: str = "pillow-native"

    def layout(
        self,
        target: FakeWidget | MountedNode,
        *,
        stylesheet: StyleSheet | None = None,
        strict_styles: bool = True,
    ) -> NativeLayout:
        return layout_native(
            target,
            stylesheet=stylesheet,
            strict_styles=strict_styles,
            text_measure=self.measure_text,
        )

    def paint(
        self,
        layout: NativeLayout,
        *,
        background: str = "#ffffff",
        focused_path: tuple[int, ...] | None = None,
    ) -> NativePaint:
        return paint_native(
            layout,
            background=background,
            focused_path=focused_path,
            text_measure=self.measure_text,
        )

    def write_png(self, paint: NativePaint, path: str | Path) -> None:
        write_pillow_native_png(paint, path, font_path=self.font_path)

    def measure_text(self, text: str, *, font_size: int) -> NativeTextMetrics:
        font = _load_font(self.font_path, font_size=font_size)
        bbox = font.getbbox(text or " ")
        line_bbox = font.getbbox("Ag")
        return NativeTextMetrics(
            width=max(1, ceil(bbox[2] - bbox[0])),
            height=max(1, ceil(line_bbox[3] - line_bbox[1])),
        )


def write_pillow_native_png(
    paint: NativePaint,
    path: str | Path,
    *,
    font_path: str | Path | None = None,
) -> None:
    Image, _, _ = _pillow_modules()
    image = Image.new("RGBA", (paint.width, paint.height), (0, 0, 0, 0))
    for command in paint.commands:
        if command.kind == "rect":
            _draw_with_clip(
                image,
                command.clip,
                lambda draw, command=command: _draw_pillow_rect(draw, command),
            )
        elif command.kind == "text":
            _draw_with_clip(
                image,
                command.clip,
                lambda draw, command=command: _draw_pillow_text(
                    draw, command, font_path=font_path
                ),
            )
        else:
            raise NativePaintError(
                f"Unknown paint command kind {command.kind!r}"
                f"{_command_location(command)}."
            )
    Path(path).write_bytes(_png_bytes(image))


def _draw_with_clip(
    image: Any,
    clip: tuple[int, int, int, int] | None,
    draw_fn: Any,
) -> None:
    Image, ImageDraw, _ = _pillow_modules()
    if clip is None:
        draw_fn(ImageDraw.Draw(image))
        return
    clip_x, clip_y, clip_width, clip_height = _clip_bounds(
        clip,
        image.width,
        image.height,
    )
    if clip_width <= 0 or clip_height <= 0:
        return
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw_fn(ImageDraw.Draw(overlay))
    region = overlay.crop((clip_x, clip_y, clip_x + clip_width, clip_y + clip_height))
    image.alpha_composite(region, (clip_x, clip_y))


def _draw_pillow_rect(draw: Any, command: PaintCommand) -> None:
    if command.width <= 0 or command.height <= 0:
        return
    fill = _command_color(command, "fill") if command.fill is not None else None
    outline = _command_color(command, "stroke") if command.stroke is not None else None
    stroke_width = max(command.stroke_width, 0)
    box = (
        command.x,
        command.y,
        command.x + max(command.width - 1, 0),
        command.y + max(command.height - 1, 0),
    )
    draw.rounded_rectangle(
        box,
        radius=max(command.radius, 0),
        fill=fill,
        outline=outline,
        width=stroke_width if outline is not None else 1,
    )


def _draw_pillow_text(
    draw: Any,
    command: PaintCommand,
    *,
    font_path: str | Path | None,
) -> None:
    if not command.text:
        return
    font = _load_font(font_path, font_size=command.font_size)
    color = _command_color(command, "color")
    bbox = font.getbbox(command.text)
    draw.text(
        (command.x - bbox[0], command.y - bbox[1]),
        command.text,
        fill=color,
        font=font,
    )


def _load_font(font_path: str | Path | None, *, font_size: int) -> Any:
    _, _, ImageFont = _pillow_modules()
    size = max(1, int(font_size))
    if font_path is None:
        return ImageFont.load_default(size=size)
    path = Path(font_path)
    if not path.exists():
        raise NativePaintError(f"Pillow native text font {str(path)!r} does not exist.")
    try:
        return ImageFont.truetype(str(path), size=size)
    except OSError as exc:
        raise NativePaintError(
            f"Pillow native text font {str(path)!r} could not be loaded: {exc}"
        ) from exc


def _pillow_modules() -> tuple[Any, Any, Any]:
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError as exc:
        raise NativePaintError(
            f"Pillow native text backend requires Pillow. {_PILLOW_INSTALL_HINT}"
        ) from exc
    return Image, ImageDraw, ImageFont


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


def _clip_bounds(
    clip: tuple[int, int, int, int],
    image_width: int,
    image_height: int,
) -> tuple[int, int, int, int]:
    x, y, width, height = clip
    x1 = max(x, 0)
    y1 = max(y, 0)
    x2 = min(x + width, image_width)
    y2 = min(y + height, image_height)
    return (x1, y1, max(0, x2 - x1), max(0, y2 - y1))


def _png_bytes(image: Any) -> bytes:
    from io import BytesIO

    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()
