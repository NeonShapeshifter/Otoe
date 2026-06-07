from __future__ import annotations

from collections.abc import Mapping
from typing import Any

BACKEND_COVERAGE_SECTIONS: tuple[tuple[str, str, str], ...] = (
    ("rendererBoundaries", "boundaries", "boundary"),
    ("widgets", "widgets", "name"),
    ("inputs", "capabilities", "capability"),
    ("styles", "properties", "property"),
    ("declaredStyleOmissions", "properties", "property"),
)


def requirements_from_backend_coverage_payload(
    payload: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    requirements = requirements_from_readiness(payload)
    if requirements:
        return requirements, payload
    return payload, {"passed": True, "blockers": []}


def requirements_from_readiness(
    readiness_report: dict[str, Any],
) -> dict[str, Any]:
    requirements = readiness_report.get("requirements", {})
    if not isinstance(requirements, dict):
        return {}
    return requirements


def has_backend_coverage_requirements(requirements: Mapping[str, Any]) -> bool:
    for section, items_name, item_key in BACKEND_COVERAGE_SECTIONS:
        names = backend_requirement_names(
            requirements.get(section, []),
            items_name=items_name,
            item_key=item_key,
        )
        if names:
            return True
    return False


def backend_requirement_names(
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
