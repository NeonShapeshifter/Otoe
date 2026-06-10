"""Experimental backend-evidence API aliases.

This facade groups RenderTree and style-evidence helpers for renderer
candidate work. App authors should not need these for ordinary Otoe surfaces.
"""

from ..render_ir import (
    RENDER_TREE_SCHEMA_VERSION,
    RenderIRError,
    RenderNode,
    RenderTree,
    assert_render_tree_valid,
    load_render_tree_artifact,
    render_node_to_dict,
    render_tree_from_dict,
    render_tree_from_target,
    render_tree_to_dict,
    validate_render_tree,
    walk_render_nodes,
)
from ..style import ResolvedStyleMap, resolved_style_map_from_style_ops_artifact

__all__ = [
    "RENDER_TREE_SCHEMA_VERSION",
    "ResolvedStyleMap",
    "RenderIRError",
    "RenderNode",
    "RenderTree",
    "assert_render_tree_valid",
    "load_render_tree_artifact",
    "render_node_to_dict",
    "render_tree_from_dict",
    "render_tree_from_target",
    "render_tree_to_dict",
    "resolved_style_map_from_style_ops_artifact",
    "validate_render_tree",
    "walk_render_nodes",
]
