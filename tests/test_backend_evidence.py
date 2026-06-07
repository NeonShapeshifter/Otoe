import hashlib
import json
from copy import deepcopy

from otoe.backend_evidence import (
    readiness_evidence_blockers,
    readiness_evidence_errors,
)


def test_readiness_evidence_ignores_non_readiness_payload():
    assert readiness_evidence_errors({"format": "backend-coverage-report"}) == []


def test_readiness_evidence_reports_missing_group_source():
    report = _valid_readiness_report()
    report["evidence"]["widgets"][0].pop("source")

    errors = readiness_evidence_errors(report)

    assert errors == [
        {
            "blocker": "widgetsEvidence",
            "message": "evidence.widgets[0].source must be a non-empty string",
        }
    ]
    assert readiness_evidence_blockers(errors) == ["widgetsEvidence"]


def test_readiness_evidence_reports_non_passing_gate_references():
    report = _valid_readiness_report()
    report["gates"]["path0RenderTreeEvidence"] = False

    errors = readiness_evidence_errors(report)
    messages = [error["message"] for error in errors]

    assert readiness_evidence_blockers(errors) == [
        "path0RenderTreeEvidence",
        "rendererBoundariesEvidence",
        "stylesEvidence",
        "declaredStyleOmissionsEvidence",
    ]
    assert "gates.path0RenderTreeEvidence must be true" in messages
    assert (
        "evidence.path0.gate references non-passing gate "
        "'path0RenderTreeEvidence'"
    ) in messages
    assert (
        "evidence.rendererBoundaries[0].gate references non-passing gate "
        "'path0RenderTreeEvidence'"
    ) in messages
    assert (
        "evidence.styles[0].gate references non-passing gate "
        "'path0RenderTreeEvidence'"
    ) in messages


def test_readiness_evidence_rejects_empty_gate_fragments():
    report = _valid_readiness_report()
    report["evidence"]["widgets"][0]["gate"] = "rendererReplay+"

    errors = readiness_evidence_errors(report)

    assert errors == [
        {
            "blocker": "widgetsEvidence",
            "message": (
                "evidence.widgets[0].gate must reference non-empty gate names"
            ),
        }
    ]
    assert readiness_evidence_blockers(errors) == ["widgetsEvidence"]


def test_readiness_evidence_requires_widget_observed_in_proof():
    report = _valid_readiness_report()
    report["evidence"]["widgets"][0]["proof"]["observedWidgets"] = []

    errors = readiness_evidence_errors(report)

    assert errors == [
        {
            "blocker": "widgetsEvidence",
            "message": (
                "evidence.widgets[0].proof.observedWidgets must include "
                "'Text' from widgets"
            ),
        }
    ]
    assert readiness_evidence_blockers(errors) == ["widgetsEvidence"]


def test_readiness_evidence_requires_capability_proof_source_match():
    report = _valid_readiness_report()
    report["evidence"]["inputs"][0]["proof"]["source"] = "otherReplay"

    errors = readiness_evidence_errors(report)

    assert errors == [
        {
            "blocker": "inputsEvidence",
            "message": (
                "evidence.inputs[0].proof.source must match "
                "evidence.inputs[0].source"
            ),
        }
    ]
    assert readiness_evidence_blockers(errors) == ["inputsEvidence"]


def test_readiness_evidence_requires_style_property_phase_proof():
    report = _valid_readiness_report()
    report["evidence"]["styles"][0]["runtime"]["paintEvidence"][
        "styleProperties"
    ].remove("borderWidth")
    report["evidence"]["styles"][0]["runtime"]["paintEvidence"][
        "observedProperties"
    ].remove("borderWidth")

    errors = readiness_evidence_errors(report)

    assert errors == [
        {
            "blocker": "stylesEvidence",
            "message": (
                "evidence.styles[0].runtime.paintEvidence.styleProperties "
                "must include 'borderWidth' for support 'layout+paint'"
            ),
        }
    ]
    assert readiness_evidence_blockers(errors) == ["stylesEvidence"]


def test_readiness_evidence_requires_observed_style_property_proof():
    report = _valid_readiness_report()
    report["evidence"]["styles"][0]["runtime"]["paintEvidence"][
        "observedProperties"
    ].remove("borderWidth")

    errors = readiness_evidence_errors(report)

    assert errors == [
        {
            "blocker": "stylesEvidence",
            "message": (
                "evidence.styles[0].runtime.paintEvidence.observedProperties "
                "must include 'borderWidth' from styleProperties"
            ),
        }
    ]
    assert readiness_evidence_blockers(errors) == ["stylesEvidence"]


def test_readiness_evidence_rejects_runtime_applied_omission():
    report = _valid_readiness_report()
    report["evidence"]["declaredStyleOmissions"][0]["runtime"]["layoutEvidence"][
        "styleProperties"
    ].append("display")
    report["evidence"]["declaredStyleOmissions"][0]["runtime"]["layoutEvidence"][
        "observedProperties"
    ].append("display")

    errors = readiness_evidence_errors(report)

    assert errors == [
        {
            "blocker": "declaredStyleOmissionsEvidence",
            "message": (
                "evidence.declaredStyleOmissions[0] omits 'display' but "
                "runtime layoutEvidence.styleProperties includes it"
            ),
        }
    ]
    assert readiness_evidence_blockers(errors) == [
        "declaredStyleOmissionsEvidence"
    ]


def test_readiness_evidence_requires_path0_render_tree_boundary_proof():
    report = _valid_readiness_report()
    report["evidence"]["path0"].pop("renderTreeBoundary")

    errors = readiness_evidence_errors(report)

    assert errors == [
        {
            "blocker": "path0RenderTreeEvidence",
            "message": (
                "evidence.path0.renderTreeBoundary must be a JSON object"
            ),
        }
    ]
    assert readiness_evidence_blockers(errors) == ["path0RenderTreeEvidence"]


def test_readiness_evidence_rejects_non_render_tree_path0_boundary():
    report = _valid_readiness_report()
    report["evidence"]["path0"]["renderTreeBoundary"]["boundary"] = "mountedTree"

    errors = readiness_evidence_errors(report)

    assert errors == [
        {
            "blocker": "path0RenderTreeEvidence",
            "message": (
                "evidence.path0.renderTreeBoundary.boundary must be 'renderTree'"
            ),
        }
    ]
    assert readiness_evidence_blockers(errors) == ["path0RenderTreeEvidence"]


def test_readiness_evidence_rejects_untraced_path0_boundary_source():
    report = _valid_readiness_report()
    report["evidence"]["path0"]["renderTreeBoundary"]["source"] = "other"

    errors = readiness_evidence_errors(report)

    assert errors == [
        {
            "blocker": "path0RenderTreeEvidence",
            "message": (
                "evidence.path0.renderTreeBoundary.source must match "
                "evidence.path0.source"
            ),
        }
    ]
    assert readiness_evidence_blockers(errors) == ["path0RenderTreeEvidence"]


def test_readiness_evidence_rejects_untraced_path0_boundary_layout_boxes():
    report = _valid_readiness_report()
    report["evidence"]["path0"]["renderTreeBoundary"]["layoutBoxes"] = 2

    errors = readiness_evidence_errors(report)

    assert errors == [
        {
            "blocker": "path0RenderTreeEvidence",
            "message": (
                "evidence.path0.renderTreeBoundary.layoutBoxes must match "
                "evidence.path0.layoutBoxes"
            ),
        }
    ]
    assert readiness_evidence_blockers(errors) == ["path0RenderTreeEvidence"]


def test_readiness_evidence_rejects_untraced_path0_boundary_output_hash():
    report = _valid_readiness_report()
    report["evidence"]["path0"]["renderTreeBoundary"]["outputHash"] = _test_sha(
        "wrong"
    )

    errors = readiness_evidence_errors(report)

    assert errors == [
        {
            "blocker": "path0RenderTreeEvidence",
            "message": (
                "evidence.path0.renderTreeBoundary.outputHash must match "
                "path0.output.layout.outputHash"
            ),
        }
    ]
    assert readiness_evidence_blockers(errors) == ["path0RenderTreeEvidence"]


def test_readiness_evidence_requires_path0_input_render_tree_hash():
    report = _valid_readiness_report()
    report["path0"]["input"].pop("renderTreeHash")

    errors = readiness_evidence_errors(report)

    assert errors == [
        {
            "blocker": "path0RenderTreeEvidence",
            "message": "path0.input.renderTreeHash must be a sha256 string",
        }
    ]
    assert readiness_evidence_blockers(errors) == ["path0RenderTreeEvidence"]


def test_readiness_evidence_rejects_malformed_path0_input_render_tree_hash():
    report = _valid_readiness_report()
    report["path0"]["input"]["renderTreeHash"] = "sha256:" + "a" * 63

    errors = readiness_evidence_errors(report)
    messages = [error["message"] for error in errors]

    assert "path0.input.renderTreeHash must be a sha256 string" in messages
    assert readiness_evidence_blockers(errors) == [
        "path0RenderTreeEvidence",
        "rendererBoundariesEvidence",
    ]


def test_readiness_evidence_rejects_uppercase_runtime_observation_hash():
    report = _valid_readiness_report()
    report["evidence"]["path0"]["layoutEvidence"]["observationHash"] = (
        "sha256:" + "A" * 64
    )

    errors = readiness_evidence_errors(report)

    assert {
        "blocker": "path0RenderTreeEvidence",
        "message": "evidence.path0.layoutEvidence.observationHash must be a sha256 string",
    } in errors
    assert readiness_evidence_blockers(errors) == ["path0RenderTreeEvidence"]


def test_readiness_evidence_rejects_path0_render_tree_hash_mismatch():
    report = _valid_readiness_report()
    report["evidence"]["path0"]["renderTreeHash"] = _test_sha("wrong")
    report["evidence"]["path0"]["renderTreeBoundary"][
        "renderTreeHash"
    ] = _test_sha("wrong")

    errors = readiness_evidence_errors(report)

    assert errors == [
        {
            "blocker": "path0RenderTreeEvidence",
            "message": (
                "evidence.path0.renderTreeHash must match "
                "path0.input.renderTreeHash"
            ),
        }
    ]
    assert readiness_evidence_blockers(errors) == ["path0RenderTreeEvidence"]


def test_readiness_evidence_rejects_untraced_path0_boundary_render_tree_hash():
    report = _valid_readiness_report()
    report["evidence"]["path0"]["renderTreeBoundary"][
        "renderTreeHash"
    ] = _test_sha("wrong")

    errors = readiness_evidence_errors(report)

    assert errors == [
        {
            "blocker": "path0RenderTreeEvidence",
            "message": (
                "evidence.path0.renderTreeBoundary.renderTreeHash must match "
                "path0.input.renderTreeHash"
            ),
        }
    ]
    assert readiness_evidence_blockers(errors) == ["path0RenderTreeEvidence"]


def test_readiness_evidence_requires_path0_output_counts_to_match():
    report = _valid_readiness_report()
    report["path0"]["output"]["layout"]["boxCount"] = 2

    errors = readiness_evidence_errors(report)

    assert errors == [
        {
            "blocker": "path0RenderTreeEvidence",
            "message": (
                "evidence.path0.output.layout.boxCount must match "
                "evidence.path0.layoutBoxes"
            ),
        },
        {
            "blocker": "path0RenderTreeEvidence",
            "message": (
                "evidence.path0.output.layout.boxes length must match "
                "evidence.path0.output.layout.boxCount"
            ),
        },
        {
            "blocker": "path0RenderTreeEvidence",
            "message": "evidence.path0.output.layout.outputHash must match payload",
        },
    ]
    assert readiness_evidence_blockers(errors) == ["path0RenderTreeEvidence"]


def test_readiness_evidence_requires_path0_output_hash_to_match():
    report = _valid_readiness_report()
    report["path0"]["output"]["paint"]["commands"][0]["fill"] = "#000000"

    errors = readiness_evidence_errors(report)

    assert errors == [
        {
            "blocker": "path0RenderTreeEvidence",
            "message": "evidence.path0.output.paint.outputHash must match payload",
        }
    ]
    assert readiness_evidence_blockers(errors) == ["path0RenderTreeEvidence"]


def test_readiness_evidence_rejects_duplicate_layout_output_path():
    report = _valid_readiness_report()
    layout = report["path0"]["output"]["layout"]
    layout["boxes"].append(deepcopy(layout["boxes"][0]))
    layout["boxCount"] = 2
    report["evidence"]["path0"]["layoutBoxes"] = 2
    report["evidence"]["path0"]["renderTreeBoundary"]["layoutBoxes"] = 2
    report["evidence"]["rendererBoundaries"][0]["boundaries"][1]["proof"][
        "layoutBoxes"
    ] = 2
    _refresh_path0_layout_hashes(report)
    report["path0"]["semanticValidation"] = {
        "passed": False,
        "errors": ["evidence.path0.output.layout.boxes[1].path must be unique"],
    }

    errors = readiness_evidence_errors(report)

    assert errors == [
        {
            "blocker": "path0RenderTreeEvidence",
            "message": "evidence.path0.output.layout.boxes[1].path must be unique",
        }
    ]
    assert readiness_evidence_blockers(errors) == ["path0RenderTreeEvidence"]


def test_readiness_evidence_rejects_bad_layout_output_bounds():
    report = _valid_readiness_report()
    report["path0"]["output"]["layout"]["boxes"][0]["bounds"] = [0, 0, -1, 10]
    _refresh_path0_layout_hashes(report)
    message = (
        "evidence.path0.output.layout.boxes[0].bounds must be finite "
        "numbers with non-negative size"
    )
    report["path0"]["semanticValidation"] = {
        "passed": False,
        "errors": [message],
    }

    errors = readiness_evidence_errors(report)

    assert errors == [
        {
            "blocker": "path0RenderTreeEvidence",
            "message": message,
        }
    ]
    assert readiness_evidence_blockers(errors) == ["path0RenderTreeEvidence"]


def test_readiness_evidence_rejects_paint_output_path_without_layout_box():
    report = _valid_readiness_report()
    report["path0"]["output"]["paint"]["commands"][0]["path"] = [99]
    _refresh_path0_paint_hashes(report)
    message = "evidence.path0.output.paint.commands[0].path must reference a layout box"
    report["path0"]["semanticValidation"] = {
        "passed": False,
        "errors": [message],
    }

    errors = readiness_evidence_errors(report)

    assert errors == [
        {
            "blocker": "path0RenderTreeEvidence",
            "message": message,
        }
    ]
    assert readiness_evidence_blockers(errors) == ["path0RenderTreeEvidence"]


def test_readiness_evidence_rejects_stale_path0_semantic_validation():
    report = _valid_readiness_report()
    report["path0"]["output"]["paint"]["commands"][0]["path"] = [99]
    _refresh_path0_paint_hashes(report)

    errors = readiness_evidence_errors(report)

    assert errors == [
        {
            "blocker": "path0RenderTreeEvidence",
            "message": (
                "evidence.path0.output.paint.commands[0].path must reference "
                "a layout box"
            ),
        },
        {
            "blocker": "path0RenderTreeEvidence",
            "message": (
                "path0.semanticValidation.passed must match path0.output "
                "semantic audit"
            ),
        },
        {
            "blocker": "path0RenderTreeEvidence",
            "message": (
                "path0.semanticValidation.errors must match path0.output "
                "semantic audit"
            ),
        },
    ]
    assert readiness_evidence_blockers(errors) == ["path0RenderTreeEvidence"]


def test_readiness_evidence_requires_path0_output_hash_reference_to_match():
    report = _valid_readiness_report()
    report["evidence"]["path0"]["layoutOutputHash"] = _test_sha("wrong")

    errors = readiness_evidence_errors(report)

    assert errors == [
        {
            "blocker": "path0RenderTreeEvidence",
            "message": "evidence.path0.layoutOutputHash must match outputHash",
        }
    ]
    assert readiness_evidence_blockers(errors) == ["path0RenderTreeEvidence"]


def test_readiness_evidence_requires_path0_style_ops_render_tree_match():
    report = _valid_readiness_report()
    report["evidence"]["path0"]["styleOpsMatchesRenderTree"] = False

    errors = readiness_evidence_errors(report)

    assert errors == [
        {
            "blocker": "path0RenderTreeEvidence",
            "message": (
                "evidence.path0.styleOpsMatchesRenderTree must be true"
            ),
        }
    ]
    assert readiness_evidence_blockers(errors) == ["path0RenderTreeEvidence"]


def test_readiness_evidence_requires_runtime_style_ops_render_tree_match():
    report = _valid_readiness_report()
    report["evidence"]["styles"][0]["runtime"][
        "styleOpsMatchesRenderTree"
    ] = False

    errors = readiness_evidence_errors(report)

    assert errors == [
        {
            "blocker": "stylesEvidence",
            "message": (
                "evidence.styles[0].runtime.styleOpsMatchesRenderTree "
                "must be true"
            ),
        }
    ]
    assert readiness_evidence_blockers(errors) == ["stylesEvidence"]


def test_readiness_evidence_requires_renderer_boundary_proof():
    report = _valid_readiness_report()
    report["evidence"]["rendererBoundaries"][0]["boundaries"][0].pop("proof")

    errors = readiness_evidence_errors(report)

    assert errors == [
        {
            "blocker": "rendererBoundariesEvidence",
            "message": (
                "evidence.rendererBoundaries[0].boundaries[0].proof must be "
                "a JSON object"
            ),
        }
    ]
    assert readiness_evidence_blockers(errors) == ["rendererBoundariesEvidence"]


def test_readiness_evidence_rejects_unknown_renderer_boundary():
    report = _valid_readiness_report()
    report["evidence"]["rendererBoundaries"][0]["boundaries"].append(
        {
            "boundary": "raster",
            "count": 1,
            "proof": {
                "phase": "raster",
                "source": "contract:minimal",
            },
        }
    )

    errors = readiness_evidence_errors(report)

    assert errors == [
        {
            "blocker": "rendererBoundariesEvidence",
            "message": (
                "evidence.rendererBoundaries[0].boundaries[2].boundary is "
                "not a supported renderer boundary"
            ),
        }
    ]
    assert readiness_evidence_blockers(errors) == ["rendererBoundariesEvidence"]


def test_readiness_evidence_rejects_untraced_renderer_layout_boundary_hash():
    report = _valid_readiness_report()
    report["evidence"]["rendererBoundaries"][0]["boundaries"][1]["proof"][
        "outputHash"
    ] = _test_sha("wrong")

    errors = readiness_evidence_errors(report)

    assert errors == [
        {
            "blocker": "rendererBoundariesEvidence",
            "message": (
                "evidence.rendererBoundaries[0].boundaries[1].proof.outputHash "
                "must match path0.output.layout.outputHash"
            ),
        }
    ]
    assert readiness_evidence_blockers(errors) == ["rendererBoundariesEvidence"]


def test_readiness_evidence_rejects_untraced_renderer_layout_boundary_render_tree_hash():
    report = _valid_readiness_report()
    report["evidence"]["rendererBoundaries"][0]["boundaries"][1]["proof"][
        "renderTreeHash"
    ] = _test_sha("wrong")

    errors = readiness_evidence_errors(report)

    assert errors == [
        {
            "blocker": "rendererBoundariesEvidence",
            "message": (
                "evidence.rendererBoundaries[0].boundaries[1].proof."
                "renderTreeHash must match path0.input.renderTreeHash"
            ),
        }
    ]
    assert readiness_evidence_blockers(errors) == ["rendererBoundariesEvidence"]


def test_readiness_evidence_rejects_untraced_renderer_paint_boundary_hash():
    report = _valid_readiness_report()
    report["evidence"]["rendererBoundaries"][0]["boundaries"][0]["proof"][
        "outputHash"
    ] = _test_sha("wrong")

    errors = readiness_evidence_errors(report)

    assert errors == [
        {
            "blocker": "rendererBoundariesEvidence",
            "message": (
                "evidence.rendererBoundaries[0].boundaries[0].proof.outputHash "
                "must match path0.output.paint.outputHash"
            ),
        }
    ]
    assert readiness_evidence_blockers(errors) == ["rendererBoundariesEvidence"]


def _valid_readiness_report() -> dict:
    return deepcopy(
        {
            "format": "backend-readiness-report",
            "gates": {
                "rendererReplay": True,
                "styleOpsReplay": True,
                "path0RenderTreeEvidence": True,
            },
            "path0": {
                "input": {
                    "renderTreeHash": _test_sha("render-tree"),
                },
                "output": _valid_path0_output(),
                "semanticValidation": {
                    "passed": True,
                    "errors": [],
                },
            },
            "evidence": {
                "rendererBoundaries": [
                    {
                        "kind": "rendererBoundary",
                        "source": "path0RenderTreeEvidence",
                        "gate": "path0RenderTreeEvidence",
                        "boundaries": [
                            {
                                "boundary": "paint",
                                "count": 1,
                                "proof": {
                                    "phase": "paint",
                                    "source": "contract:minimal",
                                    "paintCommands": 1,
                                    "outputHash": _valid_path0_output()["paint"][
                                        "outputHash"
                                    ],
                                },
                            },
                            {
                                "boundary": "renderTreeLayout",
                                "count": 1,
                                "proof": {
                                    "phase": "layout",
                                    "boundary": "renderTree",
                                    "source": "contract:minimal",
                                    "renderTreeHash": _test_sha("render-tree"),
                                    "layoutBoxes": 1,
                                    "outputHash": _valid_path0_output()["layout"][
                                        "outputHash"
                                    ],
                                },
                            },
                        ],
                    }
                ],
                "path0": {
                    "source": "contract:minimal",
                    "gate": "path0RenderTreeEvidence",
                    "rendererBackend": "path0-renderer-candidate",
                    "styleOpsPresent": True,
                    "styleOpsMatchesRenderTree": True,
                    "renderTreeHash": _test_sha("render-tree"),
                    "renderTreeBoundary": {
                        "phase": "layout",
                        "boundary": "renderTree",
                        "source": "contract:minimal",
                        "renderTreeHash": _test_sha("render-tree"),
                        "layoutBoxes": 1,
                        "outputHash": _valid_path0_output()["layout"][
                            "outputHash"
                        ],
                    },
                    "styledNodes": 1,
                    "layoutBoxes": 1,
                    "paintCommands": 1,
                    "layoutOutputHash": _valid_path0_output()["layout"][
                        "outputHash"
                    ],
                    "paintOutputHash": _valid_path0_output()["paint"][
                        "outputHash"
                    ],
                    "phases": ["layout", "paint"],
                    "layoutEvidence": {
                        "observationCount": 1,
                        "observationHash": _test_sha("layout"),
                        "styleProperties": ["width", "borderWidth"],
                        "observedProperties": ["width", "borderWidth"],
                    },
                    "paintEvidence": {
                        "observationCount": 1,
                        "observationHash": _test_sha("paint"),
                        "styleProperties": ["background", "borderWidth"],
                        "observedProperties": ["background", "borderWidth"],
                    },
                },
                "widgets": [
                    {
                        "source": "rendererReplay",
                        "gate": "rendererReplay",
                        "proof": {
                            "source": "rendererReplay",
                            "auditHash": _test_sha("widgets"),
                            "itemCount": 1,
                            "observedWidgets": ["Text"],
                        },
                        "widgets": [{"name": "Text", "count": 1}],
                    }
                ],
                "inputs": [
                    {
                        "source": "rendererReplay",
                        "gate": "rendererReplay",
                        "proof": {
                            "source": "rendererReplay",
                            "auditHash": _test_sha("inputs"),
                            "itemCount": 1,
                            "observedCapabilities": ["click"],
                        },
                        "capabilities": [{"capability": "click", "count": 1}],
                    }
                ],
                "styles": [
                    {
                        "kind": "apply",
                        "source": "styleOpsReplay+path0RenderTreeEvidence",
                        "gate": "styleOpsReplay+path0RenderTreeEvidence",
                        "support": "layout+paint",
                        "properties": [{"property": "borderWidth", "count": 1}],
                        "runtime": _valid_style_runtime(),
                    },
                    {
                        "kind": "apply",
                        "source": "styleOpsReplay+path0RenderTreeEvidence",
                        "gate": "styleOpsReplay+path0RenderTreeEvidence",
                        "support": "paint",
                        "properties": [{"property": "background", "count": 1}],
                        "runtime": _valid_style_runtime(),
                    },
                ],
                "declaredStyleOmissions": [
                    {
                        "kind": "omit",
                        "source": "styleOpsReplay+path0RenderTreeEvidence",
                        "gate": "styleOpsReplay+path0RenderTreeEvidence",
                        "status": "html-only",
                        "properties": [{"property": "display", "count": 1}],
                        "runtime": _valid_style_runtime(),
                    }
                ],
            },
        }
    )


def _valid_style_runtime() -> dict:
    return {
        "source": "contract:minimal",
        "rendererBackend": "path0-renderer-candidate",
        "styleOpsPresent": True,
        "styleOpsMatchesRenderTree": True,
        "styledNodes": 1,
        "layoutBoxes": 1,
        "paintCommands": 1,
        "layoutEvidence": {
            "observationCount": 1,
            "observationHash": _test_sha("layout"),
            "styleProperties": ["width", "borderWidth"],
            "observedProperties": ["width", "borderWidth"],
        },
        "paintEvidence": {
            "observationCount": 1,
            "observationHash": _test_sha("paint"),
            "styleProperties": ["background", "borderWidth"],
            "observedProperties": ["background", "borderWidth"],
        },
    }


def _test_sha(label: str) -> str:
    return f"sha256:{hashlib.sha256(label.encode('utf-8')).hexdigest()}"


def _valid_path0_output() -> dict:
    layout = {
        "schemaVersion": 1,
        "format": "path0-layout-output",
        "boxCount": 1,
        "rootPath": [],
        "boxes": [
            {
                "path": [],
                "name": "Text",
                "bounds": [0, 0, 10, 10],
                "id": None,
                "context": "Text",
                "text": "Hello",
                "events": [],
                "state": [],
                "style": {"width": {"type": "size", "value": 10, "unit": "px"}},
                "children": [],
            }
        ],
    }
    paint = {
        "schemaVersion": 1,
        "format": "path0-paint-output",
        "width": 10,
        "height": 10,
        "commandCount": 1,
        "commands": [
            {
                "kind": "rect",
                "path": [],
                "bounds": [0, 0, 10, 10],
                "fill": "#ffffff",
                "stroke": None,
                "strokeWidth": 0,
                "radius": 0,
                "text": None,
                "color": None,
                "fontSize": 14,
                "clip": None,
                "context": "test",
            }
        ],
    }
    return {
        "layout": {**layout, "outputHash": _output_hash(layout)},
        "paint": {**paint, "outputHash": _output_hash(paint)},
    }


def _refresh_path0_layout_hashes(report: dict) -> None:
    layout = report["path0"]["output"]["layout"]
    layout["outputHash"] = _output_hash(layout)
    report["evidence"]["path0"]["layoutOutputHash"] = layout["outputHash"]
    report["evidence"]["path0"]["renderTreeBoundary"]["outputHash"] = layout[
        "outputHash"
    ]
    report["evidence"]["rendererBoundaries"][0]["boundaries"][1]["proof"][
        "outputHash"
    ] = layout["outputHash"]


def _refresh_path0_paint_hashes(report: dict) -> None:
    paint = report["path0"]["output"]["paint"]
    paint["outputHash"] = _output_hash(paint)
    report["evidence"]["path0"]["paintOutputHash"] = paint["outputHash"]
    report["evidence"]["rendererBoundaries"][0]["boundaries"][0]["proof"][
        "outputHash"
    ] = paint["outputHash"]


def _output_hash(payload: dict) -> str:
    payload = {key: value for key, value in payload.items() if key != "outputHash"}
    encoded = json.dumps(
        payload,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"
