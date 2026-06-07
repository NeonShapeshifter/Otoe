from __future__ import annotations

from pathlib import Path
from typing import Any

from otoe import NativeLayout, NativePaint
from otoe.render_ir import RenderTree
from otoe.style import (
    ResolvedStyleMap,
    resolved_style_map_from_style_ops_artifact,
)

from .backend_candidate_layout_styles import candidate_resolved_style_map
from .backend_candidate_paint_renderer import _paint_candidate_layout
from .backend_candidate_raster_renderer import _write_candidate_png
from .backend_candidate_render_tree_layout import _layout_candidate_render_tree
from .backend_candidate_renderer_utils import _target_name
from .backend_candidate_renderer_types import RendererCandidateCall


class Path0RendererCandidate:
    """Minimal renderer candidate that owns layout, paint, and raster phases."""

    name = "path0-renderer-candidate"

    def __init__(
        self,
        *,
        name: str | None = None,
        style_map: ResolvedStyleMap | None = None,
        style_artifact: dict[str, Any] | None = None,
        strict_style_artifact: bool = True,
    ) -> None:
        if style_map is not None and style_artifact is not None:
            raise ValueError("style_map and style_artifact are mutually exclusive.")
        self.name = name or self.name
        self._style_map = (
            resolved_style_map_from_style_ops_artifact(
                style_artifact,
                strict=strict_style_artifact,
            )
            if style_artifact is not None
            else style_map
        )
        self.calls: list[RendererCandidateCall] = []

    @classmethod
    def from_style_artifact(
        cls,
        artifact: dict[str, Any],
        *,
        name: str | None = None,
        strict: bool = True,
    ) -> "Path0RendererCandidate":
        return cls(
            name=name,
            style_artifact=artifact,
            strict_style_artifact=strict,
        )

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
        style_map = self._style_map or candidate_resolved_style_map(
            target,
            stylesheet=stylesheet,
            strict_styles=strict_styles,
        )
        render_tree = _render_tree_from_target(
            target,
            stylesheet=None if style_map is not None else stylesheet,
            style_map=style_map,
            strict_styles=strict_styles,
        )
        return self.layout_render_tree(render_tree, source=_target_name(target))

    def layout_render_tree(
        self,
        render_tree: RenderTree,
        *,
        source: str = "render-tree",
    ) -> NativeLayout:
        layout = _layout_candidate_render_tree(render_tree)
        self.calls.append(
            RendererCandidateCall(
                phase="layout",
                subject=source,
                layout_boxes=len(layout.boxes),
                boundary="renderTree",
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
        paint = _paint_candidate_layout(
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
        _write_candidate_png(paint, path)
        self.calls.append(
            RendererCandidateCall(
                phase="write_png",
                subject=Path(path).name,
                paint_commands=len(paint.commands),
            )
        )

    def _count(self, phase: str) -> int:
        return sum(1 for call in self.calls if call.phase == phase)


def _render_tree_from_target(*args: Any, **kwargs: Any) -> RenderTree:
    from . import backend_candidate_renderer

    return backend_candidate_renderer.render_tree_from_target(*args, **kwargs)
