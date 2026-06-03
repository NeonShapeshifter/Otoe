from __future__ import annotations

from typing import Any

from .plan import (
    PLAN_STATUSES,
    OtoePlan,
)
from .style import Size, StyleSheet, Token, style_value_to_dict
from .style_ir import compiled_styles_to_dict as _compiled_styles_to_dict


def format_plan(plan: OtoePlan, *, target: str) -> str:
    lines = [
        f"plan {target}: profile {plan.profile}",
        f"backend: {plan.backend}",
        f"widgets: {plan.widget_count}",
        f"widget support: {_format_named_counts(plan.widget_support_counts)}",
        (
            "classes: "
            f"{len(plan.used_classes)} used, "
            f"{len(plan.planned_classes)} planned, "
            f"{len(plan.html_only_classes)} html-only, "
            f"{len(plan.invalid_classes)} invalid"
        ),
        f"style declarations: {_format_counts(plan.style_counts)}",
        f"direct style props: {_format_counts(plan.direct_style_counts)}",
        f"status: {plan.status}",
    ]
    if plan.used_classes:
        lines.append(f"used classes: {', '.join(plan.used_classes)}")
    if plan.static_classes:
        lines.append(f"static classes: {', '.join(plan.static_classes)}")
    if plan.safelisted_classes:
        lines.append(f"safelisted classes: {', '.join(plan.safelisted_classes)}")
    for diagnostic in plan.diagnostics:
        lines.append(f"{diagnostic.level}: {diagnostic.message}")
    return "\n".join(lines)


def plan_to_dict(plan: OtoePlan, *, target: str) -> dict[str, Any]:
    return {
        "schemaVersion": 1,
        "target": target,
        "profile": plan.profile,
        "backend": plan.backend,
        "status": plan.status,
        "hasErrors": plan.has_errors,
        "hasWarnings": plan.has_warnings,
        "widgetCount": plan.widget_count,
        "widgetSupportCounts": dict(plan.widget_support_counts),
        "backendCapabilities": plan.backend_capabilities.to_dict(),
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
        "directStyles": [
            {
                "path": list(entry.path),
                "widget": entry.widget,
                "declarations": {
                    declaration.property: _artifact_style_value_to_dict(
                        declaration.value
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
            for entry in plan.direct_styles
        ],
        "diagnostics": [
            {"level": diagnostic.level, "message": diagnostic.message}
            for diagnostic in plan.diagnostics
        ],
    }


def compiled_styles_to_dict(
    plan: OtoePlan,
    *,
    target: str,
    stylesheet: StyleSheet | None,
) -> dict[str, Any]:
    return _compiled_styles_to_dict(plan, target=target, stylesheet=stylesheet)


def _format_counts(counts: dict[str, int]) -> str:
    return ", ".join(f"{status}={counts[status]}" for status in PLAN_STATUSES)


def _format_named_counts(counts: dict[str, int]) -> str:
    return ", ".join(f"{name}={count}" for name, count in sorted(counts.items()))


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
