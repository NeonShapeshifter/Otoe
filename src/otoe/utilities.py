from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from .style import Size, StyleRule, StyleSheet, Token


DEFAULT_UTILITY_TOKENS: dict[str, str] = {
    "bg": "#f5f7fb",
    "panel": "#ffffff",
    "panel-soft": "#f8fafc",
    "ink": "#172033",
    "muted": "#607086",
    "quiet": "#8793a6",
    "line": "#dfe5ee",
    "accent": "#2563eb",
    "accent-soft": "#e9efff",
    "success": "#16835b",
    "success-soft": "#e8f7ef",
    "warn": "#b77912",
    "warn-soft": "#fff5db",
    "danger": "#c8374b",
    "danger-soft": "#ffe8ec",
    "white": "#ffffff",
}

SPACING_SCALE: dict[str, int] = {
    "0": 0,
    "1": 4,
    "2": 8,
    "3": 12,
    "4": 16,
    "5": 20,
    "6": 24,
    "8": 32,
    "10": 40,
    "12": 48,
}
RADIUS_SCALE: dict[str, int] = {
    "none": 0,
    "sm": 4,
    "md": 8,
    "lg": 12,
    "xl": 16,
    "full": 999,
}
FONT_SIZE_SCALE: dict[str, int] = {
    "xs": 12,
    "sm": 13,
    "base": 14,
    "lg": 16,
    "xl": 20,
}
FONT_WEIGHT_SCALE: dict[str, int] = {
    "normal": 400,
    "medium": 560,
    "semibold": 650,
    "bold": 760,
}
SHADOW_SCALE: dict[str, str] = {
    "none": "none",
    "sm": "0 8px 20px rgba(23, 32, 51, 0.08)",
    "md": "0 18px 44px rgba(23, 32, 51, 0.12)",
}

_STYLE_PROPERTY_MAP = {
    "align-items": "alignItems",
    "background": "background",
    "border-color": "borderColor",
    "border-radius": "borderRadius",
    "border-style": "borderStyle",
    "border-width": "borderWidth",
    "color": "color",
    "display": "display",
    "font-size": "fontSize",
    "font-weight": "fontWeight",
    "gap": "gap",
    "height": "height",
    "justify-content": "justifyContent",
    "margin": "margin",
    "max-height": "maxHeight",
    "max-width": "maxWidth",
    "min-height": "minHeight",
    "min-width": "minWidth",
    "opacity": "opacity",
    "padding": "padding",
    "width": "width",
}
_DIMENSION_PROPS = {
    "borderRadius",
    "borderWidth",
    "fontSize",
    "gap",
    "height",
    "margin",
    "maxHeight",
    "maxWidth",
    "minHeight",
    "minWidth",
    "padding",
    "width",
}


def utility_css(*, tokens: Mapping[str, str] | None = None) -> str:
    """Return Otoe's low-level HTML utility stylesheet."""

    merged_tokens = _merged_tokens(tokens)
    lines = [":root {"]
    for name, value in merged_tokens.items():
        lines.append(f"  --otoe-{name}: {value};")
    lines.extend(["}", ""])

    for class_name, declarations in _utility_rules(merged_tokens).items():
        lines.append(f".{class_name} {{")
        for name, value in declarations:
            lines.append(f"  {name}: {value};")
        lines.extend(["}", ""])
    return "\n".join(lines).rstrip() + "\n"


def utility_stylesheet(*, tokens: Mapping[str, str] | None = None) -> StyleSheet:
    """Return a strict-checkable portable subset of the utility layer."""

    merged_tokens = _merged_tokens(tokens)
    rules: dict[str, StyleRule] = {}
    for class_name, declarations in _utility_rules(merged_tokens).items():
        rules[f".{class_name}"] = StyleRule(
            selector=f".{class_name}",
            declarations=_portable_declarations(declarations),
        )
    return StyleSheet(rules=rules, tokens=_stylesheet_tokens(merged_tokens))


def _utility_rules(
    token_names: Iterable[str] | None = None,
) -> dict[str, tuple[tuple[str, str], ...]]:
    rules: dict[str, tuple[tuple[str, str], ...]] = {}

    rules.update(
        {
            "block": (("display", "block"),),
            "flex": (("display", "flex"),),
            "inline-flex": (("display", "inline-flex"),),
            "grid": (("display", "grid"),),
            "hidden": (("display", "none"),),
            "flex-row": (("flex-direction", "row"),),
            "flex-col": (("flex-direction", "column"),),
            "flex-wrap": (("flex-wrap", "wrap"),),
            "flex-1": (("flex", "1 1 0%"),),
            "grow": (("flex-grow", "1"),),
            "shrink-0": (("flex-shrink", "0"),),
            "items-start": (("align-items", "flex-start"),),
            "items-center": (("align-items", "center"),),
            "items-end": (("align-items", "flex-end"),),
            "items-stretch": (("align-items", "stretch"),),
            "justify-start": (("justify-content", "flex-start"),),
            "justify-center": (("justify-content", "center"),),
            "justify-end": (("justify-content", "flex-end"),),
            "justify-between": (("justify-content", "space-between"),),
            "justify-around": (("justify-content", "space-around"),),
            "justify-evenly": (("justify-content", "space-evenly"),),
            "mx-auto": (("margin-left", "auto"), ("margin-right", "auto")),
            "min-w-0": (("min-width", "0"),),
            "min-h-0": (("min-height", "0"),),
            "min-h-screen": (("min-height", "100vh"),),
            "w-full": (("width", "100%"),),
            "w-64": (("width", "256px"),),
            "w-72": (("width", "288px"),),
            "w-80": (("width", "320px"),),
            "w-96": (("width", "384px"),),
            "h-full": (("height", "100%"),),
            "max-w-full": (("max-width", "100%"),),
            "max-w-5xl": (("max-width", "1024px"),),
            "max-w-6xl": (("max-width", "1152px"),),
            "max-w-7xl": (("max-width", "1280px"),),
            "overflow-hidden": (("overflow", "hidden"),),
            "truncate": (
                ("overflow", "hidden"),
                ("text-overflow", "ellipsis"),
                ("white-space", "nowrap"),
            ),
            "text-left": (("text-align", "left"),),
            "text-center": (("text-align", "center"),),
            "text-right": (("text-align", "right"),),
        }
    )

    for name, value in SPACING_SCALE.items():
        px = f"{value}px"
        rules[f"p-{name}"] = (("padding", px),)
        rules[f"m-{name}"] = (("margin", px),)
        rules[f"gap-{name}"] = (("gap", px),)
        rules[f"px-{name}"] = (("padding-left", px), ("padding-right", px))
        rules[f"py-{name}"] = (("padding-top", px), ("padding-bottom", px))

    for name, value in FONT_SIZE_SCALE.items():
        rules[f"text-{name}"] = (("font-size", f"{value}px"),)
    for name, value in FONT_WEIGHT_SCALE.items():
        rules[f"font-{name}"] = (("font-weight", str(value)),)

    for name in token_names or DEFAULT_UTILITY_TOKENS:
        token = f"var(--otoe-{name})"
        rules[f"bg-{name}"] = (("background", token),)
        rules[f"text-{name}"] = (("color", token),)
        rules[f"border-{name}"] = (("border-color", token),)

    rules["border"] = (
        ("border-width", "1px"),
        ("border-style", "solid"),
        ("border-color", "var(--otoe-line)"),
    )
    rules["border-0"] = (("border-width", "0"),)
    for name, value in RADIUS_SCALE.items():
        rules[f"rounded-{name}"] = (("border-radius", f"{value}px"),)
    for name, value in SHADOW_SCALE.items():
        rules[f"shadow-{name}"] = (("box-shadow", value),)

    rules["opacity-0"] = (("opacity", "0"),)
    rules["opacity-50"] = (("opacity", "0.5"),)
    rules["opacity-100"] = (("opacity", "1"),)
    return rules


def _portable_declarations(
    declarations: tuple[tuple[str, str], ...],
) -> dict[str, Any]:
    portable: dict[str, Any] = {}
    for css_name, raw_value in declarations:
        prop = _STYLE_PROPERTY_MAP.get(css_name)
        if prop is None:
            continue
        value = _portable_value(prop, raw_value)
        if value is None:
            continue
        portable[prop] = value
    return portable


def _portable_value(prop: str, raw_value: str) -> Any:
    token = _token_from_var(raw_value)
    if token is not None:
        return Token(token)
    if prop in _DIMENSION_PROPS:
        if raw_value.endswith("%"):
            return None
        if raw_value.endswith("px"):
            return Size(_number(raw_value[:-2]))
        if _is_number(raw_value):
            return Size(_number(raw_value))
        return None
    if _is_number(raw_value):
        number = _number(raw_value)
        return number
    return raw_value


def _merged_tokens(tokens: Mapping[str, str] | None) -> dict[str, str]:
    return {**DEFAULT_UTILITY_TOKENS, **dict(tokens or {})}


def _stylesheet_tokens(tokens: Mapping[str, str] | None) -> dict[str, str]:
    return {
        f"otoe-{name}": value
        for name, value in _merged_tokens(tokens).items()
    }


def _token_from_var(value: str) -> str | None:
    prefix = "var(--"
    suffix = ")"
    if value.startswith(prefix) and value.endswith(suffix):
        return value[len(prefix) : -len(suffix)]
    return None


def _number(value: str) -> int | float:
    number = float(value)
    return int(number) if number.is_integer() else number


def _is_number(value: str) -> bool:
    try:
        float(value)
    except ValueError:
        return False
    return True
