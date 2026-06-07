from __future__ import annotations

from typing import Any

from otoe.render_ir import RenderTree, render_tree_to_dict, walk_render_nodes

from .backend_candidate_render_tree_types import RenderTreeCandidateAcceptanceReport


def text_node_ids(tree: RenderTree) -> dict[str, str]:
    result = {}
    for node in walk_render_nodes(tree.root):
        props = node.prop_dict()
        content = props.get("content")
        if isinstance(content, str):
            result[content] = node.node_id
    return result


def render_tree_visible_text(tree: RenderTree) -> tuple[str, ...]:
    return tuple(text_node_ids(tree))


def render_tree_contract_report_to_dict(
    report: RenderTreeCandidateAcceptanceReport,
) -> dict[str, Any]:
    payload = {
        "schemaVersion": 1,
        "format": "render-tree-contract",
        "passed": report.passed,
        "summary": {
            "minimalNodes": report.minimal.node_count,
            "taskBoardNodes": report.task_board.node_count,
            "keyedBeforeNodes": report.keyed_before.node_count,
            "keyedAfterNodes": report.keyed_after.node_count,
            "showBeforeNodes": report.show_before.node_count,
            "showAfterNodes": report.show_after.node_count,
            "artifactTargetNodes": (
                report.artifact_target.node_count
                if report.artifact_target is not None
                else 0
            ),
            "stableKeyIds": all(report.stable_key_ids.values()),
            "showBranchChanged": report.show_branch_changed,
        },
        "artifactSource": report.artifact_source,
        "stableKeyIds": dict(report.stable_key_ids),
        "visibleText": {
            "minimal": list(render_tree_visible_text(report.minimal)),
            "taskBoard": list(render_tree_visible_text(report.task_board)),
            "artifactTarget": list(render_tree_visible_text(report.artifact_target))
            if report.artifact_target is not None
            else [],
            "showBefore": list(render_tree_visible_text(report.show_before)),
            "showAfter": list(render_tree_visible_text(report.show_after)),
        },
        "runs": {
            "minimal": render_tree_to_dict(report.minimal),
            "taskBoard": render_tree_to_dict(report.task_board),
            "keyedReorder": {
                "before": render_tree_to_dict(report.keyed_before),
                "after": render_tree_to_dict(report.keyed_after),
                "textNodeIdsBefore": text_node_ids(report.keyed_before),
                "textNodeIdsAfter": text_node_ids(report.keyed_after),
            },
            "showBranch": {
                "before": render_tree_to_dict(report.show_before),
                "after": render_tree_to_dict(report.show_after),
            },
        },
        "errors": list(report.errors),
    }
    if report.artifact_target is not None:
        payload["runs"]["artifactTarget"] = render_tree_to_dict(report.artifact_target)
    return payload
