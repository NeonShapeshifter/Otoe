from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Any


CAPABILITY_PROOF_SECTIONS = {
    "widgets": {
        "items_name": "widgets",
        "item_key": "name",
        "observed_key": "observedWidgets",
    },
    "inputs": {
        "items_name": "capabilities",
        "item_key": "capability",
        "observed_key": "observedCapabilities",
    },
}


def renderer_capability_proof_expectations(
    readiness_report: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    required_for_replay = _required_for_replay(readiness_report)
    if not isinstance(required_for_replay, dict):
        return {}
    expectations: dict[str, dict[str, Any]] = {}
    for section, config in CAPABILITY_PROOF_SECTIONS.items():
        groups = required_for_replay.get(section)
        if not isinstance(groups, list):
            continue
        expectations[section] = capability_proof_expectation(
            groups,
            items_name=config["items_name"],
            item_key=config["item_key"],
            observed_key=config["observed_key"],
        )
    return expectations


def capability_proof_expectation(
    groups: list[Any],
    *,
    items_name: str,
    item_key: str,
    observed_key: str,
) -> dict[str, Any]:
    return {
        "auditHash": contract_hash(groups),
        "itemCount": capability_item_count(groups, items_name=items_name),
        observed_key: capability_item_names(
            groups,
            items_name=items_name,
            item_key=item_key,
        ),
    }


def capability_proof_matches_expectation(
    proof: Mapping[str, Any],
    expectation: Mapping[str, Any] | None,
    *,
    observed_key: str,
) -> bool:
    if expectation is None:
        return True
    if proof.get("auditHash") != expectation.get("auditHash"):
        return False
    if proof.get("itemCount") != expectation.get("itemCount"):
        return False
    expected_observed = expectation.get(observed_key)
    if not isinstance(expected_observed, list):
        return False
    actual_observed = proof.get(observed_key)
    if not isinstance(actual_observed, list):
        return False
    actual_names = sorted(
        {
            name
            for name in actual_observed
            if isinstance(name, str) and name
        }
    )
    return actual_names == expected_observed


def capability_item_count(
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


def capability_item_names(
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


def contract_hash(payload: Any) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


def _required_for_replay(readiness_report: Mapping[str, Any]) -> Any:
    renderer = readiness_report.get("renderer")
    if not isinstance(renderer, dict):
        return None
    capability_audit = renderer.get("capabilityAudit")
    if not isinstance(capability_audit, dict):
        return None
    return capability_audit.get("requiredForReplay")
