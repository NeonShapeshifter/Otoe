from __future__ import annotations

from typing import Any

from .backend_capability_proofs import renderer_capability_proof_expectations
from .backend_evidence_common import evidence_error
from .backend_evidence_path0 import path0_evidence_errors
from .backend_evidence_sections import section_evidence_errors


def readiness_evidence_blockers(
    evidence_errors: list[dict[str, str]],
) -> list[str]:
    blockers: list[str] = []
    for error in evidence_errors:
        blocker = error.get("blocker")
        if blocker and blocker not in blockers:
            blockers.append(blocker)
    return blockers


def readiness_evidence_errors(
    readiness_report: dict[str, Any],
) -> list[dict[str, str]]:
    if readiness_report.get("format") != "backend-readiness-report":
        return []
    errors: list[dict[str, str]] = []
    gates = readiness_report.get("gates", {})
    if not isinstance(gates, dict):
        errors.append(
            evidence_error(
                "path0RenderTreeEvidence",
                "gates must be a JSON object",
            )
        )
    elif gates.get("path0RenderTreeEvidence") is not True:
        errors.append(
            evidence_error(
                "path0RenderTreeEvidence",
                "gates.path0RenderTreeEvidence must be true",
            )
        )
    evidence = readiness_report.get("evidence")
    if not isinstance(evidence, dict):
        errors.append(
            evidence_error(
                "capabilityEvidence",
                "evidence must be a JSON object",
            )
        )
        return errors
    report_path0 = readiness_report.get("path0")
    output = report_path0.get("output") if isinstance(report_path0, dict) else None
    expected_render_tree_hash = _path0_render_tree_hash(report_path0)
    if (
        not isinstance(expected_render_tree_hash, str)
        or not expected_render_tree_hash.startswith("sha256:")
    ):
        errors.append(
            evidence_error(
                "path0RenderTreeEvidence",
                "path0.input.renderTreeHash must be a sha256 string",
            )
        )
    expected_renderer_boundary_hashes = _renderer_boundary_hashes(
        output,
        render_tree_hash=expected_render_tree_hash,
    )
    expected_capability_proofs = renderer_capability_proof_expectations(
        readiness_report
    )
    errors.extend(
        path0_evidence_errors(
            evidence.get("path0"),
            gates,
            output=output,
            semantic_validation=_path0_semantic_validation(report_path0),
            expected_render_tree_hash=expected_render_tree_hash,
        )
    )
    errors.extend(
        section_evidence_errors(
            evidence.get("rendererBoundaries"),
            gates,
            section="rendererBoundaries",
            items_name="boundaries",
            item_key="boundary",
            requires_runtime=False,
            expected_renderer_boundary_hashes=expected_renderer_boundary_hashes,
        )
    )
    errors.extend(
        section_evidence_errors(
            evidence.get("widgets"),
            gates,
            section="widgets",
            items_name="widgets",
            item_key="name",
            requires_runtime=False,
            expected_capability_proof=expected_capability_proofs.get("widgets"),
        )
    )
    errors.extend(
        section_evidence_errors(
            evidence.get("inputs"),
            gates,
            section="inputs",
            items_name="capabilities",
            item_key="capability",
            requires_runtime=False,
            expected_capability_proof=expected_capability_proofs.get("inputs"),
        )
    )
    errors.extend(
        section_evidence_errors(
            evidence.get("styles"),
            gates,
            section="styles",
            items_name="properties",
            item_key="property",
            requires_runtime=True,
        )
    )
    errors.extend(
        section_evidence_errors(
            evidence.get("declaredStyleOmissions"),
            gates,
            section="declaredStyleOmissions",
            items_name="properties",
            item_key="property",
            requires_runtime=True,
        )
    )
    return errors


def _renderer_boundary_hashes(
    output: Any,
    *,
    render_tree_hash: Any,
) -> dict[str, Any]:
    if not isinstance(output, dict):
        return {}
    return {
        "renderTreeLayout": _section_output_hash(output, "layout"),
        "paint": _section_output_hash(output, "paint"),
        "renderTreeHash": render_tree_hash,
    }


def _section_output_hash(output: dict[str, Any], section_name: str) -> Any:
    section = output.get(section_name)
    if not isinstance(section, dict):
        return None
    return section.get("outputHash")


def _path0_render_tree_hash(path0: Any) -> Any:
    if not isinstance(path0, dict):
        return None
    path0_input = path0.get("input")
    if not isinstance(path0_input, dict):
        return None
    return path0_input.get("renderTreeHash")


def _path0_semantic_validation(path0: Any) -> Any:
    if not isinstance(path0, dict):
        return None
    return path0.get("semanticValidation")
