from cli_helpers import (
    json,
    main,
    _write_backend_capability_profile,
)


def test_cli_backend_profile_outputs_builtin_summary(capsys):
    result = main(["backend-profile", "native"])

    captured = capsys.readouterr()
    assert result == 0
    assert "backend-profile native-python" in captured.out
    assert "label: Python native renderer" in captured.out
    assert "styles: ignored=5, layout=11, layout+paint=2, paint=7" in captured.out
    assert "widgets: container=8, control=2, text=1" in captured.out
    assert "inputs: deferred=8, supported=8" in captured.out
    assert "renderer boundaries: supported=2" in captured.out
    assert (
        "coverage: rendererBoundaries=2, widgets=11, inputs=8, styles=20, "
        "declaredStyleOmissions=5"
        in captured.out
    )

def test_cli_backend_profile_outputs_json_report(capsys):
    result = main(["backend-profile", "native-python", "--json"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert result == 0
    assert payload["schemaVersion"] == 1
    assert payload["format"] == "backend-profile-report"
    assert payload["profile"]["name"] == "native-python"
    assert payload["summary"]["styles"] == {
        "ignored": 5,
        "layout": 11,
        "layout+paint": 2,
        "paint": 7,
    }
    assert payload["summary"]["coverage"] == {
        "rendererBoundaries": 2,
        "widgets": 11,
        "inputs": 8,
        "styles": 20,
        "declaredStyleOmissions": 5,
    }
    assert payload["coverageDeclaration"]["format"] == "backend-coverage-declaration"

def test_cli_backend_profile_outputs_coverage_declaration(capsys):
    result = main(["backend-profile", "native-python", "--coverage-declaration"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert result == 0
    assert payload["backend"] == "native-python"
    assert payload["format"] == "backend-coverage-declaration"
    assert "Button" in payload["covers"]["widgets"]
    assert "click" in payload["covers"]["inputs"]

def test_cli_backend_profile_writes_coverage_declaration_artifact(tmp_path, capsys):
    output = tmp_path / "native-coverage-declaration.json"

    result = main(
        [
            "backend-profile",
            "native-python",
            "--coverage-declaration",
            "--out",
            str(output),
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert result == 0
    assert captured.out == f"backend profile artifact: {output}\n"
    assert payload["backend"] == "native-python"
    assert payload["format"] == "backend-coverage-declaration"

def test_cli_backend_profile_loads_candidate_profile_json(
    tmp_path,
    capsys,
):
    profile = tmp_path / "candidate-profile.json"
    _write_backend_capability_profile(
        profile,
        name="candidate-inspect",
        styles={"padding": "layout"},
        widgets={"Text": "text"},
        inputs={"click": "supported", "gesture": "deferred"},
    )

    result = main(
        [
            "backend-profile",
            "--backend-capability-profile",
            str(profile),
            "--json",
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert result == 0
    assert payload["profile"]["name"] == "candidate-inspect"
    assert payload["summary"]["styles"] == {"layout": 1}
    assert payload["summary"]["widgets"] == {"text": 1}
    assert payload["summary"]["inputs"] == {"deferred": 1, "supported": 1}
    assert payload["coverageDeclaration"]["covers"] == {
        "widgets": ["Text"],
        "inputs": ["click"],
        "rendererBoundaries": [],
        "styles": ["padding"],
        "declaredStyleOmissions": [],
    }

def test_cli_backend_profile_rejects_name_and_profile_json(
    tmp_path,
    capsys,
):
    profile = tmp_path / "candidate-profile.json"
    _write_backend_capability_profile(profile, name="candidate-conflict")

    result = main(
        [
            "backend-profile",
            "native-python",
            "--backend-capability-profile",
            str(profile),
        ]
    )

    captured = capsys.readouterr()
    assert result == 1
    assert (
        "profile name and --backend-capability-profile are mutually exclusive"
        in captured.err
    )

def test_cli_backend_coverage_accepts_builtin_profile(capsys):
    result = main(
        [
            "backend-coverage",
            "--requirements",
            "examples/native/contracts/backend_readiness_expected.json",
            "--backend",
            "native-python",
            "--json",
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert result == 0
    assert payload["schemaVersion"] == 1
    assert payload["format"] == "backend-coverage-report"
    assert payload["backend"] == "native-python"
    assert payload["passed"] is True
    assert payload["readiness"]["passed"] is True
    assert payload["readiness"]["candidate"]["backend"] == "native-python"
    assert payload["readiness"]["strictEvidence"] is True
    assert payload["readiness"]["evidenceSummary"] == {
        "malformed": 0,
        "malformedByBlocker": {},
    }
    assert payload["blockers"] == []
    assert payload["coverage"]["widgets"]["extra"] == []
    assert payload["coverage"]["widgets"]["evidence"]["claimed"] == [
        "Button",
        "FocusScope",
        "For",
        "HStack",
        "Input",
        "Panel",
        "ScrollView",
        "ShortcutScope",
        "Show",
        "Text",
        "VStack",
    ]
    assert payload["coverage"]["widgets"]["evidence"]["unproven"] == []
    assert payload["coverage"]["widgets"]["summary"]["unproven"] == 0
    assert payload["coverage"]["widgets"]["evidenceMap"]["Button"]["sources"][
        0
    ]["gate"] == "rendererReplay"
    assert payload["coverage"]["styles"]["missing"] == []

def test_cli_backend_coverage_audit_reports_traceable_sources(capsys):
    result = main(
        [
            "backend-coverage",
            "--requirements",
            "examples/native/contracts/backend_readiness_expected.json",
            "--backend",
            "native-python",
            "--audit",
        ]
    )

    captured = capsys.readouterr()
    assert result == 0
    assert "backend-coverage audit native-python" in captured.out
    assert (
        "rendererBoundaries: covered=2/2, missing=0, unproven=0"
        in captured.out
    )
    assert (
        "rendererBoundaries renderTreeLayout: covered required=yes "
        "declared=yes exercised=yes"
    ) in captured.out
    assert (
        "rendererBoundaries renderTreeLayout proof[0]: "
        "source=path0RenderTreeEvidence gate=path0RenderTreeEvidence "
        "kind=rendererBoundary group=0 count=1 phase=layout "
        "boundary=renderTree layoutBoxes=15 "
        "outputHash=sha256:c0f4d392a48e8631addc5e80cf0872e846076da018c92f3769ffa28b7799bc57"
    ) in captured.out
    assert (
        "rendererBoundaries paint proof[0]: "
        "source=path0RenderTreeEvidence gate=path0RenderTreeEvidence "
        "kind=rendererBoundary group=0 count=1 phase=paint paintCommands=18 "
        "outputHash=sha256:47cd28b2411e2c648a6c8b8129f77384c33ea7517156f69805b1701a9a6c0bf2"
    ) in captured.out
    assert "widgets: covered=11/11, missing=0, unproven=0" in captured.out
    assert (
        "widgets Button: covered required=yes declared=yes exercised=yes"
        in captured.out
    )
    assert (
        "widgets Button proof[0]: source=rendererReplay gate=rendererReplay "
        "kind=widget support=control group=1 count=9"
    ) in captured.out
    assert (
        "styles borderWidth: covered required=yes declared=yes exercised=yes"
        in captured.out
    )
    assert (
        "styles borderWidth proof[0]: "
        "source=styleOpsReplay+path0RenderTreeEvidence "
        "gate=styleOpsReplay+path0RenderTreeEvidence kind=apply "
        "support=layout+paint group=1 count=3 "
        "runtime=path0-renderer-candidate phases=layout+paint"
    ) in captured.out
    assert "layoutHash=sha256:" in captured.out
    assert "paintHash=sha256:" in captured.out
    assert (
        "declaredStyleOmissions display proof[0]: "
        "source=styleOpsReplay+path0RenderTreeEvidence "
        "gate=styleOpsReplay+path0RenderTreeEvidence kind=omit "
        "status=html-only group=0 count=1 runtime=path0-renderer-candidate "
        "phases=layout+paint"
    ) in captured.out
    assert "blockers: none" in captured.out

def test_cli_backend_coverage_reports_evidence_contract_errors(tmp_path, capsys):
    requirements = json.loads(
        open(
            "examples/native/contracts/backend_readiness_expected.json",
            encoding="utf-8",
        ).read()
    )
    requirements["evidence"]["widgets"][0].pop("source")
    requirements_path = tmp_path / "broken-readiness.json"
    requirements_path.write_text(json.dumps(requirements), encoding="utf-8")

    result = main(
        [
            "backend-coverage",
            "--requirements",
            str(requirements_path),
            "--backend",
            "native-python",
        ]
    )

    captured = capsys.readouterr()
    assert result == 1
    assert "status: failed" in captured.out
    assert "widgets: covered=3/11, missing=0, unproven=8" in captured.out
    assert (
        "widgets unproven: FocusScope, For, HStack, Panel, ScrollView, "
        "ShortcutScope, Show, VStack"
    ) in captured.out
    assert "evidence errors: 1" in captured.out
    assert "evidence malformed: 1" in captured.out
    assert "evidence malformed by blocker: widgetsEvidence=1" in captured.out
    assert (
        "evidence error: evidence.widgets[0].source must be a non-empty string"
        in captured.out
    )
    assert "blockers: widgetsEvidence" in captured.out

def test_cli_backend_coverage_audit_reports_unproven_claims(tmp_path, capsys):
    requirements = json.loads(
        open(
            "examples/native/contracts/backend_readiness_expected.json",
            encoding="utf-8",
        ).read()
    )
    requirements["evidence"]["widgets"][0].pop("source")
    requirements_path = tmp_path / "broken-readiness.json"
    requirements_path.write_text(json.dumps(requirements), encoding="utf-8")

    result = main(
        [
            "backend-coverage",
            "--requirements",
            str(requirements_path),
            "--backend",
            "native-python",
            "--audit",
        ]
    )

    captured = capsys.readouterr()
    assert result == 1
    assert "backend-coverage audit native-python" in captured.out
    assert (
        "widgets FocusScope: unproven required=yes declared=yes exercised=no"
        in captured.out
    )
    assert "widgets FocusScope proof: none" in captured.out
    assert "evidence errors: 1" in captured.out
    assert "evidence malformed: 1" in captured.out
    assert "evidence malformed by blocker: widgetsEvidence=1" in captured.out
    assert "blockers: widgetsEvidence" in captured.out

def test_cli_backend_coverage_rejects_readiness_without_contract_format(
    tmp_path,
    capsys,
):
    readiness = json.loads(
        open(
            "examples/native/contracts/backend_readiness_expected.json",
            encoding="utf-8",
        ).read()
    )
    readiness.pop("format")
    requirements_path = tmp_path / "missing-format-readiness.json"
    requirements_path.write_text(json.dumps(readiness), encoding="utf-8")

    result = main(
        [
            "backend-coverage",
            "--requirements",
            str(requirements_path),
            "--backend",
            "native-python",
        ]
    )

    captured = capsys.readouterr()
    assert result == 1
    assert "status: failed" in captured.out
    assert "evidence errors: 1" in captured.out
    assert "evidence malformed by blocker: backendReadinessContract=1" in captured.out
    assert (
        "evidence error: readiness.format must be 'backend-readiness-report'"
        in captured.out
    )
    assert "blockers: backendReadinessContract" in captured.out

def test_cli_backend_coverage_rejects_readiness_with_wrong_contract_format(
    tmp_path,
    capsys,
):
    readiness = json.loads(
        open(
            "examples/native/contracts/backend_readiness_expected.json",
            encoding="utf-8",
        ).read()
    )
    readiness["format"] = "not-readiness"
    requirements_path = tmp_path / "wrong-format-readiness.json"
    requirements_path.write_text(json.dumps(readiness), encoding="utf-8")

    result = main(
        [
            "backend-coverage",
            "--requirements",
            str(requirements_path),
            "--backend",
            "native-python",
        ]
    )

    captured = capsys.readouterr()
    assert result == 1
    assert "status: failed" in captured.out
    assert "evidence errors: 1" in captured.out
    assert "evidence malformed by blocker: backendReadinessContract=1" in captured.out
    assert (
        "evidence error: readiness.format must be 'backend-readiness-report'"
        in captured.out
    )
    assert "blockers: backendReadinessContract" in captured.out

def test_cli_backend_coverage_rejects_readiness_with_wrong_schema_version(
    tmp_path,
    capsys,
):
    readiness = json.loads(
        open(
            "examples/native/contracts/backend_readiness_expected.json",
            encoding="utf-8",
        ).read()
    )
    readiness["schemaVersion"] = 2
    requirements_path = tmp_path / "wrong-schema-readiness.json"
    requirements_path.write_text(json.dumps(readiness), encoding="utf-8")

    result = main(
        [
            "backend-coverage",
            "--requirements",
            str(requirements_path),
            "--backend",
            "native-python",
        ]
    )

    captured = capsys.readouterr()
    assert result == 1
    assert "status: failed" in captured.out
    assert "evidence errors: 1" in captured.out
    assert "evidence malformed by blocker: backendReadinessContract=1" in captured.out
    assert "evidence error: readiness.schemaVersion must be 1" in captured.out
    assert "blockers: backendReadinessContract" in captured.out

def test_cli_backend_coverage_rejects_backend_identity_mismatch(tmp_path, capsys):
    declaration = json.loads(
        open(
            "examples/native/contracts/backend_coverage_full_declaration.json",
            encoding="utf-8",
        ).read()
    )
    declaration["backend"] = "totally-fake-backend"
    declaration_path = tmp_path / "fake-backend-declaration.json"
    declaration_path.write_text(json.dumps(declaration), encoding="utf-8")

    result = main(
        [
            "backend-coverage",
            "--requirements",
            "examples/native/contracts/backend_readiness_expected.json",
            "--coverage-declaration",
            str(declaration_path),
        ]
    )

    captured = capsys.readouterr()
    assert result == 1
    assert "backend-coverage totally-fake-backend" in captured.out
    assert "status: failed" in captured.out
    assert "evidence malformed by blocker: backendIdentity=1" in captured.out
    assert (
        "evidence error: coverage declaration backend must match "
        "readiness.candidate.backend"
    ) in captured.out
    assert "blockers: backendIdentity" in captured.out

def test_cli_backend_coverage_reports_partial_profile_gaps(capsys):
    result = main(
        [
            "backend-coverage",
            "--requirements",
            "examples/native/contracts/backend_readiness_expected.json",
            "--backend-capability-profile",
            "examples/native/contracts/backend_candidate_partial_profile.json",
        ]
    )

    captured = capsys.readouterr()
    assert result == 1
    assert "backend-coverage partial-backend-candidate" in captured.out
    assert "status: failed" in captured.out
    assert (
        "rendererBoundaries: covered=0/2, missing=2, unproven=0"
        in captured.out
    )
    assert "rendererBoundaries missing: paint, renderTreeLayout" in captured.out
    assert "widgets: covered=8/11, missing=3, unproven=0" in captured.out
    assert "widgets missing: Button, FocusScope, Panel" in captured.out
    assert "inputs missing: focus, key_down, key_input, tab_focus" in captured.out
    assert (
        "styles missing: background, borderColor, borderRadius, borderWidth, "
        "color, fontSize, maxHeight, maxWidth, minHeight, minWidth"
        in captured.out
    )
    assert (
        "declaredStyleOmissions missing: display, fontWeight, margin, opacity"
        in captured.out
    )
    assert (
        "blockers: backendIdentity, rendererBoundariesCoverage, "
        "widgetsCoverage, inputsCoverage, stylesCoverage, "
        "declaredStyleOmissionsCoverage"
        in captured.out
    )

def test_cli_backend_coverage_rejects_requirements_without_evidence(tmp_path, capsys):
    readiness = json.loads(
        open(
            "examples/native/contracts/backend_readiness_expected.json",
            encoding="utf-8",
        ).read()
    )
    requirements_path = tmp_path / "requirements-only.json"
    requirements_path.write_text(
        json.dumps(readiness["requirements"]),
        encoding="utf-8",
    )

    result = main(
        [
            "backend-coverage",
            "--requirements",
            str(requirements_path),
            "--backend",
            "native-python",
            "--json",
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert result == 1
    assert payload["passed"] is False
    assert payload["readiness"]["strictEvidence"] is True
    assert payload["readiness"]["evidenceBlockers"] == ["capabilityEvidence"]
    assert payload["readiness"]["evidenceSummary"] == {
        "malformed": 1,
        "malformedByBlocker": {
            "capabilityEvidence": 1,
        },
    }
    assert payload["coverage"]["widgets"]["exercised"] == []
    assert payload["coverage"]["widgets"]["summary"]["unproven"] == 11
    assert "capabilityEvidence" in payload["blockers"]
    assert "widgetsEvidence" in payload["blockers"]

def test_cli_backend_coverage_rejects_audit_with_json_or_out(tmp_path, capsys):
    out = tmp_path / "coverage.json"

    json_result = main(
        [
            "backend-coverage",
            "--requirements",
            "examples/native/contracts/backend_readiness_expected.json",
            "--backend",
            "native-python",
            "--audit",
            "--json",
        ]
    )
    out_result = main(
        [
            "backend-coverage",
            "--requirements",
            "examples/native/contracts/backend_readiness_expected.json",
            "--backend",
            "native-python",
            "--audit",
            "--out",
            str(out),
        ]
    )

    captured = capsys.readouterr()
    assert json_result == 1
    assert out_result == 1
    assert not out.exists()
    assert captured.err.count("--audit cannot be combined with --json or --out") == 2

def test_cli_backend_coverage_accepts_explicit_declaration(capsys):
    result = main(
        [
            "backend-coverage",
            "--requirements",
            "examples/native/contracts/backend_readiness_expected.json",
            "--coverage-declaration",
            "examples/native/contracts/backend_coverage_full_declaration.json",
            "--json",
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert result == 0
    assert payload["backend"] == "native-python"
    assert payload["passed"] is True
    assert payload["blockers"] == []
    assert payload["declarationErrors"] == []

def test_cli_backend_coverage_writes_report_artifact(tmp_path, capsys):
    output = tmp_path / "backend-coverage.json"

    result = main(
        [
            "backend-coverage",
            "--requirements",
            "examples/native/contracts/backend_readiness_expected.json",
            "--backend",
            "native-python",
            "--out",
            str(output),
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert result == 0
    assert captured.out == f"backend coverage artifact: {output}\n"
    assert payload["backend"] == "native-python"
    assert payload["passed"] is True
    assert payload["blockers"] == []

def test_cli_backend_coverage_rejects_multiple_coverage_sources(capsys):
    result = main(
        [
            "backend-coverage",
            "--requirements",
            "examples/native/contracts/backend_readiness_expected.json",
            "--backend",
            "native-python",
            "--coverage-declaration",
            "examples/native/contracts/backend_coverage_full_declaration.json",
        ]
    )

    captured = capsys.readouterr()
    assert result == 1
    assert (
        "--coverage-declaration, --backend, and --backend-capability-profile "
        "are mutually exclusive"
        in captured.err
    )
