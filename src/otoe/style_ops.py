from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .style_ops_artifact import load_style_ir, style_ops_support_map
from .style_ops_replay import (
    expected_omitted_style_ops,
    replay_style_ops_class,
    replay_style_ops_direct,
    style_op_support,
)
from .style_ops_validation import validate_style_ops
from .style_ops_types import (
    STYLE_IR_SCHEMA_VERSION,
    STYLE_OPS_FORMAT,
    STYLE_OPS_SCHEMA_VERSION,
    AppliedStyleOps,
    StyleIRArtifact,
    StyleIRError,
    StyleOpsClassReplay,
    StyleOpsDirectReplay,
    StyleOpsValidation,
)


def apply_style_ops(
    artifact: StyleIRArtifact | Mapping[str, Any],
) -> AppliedStyleOps:
    style_ir = (
        artifact
        if isinstance(artifact, StyleIRArtifact)
        else load_style_ir(artifact)
    )
    class_replays = tuple(
        replay_style_ops_class(class_payload, style_support=style_ir.style_support)
        for class_payload in style_ir.style_ops["classes"]
    )
    direct_style_replays = tuple(
        replay_style_ops_direct(
            direct_style_payload,
            style_support=style_ir.style_support,
        )
        for direct_style_payload in style_ir.style_ops["directStyles"]
    )
    errors = _duplicate_style_ops_errors(class_replays, direct_style_replays)
    return AppliedStyleOps(
        classes=class_replays,
        direct_styles=direct_style_replays,
        errors=errors,
    )


def _duplicate_style_ops_errors(
    class_replays: tuple[StyleOpsClassReplay, ...],
    direct_style_replays: tuple[StyleOpsDirectReplay, ...],
) -> tuple[str, ...]:
    errors: list[str] = []
    seen_classes: set[str] = set()
    for replay in class_replays:
        if replay.class_name == "<invalid>":
            continue
        if replay.class_name in seen_classes:
            errors.append(f"duplicate styleOps class {replay.class_name!r}")
        seen_classes.add(replay.class_name)

    seen_paths: set[tuple[int, ...]] = set()
    seen_node_ids: set[str] = set()
    for replay in direct_style_replays:
        if replay.node_id is not None:
            if replay.node_id in seen_node_ids:
                errors.append(
                    f"duplicate styleOps directStyles nodeId {replay.node_id!r}"
                )
            seen_node_ids.add(replay.node_id)
        if replay.path in seen_paths:
            errors.append(
                f"duplicate styleOps directStyles path {list(replay.path)!r}"
            )
        seen_paths.add(replay.path)
    return tuple(errors)
