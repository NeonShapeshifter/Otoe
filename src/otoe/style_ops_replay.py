from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ._native_shared import native_style_support
from .style_ops_types import StyleOpsClassReplay, StyleOpsDirectReplay
from .style_ops_values import style_value_payload_errors


def style_op_support(
    property_name: Any,
    style_support: Mapping[str, str] | None,
) -> str:
    if not isinstance(property_name, str):
        return "unsupported"
    if style_support is not None and property_name in style_support:
        return style_support[property_name]
    return native_style_support(property_name) or "unsupported"


def replay_style_ops_class(
    class_payload: Any,
    *,
    style_support: Mapping[str, str] | None = None,
) -> StyleOpsClassReplay:
    if not isinstance(class_payload, dict):
        return StyleOpsClassReplay(
            class_name="<invalid>",
            selector="",
            missing=False,
            applied_declarations={},
            omitted_ops=(),
            errors=("styleOps class entry must be an object",),
        )

    errors: list[str] = []
    class_name = class_payload.get("className")
    if not isinstance(class_name, str):
        class_name = "<invalid>"
        errors.append("styleOps className must be a string")
    selector = class_payload.get("selector")
    if not isinstance(selector, str):
        selector = ""
        errors.append("styleOps selector must be a string")
    missing = class_payload.get("missing")
    if not isinstance(missing, bool):
        missing = False
        errors.append("styleOps missing must be a boolean")

    applied_declarations = _replay_set_style_ops(
        class_name,
        class_payload.get("ops", []),
        errors,
        style_support,
    )
    omitted_ops = _replay_omitted_style_ops(
        class_name,
        class_payload.get("omittedOps", []),
        errors,
        style_support,
    )

    return StyleOpsClassReplay(
        class_name=class_name,
        selector=selector,
        missing=missing,
        applied_declarations=applied_declarations,
        omitted_ops=omitted_ops,
        errors=tuple(errors),
    )


def replay_style_ops_direct(
    direct_payload: Any,
    *,
    style_support: Mapping[str, str] | None = None,
) -> StyleOpsDirectReplay:
    if not isinstance(direct_payload, dict):
        return StyleOpsDirectReplay(
            path=(),
            node_id=None,
            widget="<invalid>",
            applied_declarations={},
            omitted_ops=(),
            errors=("styleOps directStyles entry must be an object",),
        )

    errors: list[str] = []
    path = _style_ops_path(direct_payload.get("path"), errors)
    node_id = _style_ops_node_id(direct_payload.get("nodeId"), errors)
    widget = direct_payload.get("widget")
    if not isinstance(widget, str):
        widget = "<invalid>"
        errors.append("styleOps directStyles widget must be a string")

    label = f"direct style {list(path)}"
    applied_declarations = _replay_set_style_ops(
        label,
        direct_payload.get("ops", []),
        errors,
        style_support,
    )
    omitted_ops = _replay_omitted_style_ops(
        label,
        direct_payload.get("omittedOps", []),
        errors,
        style_support,
    )

    return StyleOpsDirectReplay(
        path=path,
        node_id=node_id,
        widget=widget,
        applied_declarations=applied_declarations,
        omitted_ops=omitted_ops,
        errors=tuple(errors),
    )


def expected_omitted_style_ops(
    rule_payload: dict[str, Any] | None,
    style_support: Mapping[str, str] | None = None,
) -> tuple[dict[str, Any], ...]:
    if not isinstance(rule_payload, dict):
        return ()
    omitted = rule_payload.get("omittedDeclarations", [])
    if not isinstance(omitted, list):
        return ()
    return tuple(
        {
            "op": "omitStyle",
            "property": declaration.get("property"),
            "support": style_op_support(declaration.get("property"), style_support),
            "status": declaration.get("status"),
            "value": declaration.get("value"),
            "message": declaration.get("message"),
        }
        for declaration in omitted
        if isinstance(declaration, dict)
    )


def _replay_set_style_ops(
    class_name: str,
    ops_payload: Any,
    errors: list[str],
    style_support: Mapping[str, str] | None,
) -> dict[str, Any]:
    if not isinstance(ops_payload, list):
        errors.append(f"styleOps class {class_name!r} ops must be a list")
        return {}

    applied_declarations: dict[str, Any] = {}
    for index, op_payload in enumerate(ops_payload):
        if not isinstance(op_payload, dict):
            errors.append(f"styleOps class {class_name!r} op {index} must be an object")
            continue
        if op_payload.get("op") != "setStyle":
            errors.append(
                f"styleOps class {class_name!r} op {index} must use op='setStyle'"
            )
            continue
        property_name = op_payload.get("property")
        if not isinstance(property_name, str):
            errors.append(
                f"styleOps class {class_name!r} op {index} property must be a string"
            )
            continue
        expected_support = style_op_support(property_name, style_support)
        if op_payload.get("support") != expected_support:
            errors.append(
                f"styleOps class {class_name!r} op {index} support "
                f"{op_payload.get('support')!r} does not match {expected_support!r}"
            )
        value = op_payload.get("value")
        errors.extend(
            style_value_payload_errors(
                value,
                label=f"styleOps class {class_name!r} op {index} value",
                portable=True,
            )
        )
        applied_declarations[property_name] = value
    return applied_declarations


def _replay_omitted_style_ops(
    class_name: str,
    omitted_ops_payload: Any,
    errors: list[str],
    style_support: Mapping[str, str] | None,
) -> tuple[dict[str, Any], ...]:
    if not isinstance(omitted_ops_payload, list):
        errors.append(f"styleOps class {class_name!r} omittedOps must be a list")
        return ()

    omitted_ops: list[dict[str, Any]] = []
    for index, op_payload in enumerate(omitted_ops_payload):
        if not isinstance(op_payload, dict):
            errors.append(
                f"styleOps class {class_name!r} omitted op {index} must be an object"
            )
            continue
        omitted_ops.append(
            _normalize_style_omitted_op(
                class_name,
                index,
                op_payload,
                errors,
                style_support,
            )
        )
    return tuple(omitted_ops)


def _normalize_style_omitted_op(
    class_name: str,
    index: int,
    op_payload: dict[str, Any],
    errors: list[str],
    style_support: Mapping[str, str] | None,
) -> dict[str, Any]:
    if op_payload.get("op") != "omitStyle":
        errors.append(
            f"styleOps class {class_name!r} omitted op {index} must use op='omitStyle'"
        )
    property_name = op_payload.get("property")
    if not isinstance(property_name, str):
        errors.append(
            f"styleOps class {class_name!r} omitted op {index} property must be a string"
        )
    expected_support = style_op_support(property_name, style_support)
    if op_payload.get("support") != expected_support:
        errors.append(
            f"styleOps class {class_name!r} omitted op {index} support "
            f"{op_payload.get('support')!r} does not match {expected_support!r}"
        )
    value = op_payload.get("value")
    errors.extend(
        style_value_payload_errors(
            value,
            label=f"styleOps class {class_name!r} omitted op {index} value",
            portable=False,
        )
    )
    return {
        "op": op_payload.get("op"),
        "property": property_name,
        "support": op_payload.get("support"),
        "status": op_payload.get("status"),
        "value": value,
        "message": op_payload.get("message"),
    }


def _style_ops_path(path_payload: Any, errors: list[str]) -> tuple[int, ...]:
    if not isinstance(path_payload, list):
        errors.append("styleOps directStyles path must be a list")
        return ()
    path: list[int] = []
    for index, item in enumerate(path_payload):
        if type(item) is not int or item < 0:
            errors.append(
                f"styleOps directStyles path item {index} must be a non-negative integer"
            )
            continue
        path.append(item)
    return tuple(path)


def _style_ops_node_id(node_id_payload: Any, errors: list[str]) -> str | None:
    if node_id_payload is None:
        errors.append("styleOps directStyles nodeId must be a non-empty string")
        return None
    if isinstance(node_id_payload, str) and node_id_payload:
        return node_id_payload
    errors.append("styleOps directStyles nodeId must be a non-empty string")
    return None
