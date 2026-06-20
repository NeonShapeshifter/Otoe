from __future__ import annotations

from typing import Any, Iterable

from ._native_contracts import NativePaintError
from ._native_shared import parse_color, resolve_token
from .capabilities import BackendCapabilityProfile
from .style import DIMENSION_PROPERTIES, Size, StyleSheet, Token


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


def classify_style_value(
    prop: str,
    value: Any,
    stylesheet: StyleSheet | None,
    capabilities: BackendCapabilityProfile,
) -> tuple[str, str | None]:
    native_support = capabilities.style(prop)
    if native_support is None:
        return "invalid", f"unsupported native style property {prop!r}"
    if native_support == "ignored":
        return "html-only", f"property {prop!r} is accepted but ignored by native"

    resolved = resolve_token(value, stylesheet.tokens if stylesheet is not None else {})
    if isinstance(resolved, Token):
        return "invalid", f"unresolved token {resolved.name!r}"

    if prop in DIMENSION_PROPERTIES:
        dimension_status = classify_dimension(prop, resolved)
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


def classify_dimension(prop: str, value: Any) -> tuple[str, str] | None:
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


def planned_class_names(
    *,
    used_classes: tuple[str, ...],
    static_classes: tuple[str, ...],
    safelisted_classes: tuple[str, ...],
) -> tuple[str, ...]:
    return dedupe_names((*used_classes, *static_classes, *safelisted_classes))


def dedupe_names(values: Iterable[str]) -> tuple[str, ...]:
    seen = set()
    result = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return tuple(result)
