from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path

import pytest

import examples.native.backend_candidate_acceptance as backend_candidate_acceptance
import examples.native.backend_candidate_cli as backend_candidate_cli
import examples.native.backend_candidate_contracts as backend_candidate_contracts
import examples.native.backend_candidate_renderer as backend_candidate_renderer
import examples.native.backend_candidate_skeleton as backend_candidate_skeleton
from examples.native.backend_candidate_skeleton import (
    BACKEND_CANDIDATE_STYLES,
    BackendCandidateAcceptanceReport,
    ComposedRendererCandidateAcceptanceReport,
    HeadlessCandidateBackend,
    HeadlessCandidateAcceptanceReport,
    HeadlessCandidateRunReport,
    LayoutOnlyCandidateAcceptanceReport,
    LayoutOnlyRendererCandidate,
    LayoutOnlyTaskBoardStaticAcceptanceReport,
    MinimalBackendCandidateReplay,
    PaintOnlyRendererCandidate,
    Path0RenderTreeEvidenceReport,
    Path0RendererCandidate,
    RasterOnlyRendererCandidate,
    RecordingBackendCandidate,
    RecordingRendererCandidate,
    RendererCandidateAcceptanceReport,
    RenderTreeCandidateAcceptanceReport,
    StyleOpsCandidateAcceptanceReport,
    StyleOpsCandidateClassReport,
    StyleOpsCandidateDirectStyleReport,
    TaskBoardBackendCandidateReplay,
    acceptance_report_to_dict,
    backend_candidate_style_artifact,
    backend_candidate_app,
    backend_coverage_report_to_dict,
    backend_readiness_report_to_dict,
    compact_composed_renderer_contract_snapshot_to_dict,
    compact_renderer_contract_snapshot_to_dict,
    composed_renderer_contract_snapshot_to_dict,
    format_acceptance_report,
    main,
    path0_render_tree_evidence_report_to_dict,
    replay_minimal_candidate,
    renderer_contract_snapshot_to_dict,
    render_tree_contract_report_to_dict,
    run_backend_candidate_acceptance,
    run_composed_renderer_candidate_acceptance,
    run_headless_candidate_acceptance,
    run_layout_only_renderer_candidate_acceptance,
    run_layout_only_task_board_static_acceptance,
    run_paint_only_renderer_candidate_acceptance,
    run_path0_render_tree_artifact_evidence,
    run_path0_renderer_candidate_acceptance,
    run_path0_render_tree_evidence,
    run_raster_only_renderer_candidate_acceptance,
    run_renderer_candidate_acceptance,
    run_render_tree_candidate_acceptance,
    run_style_ops_candidate_acceptance,
    style_ops_candidate_report_to_dict,
)
from examples.native.window_demo import NativeWindowDemo
from otoe import (
    NativeBackendAdapter,
    NativeRendererBackend,
    NativeWindowDriver,
    PYTHON_NATIVE_RENDERER_BACKEND,
    RenderNode,
    RenderTree,
    render_tree_to_dict,
    run_native,
)
from otoe.capabilities import backend_capability_profile
from otoe.cli import main as otoe_cli_main


COMPOSED_RENDERER_COMPACT_CONTRACT_FIXTURE = Path(
    "examples/native/contracts/composed_renderer_compact_expected.json"
)
STYLE_OPS_CONTRACT_FIXTURE = Path("examples/native/contracts/style_ops_expected.json")
RENDER_TREE_CONTRACT_FIXTURE = Path(
    "examples/native/contracts/render_tree_expected.json"
)
BUNDLE_STYLE_OPS_CONTRACT_FIXTURE = Path(
    "examples/native/contracts/bundle_style_ops_expected.json"
)
BACKEND_READINESS_CONTRACT_FIXTURE = Path(
    "examples/native/contracts/backend_readiness_expected.json"
)
BACKEND_COVERAGE_DECLARATION_FIXTURE = Path(
    "examples/native/contracts/backend_coverage_full_declaration.json"
)
BACKEND_CANDIDATE_PARTIAL_PROFILE_FIXTURE = Path(
    "examples/native/contracts/backend_candidate_partial_profile.json"
)

def test_backend_candidate_skeleton_main_writes_contract_json_artifact(
    tmp_path,
    capsys,
):
    output = tmp_path / "artifacts" / "renderer-contract.json"

    result = main(
        [
            "--renderer-contract-json",
            "--compact-contract",
            "--contract-out",
            str(output),
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert result == 0
    assert captured.out == f"contract artifact: {output}\n"
    assert payload["schemaVersion"] == 1
    assert payload["format"] == "renderer-contract-compact"
    assert payload["rendererBackend"] == "recording-renderer-candidate"
