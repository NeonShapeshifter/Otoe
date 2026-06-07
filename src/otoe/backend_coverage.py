from __future__ import annotations

from typing import Any

from .backend_capability_proofs import renderer_capability_proof_expectations
from .backend_coverage_declarations import backend_coverage_declaration_errors
from .backend_coverage_requirements import (
    BACKEND_COVERAGE_SECTIONS,
    has_backend_coverage_requirements,
    requirements_from_backend_coverage_payload,
    requirements_from_readiness,
)
from .backend_coverage_sections import backend_coverage_section
from .backend_evidence_common import evidence_error
from .backend_evidence import (
    readiness_evidence_blockers,
    readiness_evidence_errors,
)


def backend_coverage_report_to_dict(
    declaration: dict[str, Any],
    *,
    readiness_report: dict[str, Any] | None = None,
    requirements: dict[str, Any] | None = None,
) -> dict[str, Any]:
    readiness_report = readiness_report or {}
    if requirements is None:
        requirements = requirements_from_readiness(readiness_report)
    evidence, strict_evidence = _evidence_from_readiness(
        readiness_report,
        fallback=requirements,
    )
    readiness_blockers = readiness_report.get("blockers", [])
    if not isinstance(readiness_blockers, list):
        readiness_blockers = []
    readiness_gates = readiness_report.get("gates", {})
    if not isinstance(readiness_gates, dict):
        readiness_gates = {}
    candidate_scope = readiness_report.get("candidateScope", {})
    if not isinstance(candidate_scope, dict):
        candidate_scope = {}
    trace = _coverage_trace_from_readiness(readiness_report)
    capability_proof_expectations = renderer_capability_proof_expectations(
        readiness_report
    )
    coverage = {
        section: backend_coverage_section(
            requirements,
            evidence,
            declaration,
            section=section,
            items_name=items_name,
            item_key=item_key,
            gates=readiness_gates,
            strict_evidence=strict_evidence,
            expected_capability_proof=capability_proof_expectations.get(section),
        )
        for section, items_name, item_key in BACKEND_COVERAGE_SECTIONS
    }
    declaration_errors = backend_coverage_declaration_errors(declaration)
    evidence_errors = _readiness_contract_errors(readiness_report)
    evidence_errors.extend(readiness_evidence_errors(readiness_report))
    evidence_errors.extend(
        _coverage_evidence_errors(
            readiness_report,
            requirements=requirements,
            strict_evidence=strict_evidence,
        )
    )
    evidence_errors.extend(
        _backend_identity_errors(
            declaration,
            readiness_report,
            strict_evidence=strict_evidence,
        )
    )
    evidence_blockers = readiness_evidence_blockers(evidence_errors)
    evidence_summary = _coverage_evidence_summary(evidence_errors)
    readiness_passed = readiness_report.get("passed", True) is True
    blockers: list[str] = []
    if not readiness_passed:
        blockers.append("backendReadiness")
    blockers.extend(evidence_blockers)
    if declaration_errors:
        blockers.append("coverageDeclaration")
    blockers.extend(
        f"{section}Coverage"
        for section, section_coverage in coverage.items()
        if section_coverage["missing"]
    )
    if strict_evidence:
        blockers.extend(
            f"{section}Evidence"
            for section, section_coverage in coverage.items()
            if (
                section_coverage["unevidenced"]
                or section_coverage["evidence"]["unproven"]
            )
        )
    blockers = _unique_strings(blockers)
    return {
        "schemaVersion": 1,
        "format": "backend-coverage-report",
        "backend": declaration.get("backend"),
        "passed": not blockers,
        "readiness": {
            "passed": readiness_passed,
            "blockers": readiness_blockers,
            "candidate": _readiness_candidate_identity(readiness_report),
            "gates": readiness_gates,
            "candidateScope": candidate_scope,
            "evidenceBlockers": evidence_blockers,
            "evidenceErrors": evidence_errors,
            "evidenceSummary": evidence_summary,
            "strictEvidence": strict_evidence,
        },
        "trace": trace,
        "coverage": coverage,
        "declarationErrors": declaration_errors,
        "blockers": blockers,
    }


def _evidence_from_readiness(
    readiness_report: dict[str, Any],
    *,
    fallback: dict[str, Any],
) -> tuple[dict[str, Any], bool]:
    evidence = readiness_report.get("evidence")
    if isinstance(evidence, dict):
        return evidence, True
    if has_backend_coverage_requirements(fallback):
        return {}, True
    return {}, False


def _unique_strings(values: list[str]) -> list[str]:
    unique: list[str] = []
    for value in values:
        if value not in unique:
            unique.append(value)
    return unique


def _coverage_evidence_summary(
    evidence_errors: list[dict[str, str]],
) -> dict[str, Any]:
    malformed_by_blocker: dict[str, int] = {}
    for error in evidence_errors:
        blocker = error.get("blocker") if isinstance(error, dict) else None
        if isinstance(blocker, str) and blocker:
            malformed_by_blocker[blocker] = malformed_by_blocker.get(blocker, 0) + 1
    return {
        "malformed": sum(malformed_by_blocker.values()),
        "malformedByBlocker": dict(sorted(malformed_by_blocker.items())),
    }


def _readiness_contract_errors(
    readiness_report: dict[str, Any],
) -> list[dict[str, str]]:
    if not _looks_like_readiness_report(readiness_report):
        return []
    errors: list[dict[str, str]] = []
    if readiness_report.get("schemaVersion") != 1:
        errors.append(
            evidence_error(
                "backendReadinessContract",
                "readiness.schemaVersion must be 1",
            )
        )
    if readiness_report.get("format") != "backend-readiness-report":
        errors.append(
            evidence_error(
                "backendReadinessContract",
                "readiness.format must be 'backend-readiness-report'",
            )
        )
    return errors


def _backend_identity_errors(
    declaration: dict[str, Any],
    readiness_report: dict[str, Any],
    *,
    strict_evidence: bool,
) -> list[dict[str, str]]:
    if not strict_evidence or not _looks_like_readiness_report(readiness_report):
        return []
    candidate = readiness_report.get("candidate")
    if not isinstance(candidate, dict):
        return [
            evidence_error(
                "backendIdentity",
                "readiness.candidate must be a JSON object",
            )
        ]
    candidate_backend = candidate.get("backend")
    if not isinstance(candidate_backend, str) or not candidate_backend:
        return [
            evidence_error(
                "backendIdentity",
                "readiness.candidate.backend must be a non-empty string",
            )
        ]
    declaration_backend = declaration.get("backend")
    if isinstance(declaration_backend, str) and declaration_backend:
        if candidate_backend != declaration_backend:
            return [
                evidence_error(
                    "backendIdentity",
                    (
                        "coverage declaration backend must match "
                        "readiness.candidate.backend"
                    ),
                )
            ]
    return []


def _readiness_candidate_identity(readiness_report: dict[str, Any]) -> dict[str, Any]:
    candidate = readiness_report.get("candidate")
    if not isinstance(candidate, dict):
        return {}
    result: dict[str, Any] = {}
    for key in ("backend", "rendererBackend", "path0RendererBackend"):
        value = candidate.get(key)
        if isinstance(value, str) and value:
            result[key] = value
    return result


def _looks_like_readiness_report(readiness_report: dict[str, Any]) -> bool:
    return any(
        key in readiness_report
        for key in (
            "candidate",
            "candidateScope",
            "evidence",
            "format",
            "gates",
            "path0",
        )
    )


def _coverage_trace_from_readiness(readiness_report: dict[str, Any]) -> dict[str, Any]:
    candidate_scope = readiness_report.get("candidateScope")
    if not isinstance(candidate_scope, dict):
        candidate_scope = {}
    return {
        "candidateScope": {
            "level": _string_or_none(candidate_scope.get("level")),
        },
        "path0": {
            "renderTreeHash": _path0_render_tree_hash(readiness_report),
            "layoutOutputHash": _path0_output_hash(readiness_report, "layout"),
            "paintOutputHash": _path0_output_hash(readiness_report, "paint"),
            "semanticValidation": _path0_semantic_validation(readiness_report),
        },
    }


def _path0_render_tree_hash(readiness_report: dict[str, Any]) -> Any:
    path0 = readiness_report.get("path0")
    if not isinstance(path0, dict):
        return None
    path0_input = path0.get("input")
    if not isinstance(path0_input, dict):
        return None
    return path0_input.get("renderTreeHash")


def _path0_output_hash(readiness_report: dict[str, Any], section_name: str) -> Any:
    path0 = readiness_report.get("path0")
    if not isinstance(path0, dict):
        return None
    output = path0.get("output")
    if not isinstance(output, dict):
        return None
    section = output.get(section_name)
    if not isinstance(section, dict):
        return None
    return section.get("outputHash")


def _path0_semantic_validation(readiness_report: dict[str, Any]) -> Any:
    path0 = readiness_report.get("path0")
    if not isinstance(path0, dict):
        return None
    semantic_validation = path0.get("semanticValidation")
    if not isinstance(semantic_validation, dict):
        return None
    return {
        "passed": semantic_validation.get("passed"),
        "errors": semantic_validation.get("errors"),
    }


def _string_or_none(value: Any) -> Any:
    if isinstance(value, str) and value:
        return value
    return None


def _coverage_evidence_errors(
    readiness_report: dict[str, Any],
    *,
    requirements: dict[str, Any],
    strict_evidence: bool,
) -> list[dict[str, str]]:
    if not strict_evidence:
        return []
    if isinstance(readiness_report.get("evidence"), dict):
        return []
    if readiness_report.get("format") == "backend-readiness-report":
        return []
    if not has_backend_coverage_requirements(requirements):
        return []
    return [
        {
            "blocker": "capabilityEvidence",
            "message": (
                "backend coverage requires executed readiness evidence; "
                "requirements alone are not proof"
            ),
        }
    ]
