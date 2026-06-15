from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


SUPPORTED_PROPERTIES = {
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
    "overflow": "overflow",
    "padding": "padding",
    "text-overflow": "textOverflow",
    "white-space": "whiteSpace",
    "width": "width",
}

HTML_PROPERTIES = {value: key for key, value in SUPPORTED_PROPERTIES.items()}
DIMENSION_PROPERTIES = {
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
TOKEN_PROPERTIES = {"background", "borderColor", "color"}
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
                    raise UnknownStyleClassError(f"Unknown style class {name!r}.")
                continue
            styles.update(self.rules[selector].declarations)
        return styles

    def inline_style(self, class_name: str | None, *, strict: bool = True) -> str:
        resolved = self.resolve(class_name, strict=strict)
        return ";".join(
            f"{HTML_PROPERTIES[prop]}:{_html_value(prop, value, self.tokens)}"
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
                    raise UnknownStyleClassError(f"Unknown style class {name!r}.")
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


def _applied_style_ops_from_artifact(payload: dict[str, Any], *, strict: bool):
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
            raise StyleSyntaxError(f"Unknown style property {name!r}.")
        prop = SUPPORTED_PROPERTIES[name]
        declarations[prop] = _parse_value(prop, raw_value.strip())
    return declarations


def _parse_value(prop: str, value: str) -> Any:
    if not value:
        raise StyleSyntaxError(f"Missing value for style property {prop!r}.")
    if len(value) >= 2 and value[0] in {"'", '"'} and value[-1] == value[0]:
        return value[1:-1]
    if value in {"true", "false"}:
        return value == "true"
    if _is_number(value):
        number = float(value) if "." in value else int(value)
        return Size(number) if prop in DIMENSION_PROPERTIES else number
    size_match = re.fullmatch(r"(-?\d+(?:\.\d+)?)(px|%)", value)
    if size_match:
        raw_number = size_match.group(1)
        number = float(raw_number) if "." in raw_number else int(raw_number)
        return Size(number, size_match.group(2))
    if value.startswith("#") or value in RAW_KEYWORDS:
        return value
    if prop in TOKEN_PROPERTIES:
        return Token(value)
    return value


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


def _is_single_class_selector(selector: str) -> bool:
    return re.fullmatch(r"\.[A-Za-z0-9_-]+", selector) is not None
