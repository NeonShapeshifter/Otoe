from __future__ import annotations

from typing import Any

from otoe.render_ir import (
    RenderIRError,
    RenderTree,
    render_tree_to_dict,
)

from .backend_candidate_render_tree_fixtures import (
    _artifact_target_render_tree,
    _keyed_reorder_render_trees,
    _minimal_render_tree,
    _show_branch_render_trees,
    _stable_text_ids,
    _task_board_render_tree,
)
from .backend_candidate_render_tree_reports import (
    render_tree_visible_text,
)
from .backend_candidate_render_tree_types import RenderTreeCandidateAcceptanceReport


def run_render_tree_candidate_acceptance(
    style_artifact: dict[str, Any] | None = None,
    *,
    artifact_target: Any | None = None,
    artifact_render_tree: RenderTree | None = None,
    artifact_source: str | None = None,
) -> RenderTreeCandidateAcceptanceReport:
    errors: list[str] = []
    baseline_style_artifact = (
        style_artifact
        if artifact_target is None and artifact_render_tree is None
        else None
    )
    minimal = _json_boundary_render_tree(
        _minimal_render_tree(baseline_style_artifact),
        label="minimal",
        errors=errors,
    )
    task_board = _json_boundary_render_tree(
        _task_board_render_tree(),
        label="taskBoard",
        errors=errors,
    )
    keyed_before_raw, keyed_after_raw = _keyed_reorder_render_trees()
    keyed_before = _json_boundary_render_tree(
        keyed_before_raw,
        label="keyed.before",
        errors=errors,
    )
    keyed_after = _json_boundary_render_tree(
        keyed_after_raw,
        label="keyed.after",
        errors=errors,
    )
    show_before_raw, show_after_raw = _show_branch_render_trees()
    show_before = _json_boundary_render_tree(
        show_before_raw,
        label="show.before",
        errors=errors,
    )
    show_after = _json_boundary_render_tree(
        show_after_raw,
        label="show.after",
        errors=errors,
    )
    artifact_tree = None
    if artifact_render_tree is not None:
        artifact_tree = _json_boundary_render_tree(
            artifact_render_tree,
            label="artifactRenderTree",
            errors=errors,
        )
    elif artifact_target is not None and style_artifact is not None:
        artifact_tree = _json_boundary_render_tree(
            _artifact_target_render_tree(
                artifact_target,
                style_artifact=style_artifact,
            ),
            label="artifactTarget",
            errors=errors,
        )
    elif artifact_target is not None:
        errors.append("artifact target requires a style artifact")
    stable_key_ids = _stable_text_ids(
        keyed_before,
        keyed_after,
        labels=("Alpha", "Beta"),
    )
    show_branch_changed = (
        render_tree_visible_text(show_before) == ("Fallback",)
        and render_tree_visible_text(show_after) == ("Visible",)
    )

    if minimal.root.name != "ShortcutScope":
        errors.append("minimal render tree root must be ShortcutScope")
    if task_board.root.name != "ShortcutScope":
        errors.append("task board render tree root must be ShortcutScope")
    if not stable_key_ids:
        errors.append("keyed render tree must expose stable text node IDs")
    if any(not passed for passed in stable_key_ids.values()):
        errors.append("keyed render tree node IDs changed across reorder")
    if not show_branch_changed:
        errors.append("Show render tree did not reflect fallback/visible branch swap")
    if artifact_target is not None and artifact_tree is None:
        errors.append("artifact target did not produce a render tree")

    return RenderTreeCandidateAcceptanceReport(
        minimal=minimal,
        task_board=task_board,
        keyed_before=keyed_before,
        keyed_after=keyed_after,
        show_before=show_before,
        show_after=show_after,
        stable_key_ids=stable_key_ids,
        show_branch_changed=show_branch_changed,
        artifact_target=artifact_tree,
        artifact_source=artifact_source,
        errors=tuple(errors),
    )


def _json_boundary_render_tree(
    tree: RenderTree,
    *,
    label: str,
    errors: list[str],
) -> RenderTree:
    try:
        return _render_tree_from_dict(render_tree_to_dict(tree))
    except RenderIRError as exc:
        errors.append(f"{label} RenderTree JSON boundary failed: {exc}")
        return tree


def _render_tree_from_dict(payload: dict[str, Any]) -> RenderTree:
    from . import backend_candidate_contracts

    return backend_candidate_contracts.render_tree_from_dict(payload)
