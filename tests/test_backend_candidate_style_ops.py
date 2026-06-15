from copy import deepcopy
import json
from pathlib import Path


from examples.native.backend_candidate_skeleton import (
    StyleOpsCandidateAcceptanceReport,
    StyleOpsCandidateClassReport,
    StyleOpsCandidateDirectStyleReport,
    backend_candidate_style_artifact,
    main,
    run_style_ops_candidate_acceptance,
    style_ops_candidate_report_to_dict,
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

def test_style_ops_candidate_acceptance_replays_default_artifact():
    report = run_style_ops_candidate_acceptance()
    payload = style_ops_candidate_report_to_dict(report)
    classes = {class_report.class_name: class_report for class_report in report.classes}
    direct_styles = {
        direct_style.path: direct_style
        for direct_style in report.direct_styles
    }
    shell = classes["candidate-shell"]
    scroll = direct_styles[(0, 0, 2)]

    assert isinstance(report, StyleOpsCandidateAcceptanceReport)
    assert isinstance(shell, StyleOpsCandidateClassReport)
    assert isinstance(scroll, StyleOpsCandidateDirectStyleReport)
    assert report.passed is True
    assert payload["schemaVersion"] == 1
    assert payload["format"] == "style-ops-contract"
    assert payload["passed"] is True
    assert payload["backend"] == "native-python"
    assert payload["styleOps"] == {
        "schemaVersion": 1,
        "format": "otoe-style-ops",
    }
    assert payload["capabilityAudit"]["backend"] == "native-python"
    assert payload["capabilityAudit"]["summary"] == {
        "applied": 40,
        "omitted": 5,
        "unsupported": 0,
    }
    assert payload["capabilityAudit"]["applied"] == [
        {
            "support": "layout",
            "count": 23,
            "properties": [
                {"property": "alignItems", "count": 1},
                {"property": "gap", "count": 3},
                {"property": "height", "count": 2},
                {"property": "justifyContent", "count": 1},
                {"property": "maxHeight", "count": 2},
                {"property": "maxWidth", "count": 1},
                {"property": "minHeight", "count": 2},
                {"property": "minWidth", "count": 1},
                {"property": "padding", "count": 3},
                {"property": "scrollY", "count": 1},
                {"property": "width", "count": 6},
            ],
        },
        {
            "support": "layout+paint",
            "count": 4,
            "properties": [
                {"property": "borderWidth", "count": 3},
                {"property": "fontSize", "count": 1},
            ],
        },
        {
            "support": "paint",
            "count": 13,
            "properties": [
                {"property": "background", "count": 3},
                {"property": "borderColor", "count": 3},
                {"property": "borderRadius", "count": 3},
                {"property": "color", "count": 1},
                {"property": "overflow", "count": 1},
                {"property": "textOverflow", "count": 1},
                {"property": "whiteSpace", "count": 1},
            ],
        },
    ]
    assert payload["capabilityAudit"]["declaredOmissions"] == [
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
    assert payload["capabilityAudit"]["unsupportedProperties"] == []
    assert shell.passed is True
    assert shell.applied_declarations["width"] == {
        "type": "size",
        "value": 220,
        "unit": "px",
    }
    assert shell.applied_declarations["padding"] == {
        "type": "size",
        "value": 8,
        "unit": "px",
    }
    assert shell.applied_declarations["gap"] == {
        "type": "size",
        "value": 6,
        "unit": "px",
    }
    assert shell.applied_declarations["background"] == {
        "type": "literal",
        "value": "#f8fafc",
    }
    assert shell.omitted_ops == (
        {
            "op": "omitStyle",
            "property": "borderStyle",
            "support": "ignored",
            "status": "html-only",
            "value": {"type": "literal", "value": "solid"},
            "message": "property 'borderStyle' is accepted but ignored by native",
        },
        {
            "op": "omitStyle",
            "property": "display",
            "support": "ignored",
            "status": "html-only",
            "value": {"type": "literal", "value": "flex"},
            "message": "property 'display' is accepted but ignored by native",
        },
        {
            "op": "omitStyle",
            "property": "fontWeight",
            "support": "ignored",
            "status": "html-only",
            "value": {"type": "literal", "value": 700},
            "message": "property 'fontWeight' is accepted but ignored by native",
        },
        {
            "op": "omitStyle",
            "property": "margin",
            "support": "ignored",
            "status": "html-only",
            "value": {"type": "size", "value": 4, "unit": "px"},
            "message": "property 'margin' is accepted but ignored by native",
        },
        {
            "op": "omitStyle",
            "property": "opacity",
            "support": "ignored",
            "status": "html-only",
            "value": {"type": "literal", "value": 0.96},
            "message": "property 'opacity' is accepted but ignored by native",
        },
    )
    assert scroll.passed is True
    assert scroll.widget == "ScrollView"
    assert scroll.node_id == (
        "root:ShortcutScope/index:0:FocusScope/index:0:VStack/index:2:ScrollView"
    )
    assert scroll.applied_declarations == {
        "scrollY": {"type": "size", "value": 0, "unit": "px"}
    }
    assert scroll.omitted_ops == ()
    scroll_payload = next(
        direct_style
        for direct_style in payload["directStyles"]
        if direct_style["path"] == [0, 0, 2]
    )
    assert scroll_payload["nodeId"] == scroll.node_id

def test_style_ops_candidate_capability_audit_reports_unsupported_properties():
    artifact = deepcopy(backend_candidate_style_artifact())
    shell_rule = next(
        rule
        for rule in artifact["rules"]
        if rule["className"] == "candidate-shell"
    )
    shell_ops = next(
        class_payload
        for class_payload in artifact["styleOps"]["classes"]
        if class_payload["className"] == "candidate-shell"
    )
    shell_rule["declarations"]["customGlow"] = {
        "type": "literal",
        "value": "enabled",
    }
    shell_ops["ops"].append(
        {
            "op": "setStyle",
            "property": "customGlow",
            "support": "unsupported",
            "value": {"type": "literal", "value": "enabled"},
        }
    )

    report = run_style_ops_candidate_acceptance(artifact)
    payload = style_ops_candidate_report_to_dict(report)

    assert report.passed is True
    assert payload["capabilityAudit"]["summary"]["unsupported"] == 1
    assert payload["capabilityAudit"]["unsupportedProperties"] == [
        {"property": "customGlow", "count": 1}
    ]
    assert {
        "support": "unsupported",
        "count": 1,
        "properties": [{"property": "customGlow", "count": 1}],
    } in payload["capabilityAudit"]["applied"]

def test_style_ops_candidate_acceptance_detects_mismatch():
    artifact = deepcopy(backend_candidate_style_artifact())
    shell_ops = next(
        class_payload
        for class_payload in artifact["styleOps"]["classes"]
        if class_payload["className"] == "candidate-shell"
    )
    width_op = next(op for op in shell_ops["ops"] if op["property"] == "width")
    width_op["value"] = {"type": "size", "value": 999, "unit": "px"}

    report = run_style_ops_candidate_acceptance(artifact)
    classes = {class_report.class_name: class_report for class_report in report.classes}
    payload = style_ops_candidate_report_to_dict(report)

    assert report.passed is False
    assert payload["passed"] is False
    assert classes["candidate-shell"].passed is False
    assert (
        "styleOps class 'candidate-shell' applied declarations do not match compiled rules"
        in classes["candidate-shell"].errors
    )

def test_style_ops_candidate_acceptance_uses_artifact_capabilities():
    artifact = deepcopy(backend_candidate_style_artifact())
    artifact["styleOps"]["capabilities"]["styles"]["width"] = "paint"

    report = run_style_ops_candidate_acceptance(artifact)
    classes = {class_report.class_name: class_report for class_report in report.classes}

    assert report.passed is False
    assert (
        "styleOps class 'candidate-shell' op 0 support 'layout' does not match 'paint'"
        in classes["candidate-shell"].errors
    )

def test_style_ops_candidate_acceptance_detects_direct_style_mismatch():
    artifact = deepcopy(backend_candidate_style_artifact())
    artifact["styleOps"]["directStyles"][0]["widget"] = "Panel"

    report = run_style_ops_candidate_acceptance(artifact)
    direct_styles = {
        direct_style.path: direct_style
        for direct_style in report.direct_styles
    }

    assert report.passed is False
    assert (
        "styleOps directStyles [0, 0, 2] widget does not match compiled artifact"
        in direct_styles[(0, 0, 2)].errors
    )

def test_style_ops_contract_fixture_matches_generated_contract(tmp_path, capsys):
    actual = tmp_path / "actual-style-ops-contract.json"
    report = run_style_ops_candidate_acceptance()
    payload = style_ops_candidate_report_to_dict(report)
    actual.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")

    result = otoe_cli_main(
        [
            "compare-contract",
            str(STYLE_OPS_CONTRACT_FIXTURE),
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

def test_backend_candidate_skeleton_main_outputs_style_ops_contract_json(capsys):
    result = main(["--style-ops-contract-json"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    shell = next(
        class_payload
        for class_payload in payload["classes"]
        if class_payload["className"] == "candidate-shell"
    )
    assert result == 0
    assert payload["schemaVersion"] == 1
    assert payload["format"] == "style-ops-contract"
    assert payload["passed"] is True
    assert payload["styleOps"]["schemaVersion"] == 1
    assert payload["capabilityAudit"]["summary"] == {
        "applied": 40,
        "omitted": 5,
        "unsupported": 0,
    }
    assert shell["appliedDeclarations"]["background"] == {
        "type": "literal",
        "value": "#f8fafc",
    }
