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

def test_backend_candidate_acceptance_skeleton_runs_replays():
    report = run_backend_candidate_acceptance()

    assert isinstance(report, BackendCandidateAcceptanceReport)
    assert report.passed is True
    assert report.minimal == MinimalBackendCandidateReplay(
        title="Backend Candidate Minimal",
        initial_frame=1,
        final_frame=8,
        initial_focus=("Input", "seed"),
        final_focus=("Button", "Two"),
        echo_visible=True,
        clicked_visible=True,
        shortcut_visible=True,
        scrolled=True,
    )
    assert report.task_board == TaskBoardBackendCandidateReplay(
        title="Backend Candidate Task Board",
        initial_frame=1,
        final_frame=7,
        filtered_titles=("Input polish",),
        modal_visible_after_click=True,
        modal_closed_after_escape=True,
        shortcut_text_after_escape="Shortcuts 1",
        reset_titles=("Runtime bridge", "Input polish", "Docs pass"),
        scrolled=True,
        final_focus=("Button", "Inspect"),
    )

def test_backend_candidate_adapter_skeleton_uses_run_native_boundary():
    backend = RecordingBackendCandidate(replay_minimal_candidate)

    result = run_native(
        backend_candidate_app(),
        stylesheet=BACKEND_CANDIDATE_STYLES,
        title="Candidate Boundary",
        backend=backend,
    )

    assert result is None
    assert isinstance(backend, NativeBackendAdapter)
    assert len(backend.replays) == 1
    replay = backend.replays[0]
    assert isinstance(replay, MinimalBackendCandidateReplay)
    assert replay.title == "Candidate Boundary"
    assert replay.passed is True

def test_headless_candidate_backend_records_layout_and_paint_summary():
    backend = HeadlessCandidateBackend(replay_minimal_candidate)

    result = run_native(
        backend_candidate_app(),
        stylesheet=BACKEND_CANDIDATE_STYLES,
        title="Headless Boundary",
        backend=backend,
    )

    assert result is None
    assert isinstance(backend, NativeBackendAdapter)
    assert len(backend.reports) == 1
    report = backend.reports[0]
    assert isinstance(report, HeadlessCandidateRunReport)
    assert report.backend == "headless-candidate"
    assert report.renderer_backend == "python-native"
    assert report.title == "Headless Boundary"
    assert report.passed is True
    assert report.before.frame == 1
    assert report.before.root_name == "ShortcutScope"
    assert report.before.focused == ("Input", "seed")
    assert report.after.frame == 8
    assert report.after.focused == ("Button", "Two")
    assert report.after.layout_boxes == report.before.layout_boxes
    assert report.after.paint_commands >= report.after.layout_boxes
    assert report.input_capabilities == (
        "click",
        "focus",
        "input_text",
        "key_down",
        "key_input",
        "shortcut",
        "tab_focus",
        "wheel",
    )
    assert "Echo alpha" in report.after.visible_text
    assert "Clicked two" in report.after.visible_text
    assert "text" in report.after.paint_kinds
    assert "rect" in report.after.paint_kinds

def test_headless_candidate_acceptance_runs_minimal_and_task_board_reports():
    report = run_headless_candidate_acceptance(
        renderer_backend=PYTHON_NATIVE_RENDERER_BACKEND
    )

    assert isinstance(report, HeadlessCandidateAcceptanceReport)
    assert report.passed is True
    assert report.minimal.backend == "headless-candidate"
    assert report.minimal.renderer_backend == "python-native"
    assert report.minimal.title == "Headless Candidate Minimal"
    assert isinstance(report.minimal.replay, MinimalBackendCandidateReplay)
    assert report.minimal.replay.passed is True
    assert report.minimal.input_capabilities == (
        "click",
        "focus",
        "input_text",
        "key_down",
        "key_input",
        "shortcut",
        "tab_focus",
        "wheel",
    )
    assert report.minimal.after.frame > report.minimal.before.frame
    assert "Echo alpha" in report.minimal.after.visible_text
    assert report.task_board.backend == "headless-candidate"
    assert report.task_board.title == "Headless Candidate Task Board"
    assert isinstance(report.task_board.replay, TaskBoardBackendCandidateReplay)
    assert report.task_board.replay.passed is True
    assert report.task_board.input_capabilities == (
        "click",
        "focus",
        "input_text",
        "key_down",
        "shortcut",
        "wheel",
    )
    assert report.task_board.after.frame > report.task_board.before.frame
    assert "Runtime bridge" in report.task_board.after.visible_text
    assert "Input polish" in report.task_board.after.visible_text

def test_headless_candidate_acceptance_formats_human_report():
    report = run_headless_candidate_acceptance()

    formatted = format_acceptance_report(report)

    assert "backend candidate acceptance" in formatted
    assert "status: passed" in formatted
    assert "minimal: passed" in formatted
    assert "task_board: passed" in formatted
    assert "backend: headless-candidate" in formatted
    assert "renderer backend: python-native" in formatted
    assert "frame: 1 -> 8" in formatted
    assert "frame: 1 -> 7" in formatted
    assert "visible text:" in formatted
    assert "Echo alpha" in formatted
    assert "Runtime bridge" in formatted

def test_headless_candidate_acceptance_serializes_json_report():
    report = run_headless_candidate_acceptance()

    payload = acceptance_report_to_dict(report)

    assert payload["passed"] is True
    assert payload["minimal"]["passed"] is True
    assert payload["minimal"]["replay"]["passed"] is True
    assert payload["minimal"]["after"]["frame"] == 8
    assert "Echo alpha" in payload["minimal"]["after"]["visible_text"]
    assert payload["task_board"]["passed"] is True
    assert payload["task_board"]["replay"]["passed"] is True
    assert payload["task_board"]["after"]["frame"] == 7
    assert "Input polish" in payload["task_board"]["after"]["visible_text"]

def test_backend_candidate_skeleton_main_outputs_report(capsys):
    result = main([])

    captured = capsys.readouterr()
    assert result == 0
    assert "backend candidate acceptance" in captured.out
    assert "status: passed" in captured.out

def test_backend_candidate_skeleton_main_outputs_json(capsys):
    result = main(["--json"])

    captured = capsys.readouterr()
    assert result == 0
    assert '"passed": true' in captured.out
    assert '"headless-candidate"' in captured.out

def test_backend_candidate_minimal_target_builds_driver_directly():
    driver = NativeWindowDriver.from_target(
        backend_candidate_app(),
        stylesheet=BACKEND_CANDIDATE_STYLES,
    )

    replay = replay_minimal_candidate(driver, title="Direct Driver")

    assert replay.title == "Direct Driver"
    assert replay.passed is True
