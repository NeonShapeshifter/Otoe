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
    RenderTreeRendererCandidate,
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

def test_renderer_candidate_acceptance_runs_replays_through_renderer_spi():
    report = run_renderer_candidate_acceptance()

    assert isinstance(report, RendererCandidateAcceptanceReport)
    assert report.passed is True
    assert report.renderer_backend == "recording-renderer-candidate"
    assert report.headless.minimal.renderer_backend == "recording-renderer-candidate"
    assert report.headless.task_board.renderer_backend == "recording-renderer-candidate"
    phases = [call.phase for call in report.calls]
    assert phases.count("layout") >= 2
    assert phases.count("paint") >= 2
    assert any(call.subject == "ShortcutScope" for call in report.calls)
    assert any(call.paint_commands > 0 for call in report.calls)

def test_renderer_candidate_records_png_write(tmp_path):
    renderer = RecordingRendererCandidate()
    driver = NativeWindowDriver.from_target(
        backend_candidate_app(),
        stylesheet=BACKEND_CANDIDATE_STYLES,
        renderer_backend=renderer,
    )
    output = tmp_path / "renderer-candidate.png"

    driver.render_png(output)

    assert isinstance(renderer, NativeRendererBackend)
    assert renderer.layout_calls >= 2
    assert renderer.paint_calls >= 2
    assert renderer.write_png_calls == 1
    assert output.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")

def test_raster_only_renderer_candidate_passes_renderer_contract():
    report = run_raster_only_renderer_candidate_acceptance()
    payload = renderer_contract_snapshot_to_dict(report)

    assert isinstance(report, RendererCandidateAcceptanceReport)
    assert report.passed is True
    assert payload["rendererBackend"] == "raster-only-renderer-candidate"
    assert payload["runs"]["minimal"]["after"]["visibleText"][-3:] == [
        "Echo alpha",
        "Clicked two",
        "Shortcuts 1",
    ]
    assert payload["runs"]["taskBoard"]["after"]["focused"] == ["Button", "Inspect"]
    assert _call_signature(payload["calls"]) == _call_signature(
        renderer_contract_snapshot_to_dict(run_renderer_candidate_acceptance())["calls"]
    )

def test_raster_only_renderer_candidate_replaces_png_writer(tmp_path):
    renderer = RasterOnlyRendererCandidate()
    driver = NativeWindowDriver.from_target(
        backend_candidate_app(),
        stylesheet=BACKEND_CANDIDATE_STYLES,
        renderer_backend=renderer,
    )
    candidate_output = tmp_path / "candidate-raster.png"
    default_output = tmp_path / "default-raster.png"

    paint = driver.render_png(candidate_output)
    PYTHON_NATIVE_RENDERER_BACKEND.write_png(paint, default_output)

    assert isinstance(renderer, NativeRendererBackend)
    assert renderer.layout_calls >= 2
    assert renderer.paint_calls >= 2
    assert renderer.write_png_calls == 1
    assert candidate_output.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    assert default_output.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    assert candidate_output.read_bytes() != default_output.read_bytes()

def test_paint_only_renderer_candidate_passes_renderer_contract():
    report = run_paint_only_renderer_candidate_acceptance()
    payload = renderer_contract_snapshot_to_dict(report)
    minimal_after = payload["runs"]["minimal"]["after"]
    task_after = payload["runs"]["taskBoard"]["after"]

    assert isinstance(report, RendererCandidateAcceptanceReport)
    assert report.passed is True
    assert payload["rendererBackend"] == "paint-only-renderer-candidate"
    assert minimal_after["focused"] == ["Button", "Two"]
    assert minimal_after["visibleText"][-3:] == [
        "Echo alpha",
        "Clicked two",
        "Shortcuts 1",
    ]
    assert "rect" in minimal_after["paintKinds"]
    assert "text" in minimal_after["paintKinds"]
    assert _paint_texts(minimal_after["paint"]) == minimal_after["visibleText"]
    assert any(
        command["stroke"] == "#38bdf8"
        for command in minimal_after["paint"]
    )
    assert task_after["focused"] == ["Button", "Inspect"]
    assert "Input polish" in task_after["visibleText"]
    assert sorted(
        {
            tuple(command["clip"])
            for command in task_after["paint"]
            if command["clip"] is not None
        }
    ) == [(16, 137, 388, 92)]

def test_paint_only_renderer_candidate_replaces_paint_output(tmp_path):
    renderer = PaintOnlyRendererCandidate()
    default_driver = NativeWindowDriver.from_target(
        backend_candidate_app(),
        stylesheet=BACKEND_CANDIDATE_STYLES,
    )
    candidate_driver = NativeWindowDriver.from_target(
        backend_candidate_app(),
        stylesheet=BACKEND_CANDIDATE_STYLES,
        renderer_backend=renderer,
    )
    output = tmp_path / "paint-only.png"

    candidate_paint = candidate_driver.render_png(output)
    default_paint = default_driver.paint

    assert isinstance(renderer, NativeRendererBackend)
    assert renderer.layout_calls >= 2
    assert renderer.paint_calls >= 2
    assert renderer.write_png_calls == 1
    assert candidate_paint.commands != default_paint.commands
    assert _command_texts(candidate_paint.commands) == _command_texts(default_paint.commands)
    assert output.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")

def test_layout_only_renderer_candidate_passes_interactive_replays():
    report = run_layout_only_renderer_candidate_acceptance()

    assert isinstance(report, LayoutOnlyCandidateAcceptanceReport)
    assert report.passed is True
    assert report.renderer_backend == "layout-only-renderer-candidate"
    assert report.minimal.renderer_backend == "layout-only-renderer-candidate"
    assert report.minimal.title == "Headless Candidate Minimal"
    assert isinstance(report.minimal.replay, MinimalBackendCandidateReplay)
    assert report.minimal.replay.passed is True
    assert report.minimal.before.root_name == "ShortcutScope"
    assert report.minimal.after.root_name == "ShortcutScope"
    assert report.minimal.after.focused == ("Button", "Two")
    assert "Echo alpha" in report.minimal.after.visible_text
    assert "Clicked two" in report.minimal.after.visible_text
    assert "Shortcuts 1" in report.minimal.after.visible_text
    assert report.task_board.renderer_backend == "layout-only-renderer-candidate"
    assert report.task_board.title == "Headless Candidate Task Board"
    assert isinstance(report.task_board.replay, TaskBoardBackendCandidateReplay)
    assert report.task_board.replay.passed is True
    assert report.task_board.after.focused == ("Button", "Inspect")
    assert report.task_board.after.layout_boxes == 31
    assert report.task_board.after.paint_commands == 33
    assert "Runtime bridge" in report.task_board.after.visible_text
    assert "Input polish" in report.task_board.after.visible_text
    assert "Docs pass" in report.task_board.after.visible_text
    assert _call_signature_from_dataclasses(report.calls) == [
        ("layout", "MountedNode", 15, 0),
        ("paint", "ShortcutScope", 15, 18),
        ("paint", "ShortcutScope", 15, 19),
        ("layout", "MountedNode", 15, 0),
        ("paint", "ShortcutScope", 15, 19),
        ("layout", "MountedNode", 15, 0),
        ("paint", "ShortcutScope", 15, 19),
        ("layout", "MountedNode", 15, 0),
        ("paint", "ShortcutScope", 15, 19),
        ("layout", "MountedNode", 15, 0),
        ("paint", "ShortcutScope", 15, 19),
        ("layout", "MountedNode", 15, 0),
        ("paint", "ShortcutScope", 15, 19),
        ("layout", "MountedNode", 15, 0),
        ("paint", "ShortcutScope", 15, 19),
        ("layout", "MountedNode", 15, 0),
        ("paint", "ShortcutScope", 15, 19),
        ("layout", "MountedNode", 31, 0),
        ("paint", "ShortcutScope", 31, 32),
        ("paint", "ShortcutScope", 31, 33),
        ("layout", "MountedNode", 21, 0),
        ("paint", "ShortcutScope", 21, 21),
        ("layout", "MountedNode", 21, 0),
        ("paint", "ShortcutScope", 21, 21),
        ("layout", "MountedNode", 25, 0),
        ("paint", "ShortcutScope", 25, 26),
        ("layout", "MountedNode", 21, 0),
        ("paint", "ShortcutScope", 21, 21),
        ("layout", "MountedNode", 31, 0),
        ("paint", "ShortcutScope", 31, 33),
        ("layout", "MountedNode", 31, 0),
        ("paint", "ShortcutScope", 31, 33),
    ]

def test_layout_only_renderer_candidate_lays_out_static_task_board():
    report = run_layout_only_task_board_static_acceptance()

    assert isinstance(report, LayoutOnlyTaskBoardStaticAcceptanceReport)
    assert report.passed is True
    assert report.renderer_backend == "layout-only-renderer-candidate"
    assert report.frame.label == "task_board_static"
    assert report.frame.root_name == "ShortcutScope"
    assert report.frame.size == (420, 257)
    assert report.frame.focused == ("Input", "Search tasks")
    assert report.frame.layout_boxes == 31
    assert report.frame.paint_commands == 33
    assert report.frame.visible_text == (
        "Native Task Board",
        "3 visible",
        "Search tasks",
        "Clear",
        "New",
        "Shortcuts 0",
        "Ctrl+K clears search",
        "Runtime bridge",
        "Core",
        "Ready",
        "Inspect",
        "Input polish",
        "Native",
        "Active",
        "Inspect",
        "Docs pass",
        "DX",
        "Queued",
        "Inspect",
    )
    assert sorted(
        {
            snapshot.clip
            for snapshot in report.frame.paint_snapshot
            if snapshot.clip is not None
        }
    ) == [(16, 137, 388, 92)]
    assert _call_signature_from_dataclasses(report.calls) == [
        ("layout", "MountedNode", 31, 0),
        ("paint", "ShortcutScope", 31, 32),
        ("paint", "ShortcutScope", 31, 33),
    ]

def test_layout_only_renderer_candidate_replaces_layout_and_renders_png(tmp_path):
    renderer = LayoutOnlyRendererCandidate()
    default_driver = NativeWindowDriver.from_target(
        backend_candidate_app(),
        stylesheet=BACKEND_CANDIDATE_STYLES,
    )
    candidate_driver = NativeWindowDriver.from_target(
        backend_candidate_app(),
        stylesheet=BACKEND_CANDIDATE_STYLES,
        renderer_backend=renderer,
    )
    output = tmp_path / "layout-only.png"

    candidate_paint = candidate_driver.render_png(output)
    default_paint = default_driver.paint

    assert isinstance(renderer, NativeRendererBackend)
    assert renderer.layout_calls >= 2
    assert renderer.paint_calls >= 2
    assert renderer.write_png_calls == 1
    assert candidate_driver.surface.layout.root.name == "ShortcutScope"
    assert candidate_driver.surface.layout.root.width == default_driver.surface.layout.root.width
    assert candidate_paint.commands
    assert _command_texts(candidate_paint.commands) == _command_texts(default_paint.commands)
    assert output.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")

def test_layout_only_renderer_candidate_renders_static_task_board_png(tmp_path):
    renderer = LayoutOnlyRendererCandidate()
    demo = NativeWindowDemo(renderer_backend=renderer)
    output = tmp_path / "layout-only-task-board.png"

    paint = demo.render(output)

    assert isinstance(renderer, NativeRendererBackend)
    assert renderer.layout_calls >= 2
    assert renderer.paint_calls >= 2
    assert renderer.write_png_calls == 1
    assert demo.driver.surface.layout.root.name == "ShortcutScope"
    assert demo.driver.size == (420, 257)
    assert _command_texts(paint.commands) == list(
        run_layout_only_task_board_static_acceptance().frame.visible_text
    )
    assert output.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")

def test_path0_renderer_candidate_passes_contract_without_recording_delegation(
    monkeypatch,
):
    render_tree_targets = []
    real_render_tree_from_target = backend_candidate_renderer.render_tree_from_target

    def spy_render_tree_from_target(*args, **kwargs):
        render_tree_targets.append(args[0])
        return real_render_tree_from_target(*args, **kwargs)

    monkeypatch.setattr(
        backend_candidate_renderer,
        "render_tree_from_target",
        spy_render_tree_from_target,
    )

    report = run_path0_renderer_candidate_acceptance()
    payload = renderer_contract_snapshot_to_dict(report)

    assert isinstance(report, RendererCandidateAcceptanceReport)
    assert report.passed is True
    assert report.renderer_backend == "path0-renderer-candidate"
    assert payload["rendererBackend"] == "path0-renderer-candidate"
    assert report.headless.minimal.renderer_backend == "path0-renderer-candidate"
    assert report.headless.task_board.renderer_backend == "path0-renderer-candidate"
    assert payload["runs"]["minimal"]["after"]["focused"] == ["Button", "Two"]
    assert payload["runs"]["taskBoard"]["after"]["focused"] == ["Button", "Inspect"]
    assert "rect" in payload["runs"]["minimal"]["after"]["paintKinds"]
    assert "text" in payload["runs"]["minimal"]["after"]["paintKinds"]
    assert _paint_texts(payload["runs"]["minimal"]["after"]["paint"]) == (
        payload["runs"]["minimal"]["after"]["visibleText"]
    )
    assert render_tree_targets
    assert {call.phase for call in report.calls} == {"layout", "paint"}
    assert any(call.layout_boxes > 0 for call in report.calls)
    assert any(call.paint_commands > 0 for call in report.calls)

def test_path0_renderer_candidate_owns_layout_paint_and_raster(tmp_path):
    renderer = Path0RendererCandidate()
    driver = NativeWindowDriver.from_target(
        backend_candidate_app(),
        stylesheet=BACKEND_CANDIDATE_STYLES,
        renderer_backend=renderer,
    )
    candidate_output = tmp_path / "path0-candidate.png"
    default_output = tmp_path / "default-path0-paint.png"

    paint = driver.render_png(candidate_output)
    PYTHON_NATIVE_RENDERER_BACKEND.write_png(paint, default_output)

    assert isinstance(renderer, NativeRendererBackend)
    assert not isinstance(renderer, RecordingRendererCandidate)
    assert renderer.layout_calls >= 2
    assert renderer.paint_calls >= 2
    assert renderer.write_png_calls == 1
    assert driver.surface.layout.root.name == "ShortcutScope"
    assert _command_texts(paint.commands)[-3:] == [
        "Echo seed",
        "Clicked none",
        "Shortcuts 0",
    ]
    assert candidate_output.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    assert default_output.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    assert candidate_output.read_bytes() != default_output.read_bytes()


def test_path0_renderer_candidate_exposes_render_tree_backend_boundary():
    renderer = Path0RendererCandidate()

    assert isinstance(renderer, NativeRendererBackend)
    assert isinstance(renderer, RenderTreeRendererCandidate)
    assert hasattr(renderer, "layout_render_tree")


def test_path0_renderer_candidate_can_use_style_ops_artifact_without_stylesheet():
    artifact = deepcopy(backend_candidate_style_artifact())
    shell_rule = next(
        rule for rule in artifact["rules"] if rule["className"] == "candidate-shell"
    )
    shell_rule["declarations"]["width"] = {
        "type": "size",
        "value": 999,
        "unit": "px",
    }
    renderer = Path0RendererCandidate.from_style_artifact(
        artifact,
        strict=False,
    )
    driver = NativeWindowDriver.from_target(
        backend_candidate_app(),
        renderer_backend=renderer,
    )

    assert driver.surface.layout.by_path((0,)).width == 220
    assert renderer.layout_calls >= 1

def test_composed_renderer_candidate_combines_partial_capabilities(tmp_path):
    output = tmp_path / "composed-layout-paint-raster.png"

    report = run_composed_renderer_candidate_acceptance(output)

    assert isinstance(report, ComposedRendererCandidateAcceptanceReport)
    assert report.passed is True
    assert report.renderer_backend == "composed-layout-paint-raster-candidate"
    assert report.layout_backend == "layout-only-renderer-candidate"
    assert report.paint_backend == "paint-only-renderer-candidate"
    assert report.raster_backend == "raster-only-renderer-candidate"
    assert report.headless.minimal.renderer_backend == report.renderer_backend
    assert report.headless.task_board.renderer_backend == report.renderer_backend
    assert report.headless.minimal.passed is True
    assert report.headless.task_board.passed is True
    assert report.png_frame.label == "png_smoke"
    assert report.png_frame.root_name == "ShortcutScope"
    assert "Echo seed" in report.png_frame.visible_text
    assert {call.phase for call in report.layout_calls} == {"layout"}
    assert {call.phase for call in report.paint_calls} == {"paint"}
    assert {call.phase for call in report.raster_calls} == {"write_png"}
    assert _call_signature_from_dataclasses(report.raster_calls) == [
        ("write_png", output.name, 0, report.png_frame.paint_commands),
    ]
    assert output.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")

def test_composed_renderer_contract_snapshot_is_stable_json(tmp_path):
    output = tmp_path / "composed-contract.png"
    report = run_composed_renderer_candidate_acceptance(output)

    payload = composed_renderer_contract_snapshot_to_dict(report)
    encoded = json.dumps(payload, sort_keys=True)

    assert payload["schemaVersion"] == 1
    assert payload["rendererBackend"] == "composed-layout-paint-raster-candidate"
    assert payload["passed"] is True
    assert payload["capabilities"] == {
        "layout": "layout-only-renderer-candidate",
        "paint": "paint-only-renderer-candidate",
        "raster": "raster-only-renderer-candidate",
    }
    assert '"pngSmoke"' in encoded
    assert payload["runs"]["minimal"]["after"]["focused"] == ["Button", "Two"]
    assert payload["runs"]["taskBoard"]["after"]["focused"] == ["Button", "Inspect"]
    assert payload["pngSmoke"]["path"] == output.name
    assert payload["pngSmoke"]["frame"]["rootName"] == "ShortcutScope"
    assert "Echo seed" in payload["pngSmoke"]["frame"]["visibleText"]
    assert {call["phase"] for call in payload["calls"]["layout"]} == {"layout"}
    assert {call["phase"] for call in payload["calls"]["paint"]} == {"paint"}
    assert _call_signature(payload["calls"]["raster"]) == [
        (
            "write_png",
            output.name,
            0,
            payload["pngSmoke"]["frame"]["paintCommands"],
        ),
    ]

def test_compact_composed_renderer_contract_snapshot_uses_signatures_and_hashes(
    tmp_path,
):
    output = tmp_path / "compact-composed-contract.png"
    report = run_composed_renderer_candidate_acceptance(output)

    compact = compact_composed_renderer_contract_snapshot_to_dict(report)
    full = composed_renderer_contract_snapshot_to_dict(report)
    encoded_compact = json.dumps(compact, sort_keys=True)
    encoded_full = json.dumps(full, sort_keys=True)
    png_frame = compact["pngSmoke"]["frame"]

    assert compact["schemaVersion"] == 1
    assert compact["format"] == "composed-renderer-contract-compact"
    assert compact["rendererBackend"] == "composed-layout-paint-raster-candidate"
    assert compact["capabilities"] == full["capabilities"]
    assert len(encoded_compact) < len(encoded_full)
    assert "layout" not in png_frame
    assert "paint" not in png_frame
    assert png_frame["layoutSignature"].startswith("sha256:")
    assert png_frame["paintSignature"].startswith("sha256:")
    assert png_frame["anchors"]["layoutNames"][0] == "ShortcutScope"
    assert png_frame["anchors"]["textPaths"][0] == {
        "path": [0, 0, 0],
        "text": "seed",
    }
    assert png_frame["hashes"]["layout"].startswith("sha256:")
    assert png_frame["hashes"]["paint"].startswith("sha256:")
    assert png_frame["hashes"]["frame"].startswith("sha256:")
    assert compact["calls"]["layout"]["count"] == len(report.layout_calls)
    assert compact["calls"]["paint"]["count"] == len(report.paint_calls)
    assert compact["calls"]["raster"]["signature"] == [
        {
            "layoutBoxes": 0,
            "paintCommands": png_frame["paintCommands"],
            "phase": "write_png",
            "subject": output.name,
        }
    ]

def test_composed_renderer_compact_contract_fixture_matches_generated_contract(
    tmp_path,
    capsys,
):
    output = tmp_path / "composed_renderer_candidate.png"
    actual = tmp_path / "actual-composed-renderer-contract.json"
    report = run_composed_renderer_candidate_acceptance(output)
    payload = compact_composed_renderer_contract_snapshot_to_dict(report)
    actual.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")

    result = otoe_cli_main(
        [
            "compare-contract",
            str(COMPOSED_RENDERER_COMPACT_CONTRACT_FIXTURE),
            str(actual),
            "--json",
        ]
    )

    captured = capsys.readouterr()
    comparison = json.loads(captured.out)
    assert result == 0
    assert comparison["matched"] is True
    assert comparison["differenceCount"] == 0
    assert comparison["differences"] == []
    assert output.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")

def test_composed_renderer_compact_contract_fixture_can_ignore_smoke_filename(
    tmp_path,
    capsys,
):
    output = tmp_path / "different-smoke-name.png"
    actual = tmp_path / "actual-composed-renderer-contract.json"
    report = run_composed_renderer_candidate_acceptance(output)
    payload = compact_composed_renderer_contract_snapshot_to_dict(report)
    actual.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")

    result = otoe_cli_main(
        [
            "compare-contract",
            str(COMPOSED_RENDERER_COMPACT_CONTRACT_FIXTURE),
            str(actual),
            "--ignore-path",
            "/pngSmoke/path",
            "--ignore-path",
            "/calls/raster/signature/0/subject",
            "--ignore-path",
            "/calls/raster/hash",
            "--json",
        ]
    )

    captured = capsys.readouterr()
    comparison = json.loads(captured.out)
    assert result == 0
    assert comparison["matched"] is True
    assert comparison["differenceCount"] == 0
    assert comparison["ignoredPaths"] == [
        "/pngSmoke/path",
        "/calls/raster/signature/0/subject",
        "/calls/raster/hash",
    ]

def test_renderer_candidate_contract_snapshot_is_stable_json():
    payload = renderer_contract_snapshot_to_dict(run_renderer_candidate_acceptance())
    encoded = json.dumps(payload, sort_keys=True)
    minimal_after = payload["runs"]["minimal"]["after"]
    task_after = payload["runs"]["taskBoard"]["after"]

    assert payload["schemaVersion"] == 1
    assert payload["rendererBackend"] == "recording-renderer-candidate"
    assert payload["passed"] is True
    assert '"schemaVersion": 1' in encoded
    assert _call_signature(payload["calls"]) == [
        ("layout", "MountedNode", 15, 0),
        ("paint", "ShortcutScope", 15, 18),
        ("paint", "ShortcutScope", 15, 19),
        ("layout", "MountedNode", 15, 0),
        ("paint", "ShortcutScope", 15, 19),
        ("layout", "MountedNode", 15, 0),
        ("paint", "ShortcutScope", 15, 19),
        ("layout", "MountedNode", 15, 0),
        ("paint", "ShortcutScope", 15, 19),
        ("layout", "MountedNode", 15, 0),
        ("paint", "ShortcutScope", 15, 19),
        ("layout", "MountedNode", 15, 0),
        ("paint", "ShortcutScope", 15, 19),
        ("layout", "MountedNode", 15, 0),
        ("paint", "ShortcutScope", 15, 19),
        ("layout", "MountedNode", 15, 0),
        ("paint", "ShortcutScope", 15, 19),
        ("layout", "MountedNode", 31, 0),
        ("paint", "ShortcutScope", 31, 32),
        ("paint", "ShortcutScope", 31, 33),
        ("layout", "MountedNode", 21, 0),
        ("paint", "ShortcutScope", 21, 21),
        ("layout", "MountedNode", 21, 0),
        ("paint", "ShortcutScope", 21, 21),
        ("layout", "MountedNode", 25, 0),
        ("paint", "ShortcutScope", 25, 26),
        ("layout", "MountedNode", 21, 0),
        ("paint", "ShortcutScope", 21, 21),
        ("layout", "MountedNode", 31, 0),
        ("paint", "ShortcutScope", 31, 33),
        ("layout", "MountedNode", 31, 0),
        ("paint", "ShortcutScope", 31, 33),
    ]

    assert minimal_after["rootName"] == "ShortcutScope"
    assert minimal_after["size"] == [220, 251]
    assert minimal_after["focused"] == ["Button", "Two"]
    assert minimal_after["layoutBoxes"] == 15
    assert minimal_after["paintCommands"] == 19
    assert minimal_after["visibleText"] == [
        "alpha",
        "One",
        "Two",
        "First",
        "Second",
        "Capability Panel",
        "Echo alpha",
        "Clicked two",
        "Shortcuts 1",
    ]
    assert _layout_signature(minimal_after["layout"]) == [
        ((), "ShortcutScope", (0, 0, 220, 251), None, ("onGlobalKeyDown",)),
        ((0,), "FocusScope", (0, 0, 220, 251), None, ()),
        ((0, 0), "VStack", (0, 0, 220, 251), None, ()),
        (
            (0, 0, 0),
            "Input",
            (8, 8, 120, 36),
            "alpha",
            ("onBlur", "onChange", "onFocus", "onKeyDown"),
        ),
        ((0, 0, 1), "HStack", (8, 50, 200, 44), None, ()),
        (
            (0, 0, 1, 0),
            "Button",
            (8, 54, 42, 36),
            "One",
            ("onBlur", "onClick", "onFocus", "onKeyDown"),
        ),
        (
            (0, 0, 1, 1),
            "Button",
            (166, 54, 42, 36),
            "Two",
            ("onBlur", "onClick", "onFocus", "onKeyDown"),
        ),
        ((0, 0, 2), "ScrollView", (8, 100, 200, 44), None, ("onScroll",)),
        ((0, 0, 2, 0), "Button", (12, 68, 55, 34), "First", ("onClick",)),
        ((0, 0, 2, 1), "Button", (12, 106, 63, 34), "Second", ("onClick",)),
        ((0, 0, 3), "Panel", (8, 150, 180, 24), None, ()),
        ((0, 0, 3, 0), "Text", (11, 153, 115, 17), "Capability Panel", ()),
        ((0, 0, 4), "Text", (8, 180, 72, 17), "Echo alpha", ()),
        ((0, 0, 5), "Text", (8, 203, 79, 17), "Clicked two", ()),
        ((0, 0, 6), "Text", (8, 226, 79, 17), "Shortcuts 1", ()),
    ]
    assert _paint_texts(minimal_after["paint"]) == [
        "alpha",
        "One",
        "Two",
        "First",
        "Second",
        "Capability Panel",
        "Echo alpha",
        "Clicked two",
        "Shortcuts 1",
    ]
    assert [
        command
        for command in minimal_after["paint"]
        if command["stroke"] == "#38bdf8"
    ] == [
        {
            "bounds": [164, 52, 46, 40],
            "clip": None,
            "color": None,
            "fill": None,
            "fontSize": 14,
            "kind": "rect",
            "path": [0, 0, 1, 1],
            "radius": 10,
            "stroke": "#38bdf8",
            "strokeWidth": 2,
            "text": None,
        }
    ]

    assert task_after["rootName"] == "ShortcutScope"
    assert task_after["size"] == [420, 257]
    assert task_after["focused"] == ["Button", "Inspect"]
    assert task_after["layoutBoxes"] == 31
    assert task_after["paintCommands"] == 33
    assert task_after["visibleText"] == [
        "Native Task Board",
        "3 visible",
        "Search tasks",
        "Clear",
        "New",
        "Shortcuts 2",
        "Ctrl+K clears search",
        "Runtime bridge",
        "Core",
        "Ready",
        "Inspect",
        "Input polish",
        "Native",
        "Active",
        "Inspect",
        "Docs pass",
        "DX",
        "Queued",
        "Inspect",
    ]
    assert sorted(
        {
            tuple(command["clip"])
            for command in task_after["paint"]
            if command["clip"] is not None
        }
    ) == [(16, 137, 388, 92)]

def test_compact_renderer_contract_snapshot_uses_signatures_and_hashes():
    report = run_renderer_candidate_acceptance()

    compact = compact_renderer_contract_snapshot_to_dict(report)
    full = renderer_contract_snapshot_to_dict(report)
    encoded_compact = json.dumps(compact, sort_keys=True)
    encoded_full = json.dumps(full, sort_keys=True)
    minimal_after = compact["runs"]["minimal"]["after"]
    audit = compact["capabilityAudit"]

    assert compact["schemaVersion"] == 1
    assert compact["format"] == "renderer-contract-compact"
    assert compact["rendererBackend"] == "recording-renderer-candidate"
    assert compact["passed"] is True
    assert audit["summary"] == {
        "widgetInstances": 46,
        "widgetTypes": 11,
        "inputBindings": 24,
        "inputCapabilities": 8,
        "unsupportedWidgets": 0,
        "unsupportedInputs": 0,
    }
    assert audit["widgets"] == [
        {
            "support": "container",
            "count": 18,
            "widgets": [
                {"name": "FocusScope", "count": 1},
                {"name": "For", "count": 1},
                {"name": "HStack", "count": 7},
                {"name": "Panel", "count": 1},
                {"name": "ScrollView", "count": 2},
                {"name": "ShortcutScope", "count": 2},
                {"name": "Show", "count": 1},
                {"name": "VStack", "count": 3},
            ],
        },
        {
            "support": "control",
            "count": 11,
            "widgets": [
                {"name": "Button", "count": 9},
                {"name": "Input", "count": 2},
            ],
        },
        {
            "support": "text",
            "count": 17,
            "widgets": [{"name": "Text", "count": 17}],
        },
    ]
    assert audit["inputs"] == [
        {
            "support": "supported",
            "count": 24,
            "capabilities": [
                {"capability": "click", "count": 9},
                {"capability": "focus", "count": 6},
                {"capability": "input_text", "count": 2},
                {"capability": "key_down", "count": 3},
                {"capability": "shortcut", "count": 2},
                {"capability": "wheel", "count": 2},
            ],
        }
    ]
    assert audit["unsupportedWidgets"] == []
    assert audit["unsupportedInputs"] == []
    assert len(encoded_compact) < len(encoded_full)
    assert compact["calls"]["count"] == len(report.calls)
    assert compact["calls"]["hash"].startswith("sha256:")
    assert "layout" not in minimal_after
    assert "paint" not in minimal_after
    assert minimal_after["layoutSignature"].startswith("sha256:")
    assert minimal_after["paintSignature"].startswith("sha256:")
    assert minimal_after["anchors"]["layoutNames"][0] == "ShortcutScope"
    assert minimal_after["anchors"]["clipRects"] == [[8, 100, 200, 44]]
    assert minimal_after["hashes"]["layout"].startswith("sha256:")
    assert minimal_after["hashes"]["paint"].startswith("sha256:")

def test_backend_candidate_skeleton_main_outputs_renderer_contract_json(capsys):
    result = main(["--renderer-contract-json"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert result == 0
    assert payload["schemaVersion"] == 1
    assert payload["rendererBackend"] == "recording-renderer-candidate"
    assert payload["runs"]["minimal"]["after"]["layout"]
    assert payload["runs"]["minimal"]["after"]["paint"]

def test_backend_candidate_skeleton_main_outputs_composed_renderer_contract_json(
    tmp_path,
    capsys,
):
    output = tmp_path / "composed-cli.png"

    result = main(
        [
            "--composed-renderer-contract-json",
            "--composed-renderer-png",
            str(output),
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert result == 0
    assert output.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    assert payload["schemaVersion"] == 1
    assert payload["rendererBackend"] == "composed-layout-paint-raster-candidate"
    assert payload["capabilities"]["layout"] == "layout-only-renderer-candidate"
    assert payload["capabilities"]["paint"] == "paint-only-renderer-candidate"
    assert payload["capabilities"]["raster"] == "raster-only-renderer-candidate"
    assert payload["pngSmoke"]["path"] == output.name

def test_backend_candidate_skeleton_main_outputs_compact_renderer_contract_json(capsys):
    result = main(["--renderer-contract-json", "--compact-contract"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert result == 0
    assert payload["schemaVersion"] == 1
    assert payload["format"] == "renderer-contract-compact"
    assert payload["runs"]["minimal"]["after"]["layoutSignature"].startswith("sha256:")
    assert "layout" not in payload["runs"]["minimal"]["after"]
    assert payload["calls"]["hash"].startswith("sha256:")

def test_backend_candidate_skeleton_main_outputs_compact_composed_renderer_contract_json(
    tmp_path,
    capsys,
):
    output = tmp_path / "compact-composed-cli.png"

    result = main(
        [
            "--composed-renderer-contract-json",
            "--compact-contract",
            "--composed-renderer-png",
            str(output),
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert result == 0
    assert output.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    assert payload["schemaVersion"] == 1
    assert payload["format"] == "composed-renderer-contract-compact"
    assert payload["pngSmoke"]["path"] == output.name
    assert payload["pngSmoke"]["frame"]["paintSignature"].startswith("sha256:")
    assert "paint" not in payload["pngSmoke"]["frame"]
    assert payload["calls"]["raster"]["hash"].startswith("sha256:")

def test_backend_candidate_skeleton_main_refreshes_composed_contract_fixture(
    tmp_path,
    capsys,
):
    expected = tmp_path / "contracts" / "expected.json"
    actual_png = tmp_path / "composed.png"

    result = main(
        [
            "--composed-renderer-contract-json",
            "--compact-contract",
            "--composed-renderer-png",
            str(actual_png),
            "--contract-out",
            str(expected),
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(expected.read_text(encoding="utf-8"))
    assert result == 0
    assert captured.out == f"contract artifact: {expected}\n"
    assert actual_png.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    assert payload["format"] == "composed-renderer-contract-compact"
    assert payload["pngSmoke"]["path"] == actual_png.name
    assert payload["calls"]["layout"]["count"] > 0

def _call_signature(calls):
    return [
        (
            call["phase"],
            call["subject"],
            call["layoutBoxes"],
            call["paintCommands"],
        )
        for call in calls
    ]

def _call_signature_from_dataclasses(calls):
    return [
        (
            call.phase,
            call.subject,
            call.layout_boxes,
            call.paint_commands,
        )
        for call in calls
    ]

def _layout_signature(layout):
    return [
        (
            tuple(box["path"]),
            box["name"],
            tuple(box["bounds"]),
            box["text"],
            tuple(box["events"]),
        )
        for box in layout
    ]

def _paint_texts(paint):
    return [
        command["text"]
        for command in paint
        if command["kind"] == "text"
    ]

def _command_texts(commands):
    return [
        command.text
        for command in commands
        if command.kind == "text"
    ]
