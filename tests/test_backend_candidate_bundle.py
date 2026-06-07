from argparse import Namespace
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path

import pytest

import examples.native.backend_candidate_acceptance as backend_candidate_acceptance
from examples.native.backend_candidate_artifacts import (
    RenderTreeSource,
    render_tree_source_from_args,
)
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


def test_backend_candidate_render_tree_source_from_args_is_typed():
    source = render_tree_source_from_args(
        Namespace(
            bundle=None,
            render_tree_artifact=None,
            style_artifact=None,
        )
    )

    assert source == RenderTreeSource(
        style_artifact=None,
        target=None,
        render_tree=None,
        source=None,
    )


def _build_style_ops_bundle(tmp_path, monkeypatch, capsys):
    app = tmp_path / "bundle_style_ops_app.py"
    app.write_text(
        "from otoe import Text, VStack\n"
        "app = VStack(Text('Bundled StyleOps', className='bundle-label'), className='bundle-shell', padding=8)\n",
        encoding="utf-8",
    )
    styles = tmp_path / "styles.css"
    styles.write_text(
        ".bundle-shell { width: 180; background: #ffffff; }\n"
        ".bundle-label { color: #111827; }\n",
        encoding="utf-8",
    )
    output = tmp_path / "dist" / "bundle-style-ops"
    monkeypatch.syspath_prepend(str(tmp_path))

    result = otoe_cli_main(
        [
            "build",
            "bundle_style_ops_app:app",
            "--css",
            str(styles),
            "--out",
            str(output),
            "--validate",
        ]
    )

    capsys.readouterr()
    assert result == 0
    return output

def test_backend_candidate_skeleton_main_outputs_style_ops_contract_from_artifact(
    tmp_path,
    capsys,
):
    artifact = tmp_path / "otoe-styles.json"
    contract = tmp_path / "style-ops-contract.json"
    artifact.write_text(
        json.dumps(backend_candidate_style_artifact(), indent=2, sort_keys=True),
        encoding="utf-8",
    )

    result = main(
        [
            "--style-ops-contract-json",
            "--style-artifact",
            str(artifact),
            "--contract-out",
            str(contract),
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(contract.read_text(encoding="utf-8"))
    assert result == 0
    assert captured.out == f"contract artifact: {contract}\n"
    assert payload["passed"] is True
    assert payload["format"] == "style-ops-contract"

def test_backend_candidate_skeleton_outputs_render_tree_contract_from_artifact(
    tmp_path,
    capsys,
):
    artifact = tmp_path / "otoe-styles.json"
    contract = tmp_path / "render-tree-contract.json"
    payload = backend_candidate_style_artifact()
    artifact.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    result = main(
        [
            "--render-tree-contract-json",
            "--style-artifact",
            str(artifact),
            "--contract-out",
            str(contract),
        ]
    )

    captured = capsys.readouterr()
    contract_payload = json.loads(contract.read_text(encoding="utf-8"))
    shell = contract_payload["runs"]["minimal"]["root"]["children"][0]["children"][0]
    assert result == 0
    assert captured.out == f"contract artifact: {contract}\n"
    assert contract_payload["passed"] is True
    assert contract_payload["format"] == "render-tree-contract"
    assert contract_payload["artifactSource"] == f"style-artifact:{artifact.name}"
    assert shell["style"]["width"] == {"type": "size", "value": 220, "unit": "px"}

def test_backend_candidate_skeleton_rejects_render_tree_style_ops_tamper(
    tmp_path,
    capsys,
):
    artifact = tmp_path / "otoe-styles.json"
    payload = backend_candidate_style_artifact()
    shell_ops = next(
        entry
        for entry in payload["styleOps"]["classes"]
        if entry["className"] == "candidate-shell"
    )
    width_op = next(op for op in shell_ops["ops"] if op["property"] == "width")
    width_op["value"] = {"type": "size", "value": 999, "unit": "px"}
    artifact.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    result = main(
        [
            "--render-tree-contract-json",
            "--style-artifact",
            str(artifact),
        ]
    )

    captured = capsys.readouterr()
    assert result == 1
    assert "render-tree-contract: Invalid style artifact:" in captured.err
    assert "styleOps class 'candidate-shell' applied declarations do not match compiled rules" in captured.err

def test_backend_candidate_skeleton_replays_style_ops_from_built_bundle(
    tmp_path,
    monkeypatch,
    capsys,
):
    output = _build_style_ops_bundle(tmp_path, monkeypatch, capsys)
    contract = tmp_path / "dist" / "bundle-style-ops-contract.json"
    contract_result = main(
        [
            "--style-ops-contract-json",
            "--bundle",
            str(output),
            "--contract-out",
            str(contract),
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(contract.read_text(encoding="utf-8"))
    classes = {entry["className"]: entry for entry in payload["classes"]}
    direct_styles = {tuple(entry["path"]): entry for entry in payload["directStyles"]}
    assert contract_result == 0
    assert captured.out == f"contract artifact: {contract}\n"
    assert payload["passed"] is True
    assert classes["bundle-shell"]["appliedDeclarations"]["width"] == {
        "type": "size",
        "value": 180,
        "unit": "px",
    }
    assert classes["bundle-label"]["appliedDeclarations"]["color"] == {
        "type": "literal",
        "value": "#111827",
    }
    assert direct_styles[()]["appliedDeclarations"]["padding"] == {
        "type": "size",
        "value": 8,
        "unit": "px",
    }

def test_backend_candidate_skeleton_replays_render_tree_from_built_bundle(
    tmp_path,
    monkeypatch,
    capsys,
):
    output = _build_style_ops_bundle(tmp_path, monkeypatch, capsys)
    contract = tmp_path / "dist" / "bundle-render-tree-contract.json"

    result = main(
        [
            "--render-tree-contract-json",
            "--bundle",
            str(output),
            "--contract-out",
            str(contract),
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(contract.read_text(encoding="utf-8"))
    artifact_target = payload["runs"]["artifactTarget"]["root"]
    assert result == 0
    assert captured.out == f"contract artifact: {contract}\n"
    assert payload["passed"] is True
    assert payload["artifactSource"] == f"bundle:{output.name}"
    assert payload["summary"]["artifactTargetNodes"] == 2
    assert payload["visibleText"]["artifactTarget"] == ["Bundled StyleOps"]
    assert artifact_target["style"]["width"] == {
        "type": "size",
        "value": 180,
        "unit": "px",
    }
    assert artifact_target["style"]["padding"] == {
        "type": "size",
        "value": 8,
        "unit": "px",
    }

def test_backend_readiness_includes_render_tree_artifact_target_from_bundle(
    tmp_path,
    monkeypatch,
    capsys,
):
    output = _build_style_ops_bundle(tmp_path, monkeypatch, capsys)
    contract = tmp_path / "dist" / "bundle-readiness.json"

    result = main(
        [
            "--backend-readiness-json",
            "--bundle",
            str(output),
            "--contract-out",
            str(contract),
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(contract.read_text(encoding="utf-8"))
    assert result == 0
    assert captured.out == f"contract artifact: {contract}\n"
    assert payload["passed"] is True
    assert payload["gates"]["renderTreeReplay"] is True
    assert payload["gates"]["path0RenderTreeEvidence"] is True
    assert payload["renderTree"]["summary"]["artifactTargetNodes"] == 2
    assert payload["path0"]["input"]["source"] == f"bundle:{output.name}"
    assert payload["path0"]["input"]["nodeCount"] == 2
    assert payload["path0"]["input"]["styleOps"]["present"] is True
    assert payload["path0"]["render"]["layoutBoxes"] == 2

def test_bundle_style_ops_contract_fixture_matches_generated_bundle_contract(
    tmp_path,
    monkeypatch,
    capsys,
):
    output = _build_style_ops_bundle(tmp_path, monkeypatch, capsys)
    actual = tmp_path / "actual-bundle-style-ops-contract.json"

    contract_result = main(
        [
            "--style-ops-contract-json",
            "--bundle",
            str(output),
            "--contract-out",
            str(actual),
        ]
    )
    capsys.readouterr()
    compare_result = otoe_cli_main(
        [
            "compare-contract",
            str(BUNDLE_STYLE_OPS_CONTRACT_FIXTURE),
            str(actual),
            "--json",
        ]
    )

    captured = capsys.readouterr()
    comparison = json.loads(captured.out)
    assert contract_result == 0
    assert compare_result == 0
    assert comparison["matched"] is True
    assert comparison["differenceCount"] == 0
    assert comparison["differences"] == []

def test_backend_candidate_skeleton_bundle_replay_rejects_tampered_bundle(
    tmp_path,
    monkeypatch,
    capsys,
):
    output = _build_style_ops_bundle(tmp_path, monkeypatch, capsys)
    copied_app = output / "app" / "bundle_style_ops_app.py"
    copied_app.write_text(
        copied_app.read_text(encoding="utf-8").replace(
            "Bundled StyleOps",
            "Mangled StyleOps",
        ),
        encoding="utf-8",
    )

    result = main(["--style-ops-contract-json", "--bundle", str(output)])

    captured = capsys.readouterr()
    assert result == 1
    assert "style-ops-contract: Bundle verification failed:" in captured.err
    assert "sha256 mismatch" in captured.err

def test_backend_candidate_skeleton_render_tree_rejects_tampered_bundle(
    tmp_path,
    monkeypatch,
    capsys,
):
    output = _build_style_ops_bundle(tmp_path, monkeypatch, capsys)
    copied_app = output / "app" / "bundle_style_ops_app.py"
    copied_app.write_text(
        copied_app.read_text(encoding="utf-8").replace(
            "Bundled StyleOps",
            "Mangled RenderTree",
        ),
        encoding="utf-8",
    )

    result = main(["--render-tree-contract-json", "--bundle", str(output)])

    captured = capsys.readouterr()
    assert result == 1
    assert "render-tree-contract: Bundle verification failed:" in captured.err
    assert "sha256 mismatch" in captured.err or "expected size" in captured.err

def test_backend_candidate_skeleton_rejects_ambiguous_style_sources(
    tmp_path,
    capsys,
):
    artifact = tmp_path / "otoe-styles.json"
    bundle = tmp_path / "bundle"
    artifact.write_text("{}", encoding="utf-8")
    bundle.mkdir()

    with pytest.raises(SystemExit) as exc:
        main(
            [
                "--style-ops-contract-json",
                "--style-artifact",
                str(artifact),
                "--bundle",
                str(bundle),
            ]
        )

    captured = capsys.readouterr()
    assert exc.value.code == 2
    assert "--style-artifact and --bundle are mutually exclusive" in captured.err

    with pytest.raises(SystemExit) as render_tree_exc:
        main(
            [
                "--render-tree-contract-json",
                "--style-artifact",
                str(artifact),
                "--bundle",
                str(bundle),
            ]
        )

    render_tree_captured = capsys.readouterr()
    assert render_tree_exc.value.code == 2
    assert "--style-artifact and --bundle are mutually exclusive" in render_tree_captured.err
