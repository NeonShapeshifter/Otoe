from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .backend_capability_proofs import capability_proof_matches_expectation

_STYLE_SUPPORT_PHASES = {
    "layout": ("layout",),
    "paint": ("paint",),
    "layout+paint": ("layout", "paint"),
}
_CAPABILITY_PROOF_OBSERVED_KEYS = {
    "widgets": "observedWidgets",
    "inputs": "observedCapabilities",
}


def backend_evidence_refs_by_name(
    evidence_groups: Any,
    *,
    gates: Mapping[str, Any],
    section: str,
    items_name: str,
    item_key: str,
    strict_evidence: bool,
    expected_capability_proof: Mapping[str, Any] | None = None,
) -> dict[str, list[dict[str, Any]]]:
    if not strict_evidence:
        return _raw_evidence_refs_by_name(
            evidence_groups,
            items_name=items_name,
            item_key=item_key,
        )
    if not isinstance(evidence_groups, list):
        return {}
    refs_by_name: dict[str, list[dict[str, Any]]] = {}
    for group_index, group in enumerate(evidence_groups):
        if not isinstance(group, dict):
            continue
        if not _evidence_group_has_valid_source_and_gate(group, gates):
            continue
        if section == "rendererBoundaries":
            group_refs = _valid_renderer_boundary_refs_by_name(
                group,
                group_index=group_index,
            )
        elif section in _CAPABILITY_PROOF_OBSERVED_KEYS:
            group_refs = _valid_capability_refs_by_name(
                group,
                group_index=group_index,
                items_name=items_name,
                item_key=item_key,
                observed_key=_CAPABILITY_PROOF_OBSERVED_KEYS[section],
                expected_proof=expected_capability_proof,
            )
        elif section == "styles":
            group_refs = _valid_style_application_refs_by_name(
                group,
                group_index=group_index,
            )
        elif section == "declaredStyleOmissions":
            group_refs = _valid_style_omission_refs_by_name(
                group,
                group_index=group_index,
            )
        else:
            group_refs = _simple_evidence_refs_by_name(
                group,
                group_index=group_index,
                items_name=items_name,
                item_key=item_key,
            )
        _merge_evidence_refs(refs_by_name, group_refs)
    return refs_by_name


def coverage_evidence_map(
    *,
    required: set[str],
    declared: set[str],
    exercised: set[str],
    covered: set[str],
    missing: set[str],
    unevidenced: set[str],
    unproven: set[str],
    evidence_refs: Mapping[str, list[dict[str, Any]]],
) -> dict[str, dict[str, Any]]:
    names = sorted(required | declared | exercised)
    return {
        name: {
            "required": name in required,
            "declared": name in declared,
            "exercised": name in exercised,
            "covered": name in covered,
            "missing": name in missing,
            "unevidenced": name in unevidenced,
            "unproven": name in unproven,
            "sources": list(evidence_refs.get(name, [])),
        }
        for name in names
    }


def _raw_evidence_refs_by_name(
    evidence_groups: Any,
    *,
    items_name: str,
    item_key: str,
) -> dict[str, list[dict[str, Any]]]:
    if not isinstance(evidence_groups, list):
        return {}
    refs_by_name: dict[str, list[dict[str, Any]]] = {}
    for group_index, group in enumerate(evidence_groups):
        if not isinstance(group, dict):
            continue
        _merge_evidence_refs(
            refs_by_name,
            _simple_evidence_refs_by_name(
                group,
                group_index=group_index,
                items_name=items_name,
                item_key=item_key,
            ),
        )
    return refs_by_name


def _merge_evidence_refs(
    target: dict[str, list[dict[str, Any]]],
    source: Mapping[str, list[dict[str, Any]]],
) -> None:
    for name, refs in source.items():
        target.setdefault(name, []).extend(refs)


def _evidence_group_has_valid_source_and_gate(
    group: Mapping[str, Any],
    gates: Mapping[str, Any],
) -> bool:
    source = group.get("source")
    gate = group.get("gate")
    if not isinstance(source, str) or not source:
        return False
    if not isinstance(gate, str) or not gate:
        return False
    gate_names = [gate_name for gate_name in gate.split("+") if gate_name]
    if not gate_names:
        return False
    return all(gates.get(gate_name) is True for gate_name in gate_names)


def _simple_evidence_refs_by_name(
    group: Mapping[str, Any],
    *,
    group_index: int,
    items_name: str,
    item_key: str,
) -> dict[str, list[dict[str, Any]]]:
    items = group.get(items_name, [])
    if not isinstance(items, list):
        return {}
    refs_by_name: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        name = item.get(item_key)
        if not isinstance(name, str) or not name:
            continue
        refs_by_name.setdefault(name, []).append(
            _evidence_ref(group, group_index=group_index, item=item)
        )
    return refs_by_name


def _valid_capability_refs_by_name(
    group: Mapping[str, Any],
    *,
    group_index: int,
    items_name: str,
    item_key: str,
    observed_key: str,
    expected_proof: Mapping[str, Any] | None,
) -> dict[str, list[dict[str, Any]]]:
    proof = group.get("proof")
    if not _valid_capability_proof(proof, observed_key=observed_key):
        return {}
    if proof.get("source") != group.get("source"):
        return {}
    if not capability_proof_matches_expectation(
        proof,
        expected_proof,
        observed_key=observed_key,
    ):
        return {}
    observed = {
        name
        for name in proof.get(observed_key, [])
        if isinstance(name, str) and name
    }
    items = group.get(items_name, [])
    if not isinstance(items, list):
        return {}
    refs_by_name: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        name = item.get(item_key)
        if not isinstance(name, str) or not name or name not in observed:
            continue
        refs_by_name.setdefault(name, []).append(
            _evidence_ref(
                group,
                group_index=group_index,
                item=item,
                capability_proof=proof,
            )
        )
    return refs_by_name


def _valid_renderer_boundary_refs_by_name(
    group: Mapping[str, Any],
    *,
    group_index: int,
) -> dict[str, list[dict[str, Any]]]:
    if group.get("kind") != "rendererBoundary":
        return {}
    items = group.get("boundaries", [])
    if not isinstance(items, list):
        return {}
    refs_by_name: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        name = item.get("boundary")
        if not isinstance(name, str) or not name:
            continue
        proof = item.get("proof")
        if name == "renderTreeLayout":
            if not _valid_render_tree_boundary_proof(proof):
                continue
        elif name == "paint":
            if not _valid_paint_boundary_proof(proof):
                continue
        else:
            continue
        refs_by_name.setdefault(name, []).append(
            _evidence_ref(
                group,
                group_index=group_index,
                item=item,
                boundary_proof=proof,
            )
        )
    return refs_by_name


def _valid_style_application_refs_by_name(
    group: Mapping[str, Any],
    *,
    group_index: int,
) -> dict[str, list[dict[str, Any]]]:
    if group.get("kind") != "apply":
        return {}
    support = group.get("support")
    if support not in _STYLE_SUPPORT_PHASES:
        return {}
    runtime = group.get("runtime")
    if not _valid_style_runtime(runtime):
        return {}
    refs_by_name: dict[str, list[dict[str, Any]]] = {}
    items = group.get("properties", [])
    if not isinstance(items, list):
        return {}
    phases = _STYLE_SUPPORT_PHASES[support]
    for item in items:
        if not isinstance(item, dict):
            continue
        name = item.get("property")
        if not isinstance(name, str) or not name:
            continue
        if not all(
            name in _runtime_phase_style_properties(runtime, phase)
            for phase in phases
        ):
            continue
        refs_by_name.setdefault(name, []).append(
            _evidence_ref(
                group,
                group_index=group_index,
                item=item,
                runtime=runtime,
                phases=phases,
            )
        )
    return refs_by_name


def _valid_style_omission_refs_by_name(
    group: Mapping[str, Any],
    *,
    group_index: int,
) -> dict[str, list[dict[str, Any]]]:
    if group.get("kind") != "omit":
        return {}
    status = group.get("status")
    if not isinstance(status, str) or not status:
        return {}
    runtime = group.get("runtime")
    if not _valid_style_runtime(runtime):
        return {}
    refs_by_name: dict[str, list[dict[str, Any]]] = {}
    items = group.get("properties", [])
    if not isinstance(items, list):
        return {}
    phases = ("layout", "paint")
    for item in items:
        if not isinstance(item, dict):
            continue
        name = item.get("property")
        if not isinstance(name, str) or not name:
            continue
        if name in _runtime_phase_style_properties(
            runtime, "layout"
        ) or name in _runtime_phase_style_properties(runtime, "paint"):
            continue
        refs_by_name.setdefault(name, []).append(
            _evidence_ref(
                group,
                group_index=group_index,
                item=item,
                runtime=runtime,
                phases=phases,
            )
        )
    return refs_by_name


def _evidence_ref(
    group: Mapping[str, Any],
    *,
    group_index: int,
    item: Mapping[str, Any],
    runtime: Mapping[str, Any] | None = None,
    boundary_proof: Mapping[str, Any] | None = None,
    capability_proof: Mapping[str, Any] | None = None,
    phases: tuple[str, ...] = (),
) -> dict[str, Any]:
    ref: dict[str, Any] = {"groupIndex": group_index}
    for key in ("source", "gate", "kind", "support", "status"):
        value = group.get(key)
        if isinstance(value, str) and value:
            ref[key] = value
    count = item.get("count")
    if _positive_number(count):
        ref["count"] = count
    if runtime is not None:
        ref["runtimeProof"] = _runtime_proof_ref(runtime, phases=phases)
    if boundary_proof is not None:
        ref["boundaryProof"] = _boundary_proof_ref(boundary_proof)
    if capability_proof is not None:
        ref["capabilityProof"] = _capability_proof_ref(capability_proof)
    return ref


def _boundary_proof_ref(proof: Mapping[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {
        "phase": proof["phase"],
        "source": proof["source"],
    }
    boundary = proof.get("boundary")
    if isinstance(boundary, str) and boundary:
        result["boundary"] = boundary
    for key in ("layoutBoxes", "paintCommands"):
        value = proof.get(key)
        if _positive_number(value):
            result[key] = value
    output_hash = proof.get("outputHash")
    if isinstance(output_hash, str) and output_hash.startswith("sha256:"):
        result["outputHash"] = output_hash
    render_tree_hash = proof.get("renderTreeHash")
    if isinstance(render_tree_hash, str) and render_tree_hash.startswith("sha256:"):
        result["renderTreeHash"] = render_tree_hash
    return result


def _capability_proof_ref(proof: Mapping[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {
        "source": proof["source"],
        "auditHash": proof["auditHash"],
        "itemCount": proof["itemCount"],
    }
    for key in ("observedWidgets", "observedCapabilities"):
        value = proof.get(key)
        if isinstance(value, list):
            result[key] = list(value)
    return result


def _runtime_proof_ref(
    runtime: Mapping[str, Any],
    *,
    phases: tuple[str, ...],
) -> dict[str, Any]:
    proof: dict[str, Any] = {
        "source": runtime["source"],
        "rendererBackend": runtime["rendererBackend"],
        "styleOpsPresent": runtime["styleOpsPresent"],
        "styleOpsMatchesRenderTree": runtime["styleOpsMatchesRenderTree"],
        "styledNodes": runtime["styledNodes"],
        "layoutBoxes": runtime["layoutBoxes"],
        "paintCommands": runtime["paintCommands"],
        "phases": list(phases),
    }
    for phase in phases:
        phase_evidence = runtime[f"{phase}Evidence"]
        proof[f"{phase}ObservationCount"] = phase_evidence["observationCount"]
        proof[f"{phase}ObservationHash"] = phase_evidence["observationHash"]
        proof[f"{phase}ObservedProperties"] = list(
            phase_evidence["observedProperties"]
        )
    return proof


def _valid_style_runtime(runtime: Any) -> bool:
    if not isinstance(runtime, dict):
        return False
    if not _required_non_empty_strings(runtime, ("source", "rendererBackend")):
        return False
    if runtime.get("styleOpsPresent") is not True:
        return False
    if runtime.get("styleOpsMatchesRenderTree") is not True:
        return False
    for key in ("styledNodes", "layoutBoxes", "paintCommands"):
        if not _positive_number(runtime.get(key)):
            return False
    return _valid_phase_evidence(
        runtime.get("layoutEvidence")
    ) and _valid_phase_evidence(runtime.get("paintEvidence"))


def _valid_render_tree_boundary_proof(proof: Any) -> bool:
    return (
        isinstance(proof, dict)
        and proof.get("phase") == "layout"
        and proof.get("boundary") == "renderTree"
        and _required_non_empty_strings(proof, ("source",))
        and _valid_sha256(proof.get("outputHash"))
        and _valid_sha256(proof.get("renderTreeHash"))
        and _positive_number(proof.get("layoutBoxes"))
    )


def _valid_capability_proof(proof: Any, *, observed_key: str) -> bool:
    if not isinstance(proof, dict):
        return False
    audit_hash = proof.get("auditHash")
    observed = proof.get(observed_key)
    return (
        _required_non_empty_strings(proof, ("source",))
        and isinstance(audit_hash, str)
        and audit_hash.startswith("sha256:")
        and _positive_number(proof.get("itemCount"))
        and isinstance(observed, list)
        and all(isinstance(item, str) and item for item in observed)
    )


def _valid_paint_boundary_proof(proof: Any) -> bool:
    return (
        isinstance(proof, dict)
        and proof.get("phase") == "paint"
        and _required_non_empty_strings(proof, ("source",))
        and _valid_sha256(proof.get("outputHash"))
        and _positive_number(proof.get("paintCommands"))
    )


def _valid_phase_evidence(phase_evidence: Any) -> bool:
    if not isinstance(phase_evidence, dict):
        return False
    observation_hash = phase_evidence.get("observationHash")
    style_properties = phase_evidence.get("styleProperties")
    observed_properties = phase_evidence.get("observedProperties")
    if not isinstance(style_properties, list) or not all(
        isinstance(item, str) and item for item in style_properties
    ):
        return False
    if not isinstance(observed_properties, list) or not all(
        isinstance(item, str) and item for item in observed_properties
    ):
        return False
    return (
        _positive_number(phase_evidence.get("observationCount"))
        and isinstance(observation_hash, str)
        and observation_hash.startswith("sha256:")
    )


def _runtime_phase_style_properties(runtime: Mapping[str, Any], phase: str) -> set[str]:
    phase_evidence = runtime.get(f"{phase}Evidence")
    if not isinstance(phase_evidence, dict):
        return set()
    style_properties = phase_evidence.get("styleProperties")
    observed_properties = phase_evidence.get("observedProperties")
    if not isinstance(style_properties, list) or not isinstance(
        observed_properties, list
    ):
        return set()
    style_set = {
        property_name
        for property_name in style_properties
        if isinstance(property_name, str)
    }
    observed_set = {
        property_name
        for property_name in observed_properties
        if isinstance(property_name, str)
    }
    return style_set & observed_set


def _required_non_empty_strings(
    payload: Mapping[str, Any],
    keys: tuple[str, ...],
) -> bool:
    return all(isinstance(payload.get(key), str) and payload.get(key) for key in keys)


def _positive_number(value: Any) -> bool:
    return type(value) in {int, float} and value > 0


def _valid_sha256(value: Any) -> bool:
    return isinstance(value, str) and value.startswith("sha256:")
