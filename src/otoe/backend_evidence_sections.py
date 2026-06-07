from __future__ import annotations

from typing import Any, Mapping

from .backend_capability_proofs import capability_proof_matches_expectation
from .backend_evidence_boundaries import (
    paint_boundary_evidence_errors,
    render_tree_boundary_evidence_errors,
)
from .backend_evidence_common import (
    evidence_error,
    evidence_item_errors,
    gate_reference_errors,
    phase_evidence_errors,
    positive_number,
    required_string_errors,
)

_STYLE_SUPPORT_PHASES = {
    "layout": ("layout",),
    "paint": ("paint",),
    "layout+paint": ("layout", "paint"),
}
_CAPABILITY_PROOF_OBSERVED_KEYS = {
    "widgets": "observedWidgets",
    "inputs": "observedCapabilities",
}


def section_evidence_errors(
    section_evidence: Any,
    gates: Any,
    *,
    section: str,
    items_name: str,
    item_key: str,
    requires_runtime: bool,
    expected_renderer_boundary_hashes: Mapping[str, Any] | None = None,
    expected_capability_proof: Mapping[str, Any] | None = None,
) -> list[dict[str, str]]:
    blocker = f"{section}Evidence"
    prefix = f"evidence.{section}"
    if section_evidence is None:
        return []
    if not isinstance(section_evidence, list):
        return [evidence_error(blocker, f"{prefix} must be a list")]
    errors: list[dict[str, str]] = []
    for index, group in enumerate(section_evidence):
        group_prefix = f"{prefix}[{index}]"
        if not isinstance(group, dict):
            errors.append(
                evidence_error(blocker, f"{group_prefix} must be a JSON object")
            )
            continue
        errors.extend(
            required_string_errors(
                group,
                blocker=blocker,
                prefix=group_prefix,
                keys=("source", "gate"),
            )
        )
        gate = group.get("gate")
        if isinstance(gate, str):
            errors.extend(
                gate_reference_errors(
                    gate,
                    gates,
                    blocker=blocker,
                    prefix=f"{group_prefix}.gate",
                )
            )
        errors.extend(
            evidence_item_errors(
                group.get(items_name),
                blocker=blocker,
                prefix=f"{group_prefix}.{items_name}",
                item_key=item_key,
            )
        )
        if requires_runtime:
            errors.extend(
                _runtime_evidence_errors(
                    group.get("runtime"),
                    blocker=blocker,
                    prefix=f"{group_prefix}.runtime",
                )
            )
        if section == "styles":
            errors.extend(
                _style_application_evidence_errors(
                    group,
                    blocker=blocker,
                    prefix=group_prefix,
                )
            )
        elif section == "declaredStyleOmissions":
            errors.extend(
                _style_omission_evidence_errors(
                    group,
                    blocker=blocker,
                    prefix=group_prefix,
                )
            )
        elif section == "rendererBoundaries":
            errors.extend(
                _renderer_boundary_evidence_errors(
                    group,
                    blocker=blocker,
                    prefix=group_prefix,
                    expected_hashes=expected_renderer_boundary_hashes,
                )
            )
        elif section in _CAPABILITY_PROOF_OBSERVED_KEYS:
            errors.extend(
                _capability_group_evidence_errors(
                    group,
                    blocker=blocker,
                    prefix=group_prefix,
                    items_name=items_name,
                    item_key=item_key,
                    observed_key=_CAPABILITY_PROOF_OBSERVED_KEYS[section],
                    expected_proof=expected_capability_proof,
                )
            )
    return errors


def _renderer_boundary_evidence_errors(
    group: dict[str, Any],
    *,
    blocker: str,
    prefix: str,
    expected_hashes: Mapping[str, Any] | None,
) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    if group.get("kind") != "rendererBoundary":
        errors.append(
            evidence_error(blocker, f"{prefix}.kind must be 'rendererBoundary'")
        )
    items = group.get("boundaries")
    if not isinstance(items, list):
        return errors
    for index, item in enumerate(items):
        item_prefix = f"{prefix}.boundaries[{index}]"
        if not isinstance(item, dict):
            continue
        boundary = item.get("boundary")
        proof = item.get("proof")
        if boundary == "renderTreeLayout":
            errors.extend(
                render_tree_boundary_evidence_errors(
                    proof,
                    blocker=blocker,
                    prefix=f"{item_prefix}.proof",
                    expected_source=None,
                    expected_layout_boxes=None,
                    expected_output_hash=_expected_hash(
                        expected_hashes,
                        "renderTreeLayout",
                    ),
                    expected_render_tree_hash=_expected_hash(
                        expected_hashes,
                        "renderTreeHash",
                    ),
                )
            )
        elif boundary == "paint":
            errors.extend(
                paint_boundary_evidence_errors(
                    proof,
                    blocker=blocker,
                    prefix=f"{item_prefix}.proof",
                    expected_output_hash=_expected_hash(expected_hashes, "paint"),
                )
            )
        elif isinstance(boundary, str) and boundary:
            errors.append(
                evidence_error(
                    blocker,
                    f"{item_prefix}.boundary is not a supported renderer boundary",
                )
            )
    return errors


def _expected_hash(expected_hashes: Mapping[str, Any] | None, key: str) -> Any:
    if expected_hashes is None:
        return None
    return expected_hashes.get(key)


def _style_application_evidence_errors(
    group: dict[str, Any],
    *,
    blocker: str,
    prefix: str,
) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    if group.get("kind") != "apply":
        errors.append(evidence_error(blocker, f"{prefix}.kind must be 'apply'"))
    support = group.get("support")
    if support not in _STYLE_SUPPORT_PHASES:
        errors.append(
            evidence_error(
                blocker,
                f"{prefix}.support must be one of layout, paint, layout+paint",
            )
        )
        return errors
    runtime = group.get("runtime")
    if not isinstance(runtime, dict):
        return errors
    properties = _style_property_names(group.get("properties"))
    for property_name in properties:
        for phase in _STYLE_SUPPORT_PHASES[support]:
            phase_properties = _runtime_phase_declared_style_properties(
                runtime,
                phase,
            )
            if property_name not in phase_properties:
                errors.append(
                    evidence_error(
                        blocker,
                        (
                            f"{prefix}.runtime.{phase}Evidence.styleProperties "
                            f"must include {property_name!r} for support "
                            f"{support!r}"
                        ),
                    )
                )
    return errors


def _style_omission_evidence_errors(
    group: dict[str, Any],
    *,
    blocker: str,
    prefix: str,
) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    if group.get("kind") != "omit":
        errors.append(evidence_error(blocker, f"{prefix}.kind must be 'omit'"))
    status = group.get("status")
    if not isinstance(status, str) or not status:
        errors.append(
            evidence_error(blocker, f"{prefix}.status must be a non-empty string")
        )
    runtime = group.get("runtime")
    if not isinstance(runtime, dict):
        return errors
    properties = _style_property_names(group.get("properties"))
    for property_name in properties:
        for phase in ("layout", "paint"):
            phase_properties = _runtime_phase_style_properties(runtime, phase)
            if property_name in phase_properties:
                errors.append(
                    evidence_error(
                        blocker,
                        (
                            f"{prefix} omits {property_name!r} but runtime "
                            f"{phase}Evidence.styleProperties includes it"
                        ),
                    )
                )
    return errors


def _style_property_names(items: Any) -> list[str]:
    return _item_names(items, item_key="property")


def _item_names(items: Any, *, item_key: str) -> list[str]:
    if not isinstance(items, list):
        return []
    names: list[str] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        name = item.get(item_key)
        if isinstance(name, str) and name:
            names.append(name)
    return names


def _capability_group_evidence_errors(
    group: dict[str, Any],
    *,
    blocker: str,
    prefix: str,
    items_name: str,
    item_key: str,
    observed_key: str,
    expected_proof: Mapping[str, Any] | None,
) -> list[dict[str, str]]:
    proof = group.get("proof")
    if not isinstance(proof, dict):
        return [evidence_error(blocker, f"{prefix}.proof must be a JSON object")]
    errors: list[dict[str, str]] = []
    errors.extend(
        required_string_errors(
            proof,
            blocker=blocker,
            prefix=f"{prefix}.proof",
            keys=("source", "auditHash"),
        )
    )
    group_source = group.get("source")
    if (
        isinstance(group_source, str)
        and group_source
        and proof.get("source") != group_source
    ):
        errors.append(
            evidence_error(
                blocker,
                f"{prefix}.proof.source must match {prefix}.source",
            )
        )
    audit_hash = proof.get("auditHash")
    if not isinstance(audit_hash, str) or not audit_hash.startswith("sha256:"):
        errors.append(
            evidence_error(
                blocker,
                f"{prefix}.proof.auditHash must be a sha256 string",
            )
        )
    if not positive_number(proof.get("itemCount")):
        errors.append(
            evidence_error(
                blocker,
                f"{prefix}.proof.itemCount must be a positive number",
            )
        )
    observed = proof.get(observed_key)
    if not isinstance(observed, list) or not all(
        isinstance(item, str) and item for item in observed
    ):
        errors.append(
            evidence_error(
                blocker,
                f"{prefix}.proof.{observed_key} must be a list of strings",
            )
        )
        observed = []
    observed_set = {item for item in observed if isinstance(item, str) and item}
    if not capability_proof_matches_expectation(
        proof,
        expected_proof,
        observed_key=observed_key,
    ):
        errors.extend(
            _capability_proof_expectation_errors(
                proof,
                expected_proof,
                blocker=blocker,
                prefix=f"{prefix}.proof",
                observed_key=observed_key,
            )
        )
    for name in _item_names(group.get(items_name), item_key=item_key):
        if name not in observed_set:
            errors.append(
                evidence_error(
                    blocker,
                    (
                        f"{prefix}.proof.{observed_key} must include "
                        f"{name!r} from {items_name}"
                    ),
                )
            )
    return errors


def _capability_proof_expectation_errors(
    proof: dict[str, Any],
    expected_proof: Mapping[str, Any] | None,
    *,
    blocker: str,
    prefix: str,
    observed_key: str,
) -> list[dict[str, str]]:
    if expected_proof is None:
        return []
    errors: list[dict[str, str]] = []
    if proof.get("auditHash") != expected_proof.get("auditHash"):
        errors.append(
            evidence_error(
                blocker,
                f"{prefix}.auditHash must match renderer capability audit",
            )
        )
    if proof.get("itemCount") != expected_proof.get("itemCount"):
        errors.append(
            evidence_error(
                blocker,
                f"{prefix}.itemCount must match renderer capability audit",
            )
        )
    expected_observed = expected_proof.get(observed_key)
    actual_observed = proof.get(observed_key)
    if isinstance(expected_observed, list) and isinstance(actual_observed, list):
        actual_names = sorted(
            {
                name
                for name in actual_observed
                if isinstance(name, str) and name
            }
        )
        if actual_names != expected_observed:
            errors.append(
                evidence_error(
                    blocker,
                    (
                        f"{prefix}.{observed_key} must match renderer "
                        "capability audit"
                    ),
                )
            )
    return errors


def _runtime_phase_style_properties(runtime: dict[str, Any], phase: str) -> set[str]:
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


def _runtime_phase_declared_style_properties(
    runtime: dict[str, Any],
    phase: str,
) -> set[str]:
    phase_evidence = runtime.get(f"{phase}Evidence")
    if not isinstance(phase_evidence, dict):
        return set()
    style_properties = phase_evidence.get("styleProperties")
    if not isinstance(style_properties, list):
        return set()
    return {
        property_name
        for property_name in style_properties
        if isinstance(property_name, str)
    }


def _runtime_evidence_errors(
    runtime: Any,
    *,
    blocker: str,
    prefix: str,
) -> list[dict[str, str]]:
    if not isinstance(runtime, dict):
        return [evidence_error(blocker, f"{prefix} must be a JSON object")]
    errors: list[dict[str, str]] = []
    errors.extend(
        required_string_errors(
            runtime,
            blocker=blocker,
            prefix=prefix,
            keys=("source", "rendererBackend"),
        )
    )
    if runtime.get("styleOpsPresent") is not True:
        errors.append(
            evidence_error(blocker, f"{prefix}.styleOpsPresent must be true")
        )
    if runtime.get("styleOpsMatchesRenderTree") is not True:
        errors.append(
            evidence_error(
                blocker,
                f"{prefix}.styleOpsMatchesRenderTree must be true",
            )
        )
    for key in ("styledNodes", "layoutBoxes", "paintCommands"):
        if not positive_number(runtime.get(key)):
            errors.append(
                evidence_error(
                    blocker,
                    f"{prefix}.{key} must be a positive number",
                )
            )
    errors.extend(
        phase_evidence_errors(
            runtime.get("layoutEvidence"),
            blocker=blocker,
            prefix=f"{prefix}.layoutEvidence",
        )
    )
    errors.extend(
        phase_evidence_errors(
            runtime.get("paintEvidence"),
            blocker=blocker,
            prefix=f"{prefix}.paintEvidence",
        )
    )
    return errors
