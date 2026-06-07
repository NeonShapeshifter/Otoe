from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import re

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
    RendererCandidateCall,
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
from otoe.backend_coverage import (
    backend_coverage_report_to_dict as core_backend_coverage_report_to_dict,
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
STRICT_SHA256 = re.compile(r"^sha256:[0-9a-f]{64}$")

def test_backend_readiness_report_combines_renderer_and_style_audits():
    payload = backend_readiness_report_to_dict()

    assert payload["schemaVersion"] == 1
    assert payload["format"] == "backend-readiness-report"
    assert payload["passed"] is True
    assert payload["readiness"] == "ready-for-candidate-comparison"
    assert payload["candidateScope"] == {
        "level": "path0-render-tree-ir-v0",
        "rendererReplay": "internal-native-replay",
        "path0Evidence": "render-tree-ir-v0-fixture",
        "styleRuntime": "styleOps-resolved",
        "windowAdapterBoundary": "NativeWindowDriver",
        "externalBackendAbiStable": False,
        "productionBackend": False,
    }
    assert payload["gates"] == {
        "rendererReplay": True,
        "styleOpsReplay": True,
        "renderTreeReplay": True,
        "path0RenderTreeEvidence": True,
        "widgetInputAudit": True,
        "styleCapabilityAudit": True,
    }
    assert payload["blockers"] == []
    assert payload["candidate"] == {
        "backend": "native-python",
        "rendererBackend": "recording-renderer-candidate",
        "path0RendererBackend": "path0-renderer-candidate",
    }
    assert payload["renderer"]["backend"] == "recording-renderer-candidate"
    assert payload["renderer"]["capabilityAudit"]["summary"] == {
        "widgetInstances": 46,
        "widgetTypes": 11,
        "inputBindings": 24,
        "inputCapabilities": 8,
        "unsupportedWidgets": 0,
        "unsupportedInputs": 0,
    }
    assert payload["styleOps"]["backend"] == "native-python"
    assert payload["styleOps"]["capabilityAudit"]["summary"] == {
        "applied": 36,
        "omitted": 5,
        "unsupported": 0,
    }
    assert payload["renderTree"]["summary"] == {
        "minimalNodes": 15,
        "taskBoardNodes": 31,
        "keyedBeforeNodes": 6,
        "keyedAfterNodes": 6,
        "showBeforeNodes": 3,
        "showAfterNodes": 3,
        "artifactTargetNodes": 0,
        "stableKeyIds": True,
        "showBranchChanged": True,
    }
    assert payload["renderTree"]["stableKeyIds"] == {"Alpha": True, "Beta": True}
    assert payload["path0"]["rendererBackend"] == "path0-renderer-candidate"
    assert payload["path0"]["input"]["source"] == "contract:minimal"
    assert payload["path0"]["input"]["renderTreeHash"].startswith("sha256:")
    assert payload["path0"]["input"]["styleOps"] == {
        "present": True,
        "schemaVersion": 1,
        "format": "otoe-style-ops",
        "matchesRenderTree": True,
    }
    assert payload["path0"]["render"] == {
        "layoutBoxes": 15,
        "paintCommands": 18,
        "pngPath": None,
    }
    assert payload["path0"]["semanticValidation"] == {
        "passed": True,
        "errors": [],
    }
    assert payload["path0"]["output"]["layout"]["format"] == "path0-layout-output"
    assert payload["path0"]["output"]["layout"]["boxCount"] == 15
    assert payload["path0"]["output"]["paint"]["format"] == "path0-paint-output"
    assert payload["path0"]["output"]["paint"]["commandCount"] == 18
    assert payload["evidence"]["path0"]["layoutOutputHash"] == payload["path0"][
        "output"
    ]["layout"]["outputHash"]
    assert payload["evidence"]["path0"]["paintOutputHash"] == payload["path0"][
        "output"
    ]["paint"]["outputHash"]
    assert payload["path0"]["calls"]["count"] == 2
    assert payload["evidence"]["widgets"][0]["source"] == "rendererReplay"
    assert payload["evidence"]["inputs"][0]["gate"] == "rendererReplay"
    assert payload["evidence"]["rendererBoundaries"] == [
        {
            "kind": "rendererBoundary",
            "source": "path0RenderTreeEvidence",
            "gate": "path0RenderTreeEvidence",
            "boundaries": [
                {
                    "boundary": "renderTreeLayout",
                    "count": 1,
                    "proof": {
                        "phase": "layout",
                        "boundary": "renderTree",
                        "source": "contract:minimal",
                        "renderTreeHash": payload["path0"]["input"][
                            "renderTreeHash"
                        ],
                        "layoutBoxes": 15,
                        "outputHash": payload["path0"]["output"]["layout"][
                            "outputHash"
                        ],
                    },
                },
                {
                    "boundary": "paint",
                    "count": 1,
                    "proof": {
                        "phase": "paint",
                        "source": "contract:minimal",
                        "paintCommands": 18,
                        "outputHash": payload["path0"]["output"]["paint"][
                            "outputHash"
                        ],
                    },
                },
            ],
        }
    ]
    assert payload["evidence"]["styles"][0]["source"] == (
        "styleOpsReplay+path0RenderTreeEvidence"
    )
    style_runtime = payload["evidence"]["styles"][0]["runtime"]
    assert style_runtime == {
        "source": "contract:minimal",
        "rendererBackend": "path0-renderer-candidate",
        "styleOpsPresent": True,
        "styleOpsMatchesRenderTree": True,
        "styledNodes": 12,
        "layoutBoxes": 15,
        "paintCommands": 18,
        "layoutEvidence": style_runtime["layoutEvidence"],
        "paintEvidence": style_runtime["paintEvidence"],
        "rasterEvidence": payload["path0"]["evidence"]["raster"],
    }
    assert style_runtime["layoutEvidence"]["layoutBoxes"] == 15
    assert style_runtime["layoutEvidence"]["observationCount"] == len(
        payload["path0"]["evidence"]["layout"]["observations"]
    )
    assert style_runtime["layoutEvidence"]["observationHash"].startswith("sha256:")
    assert set(style_runtime["layoutEvidence"]["observedProperties"]) == set(
        style_runtime["layoutEvidence"]["styleProperties"]
    )
    assert style_runtime["paintEvidence"]["paintCommands"] == 18
    assert style_runtime["paintEvidence"]["observationCount"] == len(
        payload["path0"]["evidence"]["paint"]["observations"]
    )
    assert style_runtime["paintEvidence"]["observationHash"].startswith("sha256:")
    assert set(style_runtime["paintEvidence"]["observedProperties"]) == set(
        style_runtime["paintEvidence"]["styleProperties"]
    )
    assert payload["evidence"]["declaredStyleOmissions"][0]["gate"] == (
        "styleOpsReplay+path0RenderTreeEvidence"
    )
    path0_evidence = payload["evidence"]["path0"]
    assert path0_evidence == {
        "source": "contract:minimal",
        "gate": "path0RenderTreeEvidence",
        "rendererBackend": "path0-renderer-candidate",
        "nodeCount": 15,
        "styledNodes": 12,
        "styleOpsPresent": True,
        "styleOpsMatchesRenderTree": True,
        "renderTreeHash": payload["path0"]["input"]["renderTreeHash"],
        "renderTreeBoundary": {
            "phase": "layout",
            "boundary": "renderTree",
            "source": "contract:minimal",
            "renderTreeHash": payload["path0"]["input"]["renderTreeHash"],
            "layoutBoxes": 15,
            "outputHash": payload["path0"]["output"]["layout"]["outputHash"],
        },
        "layoutBoxes": 15,
        "paintCommands": 18,
        "layoutEvidence": path0_evidence["layoutEvidence"],
        "paintEvidence": path0_evidence["paintEvidence"],
        "layoutOutputHash": payload["path0"]["output"]["layout"]["outputHash"],
        "paintOutputHash": payload["path0"]["output"]["paint"]["outputHash"],
        "rasterEvidence": payload["path0"]["evidence"]["raster"],
        "phases": ["layout", "paint"],
    }
    assert path0_evidence["layoutEvidence"] == style_runtime["layoutEvidence"]
    assert path0_evidence["paintEvidence"] == style_runtime["paintEvidence"]
    assert set(payload["path0"]["evidence"]["layout"]["styleProperties"]) >= {
        "gap",
        "padding",
        "width",
    }
    align_items_observation = _style_observation(
        payload["path0"]["evidence"],
        "layout",
        "alignItems",
    )
    assert align_items_observation["samples"][0]["children"]
    assert set(payload["path0"]["evidence"]["paint"]["styleProperties"]) >= {
        "background",
        "borderColor",
        "color",
    }
    paint_background_observation = _style_observation(
        payload["path0"]["evidence"],
        "paint",
        "background",
    )
    assert paint_background_observation["samples"][0]["commands"][0]["fill"] == (
        "#f8fafc"
    )
    assert payload["path0"]["evidence"]["raster"] == {
        "pngWritten": False,
        "pngPath": None,
        "sha256": None,
        "byteSize": 0,
    }
    assert payload["requirements"]["widgets"][0]["support"] == "container"
    assert payload["requirements"]["rendererBoundaries"] == [
        {
            "kind": "rendererBoundary",
            "boundaries": [
                {"boundary": "paint"},
                {"boundary": "renderTreeLayout"},
            ],
        }
    ]
    assert payload["requirements"]["inputs"] == [
        {
            "kind": "input",
            "support": "supported",
            "capabilities": [
                {"capability": "click", "count": 10},
                {"capability": "focus", "count": 7},
                {"capability": "input_text", "count": 3},
                {"capability": "key_down", "count": 4},
                {"capability": "key_input", "count": 1},
                {"capability": "shortcut", "count": 3},
                {"capability": "tab_focus", "count": 1},
                {"capability": "wheel", "count": 3},
            ],
        }
    ]
    assert payload["requirements"]["styles"][0]["support"] == "layout"
    assert payload["requirements"]["declaredStyleOmissions"] == [
        {
            "kind": "omit",
            "status": "html-only",
            "properties": [
                {"property": "borderStyle", "count": 1},
                {"property": "display", "count": 1},
                {"property": "fontWeight", "count": 1},
                {"property": "margin", "count": 1},
                {"property": "opacity", "count": 1},
            ],
        }
    ]


def test_backend_readiness_can_include_external_path0_backend_evidence():
    payload = backend_readiness_report_to_dict(include_external_path0_backend=True)

    assert payload["passed"] is True
    assert payload["gates"]["path0ExternalJsonBackend"] is True
    assert payload["candidate"]["externalPath0Backend"] == (
        "path0-external-json-backend"
    )
    external = payload["path0"]["externalBackend"]
    assert external["format"] == "path0-external-backend-evidence"
    assert external["passed"] is True
    assert external["backend"] == "path0-external-json-backend"
    assert external["source"] == payload["path0"]["input"]["source"]
    assert external["package"]["format"] == "backend-package"
    assert external["package"]["name"] == "path0-external-json-backend"
    assert external["package"]["entrypoint"] == "path0_external_backend.py"
    assert STRICT_SHA256.fullmatch(external["package"]["packageHash"])
    assert external["process"] == {
        "mode": "subprocess",
        "entrypoint": "examples/native/path0_external_backend.py",
        "packageEntrypoint": "path0_external_backend.py",
        "packageHash": external["package"]["packageHash"],
        "exitCode": 0,
    }
    assert external["input"]["renderTreeHash"] == payload["path0"]["input"][
        "renderTreeHash"
    ]
    assert external["input"]["nodeCount"] == payload["path0"]["input"]["nodeCount"]
    assert external["input"]["styleOps"]["present"] is True
    assert external["input"]["styleOps"]["artifactHash"].startswith("sha256:")
    assert external["output"]["layout"]["format"] == "path0-layout-output"
    assert external["output"]["layout"]["boxCount"] == payload["path0"]["input"][
        "nodeCount"
    ]
    assert external["output"]["paint"]["format"] == "path0-paint-output"
    assert external["semanticValidation"] == {"passed": True, "errors": []}
    assert external["errors"] == []

    declaration = json.loads(
        BACKEND_COVERAGE_DECLARATION_FIXTURE.read_text(encoding="utf-8")
    )
    coverage = backend_coverage_report_to_dict(
        declaration,
        readiness_report=payload,
    )

    assert coverage["passed"] is True
    assert coverage["readiness"]["gates"]["path0ExternalJsonBackend"] is True
    assert coverage["trace"]["path0"]["externalBackend"] == {
        "backend": "path0-external-json-backend",
        "packageHash": external["package"]["packageHash"],
        "renderTreeHash": external["input"]["renderTreeHash"],
        "layoutOutputHash": external["output"]["layout"]["outputHash"],
        "paintOutputHash": external["output"]["paint"]["outputHash"],
        "semanticValidation": external["semanticValidation"],
    }


def test_backend_coverage_rejects_tampered_external_path0_output():
    readiness_report = backend_readiness_report_to_dict(
        include_external_path0_backend=True
    )
    declaration = json.loads(
        BACKEND_COVERAGE_DECLARATION_FIXTURE.read_text(encoding="utf-8")
    )
    readiness_report["path0"]["externalBackend"]["output"]["layout"][
        "outputHash"
    ] = "sha256:" + "0" * 64

    payload = backend_coverage_report_to_dict(
        declaration,
        readiness_report=readiness_report,
    )

    assert payload["passed"] is False
    assert "path0ExternalJsonBackend" in payload["blockers"]
    assert {
        "blocker": "path0ExternalJsonBackend",
        "message": (
            "path0.externalBackend.output.layout.outputHash must match payload"
        ),
    } in payload["readiness"]["evidenceErrors"]


def test_backend_coverage_rejects_tampered_external_path0_package():
    readiness_report = backend_readiness_report_to_dict(
        include_external_path0_backend=True
    )
    declaration = json.loads(
        BACKEND_COVERAGE_DECLARATION_FIXTURE.read_text(encoding="utf-8")
    )
    readiness_report["path0"]["externalBackend"]["package"]["packageHash"] = (
        "sha256:" + "0" * 64
    )

    payload = backend_coverage_report_to_dict(
        declaration,
        readiness_report=readiness_report,
    )

    assert payload["passed"] is False
    assert "path0ExternalJsonBackend" in payload["blockers"]
    assert {
        "blocker": "path0ExternalJsonBackend",
        "message": (
            "path0.externalBackend.package: "
            "backend package packageHash must match payload"
        ),
    } in payload["readiness"]["evidenceErrors"]


def test_backend_readiness_report_blocks_on_style_ops_mismatch():
    artifact = deepcopy(backend_candidate_style_artifact())
    shell_ops = next(
        class_payload
        for class_payload in artifact["styleOps"]["classes"]
        if class_payload["className"] == "candidate-shell"
    )
    width_op = next(op for op in shell_ops["ops"] if op["property"] == "width")
    width_op["value"] = {"type": "size", "value": 999, "unit": "px"}
    style_ops_report = run_style_ops_candidate_acceptance(artifact)

    payload = backend_readiness_report_to_dict(style_ops_report=style_ops_report)

    assert payload["passed"] is False
    assert payload["readiness"] == "blocked"
    assert payload["gates"]["rendererReplay"] is True
    assert payload["gates"]["styleOpsReplay"] is False
    assert payload["gates"]["renderTreeReplay"] is True
    assert payload["gates"]["path0RenderTreeEvidence"] is True
    assert payload["blockers"] == ["styleOpsReplay"]
    assert (
        "class 'candidate-shell': styleOps class 'candidate-shell' applied declarations do not match compiled rules"
        in payload["styleOps"]["errors"]
    )

def test_backend_readiness_requires_path0_style_ops_evidence_for_supplied_reports():
    artifact = backend_candidate_style_artifact()

    payload = backend_readiness_report_to_dict(
        renderer_report=run_renderer_candidate_acceptance(),
        style_ops_report=run_style_ops_candidate_acceptance(artifact),
        render_tree_report=run_render_tree_candidate_acceptance(artifact),
    )

    assert payload["passed"] is False
    assert payload["readiness"] == "blocked"
    assert payload["gates"]["path0RenderTreeEvidence"] is False
    assert payload["path0"]["input"]["styleOps"]["present"] is False
    assert payload["path0"]["input"]["styleOps"]["matchesRenderTree"] is False
    assert payload["blockers"] == ["path0RenderTreeEvidence"]
    assert payload["evidence"]["styles"] == []
    assert payload["evidence"]["declaredStyleOmissions"] == []

    declaration = json.loads(
        BACKEND_COVERAGE_DECLARATION_FIXTURE.read_text(encoding="utf-8")
    )
    coverage = backend_coverage_report_to_dict(
        declaration,
        readiness_report=payload,
    )
    assert coverage["blockers"] == [
        "backendReadiness",
        "path0RenderTreeEvidence",
        "rendererBoundariesEvidence",
        "stylesEvidence",
        "declaredStyleOmissionsEvidence",
    ]


def test_backend_readiness_requires_path0_render_tree_boundary_call():
    artifact = backend_candidate_style_artifact()
    render_tree_report = run_render_tree_candidate_acceptance(artifact)
    path0_report = run_path0_render_tree_evidence(
        render_tree_report.minimal,
        style_artifact=artifact,
        source="contract:minimal",
    )
    broken_path0 = replace(
        path0_report,
        calls=tuple(
            RendererCandidateCall(
                phase=call.phase,
                subject=call.subject,
                layout_boxes=call.layout_boxes,
                paint_commands=call.paint_commands,
            )
            for call in path0_report.calls
        ),
    )

    payload = backend_readiness_report_to_dict(
        renderer_report=run_renderer_candidate_acceptance(),
        style_ops_report=run_style_ops_candidate_acceptance(artifact),
        render_tree_report=render_tree_report,
        path0_report=broken_path0,
    )

    assert payload["passed"] is False
    assert payload["readiness"] == "blocked"
    assert payload["gates"]["path0RenderTreeEvidence"] is False
    assert payload["path0"]["calls"]["signature"][0] == {
        "phase": "layout",
        "subject": "contract:minimal",
        "layoutBoxes": 15,
        "paintCommands": 0,
    }
    assert payload["evidence"]["path0"]["renderTreeBoundary"] is None
    assert payload["blockers"] == ["path0RenderTreeEvidence"]


def test_backend_readiness_blocks_when_path0_paint_effect_evidence_is_missing():
    artifact = backend_candidate_style_artifact()
    render_tree_report = run_render_tree_candidate_acceptance(artifact)
    path0_report = run_path0_render_tree_evidence(
        render_tree_report.minimal,
        style_artifact=artifact,
        source="contract:minimal",
    )
    broken_path0 = replace(
        path0_report,
        paint_style_observations=tuple(
            observation
            for observation in path0_report.paint_style_observations
            if observation["property"] != "background"
        ),
    )

    payload = backend_readiness_report_to_dict(
        renderer_report=run_renderer_candidate_acceptance(),
        style_ops_report=run_style_ops_candidate_acceptance(artifact),
        render_tree_report=render_tree_report,
        path0_report=broken_path0,
    )

    assert payload["passed"] is False
    assert payload["readiness"] == "blocked"
    assert payload["gates"]["path0RenderTreeEvidence"] is False
    assert payload["blockers"] == ["path0RenderTreeEvidence"]
    assert payload["evidence"]["styles"] == []

def test_backend_candidate_skeleton_main_outputs_backend_readiness_json(capsys):
    result = main(["--backend-readiness-json"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert result == 0
    assert payload["schemaVersion"] == 1
    assert payload["format"] == "backend-readiness-report"
    assert payload["passed"] is True
    assert payload["requirements"]["widgets"]
    assert payload["requirements"]["styles"]
    assert payload["gates"]["path0RenderTreeEvidence"] is True
    assert payload["path0"]["input"]["styleOps"]["present"] is True


def test_backend_candidate_skeleton_main_outputs_external_path0_readiness_json(
    capsys,
):
    result = main(["--backend-readiness-json", "--external-path0-backend"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert result == 0
    assert payload["passed"] is True
    assert payload["gates"]["path0ExternalJsonBackend"] is True
    assert payload["path0"]["externalBackend"]["backend"] == (
        "path0-external-json-backend"
    )


def test_backend_coverage_report_accepts_full_declaration_fixture():
    declaration = json.loads(
        BACKEND_COVERAGE_DECLARATION_FIXTURE.read_text(encoding="utf-8")
    )

    readiness_report = backend_readiness_report_to_dict()
    payload = backend_coverage_report_to_dict(declaration)

    assert payload["schemaVersion"] == 1
    assert payload["format"] == "backend-coverage-report"
    assert payload["backend"] == "native-python"
    assert payload["passed"] is True
    assert payload["readiness"]["passed"] is True
    assert payload["readiness"]["candidate"]["backend"] == "native-python"
    assert payload["readiness"]["gates"]["path0RenderTreeEvidence"] is True
    assert payload["readiness"]["candidateScope"][
        "externalBackendAbiStable"
    ] is False
    assert payload["trace"] == {
        "candidateScope": {
            "level": readiness_report["candidateScope"]["level"],
        },
        "path0": {
            "renderTreeHash": readiness_report["path0"]["input"][
                "renderTreeHash"
            ],
            "layoutOutputHash": readiness_report["path0"]["output"]["layout"][
                "outputHash"
            ],
            "paintOutputHash": readiness_report["path0"]["output"]["paint"][
                "outputHash"
            ],
            "semanticValidation": readiness_report["path0"]["semanticValidation"],
        },
    }
    assert payload["readiness"]["evidenceBlockers"] == []
    assert payload["readiness"]["strictEvidence"] is True
    assert payload["blockers"] == []
    assert payload["declarationErrors"] == []
    assert payload["coverage"]["rendererBoundaries"]["summary"] == {
        "required": 2,
        "exercised": 2,
        "declared": 2,
        "covered": 2,
        "missing": 0,
        "unevidenced": 0,
        "extra": 0,
        "unproven": 0,
    }
    assert payload["coverage"]["widgets"]["summary"] == {
        "required": 11,
        "exercised": 11,
        "declared": 11,
        "covered": 11,
        "missing": 0,
        "unevidenced": 0,
        "extra": 0,
        "unproven": 0,
    }
    assert payload["coverage"]["widgets"]["evidence"]["unproven"] == []
    assert payload["coverage"]["inputs"]["missing"] == []
    assert payload["coverage"]["inputs"]["evidence"]["unproven"] == []
    render_tree_boundary_source = payload["coverage"]["rendererBoundaries"][
        "evidenceMap"
    ]["renderTreeLayout"]["sources"][0]
    assert render_tree_boundary_source == {
        "groupIndex": 0,
        "source": "path0RenderTreeEvidence",
        "gate": "path0RenderTreeEvidence",
        "kind": "rendererBoundary",
        "count": 1,
        "boundaryProof": {
            "phase": "layout",
            "source": "contract:minimal",
            "boundary": "renderTree",
            "renderTreeHash": readiness_report["path0"]["input"][
                "renderTreeHash"
            ],
            "layoutBoxes": 15,
            "outputHash": readiness_report["path0"]["output"]["layout"][
                "outputHash"
            ],
        },
    }
    paint_boundary_source = payload["coverage"]["rendererBoundaries"][
        "evidenceMap"
    ]["paint"]["sources"][0]
    assert paint_boundary_source["kind"] == "rendererBoundary"
    assert paint_boundary_source["boundaryProof"] == {
        "phase": "paint",
        "source": "contract:minimal",
        "paintCommands": 18,
        "outputHash": readiness_report["path0"]["output"]["paint"]["outputHash"],
    }
    assert payload["coverage"]["styles"]["missing"] == []
    assert payload["coverage"]["styles"]["summary"]["unproven"] == 0
    assert payload["coverage"]["declaredStyleOmissions"]["missing"] == []
    assert payload["coverage"]["declaredStyleOmissions"]["summary"]["unproven"] == 0
    button_evidence = payload["coverage"]["widgets"]["evidenceMap"]["Button"]
    assert button_evidence["required"] is True
    assert button_evidence["declared"] is True
    assert button_evidence["exercised"] is True
    assert button_evidence["covered"] is True
    assert button_evidence["missing"] is False
    assert button_evidence["unevidenced"] is False
    assert button_evidence["unproven"] is False
    button_source = button_evidence["sources"][0]
    assert button_source["source"] == "rendererReplay"
    assert button_source["gate"] == "rendererReplay"
    assert button_source["kind"] == "widget"
    assert button_source["support"] == "control"
    assert button_source["count"] == 9
    assert button_source["capabilityProof"]["source"] == "rendererReplay"
    assert button_source["capabilityProof"]["auditHash"].startswith("sha256:")
    assert button_source["capabilityProof"]["itemCount"] > 0
    assert "Button" in button_source["capabilityProof"]["observedWidgets"]
    border_width_source = payload["coverage"]["styles"]["evidenceMap"][
        "borderWidth"
    ]["sources"][0]
    assert border_width_source["source"] == (
        "styleOpsReplay+path0RenderTreeEvidence"
    )
    assert border_width_source["gate"] == "styleOpsReplay+path0RenderTreeEvidence"
    assert border_width_source["kind"] == "apply"
    assert border_width_source["support"] == "layout+paint"
    assert border_width_source["runtimeProof"]["phases"] == ["layout", "paint"]
    assert border_width_source["runtimeProof"]["layoutObservationHash"].startswith(
        "sha256:"
    )
    assert border_width_source["runtimeProof"]["paintObservationHash"].startswith(
        "sha256:"
    )
    assert "borderWidth" in border_width_source["runtimeProof"][
        "layoutObservedProperties"
    ]
    assert "borderWidth" in border_width_source["runtimeProof"][
        "paintObservedProperties"
    ]
    display_source = payload["coverage"]["declaredStyleOmissions"][
        "evidenceMap"
    ]["display"]["sources"][0]
    assert display_source["kind"] == "omit"
    assert display_source["status"] == "html-only"
    assert display_source["runtimeProof"]["phases"] == ["layout", "paint"]

def test_backend_coverage_report_rejects_readiness_without_path0_evidence():
    declaration = json.loads(
        BACKEND_COVERAGE_DECLARATION_FIXTURE.read_text(encoding="utf-8")
    )
    readiness_report = backend_readiness_report_to_dict()
    readiness_report["gates"].pop("path0RenderTreeEvidence")

    payload = backend_coverage_report_to_dict(
        declaration,
        readiness_report=readiness_report,
    )

    assert payload["passed"] is False
    assert payload["readiness"]["passed"] is True
    assert payload["readiness"]["evidenceBlockers"] == [
        "path0RenderTreeEvidence",
        "rendererBoundariesEvidence",
        "stylesEvidence",
        "declaredStyleOmissionsEvidence",
    ]
    evidence_messages = [
        error["message"]
        for error in payload["readiness"]["evidenceErrors"]
    ]
    assert "gates.path0RenderTreeEvidence must be true" in evidence_messages
    assert (
        "evidence.path0.gate references non-passing gate "
        "'path0RenderTreeEvidence'"
    ) in evidence_messages
    assert (
        "evidence.styles[0].gate references non-passing gate "
        "'path0RenderTreeEvidence'"
    ) in evidence_messages
    assert (
        "evidence.declaredStyleOmissions[0].gate references non-passing gate "
        "'path0RenderTreeEvidence'"
    ) in evidence_messages
    assert payload["blockers"] == [
        "path0RenderTreeEvidence",
        "rendererBoundariesEvidence",
        "stylesEvidence",
        "declaredStyleOmissionsEvidence",
    ]

def test_backend_coverage_rejects_evidence_group_without_source():
    declaration = json.loads(
        BACKEND_COVERAGE_DECLARATION_FIXTURE.read_text(encoding="utf-8")
    )
    readiness_report = backend_readiness_report_to_dict()
    readiness_report["evidence"]["widgets"][0].pop("source")

    payload = backend_coverage_report_to_dict(
        declaration,
        readiness_report=readiness_report,
    )

    assert payload["passed"] is False
    assert payload["readiness"]["evidenceBlockers"] == ["widgetsEvidence"]
    assert payload["readiness"]["evidenceErrors"] == [
        {
            "blocker": "widgetsEvidence",
            "message": (
                "evidence.widgets[0].source must be a non-empty string"
            ),
        }
    ]
    assert payload["coverage"]["widgets"]["exercised"] == [
        "Button",
        "Input",
        "Text",
    ]
    assert payload["coverage"]["widgets"]["summary"]["covered"] == 3
    assert payload["coverage"]["widgets"]["summary"]["unproven"] == 8
    assert payload["coverage"]["widgets"]["evidence"]["unproven"] == [
        "FocusScope",
        "For",
        "HStack",
        "Panel",
        "ScrollView",
        "ShortcutScope",
        "Show",
        "VStack",
    ]
    focus_scope_evidence = payload["coverage"]["widgets"]["evidenceMap"][
        "FocusScope"
    ]
    assert focus_scope_evidence["exercised"] is False
    assert focus_scope_evidence["unproven"] is True
    assert focus_scope_evidence["sources"] == []
    assert payload["blockers"] == ["widgetsEvidence"]


def test_backend_coverage_rejects_widget_missing_proof_observation():
    declaration = json.loads(
        BACKEND_COVERAGE_DECLARATION_FIXTURE.read_text(encoding="utf-8")
    )
    readiness_report = backend_readiness_report_to_dict()
    for group in readiness_report["evidence"]["widgets"]:
        if any(item["name"] == "Button" for item in group["widgets"]):
            group["proof"]["observedWidgets"].remove("Button")
            break

    payload = backend_coverage_report_to_dict(
        declaration,
        readiness_report=readiness_report,
    )

    assert payload["passed"] is False
    assert payload["readiness"]["evidenceBlockers"] == ["widgetsEvidence"]
    evidence_messages = [
        error["message"]
        for error in payload["readiness"]["evidenceErrors"]
    ]
    assert (
        "evidence.widgets[1].proof.observedWidgets must include "
        "'Button' from widgets"
    ) in evidence_messages
    assert "Button" not in payload["coverage"]["widgets"]["exercised"]
    assert "Button" in payload["coverage"]["widgets"]["evidence"]["unproven"]
    assert payload["coverage"]["widgets"]["evidenceMap"]["Button"]["sources"] == []
    assert payload["blockers"] == ["widgetsEvidence"]


def test_backend_coverage_rejects_widget_proof_audit_hash_mismatch():
    declaration = json.loads(
        BACKEND_COVERAGE_DECLARATION_FIXTURE.read_text(encoding="utf-8")
    )
    readiness_report = backend_readiness_report_to_dict()
    for group in readiness_report["evidence"]["widgets"]:
        if any(item["name"] == "Button" for item in group["widgets"]):
            group["proof"]["auditHash"] = "sha256:" + "0" * 64
            break

    payload = backend_coverage_report_to_dict(
        declaration,
        readiness_report=readiness_report,
    )

    assert payload["passed"] is False
    assert payload["readiness"]["evidenceBlockers"] == ["widgetsEvidence"]
    evidence_messages = [
        error["message"]
        for error in payload["readiness"]["evidenceErrors"]
    ]
    assert (
        "evidence.widgets[1].proof.auditHash must match renderer capability audit"
        in evidence_messages
    )
    assert "Button" not in payload["coverage"]["widgets"]["exercised"]
    assert "Button" in payload["coverage"]["widgets"]["evidence"]["unproven"]
    assert payload["coverage"]["widgets"]["evidenceMap"]["Button"]["sources"] == []
    assert payload["blockers"] == ["widgetsEvidence"]


def test_backend_coverage_rejects_input_missing_proof_observation():
    declaration = json.loads(
        BACKEND_COVERAGE_DECLARATION_FIXTURE.read_text(encoding="utf-8")
    )
    readiness_report = backend_readiness_report_to_dict()
    for group in readiness_report["evidence"]["inputs"]:
        if any(item["capability"] == "click" for item in group["capabilities"]):
            group["proof"]["observedCapabilities"].remove("click")
            break

    payload = backend_coverage_report_to_dict(
        declaration,
        readiness_report=readiness_report,
    )

    assert payload["passed"] is False
    assert payload["readiness"]["evidenceBlockers"] == ["inputsEvidence"]
    evidence_messages = [
        error["message"]
        for error in payload["readiness"]["evidenceErrors"]
    ]
    assert (
        "evidence.inputs[0].proof.observedCapabilities must include "
        "'click' from capabilities"
    ) in evidence_messages
    assert "click" not in payload["coverage"]["inputs"]["exercised"]
    assert "click" in payload["coverage"]["inputs"]["evidence"]["unproven"]
    assert payload["coverage"]["inputs"]["evidenceMap"]["click"]["sources"] == []
    assert payload["blockers"] == ["inputsEvidence"]


def test_backend_coverage_rejects_input_proof_extra_observation():
    declaration = json.loads(
        BACKEND_COVERAGE_DECLARATION_FIXTURE.read_text(encoding="utf-8")
    )
    readiness_report = backend_readiness_report_to_dict()
    readiness_report["evidence"]["inputs"][0]["proof"][
        "observedCapabilities"
    ].append("ghost_input")

    payload = backend_coverage_report_to_dict(
        declaration,
        readiness_report=readiness_report,
    )

    assert payload["passed"] is False
    assert payload["readiness"]["evidenceBlockers"] == ["inputsEvidence"]
    evidence_messages = [
        error["message"]
        for error in payload["readiness"]["evidenceErrors"]
    ]
    assert (
        "evidence.inputs[0].proof.observedCapabilities must match renderer capability audit"
        in evidence_messages
    )
    assert payload["coverage"]["inputs"]["exercised"] == []
    assert "click" in payload["coverage"]["inputs"]["evidence"]["unproven"]
    assert payload["coverage"]["inputs"]["evidenceMap"]["click"]["sources"] == []
    assert payload["blockers"] == ["inputsEvidence"]


def test_backend_coverage_rejects_style_evidence_without_runtime_proof():
    declaration = json.loads(
        BACKEND_COVERAGE_DECLARATION_FIXTURE.read_text(encoding="utf-8")
    )
    readiness_report = backend_readiness_report_to_dict()
    readiness_report["evidence"]["styles"][0]["runtime"]["styleOpsPresent"] = False

    payload = backend_coverage_report_to_dict(
        declaration,
        readiness_report=readiness_report,
    )

    assert payload["passed"] is False
    assert payload["readiness"]["evidenceBlockers"] == ["stylesEvidence"]
    evidence_messages = [
        error["message"]
        for error in payload["readiness"]["evidenceErrors"]
    ]
    assert (
        "evidence.styles[0].runtime.styleOpsPresent must be true"
    ) in evidence_messages
    assert payload["coverage"]["styles"]["exercised"] == []
    assert payload["coverage"]["styles"]["summary"]["unproven"] == 17
    assert payload["blockers"] == ["stylesEvidence"]


def test_backend_coverage_rejects_style_missing_layout_phase_property():
    declaration = json.loads(
        BACKEND_COVERAGE_DECLARATION_FIXTURE.read_text(encoding="utf-8")
    )
    readiness_report = backend_readiness_report_to_dict()
    layout_properties = readiness_report["evidence"]["styles"][0]["runtime"][
        "layoutEvidence"
    ]["styleProperties"]
    layout_properties.remove("width")
    observed_layout_properties = readiness_report["evidence"]["styles"][0][
        "runtime"
    ]["layoutEvidence"]["observedProperties"]
    observed_layout_properties.remove("width")

    payload = backend_coverage_report_to_dict(
        declaration,
        readiness_report=readiness_report,
    )

    assert payload["passed"] is False
    assert payload["readiness"]["evidenceBlockers"] == ["stylesEvidence"]
    evidence_messages = [
        error["message"]
        for error in payload["readiness"]["evidenceErrors"]
    ]
    assert (
        "evidence.styles[0].runtime.layoutEvidence.styleProperties must "
        "include 'width' for support 'layout'"
    ) in evidence_messages
    assert "width" not in payload["coverage"]["styles"]["exercised"]
    assert payload["coverage"]["styles"]["evidence"]["unproven"] == ["width"]
    assert payload["coverage"]["styles"]["summary"]["covered"] == 16
    width_evidence = payload["coverage"]["styles"]["evidenceMap"]["width"]
    assert width_evidence["exercised"] is False
    assert width_evidence["unproven"] is True
    assert width_evidence["sources"] == []
    assert payload["blockers"] == ["stylesEvidence"]


def test_backend_coverage_rejects_style_missing_observed_property():
    declaration = json.loads(
        BACKEND_COVERAGE_DECLARATION_FIXTURE.read_text(encoding="utf-8")
    )
    readiness_report = backend_readiness_report_to_dict()
    readiness_report["evidence"]["styles"][0]["runtime"]["layoutEvidence"][
        "observedProperties"
    ].remove("width")

    payload = backend_coverage_report_to_dict(
        declaration,
        readiness_report=readiness_report,
    )

    assert payload["passed"] is False
    assert payload["readiness"]["evidenceBlockers"] == ["stylesEvidence"]
    evidence_messages = [
        error["message"]
        for error in payload["readiness"]["evidenceErrors"]
    ]
    assert (
        "evidence.styles[0].runtime.layoutEvidence.observedProperties must "
        "include 'width' from styleProperties"
    ) in evidence_messages
    assert "width" not in payload["coverage"]["styles"]["exercised"]
    assert payload["coverage"]["styles"]["evidence"]["unproven"] == ["width"]
    assert payload["blockers"] == ["stylesEvidence"]


def test_backend_coverage_rejects_layout_paint_style_missing_paint_phase():
    declaration = json.loads(
        BACKEND_COVERAGE_DECLARATION_FIXTURE.read_text(encoding="utf-8")
    )
    readiness_report = backend_readiness_report_to_dict()
    paint_properties = readiness_report["evidence"]["styles"][1]["runtime"][
        "paintEvidence"
    ]["styleProperties"]
    paint_properties.remove("borderWidth")
    observed_paint_properties = readiness_report["evidence"]["styles"][1][
        "runtime"
    ]["paintEvidence"]["observedProperties"]
    observed_paint_properties.remove("borderWidth")

    payload = backend_coverage_report_to_dict(
        declaration,
        readiness_report=readiness_report,
    )

    assert payload["passed"] is False
    assert payload["readiness"]["evidenceBlockers"] == ["stylesEvidence"]
    evidence_messages = [
        error["message"]
        for error in payload["readiness"]["evidenceErrors"]
    ]
    assert (
        "evidence.styles[1].runtime.paintEvidence.styleProperties must "
        "include 'borderWidth' for support 'layout+paint'"
    ) in evidence_messages
    assert "borderWidth" not in payload["coverage"]["styles"]["exercised"]
    assert payload["coverage"]["styles"]["evidence"]["unproven"] == [
        "borderWidth"
    ]
    assert payload["coverage"]["styles"]["summary"]["covered"] == 16
    assert payload["blockers"] == ["stylesEvidence"]


def test_backend_coverage_rejects_omission_reported_as_applied_runtime_style():
    declaration = json.loads(
        BACKEND_COVERAGE_DECLARATION_FIXTURE.read_text(encoding="utf-8")
    )
    readiness_report = backend_readiness_report_to_dict()
    readiness_report["evidence"]["declaredStyleOmissions"][0]["runtime"][
        "layoutEvidence"
    ]["styleProperties"].append("display")
    readiness_report["evidence"]["declaredStyleOmissions"][0]["runtime"][
        "layoutEvidence"
    ]["observedProperties"].append("display")

    payload = backend_coverage_report_to_dict(
        declaration,
        readiness_report=readiness_report,
    )

    assert payload["passed"] is False
    assert payload["readiness"]["evidenceBlockers"] == [
        "declaredStyleOmissionsEvidence"
    ]
    evidence_messages = [
        error["message"]
        for error in payload["readiness"]["evidenceErrors"]
    ]
    assert (
        "evidence.declaredStyleOmissions[0] omits 'display' but runtime "
        "layoutEvidence.styleProperties includes it"
    ) in evidence_messages
    assert "display" not in payload["coverage"]["declaredStyleOmissions"][
        "exercised"
    ]
    assert payload["coverage"]["declaredStyleOmissions"]["evidence"][
        "unproven"
    ] == ["display"]
    assert payload["coverage"]["declaredStyleOmissions"]["summary"][
        "covered"
    ] == 4
    display_evidence = payload["coverage"]["declaredStyleOmissions"][
        "evidenceMap"
    ]["display"]
    assert display_evidence["exercised"] is False
    assert display_evidence["unproven"] is True
    assert display_evidence["sources"] == []
    assert payload["blockers"] == ["declaredStyleOmissionsEvidence"]


def test_backend_coverage_rejects_renderer_boundary_without_proof():
    declaration = json.loads(
        BACKEND_COVERAGE_DECLARATION_FIXTURE.read_text(encoding="utf-8")
    )
    readiness_report = backend_readiness_report_to_dict()
    readiness_report["evidence"]["rendererBoundaries"][0]["boundaries"][1].pop(
        "proof"
    )

    payload = backend_coverage_report_to_dict(
        declaration,
        readiness_report=readiness_report,
    )

    assert payload["passed"] is False
    assert payload["readiness"]["evidenceBlockers"] == [
        "rendererBoundariesEvidence"
    ]
    evidence_messages = [
        error["message"]
        for error in payload["readiness"]["evidenceErrors"]
    ]
    assert (
        "evidence.rendererBoundaries[0].boundaries[1].proof must be a JSON object"
    ) in evidence_messages
    assert payload["coverage"]["rendererBoundaries"]["exercised"] == [
        "renderTreeLayout"
    ]
    assert payload["coverage"]["rendererBoundaries"]["evidence"]["unproven"] == [
        "paint"
    ]
    assert payload["blockers"] == ["rendererBoundariesEvidence"]


def test_backend_coverage_declaration_fixture_matches_capability_profile():
    declaration = json.loads(
        BACKEND_COVERAGE_DECLARATION_FIXTURE.read_text(encoding="utf-8")
    )

    assert declaration == backend_capability_profile(
        "native-python"
    ).coverage_declaration()

def test_backend_coverage_report_blocks_missing_declared_items():
    declaration = json.loads(
        BACKEND_COVERAGE_DECLARATION_FIXTURE.read_text(encoding="utf-8")
    )
    declaration["covers"]["widgets"].remove("Button")
    declaration["covers"]["styles"].remove("background")

    payload = backend_coverage_report_to_dict(declaration)

    assert payload["passed"] is False
    assert payload["declarationErrors"] == []
    assert payload["blockers"] == ["widgetsCoverage", "stylesCoverage"]
    assert payload["coverage"]["widgets"]["missing"] == ["Button"]
    assert payload["coverage"]["styles"]["missing"] == ["background"]


def test_backend_coverage_rejects_requirements_without_executed_evidence():
    declaration = json.loads(
        BACKEND_COVERAGE_DECLARATION_FIXTURE.read_text(encoding="utf-8")
    )
    readiness_report = backend_readiness_report_to_dict()

    payload = core_backend_coverage_report_to_dict(
        declaration,
        requirements=readiness_report["requirements"],
        readiness_report={"passed": True, "blockers": []},
    )

    assert payload["passed"] is False
    assert payload["readiness"]["passed"] is True
    assert payload["readiness"]["strictEvidence"] is True
    assert payload["readiness"]["evidenceBlockers"] == ["capabilityEvidence"]
    assert payload["readiness"]["evidenceErrors"] == [
        {
            "blocker": "capabilityEvidence",
            "message": (
                "backend coverage requires executed readiness evidence; "
                "requirements alone are not proof"
            ),
        }
    ]
    assert payload["coverage"]["widgets"]["exercised"] == []
    assert payload["coverage"]["widgets"]["summary"]["covered"] == 0
    assert payload["coverage"]["widgets"]["summary"]["unproven"] == 11
    assert payload["coverage"]["styles"]["summary"]["unproven"] == 17
    assert payload["blockers"] == [
        "capabilityEvidence",
        "rendererBoundariesEvidence",
        "widgetsEvidence",
        "inputsEvidence",
        "stylesEvidence",
        "declaredStyleOmissionsEvidence",
    ]


def test_backend_candidate_skeleton_main_outputs_backend_coverage_json(capsys):
    result = main(
        [
            "--backend-coverage-json",
            "--coverage-declaration",
            str(BACKEND_COVERAGE_DECLARATION_FIXTURE),
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert result == 0
    assert payload["schemaVersion"] == 1
    assert payload["format"] == "backend-coverage-report"
    assert payload["passed"] is True
    assert payload["blockers"] == []
    assert payload["coverage"]["widgets"]["covered"]
    assert (
        "--backend-coverage-json is compatibility-only"
        in captured.err
    )

def test_backend_candidate_skeleton_main_outputs_profile_backend_coverage_json(capsys):
    result = main(
        [
            "--backend-coverage-json",
            "--backend-capability",
            "native-python",
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert result == 0
    assert payload["backend"] == "native-python"
    assert payload["passed"] is True
    assert payload["coverage"]["widgets"]["extra"] == []
    assert payload["coverage"]["inputs"]["extra"] == []
    assert (
        "--backend-coverage-json is compatibility-only"
        in captured.err
    )

def test_backend_candidate_skeleton_main_outputs_coverage_declaration_json(capsys):
    result = main(
        [
            "--backend-coverage-declaration-json",
            "--backend-capability",
            "native-python",
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert result == 0
    assert payload == backend_capability_profile(
        "native-python"
    ).coverage_declaration()
    assert (
        "--backend-coverage-declaration-json is compatibility-only"
        in captured.err
    )

def test_backend_candidate_skeleton_main_outputs_custom_profile_declaration(capsys):
    result = main(
        [
            "--backend-coverage-declaration-json",
            "--backend-capability-profile",
            str(BACKEND_CANDIDATE_PARTIAL_PROFILE_FIXTURE),
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert result == 0
    assert payload["backend"] == "partial-backend-candidate"
    assert payload["source"] == {
        "kind": "backendCapabilityProfile",
        "name": "partial-backend-candidate",
    }
    assert "Button" not in payload["covers"]["widgets"]
    assert "background" not in payload["covers"]["styles"]

def test_backend_candidate_skeleton_main_reports_custom_profile_gaps(capsys):
    result = main(
        [
            "--backend-coverage-json",
            "--backend-capability-profile",
            str(BACKEND_CANDIDATE_PARTIAL_PROFILE_FIXTURE),
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert result == 1
    assert payload["backend"] == "partial-backend-candidate"
    assert payload["passed"] is False
    assert payload["blockers"] == [
        "backendIdentity",
        "rendererBoundariesCoverage",
        "widgetsCoverage",
        "inputsCoverage",
        "stylesCoverage",
        "declaredStyleOmissionsCoverage",
    ]
    assert payload["readiness"]["evidenceBlockers"] == ["backendIdentity"]
    assert payload["coverage"]["widgets"]["missing"] == [
        "Button",
        "FocusScope",
        "Panel",
    ]
    assert payload["coverage"]["inputs"]["missing"] == [
        "focus",
        "key_down",
        "key_input",
        "tab_focus",
    ]
    assert payload["coverage"]["styles"]["missing"] == [
        "background",
        "borderColor",
        "borderRadius",
        "borderWidth",
        "color",
        "fontSize",
        "maxHeight",
        "maxWidth",
        "minHeight",
        "minWidth",
    ]

def test_backend_readiness_contract_fixture_matches_generated_report(tmp_path, capsys):
    actual = tmp_path / "actual-backend-readiness.json"
    payload = backend_readiness_report_to_dict()
    actual.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")

    result = otoe_cli_main(
        [
            "compare-contract",
            str(BACKEND_READINESS_CONTRACT_FIXTURE),
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

def _style_observation(evidence, phase, property_name):
    for observation in evidence[phase]["observations"]:
        if observation["property"] == property_name:
            return observation
    raise AssertionError(f"missing {phase} observation for {property_name!r}")
