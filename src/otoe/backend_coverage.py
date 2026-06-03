from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def backend_coverage_report_to_dict(
    declaration: dict[str, Any],
    *,
    readiness_report: dict[str, Any] | None = None,
    requirements: dict[str, Any] | None = None,
) -> dict[str, Any]:
    readiness_report = readiness_report or {}
    if requirements is None:
        requirements = _requirements_from_readiness(readiness_report)
    coverage = {
        "widgets": _backend_coverage_section(
            requirements,
            declaration,
            section="widgets",
            items_name="widgets",
            item_key="name",
        ),
        "inputs": _backend_coverage_section(
            requirements,
            declaration,
            section="inputs",
            items_name="capabilities",
            item_key="capability",
        ),
        "styles": _backend_coverage_section(
            requirements,
            declaration,
            section="styles",
            items_name="properties",
            item_key="property",
        ),
        "declaredStyleOmissions": _backend_coverage_section(
            requirements,
            declaration,
            section="declaredStyleOmissions",
            items_name="properties",
            item_key="property",
        ),
    }
    declaration_errors = backend_coverage_declaration_errors(declaration)
    readiness_blockers = readiness_report.get("blockers", [])
    if not isinstance(readiness_blockers, list):
        readiness_blockers = []
    readiness_passed = readiness_report.get("passed", True) is True
    blockers: list[str] = []
    if not readiness_passed:
        blockers.append("backendReadiness")
    if declaration_errors:
        blockers.append("coverageDeclaration")
    blockers.extend(
        f"{section}Coverage"
        for section, section_coverage in coverage.items()
        if section_coverage["missing"]
    )
    return {
        "schemaVersion": 1,
        "format": "backend-coverage-report",
        "backend": declaration.get("backend"),
        "passed": not blockers,
        "readiness": {
            "passed": readiness_passed,
            "blockers": readiness_blockers,
        },
        "coverage": coverage,
        "declarationErrors": declaration_errors,
        "blockers": blockers,
    }


def requirements_from_backend_coverage_payload(
    payload: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    requirements = _requirements_from_readiness(payload)
    if requirements:
        return requirements, payload
    return payload, {"passed": True, "blockers": []}


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
    for key in ("widgets", "inputs", "styles", "declaredStyleOmissions"):
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


def _requirements_from_readiness(
    readiness_report: dict[str, Any],
) -> dict[str, Any]:
    requirements = readiness_report.get("requirements", {})
    if not isinstance(requirements, dict):
        return {}
    return requirements


def _backend_coverage_section(
    requirements: Mapping[str, Any],
    declaration: dict[str, Any],
    *,
    section: str,
    items_name: str,
    item_key: str,
) -> dict[str, Any]:
    required = _backend_requirement_names(
        requirements.get(section, []),
        items_name=items_name,
        item_key=item_key,
    )
    declared = _backend_declared_coverage_names(declaration, section)
    covered = required & declared
    missing = required - declared
    extra = declared - required
    return {
        "required": sorted(required),
        "declared": sorted(declared),
        "covered": sorted(covered),
        "missing": sorted(missing),
        "extra": sorted(extra),
        "summary": {
            "required": len(required),
            "declared": len(declared),
            "covered": len(covered),
            "missing": len(missing),
            "extra": len(extra),
        },
    }


def _backend_requirement_names(
    requirement_groups: Any,
    *,
    items_name: str,
    item_key: str,
) -> set[str]:
    if not isinstance(requirement_groups, list):
        return set()
    names: set[str] = set()
    for group in requirement_groups:
        if not isinstance(group, dict):
            continue
        items = group.get(items_name, [])
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            name = item.get(item_key)
            if isinstance(name, str):
                names.add(name)
    return names


def _backend_declared_coverage_names(
    declaration: dict[str, Any],
    section: str,
) -> set[str]:
    covers = declaration.get("covers", {})
    if not isinstance(covers, dict):
        return set()
    keys = (section,)
    if section == "declaredStyleOmissions":
        keys = ("declaredStyleOmissions", "styleOmissions")
    names: set[str] = set()
    for key in keys:
        values = covers.get(key, [])
        if not isinstance(values, list):
            continue
        names.update(value for value in values if isinstance(value, str))
    return names
