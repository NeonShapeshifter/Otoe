from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ._native_shared import (
    NATIVE_STYLE_SUPPORT,
    parse_color,
    resolve_token,
    walk_widgets,
)
from ._native_contracts import NativePaintError
from .mount import MountedNode, root_widget
from .style import DIMENSION_PROPERTIES, Size, StyleSheet, Token, style_value_to_dict


PLAN_STATUSES = ("portable", "html-only", "deferred", "invalid")
SUPPORTED_PLAN_PROFILES = frozenset({"cage"})
DIRECT_STYLE_PROPS = ("gap", "padding", "scrollY", "color")
TOKEN_STYLE_PROPS = frozenset({"background", "borderColor", "color"})
ALIGN_VALUES = frozenset({"start", "flex-start", "center", "end", "flex-end", "stretch"})
JUSTIFY_VALUES = frozenset(
    {
        "start",
        "flex-start",
        "center",
        "end",
        "flex-end",
        "space-between",
        "space-around",
        "space-evenly",
    }
)


class PlanError(ValueError):
    pass


@dataclass(frozen=True)
class PlanDiagnostic:
    level: str
    message: str


@dataclass(frozen=True)
class OtoePlan:
    profile: str
    widget_count: int
    used_classes: tuple[str, ...]
    static_classes: tuple[str, ...]
    safelisted_classes: tuple[str, ...]
    planned_classes: tuple[str, ...]
    html_only_classes: tuple[str, ...]
    invalid_classes: tuple[str, ...]
    style_counts: dict[str, int]
    direct_style_counts: dict[str, int]
    diagnostics: tuple[PlanDiagnostic, ...]

    @property
    def has_errors(self) -> bool:
        return any(diagnostic.level == "error" for diagnostic in self.diagnostics)

    @property
    def has_warnings(self) -> bool:
        if any(diagnostic.level == "warning" for diagnostic in self.diagnostics):
            return True
        return self.style_counts["html-only"] > 0 or self.style_counts["deferred"] > 0

    @property
    def status(self) -> str:
        if self.has_errors:
            return "invalid"
        if self.has_warnings:
            return "warnings"
        return "ok"


def plan_mounted(
    target: MountedNode,
    *,
    profile: str = "cage",
    stylesheet: StyleSheet | None = None,
    static_classes: tuple[str, ...] = (),
    safelist: tuple[str, ...] = (),
    diagnostics: tuple[PlanDiagnostic, ...] = (),
    strict_styles: bool = True,
) -> OtoePlan:
    if profile not in SUPPORTED_PLAN_PROFILES:
        raise PlanError(f"unsupported plan profile {profile!r}; supported: cage")

    widget = root_widget(target)
    widgets = walk_widgets(widget)
    used_classes = _used_classes(widgets)
    safelisted_classes = tuple(_dedupe(safelist))
    static_classes = tuple(
        _dedupe(
            class_name
            for class_name in static_classes
            if class_name not in used_classes and class_name not in safelisted_classes
        )
    )
    classes_to_plan = _planned_class_names(
        used_classes=used_classes,
        static_classes=static_classes,
        safelisted_classes=safelisted_classes,
    )
    planned_classes: list[str] = []
    html_only_classes: list[str] = []
    invalid_classes: list[str] = []
    diagnostics = list(diagnostics)
    style_counts = _empty_counts()
    direct_style_counts = _empty_counts()

    for class_name in classes_to_plan:
        rule = stylesheet.rules.get(f".{class_name}") if stylesheet is not None else None
        if rule is None:
            message = (
                f"class {class_name!r} has no portable rule for profile {profile!r}"
            )
            if strict_styles:
                invalid_classes.append(class_name)
                style_counts["invalid"] += 1
                diagnostics.append(PlanDiagnostic("error", message))
            else:
                html_only_classes.append(class_name)
                diagnostics.append(
                    PlanDiagnostic("warning", f"{message}; treating it as html-only")
                )
            continue

        planned_classes.append(class_name)
        if not rule.declarations:
            html_only_classes.append(class_name)
            diagnostics.append(
                PlanDiagnostic(
                    "warning",
                    f"class {class_name!r} has no portable declarations for profile {profile!r}",
                )
            )
            continue

        for prop, value in rule.declarations.items():
            status, message = _classify_style_value(prop, value, stylesheet)
            style_counts[status] += 1
            if message is not None:
                diagnostics.append(
                    PlanDiagnostic(
                        "error" if status == "invalid" else "warning",
                        f"class {class_name!r}: {message}",
                    )
                )

    for widget in widgets:
        for prop in DIRECT_STYLE_PROPS:
            if prop not in widget.props:
                continue
            status, message = _classify_style_value(
                prop,
                widget.props[prop],
                stylesheet,
            )
            direct_style_counts[status] += 1
            if message is not None:
                diagnostics.append(
                    PlanDiagnostic(
                        "error" if status == "invalid" else "warning",
                        f"{widget.name} direct style {prop!r}: {message}",
                    )
                )

    return OtoePlan(
        profile=profile,
        widget_count=len(widgets),
        used_classes=used_classes,
        static_classes=static_classes,
        safelisted_classes=safelisted_classes,
        planned_classes=tuple(planned_classes),
        html_only_classes=tuple(_dedupe(html_only_classes)),
        invalid_classes=tuple(_dedupe(invalid_classes)),
        style_counts=style_counts,
        direct_style_counts=direct_style_counts,
        diagnostics=tuple(diagnostics),
    )


def format_plan(plan: OtoePlan, *, target: str) -> str:
    lines = [
        f"plan {target}: profile {plan.profile}",
        f"widgets: {plan.widget_count}",
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
        "status": plan.status,
        "hasErrors": plan.has_errors,
        "hasWarnings": plan.has_warnings,
        "widgetCount": plan.widget_count,
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
    return {
        "schemaVersion": 1,
        "target": target,
        "profile": plan.profile,
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
        "tokens": _compiled_tokens(stylesheet),
        "rules": _compiled_rules(plan, stylesheet),
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

        declarations: dict[str, dict[str, Any]] = {}
        omitted: list[dict[str, Any]] = []
        for prop, value in rule.declarations.items():
            status, message = _classify_style_value(prop, value, stylesheet)
            resolved = resolve_token(value, stylesheet.tokens)
            if status == "portable":
                declarations[prop] = style_value_to_dict(resolved)
            else:
                omitted.append(
                    {
                        "property": prop,
                        "status": status,
                        "value": style_value_to_dict(value),
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
        "schemaVersion": 1,
        "format": "otoe-style-ops",
        "classes": [
            _compiled_class_style_ops(class_name, stylesheet)
            for class_name in _compiled_class_names(plan)
        ],
    }


def _compiled_class_style_ops(
    class_name: str,
    stylesheet: StyleSheet | None,
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

    ops: list[dict[str, Any]] = []
    omitted_ops: list[dict[str, Any]] = []
    for prop, value in rule.declarations.items():
        status, message = _classify_style_value(prop, value, stylesheet)
        support = NATIVE_STYLE_SUPPORT.get(prop, "unsupported")
        resolved = resolve_token(value, stylesheet.tokens)
        if status == "portable":
            ops.append(
                {
                    "op": "setStyle",
                    "property": prop,
                    "support": support,
                    "value": style_value_to_dict(resolved),
                }
            )
            continue
        omitted_ops.append(
            {
                "op": "omitStyle",
                "property": prop,
                "support": support,
                "status": status,
                "value": style_value_to_dict(value),
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


def _classify_style_value(
    prop: str,
    value: Any,
    stylesheet: StyleSheet | None,
) -> tuple[str, str | None]:
    native_support = NATIVE_STYLE_SUPPORT.get(prop)
    if native_support is None:
        return "invalid", f"unsupported native style property {prop!r}"
    if native_support == "ignored":
        return "html-only", f"property {prop!r} is accepted but ignored by native"

    resolved = resolve_token(value, stylesheet.tokens if stylesheet is not None else {})
    if isinstance(resolved, Token):
        return "invalid", f"unresolved token {resolved.name!r}"

    if prop in DIMENSION_PROPERTIES:
        dimension_status = _classify_dimension(prop, resolved)
        if dimension_status is not None:
            return dimension_status

    if prop in TOKEN_STYLE_PROPS and isinstance(resolved, str):
        try:
            parse_color(resolved)
        except NativePaintError as exc:
            return "invalid", str(exc)

    if prop == "alignItems" and str(resolved) not in ALIGN_VALUES:
        return "invalid", f"unsupported native alignItems value {resolved!r}"
    if prop == "justifyContent" and str(resolved) not in JUSTIFY_VALUES:
        return "invalid", f"unsupported native justifyContent value {resolved!r}"

    return "portable", None


def _classify_dimension(prop: str, value: Any) -> tuple[str, str] | None:
    if isinstance(value, Size):
        if value.unit != "px":
            return "deferred", f"property {prop!r} uses non-px dimension {value.unit!r}"
        if value.value < 0:
            return "invalid", f"property {prop!r} uses negative dimension {value.value!r}"
        return None
    if isinstance(value, (int, float)):
        if value < 0:
            return "invalid", f"property {prop!r} uses negative dimension {value!r}"
        return None
    return "deferred", f"property {prop!r} needs a px dimension, got {value!r}"


def _used_classes(widgets) -> tuple[str, ...]:
    class_names: list[str] = []
    for widget in widgets:
        raw = widget.props.get("className")
        if raw is None:
            continue
        class_names.extend(name for name in str(raw).split() if name)
    return tuple(_dedupe(class_names))


def _compiled_class_names(plan: OtoePlan) -> tuple[str, ...]:
    return _planned_class_names(
        used_classes=plan.used_classes,
        static_classes=plan.static_classes,
        safelisted_classes=plan.safelisted_classes,
    )


def _planned_class_names(
    *,
    used_classes: tuple[str, ...],
    static_classes: tuple[str, ...],
    safelisted_classes: tuple[str, ...],
) -> tuple[str, ...]:
    return _dedupe((*used_classes, *static_classes, *safelisted_classes))


def _dedupe(values) -> tuple[str, ...]:
    seen = set()
    result = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return tuple(result)


def _empty_counts() -> dict[str, int]:
    return {status: 0 for status in PLAN_STATUSES}


def _format_counts(counts: dict[str, int]) -> str:
    return ", ".join(f"{status}={counts[status]}" for status in PLAN_STATUSES)
