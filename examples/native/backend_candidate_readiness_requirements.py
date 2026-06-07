from __future__ import annotations

from typing import Any


PATH0_RENDERER_BOUNDARY_REQUIREMENTS = (
    {"boundary": "paint"},
    {"boundary": "renderTreeLayout"},
)


def backend_readiness_requirements(
    renderer_audit: dict[str, Any],
    style_ops_audit: dict[str, Any],
) -> dict[str, Any]:
    renderer_requirements = renderer_audit.get("requiredForReplay", {})
    if not isinstance(renderer_requirements, dict):
        renderer_requirements = {}
    return {
        "rendererBoundaries": [
            {
                "kind": "rendererBoundary",
                "boundaries": [
                    dict(boundary)
                    for boundary in PATH0_RENDERER_BOUNDARY_REQUIREMENTS
                ],
            }
        ],
        "widgets": list(renderer_requirements.get("widgets", [])),
        "inputs": list(renderer_requirements.get("inputs", [])),
        "styles": list(style_ops_audit.get("requiredForReplay", [])),
        "declaredStyleOmissions": list(style_ops_audit.get("declaredOmissions", [])),
    }
