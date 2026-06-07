from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from otoe.render_ir import RenderTree

from .backend_candidate_renderer_types import RendererCandidateCall


@dataclass(frozen=True)
class RenderTreeCandidateAcceptanceReport:
    minimal: RenderTree
    task_board: RenderTree
    keyed_before: RenderTree
    keyed_after: RenderTree
    show_before: RenderTree
    show_after: RenderTree
    stable_key_ids: dict[str, bool]
    show_branch_changed: bool
    artifact_target: RenderTree | None = None
    artifact_source: str | None = None
    errors: tuple[str, ...] = ()

    @property
    def passed(self) -> bool:
        return (
            not self.errors
            and self.minimal.node_count > 0
            and self.task_board.node_count > self.minimal.node_count
            and all(self.stable_key_ids.values())
            and self.show_branch_changed
            and (
                self.artifact_target is None
                or self.artifact_target.node_count > 0
            )
        )


@dataclass(frozen=True)
class Path0RenderTreeEvidenceReport:
    renderer_backend: str
    source: str
    render_tree_hash: str
    style_ops_present: bool
    style_ops_schema_version: Any
    style_ops_format: Any
    style_ops_matches_render_tree: bool
    node_count: int
    styled_nodes: int
    layout_boxes: int
    paint_commands: int
    layout_style_properties: tuple[str, ...]
    paint_style_properties: tuple[str, ...]
    layout_style_observations: tuple[dict[str, Any], ...]
    paint_style_observations: tuple[dict[str, Any], ...]
    layout_output: dict[str, Any]
    paint_output: dict[str, Any]
    png_path: str | None
    png_sha256: str | None
    png_bytes: int
    calls: tuple[RendererCandidateCall, ...]
    errors: tuple[str, ...] = ()

    @property
    def passed(self) -> bool:
        phases = {call.phase for call in self.calls}
        has_render_tree_layout = any(
            call.phase == "layout"
            and call.boundary == "renderTree"
            and call.layout_boxes > 0
            for call in self.calls
        )
        style_ops_valid = (
            not self.style_ops_present
            or (
                self.style_ops_schema_version == 1
                and self.style_ops_format == "otoe-style-ops"
                and self.style_ops_matches_render_tree
            )
        )
        png_valid = (
            self.png_path is None
            or any(call.phase == "write_png" for call in self.calls)
        )
        return (
            not self.errors
            and style_ops_valid
            and png_valid
            and self.node_count > 0
            and self.layout_boxes > 0
            and self.paint_commands > 0
            and has_render_tree_layout
            and {"layout", "paint"} <= phases
        )
