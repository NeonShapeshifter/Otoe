from __future__ import annotations

from pathlib import Path
from typing import Any

from otoe import NativeLayout, NativePaint
from otoe.render_ir import RenderTree

from .backend_candidate_paint_renderer import _paint_candidate_layout
from .backend_candidate_raster_renderer import _write_candidate_png
from .backend_candidate_recording_renderer import RecordingRendererCandidate
from .backend_candidate_render_tree_layout import _layout_candidate_render_tree
from .backend_candidate_renderer_utils import _target_name
from .backend_candidate_renderer_types import RendererCandidateCall


class RasterOnlyRendererCandidate(RecordingRendererCandidate):
    """Candidate that keeps Python layout/paint and replaces only PNG raster."""

    name = "raster-only-renderer-candidate"

    def write_png(self, paint: NativePaint, path: str | Path) -> None:
        _write_candidate_png(paint, path)
        self.calls.append(
            RendererCandidateCall(
                phase="write_png",
                subject=Path(path).name,
                paint_commands=len(paint.commands),
            )
        )


class PaintOnlyRendererCandidate(RecordingRendererCandidate):
    """Candidate that keeps Python layout/raster and replaces only paint."""

    name = "paint-only-renderer-candidate"

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


class LayoutOnlyRendererCandidate(RecordingRendererCandidate):
    """Minimal replay candidate that replaces only layout."""

    name = "layout-only-renderer-candidate"

    def layout(
        self,
        target: Any,
        *,
        stylesheet: Any = None,
        strict_styles: bool = True,
    ) -> NativeLayout:
        render_tree = _render_tree_from_target(
            target,
            stylesheet=stylesheet,
            strict_styles=strict_styles,
        )
        layout = _layout_candidate_render_tree(render_tree)
        self.calls.append(
            RendererCandidateCall(
                phase="layout",
                subject=_target_name(target),
                layout_boxes=len(layout.boxes),
            )
        )
        return layout


def _render_tree_from_target(*args: Any, **kwargs: Any) -> RenderTree:
    from . import backend_candidate_renderer

    return backend_candidate_renderer.render_tree_from_target(*args, **kwargs)
