from __future__ import annotations

import hashlib
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from otoe import NativeLayout, NativePaint
from otoe.render_ir import (
    RenderNode,
    RenderTree,
    load_render_tree_artifact,
    render_tree_to_dict,
    validate_render_tree,
    walk_render_nodes,
)
from otoe.style import resolved_style_map_from_style_ops_artifact

from .backend_candidate_compact_snapshots import contract_hash
from .backend_candidate_path0_observations import (
    path0_layout_style_observations,
    path0_layout_style_properties,
    path0_paint_style_observations,
    path0_paint_style_properties,
)
from .backend_candidate_path0_output import (
    path0_layout_output_to_dict,
    path0_paint_output_to_dict,
)
from .backend_candidate_render_tree_types import Path0RenderTreeEvidenceReport
from .backend_candidate_renderer_types import (
    RendererCandidateCall,
)


@runtime_checkable
class RenderTreeRendererCandidate(Protocol):
    """Backend-candidate boundary for already-resolved RenderTree IR."""

    name: str
    calls: Sequence[RendererCandidateCall]

    def layout_render_tree(
        self,
        render_tree: RenderTree,
        *,
        source: str = "render-tree",
    ) -> NativeLayout:
        ...

    def paint(
        self,
        layout: NativeLayout,
        *,
        background: str = "#ffffff",
        focused_path: tuple[int, ...] | None = None,
    ) -> NativePaint:
        ...

    def write_png(self, paint: NativePaint, path: str | Path) -> None:
        ...


def run_path0_render_tree_evidence(
    render_tree: RenderTree,
    *,
    renderer_backend: RenderTreeRendererCandidate | None = None,
    style_artifact: dict[str, Any] | None = None,
    source: str = "render-tree",
    output_path: str | Path | None = None,
    background: str = "#ffffff",
    focused_path: tuple[int, ...] | None = None,
) -> Path0RenderTreeEvidenceReport:
    """Render a resolved RenderTree through Path0 without mounting components."""

    errors: list[str] = []
    calls: list[RendererCandidateCall] = []
    style_ops_present, style_ops_schema_version, style_ops_format = (
        _path0_style_ops_metadata(style_artifact, errors)
    )
    render_tree_errors = validate_render_tree(render_tree)
    errors.extend(render_tree_errors)
    style_ops_matches_render_tree, render_tree_style_errors = (
        _path0_style_ops_render_tree_match(render_tree, style_artifact)
    )
    errors.extend(render_tree_style_errors)

    layout_boxes = 0
    paint_commands = 0
    png_path = str(output_path) if output_path is not None else None
    png_sha256 = None
    png_bytes = 0
    layout_style_properties: tuple[str, ...] = ()
    paint_style_properties: tuple[str, ...] = ()
    layout_style_observations: tuple[dict[str, Any], ...] = ()
    paint_style_observations: tuple[dict[str, Any], ...] = ()
    layout_output: dict[str, Any] = {}
    paint_output: dict[str, Any] = {}
    renderer = renderer_backend or _default_path0_renderer()

    if not render_tree_errors:
        layout_style_properties = path0_layout_style_properties(render_tree)
        paint_style_properties = path0_paint_style_properties(render_tree)

        try:
            layout = renderer.layout_render_tree(render_tree, source=source)
            layout_boxes = len(layout.boxes)
            layout_output = path0_layout_output_to_dict(layout)
            layout_style_observations = path0_layout_style_observations(layout)
            paint = renderer.paint(
                layout,
                background=background,
                focused_path=focused_path,
            )
            paint_commands = len(paint.commands)
            paint_output = path0_paint_output_to_dict(paint)
            paint_style_observations = path0_paint_style_observations(layout, paint)
            if output_path is not None:
                renderer.write_png(paint, output_path)
                png_data = Path(output_path).read_bytes()
                png_sha256 = f"sha256:{hashlib.sha256(png_data).hexdigest()}"
                png_bytes = len(png_data)
        except Exception as exc:  # pragma: no cover - defensive evidence reporting
            errors.append(f"path0 render tree evidence failed: {exc}")
        calls = list(getattr(renderer, "calls", ()))

    return Path0RenderTreeEvidenceReport(
        renderer_backend=renderer.name,
        source=source,
        render_tree_hash=contract_hash(render_tree_to_dict(render_tree)),
        style_ops_present=style_ops_present,
        style_ops_schema_version=style_ops_schema_version,
        style_ops_format=style_ops_format,
        style_ops_matches_render_tree=style_ops_matches_render_tree,
        node_count=_safe_render_tree_node_count(render_tree),
        styled_nodes=_safe_render_tree_styled_node_count(render_tree),
        layout_boxes=layout_boxes,
        paint_commands=paint_commands,
        layout_style_properties=layout_style_properties,
        paint_style_properties=paint_style_properties,
        layout_style_observations=layout_style_observations,
        paint_style_observations=paint_style_observations,
        layout_output=layout_output,
        paint_output=paint_output,
        png_path=png_path,
        png_sha256=png_sha256,
        png_bytes=png_bytes,
        calls=tuple(calls),
        errors=tuple(errors),
    )


def run_path0_render_tree_artifact_evidence(
    render_tree_artifact: str | Path,
    *,
    renderer_backend: RenderTreeRendererCandidate | None = None,
    style_artifact: dict[str, Any] | None = None,
    source: str | None = None,
    output_path: str | Path | None = None,
    background: str = "#ffffff",
    focused_path: tuple[int, ...] | None = None,
) -> Path0RenderTreeEvidenceReport:
    artifact_path = Path(render_tree_artifact)
    return run_path0_render_tree_evidence(
        load_render_tree_artifact(artifact_path),
        renderer_backend=renderer_backend,
        style_artifact=style_artifact,
        source=source or f"render-tree-artifact:{artifact_path.name}",
        output_path=output_path,
        background=background,
        focused_path=focused_path,
    )


def _default_path0_renderer() -> RenderTreeRendererCandidate:
    from .backend_candidate_path0_renderer import Path0RendererCandidate

    return Path0RendererCandidate()


def _safe_render_tree_node_count(render_tree: RenderTree) -> int:
    try:
        return render_tree.node_count
    except Exception:
        return 0


def _safe_render_tree_styled_node_count(render_tree: RenderTree) -> int:
    try:
        return sum(1 for node in walk_render_nodes(render_tree.root) if node.style)
    except Exception:
        return 0


def _path0_style_ops_metadata(
    style_artifact: dict[str, Any] | None,
    errors: list[str],
) -> tuple[bool, Any, Any]:
    if style_artifact is None:
        return False, None, None
    if not isinstance(style_artifact, dict):
        errors.append("style artifact must be a JSON object")
        return True, None, None
    style_ops = style_artifact.get("styleOps")
    if not isinstance(style_ops, dict):
        errors.append("style artifact must include a styleOps object")
        return True, None, None
    schema_version = style_ops.get("schemaVersion")
    style_ops_format = style_ops.get("format")
    if schema_version != 1:
        errors.append(f"styleOps schemaVersion must be 1; got {schema_version!r}")
    if style_ops_format != "otoe-style-ops":
        errors.append(
            "styleOps format must be 'otoe-style-ops'; "
            f"got {style_ops_format!r}"
        )
    return True, schema_version, style_ops_format


def _path0_style_ops_render_tree_match(
    render_tree: RenderTree,
    style_artifact: dict[str, Any] | None,
) -> tuple[bool, tuple[str, ...]]:
    if style_artifact is None:
        return False, ()
    if not isinstance(style_artifact, dict):
        return False, ()
    try:
        style_map = resolved_style_map_from_style_ops_artifact(style_artifact)
    except Exception as exc:
        return False, (f"styleOps could not resolve RenderTree styles: {exc}",)

    errors: list[str] = []
    for node in walk_render_nodes(render_tree.root):
        try:
            expected = style_map.resolve(
                node.class_name,
                path=node.path,
                node_id=node.node_id,
            )
        except Exception as exc:
            errors.append(
                f"RenderTree node {node.node_id!r} styleOps resolution failed: {exc}"
            )
            if len(errors) >= 5:
                errors.append("RenderTree styleOps mismatch report truncated.")
                break
            continue
        actual = node.style_dict()
        if actual == expected:
            continue
        errors.append(_render_tree_style_mismatch_error(node, actual, expected))
        if len(errors) >= 5:
            errors.append("RenderTree styleOps mismatch report truncated.")
            break
    return not errors, tuple(errors)


def _render_tree_style_mismatch_error(
    node: RenderNode,
    actual: dict[str, Any],
    expected: dict[str, Any],
) -> str:
    actual_keys = tuple(sorted(actual))
    expected_keys = tuple(sorted(expected))
    return (
        f"RenderTree node {node.node_id!r} style does not match styleOps artifact "
        f"(path={list(node.path)!r}, className={node.class_name!r}, "
        f"actualKeys={list(actual_keys)!r}, expectedKeys={list(expected_keys)!r})"
    )
