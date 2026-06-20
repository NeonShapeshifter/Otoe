from __future__ import annotations

from typing import Any

from .capabilities import BackendCapabilityProfile
from ._style_schema import portable_dimension_properties
from ._native_shared import resolve_token
from ._style_planning import classify_style_value, planned_class_names
from .plan import OtoePlan
from .style import DIMENSION_PROPERTIES, Size, StyleSheet, Token, style_value_to_dict
from .style_ops import (
    STYLE_IR_SCHEMA_VERSION,
    STYLE_OPS_FORMAT,
    STYLE_OPS_SCHEMA_VERSION,
    AppliedStyleOps,
    StyleIRArtifact,
    StyleIRError,
    StyleOpsClassReplay,
    StyleOpsDirectReplay,
    StyleOpsValidation,
    apply_style_ops,
    expected_omitted_style_ops,
    load_style_ir,
    replay_style_ops_class,
    replay_style_ops_direct,
    style_op_support,
    style_ops_support_map,
    validate_style_ops,
)

__all__ = [
    "BackendCapabilityProfile",
    "resolve_token",
    "OtoePlan",
    "DIMENSION_PROPERTIES",
    "Size",
    "StyleSheet",
    "Token",
    "style_value_to_dict",
    "STYLE_IR_SCHEMA_VERSION",
    "STYLE_OPS_FORMAT",
    "STYLE_OPS_SCHEMA_VERSION",
    "AppliedStyleOps",
    "StyleIRArtifact",
    "StyleIRError",
    "StyleOpsClassReplay",
    "StyleOpsDirectReplay",
    "StyleOpsValidation",
    "apply_style_ops",
    "expected_omitted_style_ops",
    "load_style_ir",
    "replay_style_ops_class",
    "replay_style_ops_direct",
    "style_op_support",
    "style_ops_support_map",
    "validate_style_ops",
    "PORTABLE_DIMENSION_PROPERTIES",
    "compiled_styles_to_dict",
]


PORTABLE_DIMENSION_PROPERTIES = portable_dimension_properties()


def compiled_styles_to_dict(
    plan: OtoePlan,
    *,
    target: str,
    stylesheet: StyleSheet | None,
) -> dict[str, Any]:
    return {
        "schemaVersion": STYLE_IR_SCHEMA_VERSION,
        "target": target,
        "profile": plan.profile,
        "backend": plan.backend,
        "status": plan.status,
        "classes": {
            "used": list(plan.used_classes),
            "static": list(plan.static_classes),
            "safelisted": list(plan.safelisted_classes),
            "planned": list(plan.planned_classes),
            "htmlOnly": list(plan.html_only_classes),
            "invalid": list(plan.invalid_classes),
        },
        "styleCounts": dict(plan.style_counts),
        "directStyleCounts": dict(plan.direct_style_counts),
        "backendCapabilities": plan.backend_capabilities.to_dict(),
        "tokens": _compiled_tokens(stylesheet),
        "rules": _compiled_rules(plan, stylesheet),
        "directStyles": _compiled_direct_styles(plan, stylesheet),
        "styleOps": _compiled_style_ops(plan, stylesheet),
        "diagnostics": [
            {"level": diagnostic.level, "message": diagnostic.message}
            for diagnostic in plan.diagnostics
        ],
    }


def _compiled_tokens(stylesheet: StyleSheet | None) -> dict[str, dict[str, Any]]:
    if stylesheet is None:
        return {}
    return {
        name: style_value_to_dict(value)
        for name, value in sorted(stylesheet.tokens.items())
    }


def _compiled_rules(
    plan: OtoePlan,
    stylesheet: StyleSheet | None,
) -> list[dict[str, Any]]:
    rules: list[dict[str, Any]] = []
    for class_name in _compiled_class_names(plan):
        selector = f".{class_name}"
        rule = stylesheet.rules.get(selector) if stylesheet is not None else None
        if rule is None:
            rules.append(
                {
                    "className": class_name,
                    "selector": selector,
                    "declarations": {},
                    "omittedDeclarations": [],
                    "missing": True,
                }
            )
            continue

        assert stylesheet is not None
        declarations: dict[str, dict[str, Any]] = {}
        omitted: list[dict[str, Any]] = []
        for prop, value in rule.declarations.items():
            status, message = classify_style_value(
                prop,
                value,
                stylesheet,
                plan.backend_capabilities,
            )
            resolved = resolve_token(value, stylesheet.tokens)
            if status == "portable":
                declarations[prop] = _portable_style_value_to_dict(prop, resolved)
            else:
                omitted.append(
                    {
                        "property": prop,
                        "status": status,
                        "value": _artifact_style_value_to_dict(value),
                        "message": message,
                    }
                )
        rules.append(
            {
                "className": class_name,
                "selector": selector,
                "declarations": declarations,
                "omittedDeclarations": omitted,
                "missing": False,
            }
        )
    return rules


def _compiled_style_ops(
    plan: OtoePlan,
    stylesheet: StyleSheet | None,
) -> dict[str, Any]:
    return {
        "schemaVersion": STYLE_OPS_SCHEMA_VERSION,
        "format": STYLE_OPS_FORMAT,
        "backend": plan.backend,
        "capabilities": {
            "styles": dict(sorted(plan.backend_capabilities.style_support.items())),
        },
        "classes": [
            _compiled_class_style_ops(
                class_name,
                stylesheet,
                plan.backend_capabilities,
            )
            for class_name in _compiled_class_names(plan)
        ],
        "directStyles": [
            _compiled_direct_style_ops(
                entry,
                stylesheet,
                plan.backend_capabilities,
            )
            for entry in plan.direct_styles
        ],
    }


def _compiled_class_style_ops(
    class_name: str,
    stylesheet: StyleSheet | None,
    capabilities: BackendCapabilityProfile,
) -> dict[str, Any]:
    selector = f".{class_name}"
    rule = stylesheet.rules.get(selector) if stylesheet is not None else None
    if rule is None:
        return {
            "className": class_name,
            "selector": selector,
            "missing": True,
            "ops": [],
            "omittedOps": [],
        }

    assert stylesheet is not None
    ops: list[dict[str, Any]] = []
    omitted_ops: list[dict[str, Any]] = []
    for prop, value in rule.declarations.items():
        status, message = classify_style_value(prop, value, stylesheet, capabilities)
        support = capabilities.style(prop) or "unsupported"
        resolved = resolve_token(value, stylesheet.tokens)
        if status == "portable":
            ops.append(
                {
                    "op": "setStyle",
                    "property": prop,
                    "support": support,
                    "value": _portable_style_value_to_dict(prop, resolved),
                }
            )
            continue
        omitted_ops.append(
            {
                "op": "omitStyle",
                "property": prop,
                "support": support,
                "status": status,
                "value": _artifact_style_value_to_dict(value),
                "message": message,
            }
        )

    return {
        "className": class_name,
        "selector": selector,
        "missing": False,
        "ops": ops,
        "omittedOps": omitted_ops,
    }


def _compiled_class_names(plan: OtoePlan) -> tuple[str, ...]:
    return planned_class_names(
        used_classes=plan.used_classes,
        static_classes=plan.static_classes,
        safelisted_classes=plan.safelisted_classes,
    )


def _compiled_direct_styles(
    plan: OtoePlan,
    stylesheet: StyleSheet | None,
) -> list[dict[str, Any]]:
    tokens = stylesheet.tokens if stylesheet is not None else {}
    entries: list[dict[str, Any]] = []
    for entry in plan.direct_styles:
        entries.append(
            {
                "path": list(entry.path),
                "nodeId": entry.node_id,
                "widget": entry.widget,
                "declarations": {
                    declaration.property: _portable_style_value_to_dict(
                        declaration.property,
                        resolve_token(declaration.value, tokens),
                    )
                    for declaration in entry.declarations
                },
                "omittedDeclarations": [
                    {
                        "property": omission.property,
                        "status": omission.status,
                        "value": _artifact_style_value_to_dict(omission.value),
                        "message": omission.message,
                    }
                    for omission in entry.omitted_declarations
                ],
            }
        )
    return entries


def _compiled_direct_style_ops(
    entry: Any,
    stylesheet: StyleSheet | None,
    capabilities: BackendCapabilityProfile,
) -> dict[str, Any]:
    tokens = stylesheet.tokens if stylesheet is not None else {}
    ops = [
        {
            "op": "setStyle",
            "property": declaration.property,
            "support": capabilities.style(declaration.property) or "unsupported",
            "value": _portable_style_value_to_dict(
                declaration.property,
                resolve_token(declaration.value, tokens),
            ),
        }
        for declaration in entry.declarations
    ]
    omitted_ops = [
        {
            "op": "omitStyle",
            "property": omission.property,
            "support": capabilities.style(omission.property) or "unsupported",
            "status": omission.status,
            "value": _artifact_style_value_to_dict(omission.value),
            "message": omission.message,
        }
        for omission in entry.omitted_declarations
    ]
    return {
        "path": list(entry.path),
        "nodeId": entry.node_id,
        "widget": entry.widget,
        "ops": ops,
        "omittedOps": omitted_ops,
    }


def _portable_style_value_to_dict(prop: str, value: Any) -> dict[str, Any]:
    return style_value_to_dict(_portable_style_value(prop, value))


def _portable_style_value(prop: str, value: Any) -> Any:
    if prop in PORTABLE_DIMENSION_PROPERTIES and type(value) in {int, float}:
        return Size(value)
    return value


def _artifact_style_value_to_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, (Size, Token)):
        return style_value_to_dict(value)
    if value is None or type(value) in {str, int, float, bool}:
        return style_value_to_dict(value)
    return {
        "type": "runtime",
        "valueType": type(value).__name__,
        "repr": repr(value),
    }
