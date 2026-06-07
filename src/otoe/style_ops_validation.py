from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .style_ops_artifact import load_style_ir, payload_path
from .style_ops_replay import expected_omitted_style_ops
from .style_ops_types import (
    AppliedStyleOps,
    StyleIRArtifact,
    StyleOpsDirectReplay,
    StyleOpsValidation,
)
from .style_ops_values import (
    declaration_value_errors,
    omitted_declaration_value_errors,
)


def validate_style_ops(
    artifact: StyleIRArtifact | Mapping[str, Any],
    *,
    applied: AppliedStyleOps | None = None,
) -> StyleOpsValidation:
    style_ir = (
        artifact
        if isinstance(artifact, StyleIRArtifact)
        else load_style_ir(artifact)
    )
    if applied is None:
        from .style_ops import apply_style_ops

        applied = apply_style_ops(style_ir)
    errors: list[str] = [
        *applied.errors,
        *(
            error
            for replay in applied.classes
            for error in replay.errors
        ),
        *(
            error
            for replay in applied.direct_styles
            for error in replay.errors
        ),
    ]
    errors.extend(_validate_class_style_ops(style_ir, applied))
    errors.extend(_validate_direct_style_ops(style_ir, applied))
    return StyleOpsValidation(applied=applied, errors=tuple(errors))


def _validate_class_style_ops(
    style_ir: StyleIRArtifact,
    applied: AppliedStyleOps,
) -> tuple[str, ...]:
    errors: list[str] = []
    seen_classes: set[str] = set()
    for replay in applied.classes:
        if replay.class_name == "<invalid>":
            continue
        seen_classes.add(replay.class_name)
        rule_payload = style_ir.rules_by_class.get(replay.class_name)
        if rule_payload is None:
            errors.append(
                f"styleOps class {replay.class_name!r} is not present in compiled rules"
            )
            continue

        expected_missing = bool(rule_payload.get("missing"))
        expected_declarations = rule_payload.get("declarations", {})
        if not isinstance(expected_declarations, dict):
            expected_declarations = {}
            errors.append(
                f"compiled rule {replay.class_name!r} declarations must be an object"
            )
        else:
            errors.extend(
                declaration_value_errors(
                    expected_declarations,
                    label=f"compiled rule {replay.class_name!r}",
                    portable=True,
                )
            )
        errors.extend(
            omitted_declaration_value_errors(
                rule_payload.get("omittedDeclarations", []),
                label=f"compiled rule {replay.class_name!r}",
            )
        )
        expected_omitted_ops = expected_omitted_style_ops(
            rule_payload,
            style_ir.style_support,
        )

        if replay.missing is not expected_missing:
            errors.append(
                f"styleOps class {replay.class_name!r} missing flag does not match compiled rule"
            )
        if replay.applied_declarations != expected_declarations:
            errors.append(
                f"styleOps class {replay.class_name!r} applied declarations do not match compiled rules"
            )
        if replay.omitted_ops != expected_omitted_ops:
            errors.append(
                f"styleOps class {replay.class_name!r} omitted ops do not match compiled rules"
            )

    missing_ops = sorted(set(style_ir.rules_by_class) - seen_classes)
    if missing_ops:
        errors.append(
            "styleOps missing classes from compiled rules: "
            + ", ".join(missing_ops)
        )
    return tuple(errors)


def _validate_direct_style_ops(
    style_ir: StyleIRArtifact,
    applied: AppliedStyleOps,
) -> tuple[str, ...]:
    errors: list[str] = []
    seen_paths: set[tuple[int, ...]] = set()
    seen_node_ids: set[str] = set()
    for replay in applied.direct_styles:
        seen_paths.add(replay.path)
        if replay.node_id is not None:
            seen_node_ids.add(replay.node_id)
        expected_payload = _expected_direct_style_payload(style_ir, replay)
        if expected_payload is None:
            errors.append(_missing_direct_style_message(replay))
            continue

        expected_node_id = expected_payload.get("nodeId")
        expected_path = payload_path(expected_payload.get("path"))
        expected_widget = expected_payload.get("widget")
        expected_declarations = expected_payload.get("declarations", {})
        if not isinstance(expected_declarations, dict):
            expected_declarations = {}
            errors.append(
                f"compiled directStyles {list(replay.path)!r} declarations must be an object"
            )
        else:
            errors.extend(
                declaration_value_errors(
                    expected_declarations,
                    label=f"compiled directStyles {list(replay.path)!r}",
                    portable=True,
                )
            )
        errors.extend(
            omitted_declaration_value_errors(
                expected_payload.get("omittedDeclarations", []),
                label=f"compiled directStyles {list(replay.path)!r}",
            )
        )
        expected_omitted_ops = expected_omitted_style_ops(
            expected_payload,
            style_ir.style_support,
        )

        if isinstance(expected_node_id, str) and replay.node_id != expected_node_id:
            errors.append(
                f"styleOps directStyles {list(replay.path)!r} nodeId does not match compiled artifact"
            )
        if expected_path is not None and replay.path != expected_path:
            errors.append(
                f"styleOps directStyles {list(replay.path)!r} path does not match compiled artifact"
            )
        if replay.widget != expected_widget:
            errors.append(
                f"styleOps directStyles {list(replay.path)!r} widget does not match compiled artifact"
            )
        if replay.applied_declarations != expected_declarations:
            errors.append(
                f"styleOps directStyles {list(replay.path)!r} applied declarations do not match compiled artifact"
            )
        if replay.omitted_ops != expected_omitted_ops:
            errors.append(
                f"styleOps directStyles {list(replay.path)!r} omitted ops do not match compiled artifact"
            )

    missing_node_ops = sorted(set(style_ir.direct_styles_by_node_id) - seen_node_ids)
    if missing_node_ops:
        errors.append(
            "styleOps missing directStyles from compiled artifact: "
            + ", ".join(repr(node_id) for node_id in missing_node_ops)
        )
    legacy_paths = {
        path
        for path, payload in style_ir.direct_styles_by_path.items()
        if not isinstance(payload.get("nodeId"), str)
    }
    missing_direct_ops = sorted(legacy_paths - seen_paths)
    if missing_direct_ops:
        errors.append(
            "styleOps missing directStyles from compiled artifact: "
            + ", ".join(str(list(path)) for path in missing_direct_ops)
        )
    return tuple(errors)


def _expected_direct_style_payload(
    style_ir: StyleIRArtifact,
    replay: StyleOpsDirectReplay,
) -> dict[str, Any] | None:
    if replay.node_id is not None:
        return style_ir.direct_styles_by_node_id.get(replay.node_id)
    return style_ir.direct_styles_by_path.get(replay.path)


def _missing_direct_style_message(replay: StyleOpsDirectReplay) -> str:
    if replay.node_id is not None:
        return (
            f"styleOps directStyles nodeId {replay.node_id!r} "
            "is not present in compiled artifact"
        )
    return (
        f"styleOps directStyles {list(replay.path)!r} "
        "is not present in compiled artifact"
    )
