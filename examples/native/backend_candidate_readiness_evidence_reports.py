from __future__ import annotations

from typing import Any

from .backend_candidate_readiness_requirements import backend_readiness_requirements
from .backend_candidate_compact_snapshots import contract_hash


def backend_readiness_evidence(
    renderer_audit: dict[str, Any],
    style_ops_audit: dict[str, Any],
    path0_contract: dict[str, Any],
    *,
    gates: dict[str, bool],
) -> dict[str, Any]:
    requirements = backend_readiness_requirements(renderer_audit, style_ops_audit)
    style_runtime_evidence = (
        gates.get("styleOpsReplay") is True
        and gates.get("path0RenderTreeEvidence") is True
    )
    path0_layout_evidence = _path0_phase_evidence_summary(
        path0_contract["evidence"]["layout"]
    )
    path0_paint_evidence = _path0_phase_evidence_summary(
        path0_contract["evidence"]["paint"]
    )
    path0_raster_evidence = path0_contract["evidence"]["raster"]
    path0_boundary_evidence = _path0_render_tree_boundary_evidence(path0_contract)
    return {
        "widgets": _capability_evidence_groups(
            requirements["widgets"],
            source="rendererReplay",
            gate="rendererReplay",
            proof=_renderer_replay_capability_proof(
                renderer_audit,
                section="widgets",
                items_name="widgets",
                item_key="name",
                observed_key="observedWidgets",
            ),
        ),
        "inputs": _capability_evidence_groups(
            requirements["inputs"],
            source="rendererReplay",
            gate="rendererReplay",
            proof=_renderer_replay_capability_proof(
                renderer_audit,
                section="inputs",
                items_name="capabilities",
                item_key="capability",
                observed_key="observedCapabilities",
            ),
        ),
        "rendererBoundaries": _path0_renderer_boundary_evidence_groups(
            path0_contract,
            enabled=gates.get("path0RenderTreeEvidence") is True,
        ),
        "styles": _path0_style_evidence_groups(
            requirements["styles"],
            path0_contract=path0_contract,
            enabled=style_runtime_evidence,
        ),
        "declaredStyleOmissions": _path0_style_evidence_groups(
            requirements["declaredStyleOmissions"],
            path0_contract=path0_contract,
            enabled=style_runtime_evidence,
        ),
        "path0": {
            "source": path0_contract["input"]["source"],
            "gate": "path0RenderTreeEvidence",
            "rendererBackend": path0_contract["rendererBackend"],
            "nodeCount": path0_contract["input"]["nodeCount"],
            "styledNodes": path0_contract["input"]["styledNodes"],
            "renderTreeHash": path0_contract["input"]["renderTreeHash"],
            "styleOpsPresent": path0_contract["input"]["styleOps"]["present"],
            "styleOpsMatchesRenderTree": path0_contract["input"]["styleOps"][
                "matchesRenderTree"
            ],
            "renderTreeBoundary": path0_boundary_evidence,
            "layoutBoxes": path0_contract["render"]["layoutBoxes"],
            "paintCommands": path0_contract["render"]["paintCommands"],
            "layoutOutputHash": path0_contract["output"]["layout"]["outputHash"],
            "paintOutputHash": path0_contract["output"]["paint"]["outputHash"],
            "layoutEvidence": path0_layout_evidence,
            "paintEvidence": path0_paint_evidence,
            "rasterEvidence": path0_raster_evidence,
            "phases": [call["phase"] for call in path0_contract["calls"]],
        },
    }


def _path0_renderer_boundary_evidence_groups(
    path0_contract: dict[str, Any],
    *,
    enabled: bool,
) -> list[dict[str, Any]]:
    if not enabled:
        return []
    boundaries: list[dict[str, Any]] = []
    render_tree_boundary = _path0_render_tree_boundary_evidence(path0_contract)
    if render_tree_boundary is not None:
        boundaries.append(
            {
                "boundary": "renderTreeLayout",
                "count": 1,
                "proof": render_tree_boundary,
            }
        )
    paint_proof = _path0_paint_boundary_evidence(path0_contract)
    if paint_proof is not None:
        boundaries.append(
            {
                "boundary": "paint",
                "count": 1,
                "proof": paint_proof,
            }
        )
    return [
        {
            "kind": "rendererBoundary",
            "source": "path0RenderTreeEvidence",
            "gate": "path0RenderTreeEvidence",
            "boundaries": boundaries,
        }
    ]


def _path0_render_tree_boundary_evidence(
    path0_contract: dict[str, Any],
) -> dict[str, Any] | None:
    source = path0_contract["input"]["source"]
    layout_boxes = path0_contract["render"]["layoutBoxes"]
    for call in path0_contract["calls"]:
        if not isinstance(call, dict):
            continue
        if (
            call.get("phase") == "layout"
            and call.get("boundary") == "renderTree"
            and call.get("subject") == source
            and call.get("layoutBoxes") == layout_boxes
            and layout_boxes > 0
        ):
            return {
                "phase": "layout",
                "boundary": "renderTree",
                "source": source,
                "renderTreeHash": path0_contract["input"]["renderTreeHash"],
                "layoutBoxes": layout_boxes,
                "outputHash": path0_contract["output"]["layout"]["outputHash"],
            }
    return None


def _path0_paint_boundary_evidence(
    path0_contract: dict[str, Any],
) -> dict[str, Any] | None:
    source = path0_contract["input"]["source"]
    paint_commands = path0_contract["render"]["paintCommands"]
    for call in path0_contract["calls"]:
        if not isinstance(call, dict):
            continue
        if (
            call.get("phase") == "paint"
            and call.get("paintCommands") == paint_commands
            and paint_commands > 0
        ):
            return {
                "phase": "paint",
                "source": source,
                "paintCommands": paint_commands,
                "outputHash": path0_contract["output"]["paint"]["outputHash"],
            }
    return None


def _capability_evidence_groups(
    groups: list[dict[str, Any]],
    *,
    source: str,
    gate: str,
    proof: dict[str, Any] | None = None,
    runtime: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    return [
        {
            **group,
            "source": source,
            "gate": gate,
            **({"proof": proof} if proof is not None else {}),
            **({"runtime": runtime} if runtime is not None else {}),
        }
        for group in groups
    ]


def _renderer_replay_capability_proof(
    renderer_audit: dict[str, Any],
    *,
    section: str,
    items_name: str,
    item_key: str,
    observed_key: str,
) -> dict[str, Any]:
    replay_requirements = renderer_audit.get("requiredForReplay", {})
    if not isinstance(replay_requirements, dict):
        replay_groups: Any = []
    else:
        replay_groups = replay_requirements.get(section, [])
    return {
        "source": "rendererReplay",
        "auditHash": contract_hash(replay_groups),
        "itemCount": _capability_item_count(
            replay_groups,
            items_name=items_name,
        ),
        observed_key: _capability_item_names(
            replay_groups,
            items_name=items_name,
            item_key=item_key,
        ),
    }


def _capability_item_count(
    groups: Any,
    *,
    items_name: str,
) -> int:
    if not isinstance(groups, list):
        return 0
    total = 0
    for group in groups:
        if not isinstance(group, dict):
            continue
        items = group.get(items_name)
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            count = item.get("count")
            if type(count) is int and count > 0:
                total += count
    return total


def _capability_item_names(
    groups: Any,
    *,
    items_name: str,
    item_key: str,
) -> list[str]:
    if not isinstance(groups, list):
        return []
    names = set()
    for group in groups:
        if not isinstance(group, dict):
            continue
        items = group.get(items_name)
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            name = item.get(item_key)
            if isinstance(name, str) and name:
                names.add(name)
    return sorted(names)


def _path0_style_evidence_groups(
    groups: list[dict[str, Any]],
    *,
    path0_contract: dict[str, Any],
    enabled: bool,
) -> list[dict[str, Any]]:
    if not enabled:
        return []
    return _capability_evidence_groups(
        groups,
        source="styleOpsReplay+path0RenderTreeEvidence",
        gate="styleOpsReplay+path0RenderTreeEvidence",
        runtime=_path0_style_runtime_evidence(path0_contract),
    )


def _path0_style_runtime_evidence(
    path0_contract: dict[str, Any],
) -> dict[str, Any]:
    path0_input = path0_contract["input"]
    path0_render = path0_contract["render"]
    path0_evidence = path0_contract["evidence"]
    return {
        "source": path0_input["source"],
        "rendererBackend": path0_contract["rendererBackend"],
        "styleOpsPresent": path0_input["styleOps"]["present"],
        "styleOpsMatchesRenderTree": path0_input["styleOps"]["matchesRenderTree"],
        "styledNodes": path0_input["styledNodes"],
        "layoutBoxes": path0_render["layoutBoxes"],
        "paintCommands": path0_render["paintCommands"],
        "layoutEvidence": _path0_phase_evidence_summary(path0_evidence["layout"]),
        "paintEvidence": _path0_phase_evidence_summary(path0_evidence["paint"]),
        "rasterEvidence": path0_evidence["raster"],
    }


def _path0_phase_evidence_summary(
    phase_evidence: dict[str, Any],
) -> dict[str, Any]:
    observations = phase_evidence.get("observations", [])
    style_properties = list(phase_evidence.get("styleProperties", []))
    summary = {
        "styleProperties": style_properties,
        "observedProperties": _observed_style_properties(
            observations,
            style_properties=style_properties,
        ),
        "observationCount": len(observations) if isinstance(observations, list) else 0,
        "observationHash": contract_hash(observations),
    }
    if "layoutBoxes" in phase_evidence:
        summary["layoutBoxes"] = phase_evidence["layoutBoxes"]
    if "paintCommands" in phase_evidence:
        summary["paintCommands"] = phase_evidence["paintCommands"]
    return summary


def _observed_style_properties(
    observations: Any,
    *,
    style_properties: list[str],
) -> list[str]:
    if not isinstance(observations, list):
        return []
    expected = set(style_properties)
    observed = set()
    for observation in observations:
        if not isinstance(observation, dict):
            continue
        property_name = observation.get("property")
        samples = observation.get("samples")
        if property_name not in expected:
            continue
        if isinstance(samples, list) and samples:
            observed.add(property_name)
    return sorted(observed)
