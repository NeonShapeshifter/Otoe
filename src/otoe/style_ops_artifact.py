from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .style_ops_types import (
    STYLE_IR_SCHEMA_VERSION,
    STYLE_OPS_FORMAT,
    STYLE_OPS_SCHEMA_VERSION,
    StyleIRArtifact,
    StyleIRError,
)


def load_style_ir(payload: Mapping[str, Any]) -> StyleIRArtifact:
    if not isinstance(payload, Mapping):
        raise StyleIRError("style artifact must be a JSON object")
    _require_schema_version(payload, "style artifact", STYLE_IR_SCHEMA_VERSION)

    style_ops = payload.get("styleOps")
    if not isinstance(style_ops, dict):
        raise StyleIRError("style artifact is missing object styleOps")
    _require_schema_version(style_ops, "styleOps", STYLE_OPS_SCHEMA_VERSION)
    if style_ops.get("format") != STYLE_OPS_FORMAT:
        raise StyleIRError(
            f"styleOps format must be {STYLE_OPS_FORMAT!r}; "
            f"got {style_ops.get('format')!r}"
        )

    rules = _require_payload_list(payload, "rules", default=())
    direct_styles = _require_payload_list(payload, "directStyles", default=())
    classes = _require_payload_list(style_ops, "classes", default=(), label="styleOps")
    direct_style_ops = _require_payload_list(
        style_ops,
        "directStyles",
        default=(),
        label="styleOps",
    )
    normalized_style_ops = dict(style_ops)
    normalized_style_ops["classes"] = list(classes)
    normalized_style_ops["directStyles"] = list(direct_style_ops)

    return StyleIRArtifact(
        payload=dict(payload),
        style_ops=normalized_style_ops,
        rules=tuple(rules),
        direct_styles=tuple(direct_styles),
        rules_by_class=_rules_by_class(rules),
        direct_styles_by_path=_direct_styles_by_path(direct_styles),
        direct_styles_by_node_id=_direct_styles_by_node_id(direct_styles),
        style_support=style_ops_support_map(normalized_style_ops),
    )


def style_ops_support_map(style_ops: dict[str, Any]) -> dict[str, str]:
    capabilities = style_ops.get("capabilities")
    if not isinstance(capabilities, dict):
        return {}
    styles = capabilities.get("styles")
    if not isinstance(styles, dict):
        return {}
    return {
        property_name: support
        for property_name, support in styles.items()
        if isinstance(property_name, str) and isinstance(support, str)
    }


def payload_path(path_payload: Any) -> tuple[int, ...] | None:
    if not isinstance(path_payload, list):
        return None
    path: list[int] = []
    for item in path_payload:
        if type(item) is not int or item < 0:
            return None
        path.append(item)
    return tuple(path)


def _require_schema_version(
    payload: Mapping[str, Any],
    label: str,
    expected: int,
) -> None:
    version = payload.get("schemaVersion")
    if version != expected:
        raise StyleIRError(
            f"{label}: unsupported schemaVersion {version!r}; expected {expected}"
        )


def _require_payload_list(
    payload: Mapping[str, Any],
    key: str,
    *,
    default: tuple[Any, ...],
    label: str = "style artifact",
) -> tuple[Any, ...]:
    value = payload.get(key, list(default))
    if not isinstance(value, list):
        raise StyleIRError(f"{label} {key} must be a list")
    return tuple(value)


def _rules_by_class(rules: tuple[Any, ...]) -> dict[str, dict[str, Any]]:
    return {
        rule["className"]: rule
        for rule in rules
        if isinstance(rule, dict) and isinstance(rule.get("className"), str)
    }


def _direct_styles_by_path(
    direct_styles: tuple[Any, ...],
) -> dict[tuple[int, ...], dict[str, Any]]:
    return {
        path: direct_style
        for direct_style in direct_styles
        if isinstance(direct_style, dict)
        and (path := payload_path(direct_style.get("path"))) is not None
    }


def _direct_styles_by_node_id(
    direct_styles: tuple[Any, ...],
) -> dict[str, dict[str, Any]]:
    return {
        node_id: direct_style
        for direct_style in direct_styles
        if isinstance(direct_style, dict)
        and (node_id := _payload_node_id(direct_style.get("nodeId"))) is not None
    }


def _payload_node_id(node_id_payload: Any) -> str | None:
    if isinstance(node_id_payload, str) and node_id_payload:
        return node_id_payload
    return None
