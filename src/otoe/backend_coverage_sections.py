from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .backend_coverage_declarations import backend_declared_coverage_names
from .backend_coverage_evidence import (
    backend_evidence_refs_by_name,
    coverage_evidence_map,
)
from .backend_coverage_requirements import backend_requirement_names


def backend_coverage_section(
    requirements: Mapping[str, Any],
    evidence: Mapping[str, Any],
    declaration: dict[str, Any],
    *,
    section: str,
    items_name: str,
    item_key: str,
    gates: Mapping[str, Any],
    strict_evidence: bool,
    expected_capability_proof: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    required = backend_requirement_names(
        requirements.get(section, []),
        items_name=items_name,
        item_key=item_key,
    )
    evidence_refs = backend_evidence_refs_by_name(
        evidence.get(section, []),
        gates=gates,
        section=section,
        items_name=items_name,
        item_key=item_key,
        strict_evidence=strict_evidence,
        expected_capability_proof=expected_capability_proof,
    )
    exercised = set(evidence_refs)
    declared = backend_declared_coverage_names(declaration, section)
    covered = required & declared & exercised
    missing = required - declared
    unevidenced = required - exercised
    extra = declared - required
    unproven = declared - exercised
    return {
        "required": sorted(required),
        "exercised": sorted(exercised),
        "declared": sorted(declared),
        "covered": sorted(covered),
        "missing": sorted(missing),
        "unevidenced": sorted(unevidenced),
        "extra": sorted(extra),
        "evidence": {
            "claimed": sorted(declared),
            "required": sorted(required),
            "exercised": sorted(exercised),
            "covered": sorted(covered),
            "missing": sorted(missing),
            "unevidenced": sorted(unevidenced),
            "unproven": sorted(unproven),
        },
        "evidenceMap": coverage_evidence_map(
            required=required,
            declared=declared,
            exercised=exercised,
            covered=covered,
            missing=missing,
            unevidenced=unevidenced,
            unproven=unproven,
            evidence_refs=evidence_refs,
        ),
        "summary": {
            "required": len(required),
            "exercised": len(exercised),
            "declared": len(declared),
            "covered": len(covered),
            "missing": len(missing),
            "unevidenced": len(unevidenced),
            "extra": len(extra),
            "unproven": len(unproven),
        },
    }
