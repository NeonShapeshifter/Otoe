from dataclasses import replace
import json
from pathlib import Path


import examples.native.backend_candidate_contracts as backend_candidate_contracts
import examples.native.backend_candidate_renderer as backend_candidate_renderer
from examples.native.backend_candidate_skeleton import (
    Path0RenderTreeEvidenceReport,
    Path0RendererCandidate,
    RenderTreeCandidateAcceptanceReport,
    backend_candidate_style_artifact,
    main,
    path0_render_tree_evidence_report_to_dict,
    render_tree_contract_report_to_dict,
    run_path0_render_tree_artifact_evidence,
    run_path0_render_tree_evidence,
    run_render_tree_candidate_acceptance,
)
from otoe import (
    RenderNode,
    RenderTree,
    render_tree_to_dict,
)
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

def test_path0_render_tree_evidence_consumes_render_tree_without_mounting(
    monkeypatch,
    tmp_path,
):
    artifact = backend_candidate_style_artifact()
    render_tree = run_render_tree_candidate_acceptance(artifact).minimal

    def fail_render_tree_from_target(*args, **kwargs):
        raise AssertionError("Path0 evidence must consume RenderTree directly.")

    monkeypatch.setattr(
        backend_candidate_renderer,
        "render_tree_from_target",
        fail_render_tree_from_target,
    )
    output = tmp_path / "path0-render-tree-evidence.png"

    report = run_path0_render_tree_evidence(
        render_tree,
        style_artifact=artifact,
        source="contract:minimal",
        output_path=output,
    )
    payload = path0_render_tree_evidence_report_to_dict(report)

    assert isinstance(report, Path0RenderTreeEvidenceReport)
    assert report.passed is True
    assert report.renderer_backend == "path0-renderer-candidate"
    assert report.node_count == 15
    assert report.styled_nodes > 0
    assert report.layout_boxes == 15
    assert report.paint_commands > 0
    assert report.style_ops_present is True
    assert report.style_ops_schema_version == 1
    assert report.style_ops_format == "otoe-style-ops"
    assert payload["format"] == "path0-render-tree-evidence"
    assert payload["passed"] is True
    assert payload["input"]["source"] == "contract:minimal"
    assert payload["input"]["renderTreeHash"].startswith("sha256:")
    assert payload["input"]["renderTreeHash"] == report.render_tree_hash
    assert payload["input"]["styleOps"] == {
        "present": True,
        "schemaVersion": 1,
        "format": "otoe-style-ops",
        "matchesRenderTree": True,
    }
    assert payload["output"]["layout"]["format"] == "path0-layout-output"
    assert payload["output"]["layout"]["boxCount"] == report.layout_boxes
    assert payload["output"]["layout"]["outputHash"].startswith("sha256:")
    assert payload["output"]["layout"]["boxes"][0]["name"] == "ShortcutScope"
    assert payload["output"]["paint"]["format"] == "path0-paint-output"
    assert payload["output"]["paint"]["commandCount"] == report.paint_commands
    assert payload["output"]["paint"]["outputHash"].startswith("sha256:")
    assert payload["output"]["paint"]["commands"][0]["kind"] == "rect"
    assert payload["semanticValidation"] == {
        "passed": True,
        "errors": [],
    }
    assert _call_signature(payload["calls"]) == [
        ("layout", "contract:minimal", report.layout_boxes, 0),
        (
            "paint",
            "ShortcutScope",
            report.layout_boxes,
            report.paint_commands,
        ),
        (
            "write_png",
            output.name,
            0,
            report.paint_commands,
        ),
    ]
    assert payload["render"]["pngPath"] == output.name
    assert set(payload["evidence"]["layout"]["styleProperties"]) >= {
        "gap",
        "padding",
        "width",
    }
    width_observation = _style_observation(payload["evidence"], "layout", "width")
    assert width_observation["count"] > 0
    assert width_observation["samples"][0]["bounds"][2] > 0
    assert set(payload["evidence"]["paint"]["styleProperties"]) >= {
        "background",
        "borderColor",
        "color",
    }
    background_observation = _style_observation(
        payload["evidence"],
        "paint",
        "background",
    )
    assert background_observation["samples"][0]["commandCount"] > 0
    assert background_observation["samples"][0]["commands"][0]["fill"].startswith("#")
    assert payload["evidence"]["raster"]["pngWritten"] is True
    assert payload["evidence"]["raster"]["pngPath"] == output.name
    assert payload["evidence"]["raster"]["sha256"].startswith("sha256:")
    assert payload["evidence"]["raster"]["byteSize"] > 0
    assert output.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    border_observation = _style_observation(
        payload["evidence"],
        "paint",
        "borderColor",
    )
    border_sample = border_observation["samples"][0]
    assert border_sample["commands"][0]["stroke"] == border_sample["value"]["value"]
    min_height_observation = _style_observation(
        payload["evidence"],
        "layout",
        "minHeight",
    )
    min_height_sample = min_height_observation["samples"][0]
    assert min_height_sample["bounds"][3] >= min_height_sample["value"]["value"]


def test_path0_render_tree_evidence_uses_render_tree_backend_boundary(tmp_path):
    artifact = backend_candidate_style_artifact()
    render_tree = run_render_tree_candidate_acceptance(artifact).minimal

    class BoundaryOnlyPath0Backend(Path0RendererCandidate):
        name = "boundary-only-path0"

        def __init__(self):
            super().__init__()
            self.render_tree_inputs = []

        def layout(self, *args, **kwargs):
            raise AssertionError("Path0 evidence must not use component layout.")

        def layout_render_tree(self, render_tree, *, source="render-tree"):
            self.render_tree_inputs.append((render_tree, source))
            return super().layout_render_tree(render_tree, source=source)

    renderer = BoundaryOnlyPath0Backend()
    output = tmp_path / "boundary-path0.png"

    report = run_path0_render_tree_evidence(
        render_tree,
        renderer_backend=renderer,
        style_artifact=artifact,
        source="contract:minimal",
        output_path=output,
    )

    assert report.passed is True
    assert report.renderer_backend == "boundary-only-path0"
    assert renderer.render_tree_inputs == [(render_tree, "contract:minimal")]
    assert _call_signature(path0_render_tree_evidence_report_to_dict(report)["calls"])[
        0
    ] == ("layout", "contract:minimal", report.layout_boxes, 0)
    assert output.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")


def test_path0_render_tree_evidence_rejects_style_ops_render_tree_drift():
    artifact = backend_candidate_style_artifact()
    render_tree = run_render_tree_candidate_acceptance(artifact).minimal
    broken_root, replaced = _replace_first_styled_node(render_tree.root)
    broken_tree = RenderTree(root=broken_root)

    assert replaced is True
    report = run_path0_render_tree_evidence(
        broken_tree,
        style_artifact=artifact,
        source="contract:drift",
    )
    payload = path0_render_tree_evidence_report_to_dict(report)

    assert report.passed is False
    assert report.style_ops_present is True
    assert report.style_ops_matches_render_tree is False
    assert payload["input"]["styleOps"]["matchesRenderTree"] is False
    assert report.errors
    assert "style does not match styleOps artifact" in report.errors[0]


def test_path0_render_tree_artifact_evidence_loads_json_without_mounting(
    monkeypatch,
    tmp_path,
):
    artifact = backend_candidate_style_artifact()
    render_tree = run_render_tree_candidate_acceptance(artifact).minimal
    render_tree_artifact = tmp_path / "render-tree.json"
    render_tree_artifact.write_text(
        json.dumps(render_tree_to_dict(render_tree), indent=2, sort_keys=True),
        encoding="utf-8",
    )

    def fail_render_tree_from_target(*args, **kwargs):
        raise AssertionError("Path0 artifact evidence must not mount Otoe targets.")

    monkeypatch.setattr(
        backend_candidate_renderer,
        "render_tree_from_target",
        fail_render_tree_from_target,
    )
    output = tmp_path / "path0-render-tree-artifact.png"

    report = run_path0_render_tree_artifact_evidence(
        render_tree_artifact,
        style_artifact=artifact,
        output_path=output,
    )

    assert isinstance(report, Path0RenderTreeEvidenceReport)
    assert report.passed is True
    assert report.source == f"render-tree-artifact:{render_tree_artifact.name}"
    assert report.node_count == render_tree.node_count
    assert report.layout_boxes == render_tree.node_count
    assert report.paint_commands > 0
    assert output.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")

def test_path0_render_tree_evidence_rejects_invalid_render_tree_without_layout():
    tree = RenderTree(
        root=RenderNode(
            node_id="root",
            path=(),
            name="VStack",
            widget_id=None,
            key=None,
            class_name=None,
            props=(),
            events=(),
            state=(),
            context="VStack",
            style=(),
            children=(
                RenderNode(
                    node_id="root",
                    path=(0,),
                    name="Text",
                    widget_id=None,
                    key=None,
                    class_name=None,
                    props=(("content", "Broken"),),
                    events=(),
                    state=(),
                    context="Text",
                    style=(),
                    children=(),
                ),
            ),
        )
    )

    report = run_path0_render_tree_evidence(tree)

    assert report.passed is False
    assert report.errors == ("RenderTree node id 'root' is duplicated",)
    assert report.layout_boxes == 0
    assert report.paint_commands == 0
    assert report.calls == ()

def test_render_tree_candidate_acceptance_covers_core_tree_shapes():
    report = run_render_tree_candidate_acceptance()
    payload = render_tree_contract_report_to_dict(report)

    assert isinstance(report, RenderTreeCandidateAcceptanceReport)
    assert report.passed is True
    assert payload["schemaVersion"] == 1
    assert payload["format"] == "render-tree-contract"
    assert payload["passed"] is True
    assert payload["summary"]["minimalNodes"] == 15
    assert payload["summary"]["taskBoardNodes"] == 31
    assert payload["summary"]["stableKeyIds"] is True
    assert payload["summary"]["showBranchChanged"] is True
    assert payload["stableKeyIds"] == {"Alpha": True, "Beta": True}
    assert payload["runs"]["minimal"]["root"]["name"] == "ShortcutScope"
    assert payload["runs"]["taskBoard"]["root"]["name"] == "ShortcutScope"
    assert "Capability Panel" in payload["visibleText"]["minimal"]
    assert "Native Task Board" in payload["visibleText"]["taskBoard"]
    assert payload["visibleText"]["showBefore"] == ["Fallback"]
    assert payload["visibleText"]["showAfter"] == ["Visible"]
    assert (
        payload["runs"]["keyedReorder"]["before"]["root"]["children"][0]["children"][0]["id"]
        == payload["runs"]["keyedReorder"]["after"]["root"]["children"][0]["children"][1]["id"]
    )

def test_render_tree_candidate_acceptance_uses_json_boundary(monkeypatch):
    calls = []
    original = backend_candidate_contracts.render_tree_from_dict

    def recording_render_tree_from_dict(payload):
        calls.append(payload["root"]["id"])
        return original(payload)

    monkeypatch.setattr(
        backend_candidate_contracts,
        "render_tree_from_dict",
        recording_render_tree_from_dict,
    )

    report = run_render_tree_candidate_acceptance()

    assert report.passed is True
    assert len(calls) == 6
    assert all(isinstance(node_id, str) and node_id for node_id in calls)

def test_backend_candidate_skeleton_main_outputs_render_tree_contract_json(capsys):
    result = main(["--render-tree-contract-json"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert result == 0
    assert payload["schemaVersion"] == 1
    assert payload["format"] == "render-tree-contract"
    assert payload["passed"] is True
    assert payload["summary"]["stableKeyIds"] is True
    assert payload["visibleText"]["showBefore"] == ["Fallback"]

def test_backend_candidate_skeleton_main_outputs_path0_render_tree_evidence_json(
    tmp_path,
    capsys,
):
    output = tmp_path / "path0-evidence.png"

    result = main(
        [
            "--path0-render-tree-evidence-json",
            "--path0-render-tree-png",
            str(output),
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert result == 0
    assert payload["schemaVersion"] == 1
    assert payload["format"] == "path0-render-tree-evidence"
    assert payload["passed"] is True
    assert payload["rendererBackend"] == "path0-renderer-candidate"
    assert payload["input"]["source"] == "contract:minimal"
    assert payload["input"]["renderTreeHash"].startswith("sha256:")
    assert payload["input"]["styleOps"] == {
        "present": True,
        "schemaVersion": 1,
        "format": "otoe-style-ops",
        "matchesRenderTree": True,
    }
    assert payload["render"]["layoutBoxes"] == 15
    assert payload["render"]["paintCommands"] > 0
    assert payload["render"]["pngPath"] == output.name
    assert payload["semanticValidation"] == {
        "passed": True,
        "errors": [],
    }
    assert payload["output"]["layout"]["boxCount"] == payload["render"]["layoutBoxes"]
    assert payload["output"]["paint"]["commandCount"] == payload["render"][
        "paintCommands"
    ]
    assert "width" in payload["evidence"]["layout"]["styleProperties"]
    assert "background" in payload["evidence"]["paint"]["styleProperties"]
    assert _style_observation(payload["evidence"], "layout", "width")["samples"]
    assert _style_observation(payload["evidence"], "paint", "background")[
        "samples"
    ][0]["commandCount"] > 0
    assert payload["evidence"]["raster"]["sha256"].startswith("sha256:")
    assert payload["evidence"]["raster"]["byteSize"] > 0
    assert output.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")

def test_backend_candidate_skeleton_loads_render_tree_contract_artifact(
    tmp_path,
    capsys,
):
    render_tree_artifact = tmp_path / "render-tree.json"
    contract = tmp_path / "render-tree-contract.json"
    source_tree = run_render_tree_candidate_acceptance(
        backend_candidate_style_artifact()
    ).minimal
    _write_render_tree_artifact(render_tree_artifact, source_tree)

    result = main(
        [
            "--render-tree-contract-json",
            "--render-tree-artifact",
            str(render_tree_artifact),
            "--contract-out",
            str(contract),
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(contract.read_text(encoding="utf-8"))
    assert result == 0
    assert captured.out == f"contract artifact: {contract}\n"
    assert payload["passed"] is True
    assert payload["artifactSource"] == f"render-tree-artifact:{render_tree_artifact.name}"
    assert payload["summary"]["artifactTargetNodes"] == source_tree.node_count
    assert payload["runs"]["artifactTarget"] == render_tree_to_dict(source_tree)

def test_backend_candidate_skeleton_path0_loads_render_tree_artifact(
    tmp_path,
    capsys,
):
    render_tree_artifact = tmp_path / "render-tree.json"
    output = tmp_path / "path0-artifact-evidence.png"
    source_tree = run_render_tree_candidate_acceptance(
        backend_candidate_style_artifact()
    ).minimal
    _write_render_tree_artifact(render_tree_artifact, source_tree)

    result = main(
        [
            "--path0-render-tree-evidence-json",
            "--render-tree-artifact",
            str(render_tree_artifact),
            "--path0-render-tree-png",
            str(output),
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert result == 0
    assert payload["passed"] is True
    assert payload["input"]["source"] == f"render-tree-artifact:{render_tree_artifact.name}"
    assert payload["input"]["renderTreeHash"].startswith("sha256:")
    assert payload["input"]["nodeCount"] == source_tree.node_count
    assert payload["render"]["layoutBoxes"] == source_tree.node_count
    assert payload["render"]["pngPath"] == output.name
    assert output.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")

def test_backend_readiness_uses_render_tree_artifact_for_path0(
    tmp_path,
    capsys,
):
    render_tree_artifact = tmp_path / "render-tree.json"
    contract = tmp_path / "readiness-from-render-tree-artifact.json"
    source_tree = run_render_tree_candidate_acceptance(
        backend_candidate_style_artifact()
    ).minimal
    _write_render_tree_artifact(render_tree_artifact, source_tree)

    result = main(
        [
            "--backend-readiness-json",
            "--render-tree-artifact",
            str(render_tree_artifact),
            "--contract-out",
            str(contract),
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(contract.read_text(encoding="utf-8"))
    assert result == 0
    assert captured.out == f"contract artifact: {contract}\n"
    assert payload["passed"] is True
    assert payload["renderTree"]["summary"]["artifactTargetNodes"] == (
        source_tree.node_count
    )
    assert payload["path0"]["input"]["source"] == (
        f"render-tree-artifact:{render_tree_artifact.name}"
    )
    assert payload["path0"]["input"]["renderTreeHash"].startswith("sha256:")
    assert payload["path0"]["input"]["nodeCount"] == source_tree.node_count
    assert payload["path0"]["render"]["layoutBoxes"] == source_tree.node_count
    assert payload["gates"]["path0RenderTreeEvidence"] is True

def test_render_tree_contract_fixture_matches_generated_contract(tmp_path, capsys):
    actual = tmp_path / "actual-render-tree-contract.json"
    payload = render_tree_contract_report_to_dict(
        run_render_tree_candidate_acceptance()
    )
    actual.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")

    result = otoe_cli_main(
        [
            "compare-contract",
            str(RENDER_TREE_CONTRACT_FIXTURE),
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

def _write_render_tree_artifact(path, tree):
    path.write_text(
        json.dumps(render_tree_to_dict(tree), indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _replace_first_styled_node(node):
    if node.style:
        property_name, _value = node.style[0]
        return (
            replace(
                node,
                style=((property_name, "__style_ops_drift__"), *node.style[1:]),
            ),
            True,
        )
    children = []
    replaced = False
    for child in node.children:
        if replaced:
            children.append(child)
            continue
        next_child, replaced = _replace_first_styled_node(child)
        children.append(next_child)
    return (
        replace(
            node,
            children=tuple(children),
        ),
        replaced,
    )


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

def _style_observation(evidence, phase, property_name):
    for observation in evidence[phase]["observations"]:
        if observation["property"] == property_name:
            return observation
    raise AssertionError(f"missing {phase} observation for {property_name!r}")
