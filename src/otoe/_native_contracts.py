from __future__ import annotations

from dataclasses import dataclass
from typing import Any


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
    context: str | None = None
    text: str | None = None
    events: tuple[str, ...] = ()
    state: tuple[str, ...] = ()
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
