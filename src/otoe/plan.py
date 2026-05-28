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
from .style import DIMENSION_PROPERTIES, Size, StyleSheet, Token


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
    strict_styles: bool = True,
) -> OtoePlan:
    if profile not in SUPPORTED_PLAN_PROFILES:
        raise PlanError(f"unsupported plan profile {profile!r}; supported: cage")

    widget = root_widget(target)
    widgets = walk_widgets(widget)
    used_classes = _used_classes(widgets)
    planned_classes: list[str] = []
    html_only_classes: list[str] = []
    invalid_classes: list[str] = []
    diagnostics: list[PlanDiagnostic] = []
    style_counts = _empty_counts()
    direct_style_counts = _empty_counts()

    for class_name in used_classes:
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
