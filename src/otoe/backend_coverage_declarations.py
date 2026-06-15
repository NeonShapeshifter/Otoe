from __future__ import annotations

from typing import Any


def backend_coverage_declaration_errors(
    declaration: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    if declaration.get("schemaVersion") != 1:
        errors.append("schemaVersion must be 1")
    if declaration.get("format") != "backend-coverage-declaration":
        errors.append("format must be 'backend-coverage-declaration'")
    backend = declaration.get("backend")
    if not isinstance(backend, str) or not backend:
        errors.append("backend must be a non-empty string")
    covers = declaration.get("covers")
    if not isinstance(covers, dict):
        errors.append("covers must be a JSON object")
        return errors
    for key in (
        "rendererBoundaries",
        "widgets",
        "inputs",
        "styles",
        "declaredStyleOmissions",
    ):
        value = covers.get(key, [])
        if not isinstance(value, list) or not all(
            isinstance(item, str) for item in value
        ):
            errors.append(f"covers.{key} must be a list of strings")
    if "styleOmissions" in covers:
        value = covers["styleOmissions"]
        if not isinstance(value, list) or not all(
            isinstance(item, str) for item in value
        ):
            errors.append("covers.styleOmissions must be a list of strings")
    return errors


def backend_declared_coverage_names(
    declaration: dict[str, Any],
    section: str,
) -> set[str]:
    covers = declaration.get("covers", {})
    if not isinstance(covers, dict):
        return set()
    keys: tuple[str, ...] = (section,)
    if section == "declaredStyleOmissions":
        keys = ("declaredStyleOmissions", "styleOmissions")
    names: set[str] = set()
    for key in keys:
        values = covers.get(key, [])
        if not isinstance(values, list):
            continue
        names.update(value for value in values if isinstance(value, str))
    return names
