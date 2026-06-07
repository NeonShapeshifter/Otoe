from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def declaration_value_errors(
    declarations: Mapping[str, Any],
    *,
    label: str,
    portable: bool,
) -> tuple[str, ...]:
    errors: list[str] = []
    for property_name, value in declarations.items():
        if not isinstance(property_name, str):
            errors.append(f"{label} declaration property must be a string")
            continue
        errors.extend(
            style_value_payload_errors(
                value,
                label=f"{label} declaration {property_name!r} value",
                portable=portable,
            )
        )
    return tuple(errors)


def omitted_declaration_value_errors(
    omitted_declarations: Any,
    *,
    label: str,
) -> tuple[str, ...]:
    if not isinstance(omitted_declarations, list):
        return ()
    errors: list[str] = []
    for index, declaration in enumerate(omitted_declarations):
        if not isinstance(declaration, dict):
            continue
        errors.extend(
            style_value_payload_errors(
                declaration.get("value"),
                label=f"{label} omitted declaration {index} value",
                portable=False,
            )
        )
    return tuple(errors)


def style_value_payload_errors(
    value: Any,
    *,
    label: str,
    portable: bool,
) -> tuple[str, ...]:
    if not isinstance(value, dict):
        return (f"{label} must be a serialized style value object",)

    kind = value.get("type")
    if kind == "literal":
        return _literal_style_value_errors(value, label=label)
    if kind == "size":
        return _size_style_value_errors(value, label=label)
    if kind == "token":
        if portable:
            return (f"{label} must be resolved before styleOps runtime",)
        return _token_style_value_errors(value, label=label)
    if kind == "runtime":
        if portable:
            return (f"{label} cannot be a runtime style value",)
        return _runtime_style_value_errors(value, label=label)
    if not isinstance(kind, str):
        return (f"{label} type must be a string",)
    return (f"{label} has unknown serialized style value type {kind!r}",)


def _literal_style_value_errors(
    value: Mapping[str, Any],
    *,
    label: str,
) -> tuple[str, ...]:
    if "value" not in value:
        return (f"{label} literal value is required",)
    literal = value.get("value")
    if literal is None or type(literal) in {str, int, float, bool}:
        return ()
    return (f"{label} literal value must be JSON scalar",)


def _size_style_value_errors(
    value: Mapping[str, Any],
    *,
    label: str,
) -> tuple[str, ...]:
    errors: list[str] = []
    size_value = value.get("value")
    if type(size_value) not in {int, float}:
        errors.append(f"{label} size value must be int or float")
    unit = value.get("unit")
    if not isinstance(unit, str) or not unit:
        errors.append(f"{label} size unit must be a non-empty string")
    return tuple(errors)


def _token_style_value_errors(
    value: Mapping[str, Any],
    *,
    label: str,
) -> tuple[str, ...]:
    token_name = value.get("name")
    if not isinstance(token_name, str) or not token_name:
        return (f"{label} token name must be a non-empty string",)
    return ()


def _runtime_style_value_errors(
    value: Mapping[str, Any],
    *,
    label: str,
) -> tuple[str, ...]:
    errors: list[str] = []
    if not isinstance(value.get("valueType"), str) or not value.get("valueType"):
        errors.append(f"{label} runtime valueType must be a non-empty string")
    if not isinstance(value.get("repr"), str):
        errors.append(f"{label} runtime repr must be a string")
    return tuple(errors)
