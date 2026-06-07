from __future__ import annotations

from pathlib import Path
from typing import Any

from otoe import (
    NativeLayout,
    NativePaint,
    NativeRendererBackend,
    PYTHON_NATIVE_RENDERER_BACKEND,
)

from .backend_candidate_renderer_utils import _target_name
from .backend_candidate_renderer_types import RendererCandidateCall


class RecordingRendererCandidate:
    """Renderer-candidate skeleton that records the SPI calls it receives."""

    name = "recording-renderer-candidate"

    def __init__(
        self,
        *,
        inner: NativeRendererBackend | None = None,
        name: str | None = None,
    ) -> None:
        self.name = name or self.name
        self._inner = inner or PYTHON_NATIVE_RENDERER_BACKEND
        self.calls: list[RendererCandidateCall] = []

    @property
    def layout_calls(self) -> int:
        return self._count("layout")

    @property
    def paint_calls(self) -> int:
        return self._count("paint")

    @property
    def write_png_calls(self) -> int:
        return self._count("write_png")

    def layout(
        self,
        target: Any,
        *,
        stylesheet: Any = None,
        strict_styles: bool = True,
    ) -> NativeLayout:
        layout = self._inner.layout(
            target,
            stylesheet=stylesheet,
            strict_styles=strict_styles,
        )
        self.calls.append(
            RendererCandidateCall(
                phase="layout",
                subject=_target_name(target),
                layout_boxes=len(layout.boxes),
            )
        )
        return layout

    def paint(
        self,
        layout: NativeLayout,
        *,
        background: str = "#ffffff",
        focused_path: tuple[int, ...] | None = None,
    ) -> NativePaint:
        paint = self._inner.paint(
            layout,
            background=background,
            focused_path=focused_path,
        )
        self.calls.append(
            RendererCandidateCall(
                phase="paint",
                subject=layout.root.name,
                layout_boxes=len(layout.boxes),
                paint_commands=len(paint.commands),
            )
        )
        return paint

    def write_png(self, paint: NativePaint, path: str | Path) -> None:
        self._inner.write_png(paint, path)
        self.calls.append(
            RendererCandidateCall(
                phase="write_png",
                subject=Path(path).name,
                paint_commands=len(paint.commands),
            )
        )

    def _count(self, phase: str) -> int:
        return sum(1 for call in self.calls if call.phase == phase)
