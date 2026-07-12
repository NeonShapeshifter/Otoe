from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

from ._style_schema import (
    STYLE_PROPERTY_SPECS_BY_INTERNAL_NAME,
    dimension_properties,
    html_properties,
    supported_properties,
    token_properties,
)
from .style_ops_types import AppliedStyleOps


SUPPORTED_PROPERTIES = supported_properties()
HTML_PROPERTIES = html_properties()
DIMENSION_PROPERTIES = dimension_properties()
TOKEN_PROPERTIES = token_properties()
_ALIGN_ITEMS_VALUES = frozenset(
    {"baseline", "center", "end", "flex-end", "flex-start", "start", "stretch"}
)
_JUSTIFY_CONTENT_VALUES = frozenset(
    {
        "center",
        "end",
        "flex-end",
        "flex-start",
        "space-around",
        "space-between",
        "space-evenly",
        "start",
        "stretch",
    }
)
_OVERFLOW_VALUES = frozenset({"auto", "hidden", "scroll", "visible"})
_DISPLAY_VALUES = frozenset(
    {"block", "contents", "flex", "grid", "inline", "inline-block", "inline-flex", "none"}
)
_BORDER_STYLE_VALUES = frozenset(
    {
        "dashed",
        "dotted",
        "double",
        "groove",
        "hidden",
        "inset",
        "none",
        "outset",
        "ridge",
        "solid",
    }
)
_TEXT_OVERFLOW_VALUES = frozenset({"clip", "ellipsis"})
_WHITE_SPACE_VALUES = frozenset(
    {"normal", "nowrap", "pre", "pre-line", "pre-wrap"}
)
_KEYWORD_VALUES = {
    "alignItems": _ALIGN_ITEMS_VALUES,
    "borderStyle": _BORDER_STYLE_VALUES,
    "display": _DISPLAY_VALUES,
    "justifyContent": _JUSTIFY_CONTENT_VALUES,
    "overflow": _OVERFLOW_VALUES,
    "textOverflow": _TEXT_OVERFLOW_VALUES,
    "whiteSpace": _WHITE_SPACE_VALUES,
}
_FONT_WEIGHT_KEYWORDS = frozenset({"bold", "bolder", "lighter", "normal"})
_AUTO_DIMENSION_PROPERTIES = frozenset(
    {"height", "margin", "minHeight", "minWidth", "width"}
)
_COLOR_KEYWORDS = frozenset(
    {"black", "blue", "green", "red", "transparent", "white"}
)
_TOKEN_NAME_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_-]*")
RAW_KEYWORDS = {
    "auto",
    "block",
    "bold",
    "center",
    "column",
    "flex",
    "grid",
    "hidden",
    "inherit",
    "initial",
    "inline",
    "inline-flex",
    "ellipsis",
    "none",
    "normal",
    "nowrap",
    "row",
    "solid",
    "transparent",
    "visible",
}


class StyleError(ValueError):
    pass


class StyleSyntaxError(StyleError):
    pass


class UnknownStyleClassError(StyleError):
    pass


@dataclass(frozen=True)
class Token:
    name: str


@dataclass(frozen=True)
class Size:
    value: int | float
    unit: str = "px"


@dataclass(frozen=True)
class StyleRule:
    selector: str
    declarations: dict[str, Any]


@dataclass(frozen=True)
class StyleSheet:
    rules: dict[str, StyleRule]
    tokens: dict[str, Any]

    def resolve(self, class_name: str | None, *, strict: bool = True) -> dict[str, Any]:
        styles: dict[str, Any] = {}
        for name in _class_names(class_name):
            selector = f".{name}"
            if selector not in self.rules:
                if strict:
                    raise UnknownStyleClassError(
                        _unknown_style_class_message(name, self.rules)
                    )
                continue
            styles.update(self.rules[selector].declarations)
        return styles

    def inline_style(self, class_name: str | None, *, strict: bool = True) -> str:
        resolved = self.resolve(class_name, strict=strict)
        return ";".join(
            f"{_html_property(prop)}:{_html_value(prop, value, self.tokens)}"
            for prop, value in resolved.items()
        )


@dataclass(frozen=True)
class ResolvedStyleMap:
    classes: dict[str, dict[str, Any]]
    direct_styles: dict[tuple[int, ...], dict[str, Any]] = field(default_factory=dict)
    direct_styles_by_node_id: dict[str, dict[str, Any]] = field(default_factory=dict)

    def resolve(
        self,
        class_name: str | None,
        *,
        path: tuple[int, ...] | None = None,
        node_id: str | None = None,
        strict: bool = True,
    ) -> dict[str, Any]:
        styles: dict[str, Any] = {}
        for name in _class_names(class_name):
            if name not in self.classes:
                if strict:
                    raise UnknownStyleClassError(
                        _unknown_resolved_style_class_message(name, self.classes)
                    )
                continue
            styles.update(self.classes[name])
        if node_id is not None and node_id in self.direct_styles_by_node_id:
            styles.update(self.direct_styles_by_node_id[node_id])
        elif path is not None and path in self.direct_styles:
            styles.update(self.direct_styles[path])
        return styles


def style_value_to_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, Size):
        return {"type": "size", "value": value.value, "unit": value.unit}
    if isinstance(value, Token):
        return {"type": "token", "name": value.name}
    return {"type": "literal", "value": value}


def style_value_from_dict(payload: dict[str, Any]) -> Any:
    kind = payload.get("type")
    if kind == "size":
        return Size(payload["value"], payload.get("unit", "px"))
    if kind == "token":
        return Token(payload["name"])
    if kind == "literal":
        return payload.get("value")
    raise StyleSyntaxError(f"Unknown serialized style value type {kind!r}.")


def stylesheet_from_artifact(
    payload: dict[str, Any],
    *,
    strict: bool = True,
) -> StyleSheet:
    if strict:
        _validate_stylesheet_artifact(payload)
    rules: dict[str, StyleRule] = {}
    for entry in payload.get("rules", []):
        selector = entry.get("selector") or f".{entry['className']}"
        declarations = {
            prop: style_value_from_dict(value)
            for prop, value in entry.get("declarations", {}).items()
        }
        rules[selector] = StyleRule(selector=selector, declarations=declarations)
    tokens = {
        name: style_value_from_dict(value)
        for name, value in payload.get("tokens", {}).items()
    }
    return StyleSheet(rules=rules, tokens=tokens)


def stylesheet_from_style_ops_artifact(
    payload: dict[str, Any],
    *,
    strict: bool = True,
) -> StyleSheet:
    applied = _applied_style_ops_from_artifact(payload, strict=strict)

    rules: dict[str, StyleRule] = {}
    for replay in applied.classes:
        if replay.class_name == "<invalid>":
            continue
        declarations = {
            prop: style_value_from_dict(value)
            for prop, value in replay.applied_declarations.items()
        }
        rules[replay.selector] = StyleRule(
            selector=replay.selector,
            declarations=declarations,
        )
    return StyleSheet(rules=rules, tokens={})


def resolved_style_map_from_style_ops_artifact(
    payload: dict[str, Any],
    *,
    strict: bool = True,
) -> ResolvedStyleMap:
    applied = _applied_style_ops_from_artifact(payload, strict=strict)
    return ResolvedStyleMap(
        classes={
            replay.class_name: {
                prop: style_value_from_dict(value)
                for prop, value in replay.applied_declarations.items()
            }
            for replay in applied.classes
            if replay.class_name != "<invalid>"
        },
        direct_styles={
            replay.path: {
                prop: style_value_from_dict(value)
                for prop, value in replay.applied_declarations.items()
            }
            for replay in applied.direct_styles
        },
        direct_styles_by_node_id={
            replay.node_id: {
                prop: style_value_from_dict(value)
                for prop, value in replay.applied_declarations.items()
            }
            for replay in applied.direct_styles
            if replay.node_id is not None
        },
    )


def _applied_style_ops_from_artifact(
    payload: dict[str, Any],
    *,
    strict: bool,
) -> AppliedStyleOps:
    from .style_ops import (
        StyleIRError,
        apply_style_ops,
        load_style_ir,
        validate_style_ops,
    )

    try:
        style_ir = load_style_ir(payload)
        if strict:
            validation = validate_style_ops(style_ir)
            if not validation.passed:
                details = "; ".join(validation.errors) or "styleOps drift detected"
                raise StyleSyntaxError(f"Invalid style artifact: {details}")
            return validation.applied
        return apply_style_ops(style_ir)
    except StyleIRError as exc:
        raise StyleSyntaxError(f"Invalid style artifact: {exc}") from exc


def _validate_stylesheet_artifact(payload: dict[str, Any]) -> None:
    from .style_ops import StyleIRError, load_style_ir, validate_style_ops

    try:
        validation = validate_style_ops(load_style_ir(payload))
    except StyleIRError as exc:
        raise StyleSyntaxError(f"Invalid style artifact: {exc}") from exc
    if validation.passed:
        return
    details = "; ".join(validation.errors) or "styleOps drift detected"
    raise StyleSyntaxError(f"Invalid style artifact: {details}")


def css(source: str, *, tokens: dict[str, Any] | None = None) -> StyleSheet:
    rules: dict[str, StyleRule] = {}
    cleaned = _strip_comments(source)
    for selector, body in _rule_blocks(cleaned):
        selector = selector.strip()
        if not _is_single_class_selector(selector):
            raise StyleSyntaxError(
                f"Only single class selectors are supported; got {selector!r}."
            )
        declarations = _declarations(body)
        rules[selector] = StyleRule(selector=selector, declarations=declarations)
    return StyleSheet(rules=rules, tokens=tokens or {})


def merge_inline_styles(*styles: str | None) -> str:
    parts = [style.strip().rstrip(";") for style in styles if style]
    return ";".join(part for part in parts if part)


def _strip_comments(source: str) -> str:
    return re.sub(r"/\*.*?\*/", "", source, flags=re.S)


def _rule_blocks(source: str) -> list[tuple[str, str]]:
    blocks = re.findall(r"([^{}]+)\{([^{}]*)\}", source, flags=re.S)
    remainder = re.sub(r"([^{}]+)\{([^{}]*)\}", "", source, flags=re.S).strip()
    if remainder:
        raise StyleSyntaxError(f"Unexpected style content {remainder!r}.")
    return blocks


def _declarations(body: str) -> dict[str, Any]:
    declarations = {}
    for raw_declaration in body.split(";"):
        declaration = raw_declaration.strip()
        if not declaration:
            continue
        if ":" not in declaration:
            raise StyleSyntaxError(f"Invalid style declaration {declaration!r}.")
        raw_name, raw_value = declaration.split(":", 1)
        name = raw_name.strip()
        if name not in SUPPORTED_PROPERTIES:
            raise StyleSyntaxError(
                f"Unknown style property {name!r}. Known portable properties: "
                f"{_format_known_names(SUPPORTED_PROPERTIES)}."
            )
        prop = SUPPORTED_PROPERTIES[name]
        declarations[prop] = _parse_value(prop, raw_value.strip())
    return declarations


def _unknown_style_class_message(
    name: str,
    rules: dict[str, StyleRule],
) -> str:
    known = sorted(selector.removeprefix(".") for selector in rules)
    return _unknown_class_message(name, known)


def _unknown_resolved_style_class_message(
    name: str,
    classes: dict[str, dict[str, Any]],
) -> str:
    return _unknown_class_message(name, sorted(classes))


def _unknown_class_message(name: str, known: list[str]) -> str:
    message = f"Unknown style class {name!r}."
    if not known:
        return f"{message} No style classes are defined."
    return f"{message} Known classes: {_format_known_names(known)}."


def _format_known_names(names: Iterable[str]) -> str:
    ordered = sorted(names)
    return ", ".join(ordered)


def _parse_value(prop: str, value: str) -> Any:
    if not value:
        raise StyleSyntaxError(f"Missing value for style property {prop!r}.")
    if len(value) >= 2 and value[0] in {"'", '"'} and value[-1] == value[0]:
        parsed: Any = value[1:-1]
    elif value in {"true", "false"}:
        parsed = value == "true"
    elif _is_number(value):
        number = float(value) if "." in value else int(value)
        parsed = Size(number) if prop in DIMENSION_PROPERTIES else number
    elif size_match := re.fullmatch(r"(-?\d+(?:\.\d+)?)(px|%)", value):
        raw_number = size_match.group(1)
        number = float(raw_number) if "." in raw_number else int(raw_number)
        parsed = Size(number, size_match.group(2))
    elif (
        value.startswith("#")
        or value in RAW_KEYWORDS
        or (prop in TOKEN_PROPERTIES and value in _COLOR_KEYWORDS)
    ):
        parsed = value
    elif prop in TOKEN_PROPERTIES:
        parsed = Token(value)
    else:
        parsed = value
    _validate_style_value(prop, value, parsed)
    return parsed


def _validate_style_value(prop: str, raw_value: str, value: Any) -> None:
    spec = STYLE_PROPERTY_SPECS_BY_INTERNAL_NAME.get(prop)
    if spec is None:
        return
    if spec.value_kind == "keyword":
        _validate_keyword_value(prop, raw_value, value)
    elif spec.value_kind == "number-keyword":
        _validate_number_keyword_value(prop, raw_value, value)
    elif spec.value_kind == "dimension" and prop in DIMENSION_PROPERTIES:
        _validate_dimension_value(prop, raw_value, value)
    elif spec.value_kind == "color-token" and prop in TOKEN_PROPERTIES:
        _validate_color_token_value(prop, raw_value, value)


def _validate_keyword_value(prop: str, raw_value: str, value: Any) -> None:
    allowed_values = _KEYWORD_VALUES.get(prop)
    if allowed_values is None:
        return
    if isinstance(value, str) and value in allowed_values:
        return
    _raise_invalid_style_value(prop, raw_value)


def _validate_number_keyword_value(prop: str, raw_value: str, value: Any) -> None:
    if prop == "opacity":
        _validate_opacity_value(prop, raw_value, value)
        return
    if prop == "fontWeight":
        _validate_font_weight_value(prop, raw_value, value)


def _validate_opacity_value(prop: str, raw_value: str, value: Any) -> None:
    if isinstance(value, (int, float)) and not isinstance(value, bool) and 0 <= value <= 1:
        return
    _raise_invalid_style_value(prop, raw_value)


def _validate_font_weight_value(prop: str, raw_value: str, value: Any) -> None:
    if (
        type(value) is int
        and 1 <= value <= 1000
    ) or (isinstance(value, str) and value in _FONT_WEIGHT_KEYWORDS):
        return
    _raise_invalid_style_value(prop, raw_value)


def _validate_dimension_value(prop: str, raw_value: str, value: Any) -> None:
    if isinstance(value, Size):
        return
    if isinstance(value, str) and value == "auto" and prop in _AUTO_DIMENSION_PROPERTIES:
        return
    _raise_invalid_style_value(prop, raw_value)


def _validate_color_token_value(prop: str, raw_value: str, value: Any) -> None:
    if isinstance(value, Token):
        if _TOKEN_NAME_RE.fullmatch(value.name):
            return
        _raise_invalid_style_value(prop, raw_value)
    if isinstance(value, str) and (
        _is_hex_color(value) or value in _COLOR_KEYWORDS
    ):
        return
    _raise_invalid_style_value(prop, raw_value)


def _raise_invalid_style_value(prop: str, raw_value: str) -> None:
    raise StyleSyntaxError(
        f"Invalid value {raw_value!r} for style property "
        f"{HTML_PROPERTIES.get(prop, prop)!r}."
    )


def _html_property(prop: str) -> str:
    try:
        return HTML_PROPERTIES[prop]
    except KeyError as exc:
        raise StyleSyntaxError(
            f"Style property {prop!r} cannot be rendered as HTML."
        ) from exc


def _html_value(
    prop: str,
    value: Any,
    tokens: dict[str, Any],
    seen_tokens: tuple[str, ...] = (),
) -> str:
    if isinstance(value, Size):
        return f"{_format_number(value.value)}{value.unit}"
    if isinstance(value, Token):
        if value.name in seen_tokens:
            raise StyleSyntaxError(_format_token_cycle((*seen_tokens, value.name)))
        if value.name in tokens:
            return _html_value(
                prop,
                tokens[value.name],
                tokens,
                (*seen_tokens, value.name),
            )
        return f"var(--{value.name})"
    if isinstance(value, (int, float)) and prop in DIMENSION_PROPERTIES:
        return f"{_format_number(value)}px"
    return str(value)


def _format_token_cycle(path: tuple[str, ...]) -> str:
    return f"Cyclic style token reference: {' -> '.join(path)}."


def _format_number(value: int | float) -> str:
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def _class_names(class_name: str | None) -> list[str]:
    if not class_name:
        return []
    return [name for name in class_name.split() if name]


def _is_number(value: str) -> bool:
    try:
        float(value)
    except ValueError:
        return False
    return True


def _is_hex_color(value: str) -> bool:
    return re.fullmatch(
        r"#(?:[0-9A-Fa-f]{3}|[0-9A-Fa-f]{6}|[0-9A-Fa-f]{8})",
        value,
    ) is not None


def _is_single_class_selector(selector: str) -> bool:
    return re.fullmatch(r"\.[A-Za-z0-9_-]+", selector) is not None
