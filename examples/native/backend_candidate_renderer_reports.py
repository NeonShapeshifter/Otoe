from __future__ import annotations

from pathlib import Path
from typing import Any

from .backend_candidate_renderer_capability_audits import (
    renderer_capability_audit_to_dict,
)
from .backend_candidate_compact_snapshots import (
    compact_call_stream,
    compact_frame_contract_snapshot_to_dict,
    compact_run_contract_snapshot_to_dict,
)
from .backend_candidate_snapshot_payloads import (
    frame_contract_snapshot_to_dict,
    renderer_call_to_dict,
    run_contract_snapshot_to_dict,
)
from .backend_candidate_renderer_types import (
    ComposedRendererCandidateAcceptanceReport,
    RendererCandidateAcceptanceReport,
)


def renderer_contract_snapshot_to_dict(
    report: RendererCandidateAcceptanceReport,
) -> dict[str, Any]:
    return {
        "schemaVersion": 1,
        "rendererBackend": report.renderer_backend,
        "passed": report.passed,
        "capabilityAudit": renderer_capability_audit_to_dict(report.headless),
        "calls": [renderer_call_to_dict(call) for call in report.calls],
        "runs": {
            "minimal": run_contract_snapshot_to_dict(report.headless.minimal),
            "taskBoard": run_contract_snapshot_to_dict(report.headless.task_board),
        },
    }


def compact_renderer_contract_snapshot_to_dict(
    report: RendererCandidateAcceptanceReport,
) -> dict[str, Any]:
    return {
        "schemaVersion": 1,
        "format": "renderer-contract-compact",
        "rendererBackend": report.renderer_backend,
        "passed": report.passed,
        "capabilityAudit": renderer_capability_audit_to_dict(report.headless),
        "calls": compact_call_stream(report.calls),
        "runs": {
            "minimal": compact_run_contract_snapshot_to_dict(report.headless.minimal),
            "taskBoard": compact_run_contract_snapshot_to_dict(
                report.headless.task_board
            ),
        },
    }


def composed_renderer_contract_snapshot_to_dict(
    report: ComposedRendererCandidateAcceptanceReport,
) -> dict[str, Any]:
    return {
        "schemaVersion": 1,
        "rendererBackend": report.renderer_backend,
        "passed": report.passed,
        "capabilityAudit": renderer_capability_audit_to_dict(report.headless),
        "capabilities": {
            "layout": report.layout_backend,
            "paint": report.paint_backend,
            "raster": report.raster_backend,
        },
        "calls": {
            "layout": [renderer_call_to_dict(call) for call in report.layout_calls],
            "paint": [renderer_call_to_dict(call) for call in report.paint_calls],
            "raster": [renderer_call_to_dict(call) for call in report.raster_calls],
        },
        "runs": {
            "minimal": run_contract_snapshot_to_dict(report.headless.minimal),
            "taskBoard": run_contract_snapshot_to_dict(report.headless.task_board),
        },
        "pngSmoke": {
            "path": Path(report.png_path).name,
            "frame": frame_contract_snapshot_to_dict(report.png_frame),
        },
    }


def compact_composed_renderer_contract_snapshot_to_dict(
    report: ComposedRendererCandidateAcceptanceReport,
) -> dict[str, Any]:
    return {
        "schemaVersion": 1,
        "format": "composed-renderer-contract-compact",
        "rendererBackend": report.renderer_backend,
        "passed": report.passed,
        "capabilityAudit": renderer_capability_audit_to_dict(report.headless),
        "capabilities": {
            "layout": report.layout_backend,
            "paint": report.paint_backend,
            "raster": report.raster_backend,
        },
        "calls": {
            "layout": compact_call_stream(report.layout_calls),
            "paint": compact_call_stream(report.paint_calls),
            "raster": compact_call_stream(report.raster_calls),
        },
        "runs": {
            "minimal": compact_run_contract_snapshot_to_dict(report.headless.minimal),
            "taskBoard": compact_run_contract_snapshot_to_dict(
                report.headless.task_board
            ),
        },
        "pngSmoke": {
            "path": Path(report.png_path).name,
            "frame": compact_frame_contract_snapshot_to_dict(report.png_frame),
        },
    }
