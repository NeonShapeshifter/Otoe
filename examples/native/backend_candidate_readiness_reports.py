from __future__ import annotations

from typing import Any

from .backend_candidate_renderer_capability_audits import (
    renderer_capability_audit_to_dict,
)
from .backend_candidate_readiness_evidence_reports import (
    backend_readiness_evidence,
)
from .backend_candidate_readiness_requirements import backend_readiness_requirements
from .backend_candidate_compact_snapshots import compact_call_stream
from .backend_candidate_path0_readiness_reports import (
    path0_render_tree_evidence_report_to_dict,
    path0_report_has_style_phase_evidence,
)
from .backend_candidate_render_tree_reports import render_tree_contract_report_to_dict
from .backend_candidate_style_ops_reports import style_ops_report_errors
from .backend_candidate_style_ops_capability_audits import (
    style_ops_capability_audit_to_dict,
)
from .backend_candidate_render_tree_types import (
    Path0RenderTreeEvidenceReport,
    RenderTreeCandidateAcceptanceReport,
)
from .backend_candidate_renderer_types import RendererCandidateAcceptanceReport
from .backend_candidate_style_ops_types import (
    StyleOpsCandidateAcceptanceReport,
)


def backend_readiness_report_payload_to_dict(
    *,
    renderer_report: RendererCandidateAcceptanceReport,
    style_ops_report: StyleOpsCandidateAcceptanceReport,
    render_tree_report: RenderTreeCandidateAcceptanceReport,
    path0_report: Path0RenderTreeEvidenceReport,
) -> dict[str, Any]:
    renderer_audit = renderer_capability_audit_to_dict(renderer_report.headless)
    style_ops_audit = style_ops_capability_audit_to_dict(style_ops_report)
    render_tree_contract = render_tree_contract_report_to_dict(render_tree_report)
    path0_contract = path0_render_tree_evidence_report_to_dict(path0_report)
    gates = {
        "rendererReplay": renderer_report.passed,
        "styleOpsReplay": style_ops_report.passed,
        "renderTreeReplay": render_tree_report.passed,
        "path0RenderTreeEvidence": path0_report_has_style_phase_evidence(
            path0_report
        ),
        "widgetInputAudit": _audit_has_no_unsupported(
            renderer_audit,
            unsupported_keys=("unsupportedWidgets", "unsupportedInputs"),
        ),
        "styleCapabilityAudit": _audit_has_no_unsupported(
            style_ops_audit,
            unsupported_keys=("unsupportedProperties",),
        ),
    }
    blockers = [
        name
        for name, passed in gates.items()
        if not passed
    ]
    return {
        "schemaVersion": 1,
        "format": "backend-readiness-report",
        "passed": not blockers,
        "readiness": "ready-for-candidate-comparison" if not blockers else "blocked",
        "candidate": {
            "backend": style_ops_report.backend,
            "rendererBackend": renderer_report.renderer_backend,
            "path0RendererBackend": path0_report.renderer_backend,
        },
        "candidateScope": backend_candidate_scope_to_dict(),
        "gates": gates,
        "blockers": blockers,
        "renderer": {
            "backend": renderer_report.renderer_backend,
            "calls": compact_call_stream(renderer_report.calls),
            "capabilityAudit": renderer_audit,
        },
        "styleOps": {
            "backend": style_ops_report.backend,
            "schemaVersion": style_ops_report.style_ops_schema_version,
            "format": style_ops_report.style_ops_format,
            "capabilityAudit": style_ops_audit,
            "classCount": len(style_ops_report.classes),
            "directStyleCount": len(style_ops_report.direct_styles),
            "errors": style_ops_report_errors(style_ops_report),
        },
        "renderTree": {
            "format": render_tree_contract["format"],
            "summary": render_tree_contract["summary"],
            "stableKeyIds": render_tree_contract["stableKeyIds"],
            "errors": render_tree_contract["errors"],
        },
        "path0": {
            "rendererBackend": path0_report.renderer_backend,
            "input": path0_contract["input"],
            "render": path0_contract["render"],
            "output": path0_contract["output"],
            "semanticValidation": path0_contract["semanticValidation"],
            "evidence": path0_contract["evidence"],
            "calls": compact_call_stream(path0_report.calls),
            "errors": path0_contract["errors"],
        },
        "evidence": backend_readiness_evidence(
            renderer_audit,
            style_ops_audit,
            path0_contract,
            gates=gates,
        ),
        "requirements": backend_readiness_requirements(
            renderer_audit,
            style_ops_audit,
        ),
    }


def backend_candidate_scope_to_dict() -> dict[str, Any]:
    return {
        "level": "path0-render-tree-ir-v0",
        "rendererReplay": "internal-native-replay",
        "path0Evidence": "render-tree-ir-v0-fixture",
        "styleRuntime": "styleOps-resolved",
        "windowAdapterBoundary": "NativeWindowDriver",
        "externalBackendAbiStable": False,
        "productionBackend": False,
    }


def _audit_has_no_unsupported(
    audit: dict[str, Any],
    *,
    unsupported_keys: tuple[str, ...],
) -> bool:
    return all(not audit.get(key) for key in unsupported_keys)
