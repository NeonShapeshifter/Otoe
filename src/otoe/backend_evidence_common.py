from __future__ import annotations

from typing import Any


def evidence_error(blocker: str, message: str) -> dict[str, str]:
    return {
        "blocker": blocker,
        "message": message,
    }


def required_string_errors(
    payload: dict[str, Any],
    *,
    blocker: str,
    prefix: str,
    keys: tuple[str, ...],
) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    for key in keys:
        value = payload.get(key)
        if not isinstance(value, str) or not value:
            errors.append(
                evidence_error(
                    blocker,
                    f"{prefix}.{key} must be a non-empty string",
                )
            )
    return errors


def gate_reference_errors(
    gate: str,
    gates: Any,
    *,
    blocker: str,
    prefix: str,
) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    gate_names = gate.split("+")
    if not gate_names or not all(gate_names):
        errors.append(
            evidence_error(
                blocker,
                f"{prefix} must reference non-empty gate names",
            )
        )
        return errors
    if not isinstance(gates, dict):
        return errors
    for gate_name in gate_names:
        if gates.get(gate_name) is not True:
            errors.append(
                evidence_error(
                    blocker,
                    f"{prefix} references non-passing gate {gate_name!r}",
                )
            )
    return errors


def evidence_item_errors(
    items: Any,
    *,
    blocker: str,
    prefix: str,
    item_key: str,
) -> list[dict[str, str]]:
    if not isinstance(items, list):
        return [evidence_error(blocker, f"{prefix} must be a list")]
    errors: list[dict[str, str]] = []
    for index, item in enumerate(items):
        item_prefix = f"{prefix}[{index}]"
        if not isinstance(item, dict):
            errors.append(
                evidence_error(blocker, f"{item_prefix} must be a JSON object")
            )
            continue
        value = item.get(item_key)
        if not isinstance(value, str) or not value:
            errors.append(
                evidence_error(
                    blocker,
                    f"{item_prefix}.{item_key} must be a non-empty string",
                )
            )
    return errors


def phase_evidence_errors(
    phase_evidence: Any,
    *,
    blocker: str,
    prefix: str,
) -> list[dict[str, str]]:
    if not isinstance(phase_evidence, dict):
        return [evidence_error(blocker, f"{prefix} must be a JSON object")]
    errors: list[dict[str, str]] = []
    if not positive_number(phase_evidence.get("observationCount")):
        errors.append(
            evidence_error(
                blocker,
                f"{prefix}.observationCount must be a positive number",
            )
        )
    observation_hash = phase_evidence.get("observationHash")
    if not isinstance(observation_hash, str) or not observation_hash.startswith(
        "sha256:"
    ):
        errors.append(
            evidence_error(
                blocker,
                f"{prefix}.observationHash must be a sha256 string",
            )
        )
    style_properties = phase_evidence.get("styleProperties")
    if not isinstance(style_properties, list) or not all(
        isinstance(item, str) and item for item in style_properties
    ):
        errors.append(
            evidence_error(
                blocker,
                f"{prefix}.styleProperties must be a list of strings",
            )
        )
        style_properties = []
    observed_properties = phase_evidence.get("observedProperties")
    if not isinstance(observed_properties, list) or not all(
        isinstance(item, str) and item for item in observed_properties
    ):
        errors.append(
            evidence_error(
                blocker,
                f"{prefix}.observedProperties must be a list of strings",
            )
        )
        observed_properties = []
    if isinstance(style_properties, list) and isinstance(observed_properties, list):
        style_set = {
            item for item in style_properties if isinstance(item, str) and item
        }
        observed_set = {
            item for item in observed_properties if isinstance(item, str) and item
        }
        for property_name in sorted(style_set - observed_set):
            errors.append(
                evidence_error(
                    blocker,
                    (
                        f"{prefix}.observedProperties must include "
                        f"{property_name!r} from styleProperties"
                    ),
                )
            )
        for property_name in sorted(observed_set - style_set):
            errors.append(
                evidence_error(
                    blocker,
                    (
                        f"{prefix}.observedProperties must not include "
                        f"{property_name!r} outside styleProperties"
                    ),
                )
            )
    return errors


def positive_number(value: Any) -> bool:
    return type(value) in {int, float} and value > 0
