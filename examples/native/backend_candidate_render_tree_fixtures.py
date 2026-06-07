from __future__ import annotations

from typing import Any

from otoe import (
    For,
    HStack,
    MountedNode,
    Node,
    Show,
    Text,
    VStack,
    mount,
    signal,
    unmount,
)
from otoe.render_ir import RenderTree, render_tree_from_target
from otoe.style import resolved_style_map_from_style_ops_artifact

from .backend_candidate_apps import (
    BACKEND_CANDIDATE_STYLES,
    backend_candidate_app,
)
from .backend_candidate_layout_styles import (
    candidate_resolved_style_map as _candidate_resolved_style_map,
)
from .backend_candidate_render_tree_reports import text_node_ids
from .window_demo import NativeWindowDemo


def _minimal_render_tree(style_artifact: dict[str, Any] | None = None) -> RenderTree:
    mounted = mount(backend_candidate_app())
    try:
        style_map = (
            resolved_style_map_from_style_ops_artifact(style_artifact)
            if style_artifact is not None
            else _candidate_resolved_style_map(
                mounted,
                stylesheet=BACKEND_CANDIDATE_STYLES,
                strict_styles=True,
            )
        )
        return render_tree_from_target(
            mounted,
            style_map=style_map,
        )
    finally:
        unmount(mounted)


def _artifact_target_render_tree(
    target: Any,
    *,
    style_artifact: dict[str, Any],
) -> RenderTree:
    style_map = resolved_style_map_from_style_ops_artifact(style_artifact)
    if isinstance(target, Node):
        mounted = mount(target)
        try:
            return render_tree_from_target(mounted, style_map=style_map)
        finally:
            unmount(mounted)
    if isinstance(target, MountedNode):
        return render_tree_from_target(target, style_map=style_map)
    return render_tree_from_target(target, style_map=style_map)


def _task_board_render_tree() -> RenderTree:
    demo = NativeWindowDemo()
    surface = demo.driver.surface
    style_map = _candidate_resolved_style_map(
        surface.target,
        stylesheet=surface.stylesheet,
        strict_styles=surface.strict_styles,
    )
    return render_tree_from_target(
        surface.target,
        style_map=style_map,
        strict_styles=surface.strict_styles,
    )


def _keyed_reorder_render_trees() -> tuple[RenderTree, RenderTree]:
    items = signal(
        [
            {"id": "alpha", "label": "Alpha"},
            {"id": "beta", "label": "Beta"},
        ]
    )
    mounted = mount(
        VStack(
            For(
                each=items,
                key=lambda item: item["id"],
                children=lambda item: HStack(Text(item["label"])),
            )
        )
    )
    try:
        before = render_tree_from_target(mounted)
        items.set(
            [
                {"id": "beta", "label": "Beta"},
                {"id": "alpha", "label": "Alpha"},
            ]
        )
        after = render_tree_from_target(mounted)
        return before, after
    finally:
        unmount(mounted)


def _show_branch_render_trees() -> tuple[RenderTree, RenderTree]:
    visible = signal(False)
    mounted = mount(
        VStack(
            Show(
                Text("Visible"),
                when=visible,
                fallback=Text("Fallback"),
            )
        )
    )
    try:
        before = render_tree_from_target(mounted)
        visible.set(True)
        after = render_tree_from_target(mounted)
        return before, after
    finally:
        unmount(mounted)


def _stable_text_ids(
    before: RenderTree,
    after: RenderTree,
    *,
    labels: tuple[str, ...],
) -> dict[str, bool]:
    before_ids = text_node_ids(before)
    after_ids = text_node_ids(after)
    return {
        label: before_ids.get(label) == after_ids.get(label)
        for label in labels
    }
