import hashlib
import json
from pathlib import Path

import pytest

import otoe.build_runner_template as runner
from otoe.backend_package import package_hash
from otoe.bundle_backend_coverage import verify_backend_coverage_contract
from otoe.bundle_backend_package import (
    verify_backend_package,
    verify_backend_package_report,
)
from otoe.bundle_deps import verify_dependency_audit_contract


def test_dependency_audit_contract_accepts_audit_only_payload():
    payload = {
        "hasErrors": False,
        "status": "ok",
        "runtimeInstallsAllowed": False,
        "resolution": {
            "mode": "audit-only",
            "lockfile": False,
            "wheelClosure": False,
            "runtimeInstallsAllowed": False,
        },
        "runtimePolicy": {
            "mode": "audit-only",
            "network": "warn",
            "subprocess": "error",
            "findings": [
                {
                    "category": "network",
                    "action": "warning",
                    "module": "app.demo",
                    "source": "app/demo.py",
                    "mechanism": "urllib",
                    "line": 12,
                }
            ],
        },
    }

    verify_dependency_audit_contract(payload, "otoe-deps.json")


def test_dependency_audit_contract_rejects_invalid_runtime_policy_finding():
    payload = {
        "hasErrors": False,
        "status": "ok",
        "runtimeInstallsAllowed": False,
        "resolution": {
            "mode": "audit-only",
            "lockfile": False,
            "wheelClosure": False,
            "runtimeInstallsAllowed": False,
        },
        "runtimePolicy": {
            "mode": "audit-only",
            "network": "warn",
            "subprocess": "error",
            "findings": [
                {
                    "category": "filesystem",
                    "action": "warning",
                    "module": "app.demo",
                    "source": "app/demo.py",
                    "mechanism": "open",
                    "line": 0,
                }
            ],
        },
    }

    with pytest.raises(
        ValueError,
        match="runtimePolicy.findings\\[0\\].category must be network or subprocess",
    ):
        verify_dependency_audit_contract(payload, "otoe-deps.json")


def test_backend_coverage_contract_accepts_minimal_traceable_empty_report():
    verify_backend_coverage_contract(
        _backend_coverage_payload(),
        "otoe-backend-coverage.json",
    )


def test_backend_coverage_contract_accepts_traceability_proofs():
    payload = _backend_coverage_payload()
    trace = payload["trace"]["path0"]
    payload["coverage"]["rendererBoundaries"] = _covered_section(
        "renderTreeLayout",
        {
            "groupIndex": 0,
            "source": "path0",
            "gate": "required",
            "boundaryProof": {
                "phase": "layout",
                "source": "path0",
                "boundary": "renderTree",
                "outputHash": trace["layoutOutputHash"],
                "renderTreeHash": trace["renderTreeHash"],
                "layoutBoxes": 1,
            },
        },
    )
    payload["coverage"]["widgets"] = _covered_section(
        "Text",
        {
            "groupIndex": 0,
            "source": "widget-audit",
            "gate": "required",
            "capabilityProof": {
                "source": "widget-audit",
                "auditHash": _sha_uri("widgets"),
                "itemCount": 1,
                "observedWidgets": ["Text"],
            },
        },
    )
    payload["coverage"]["styles"] = _covered_section(
        "background",
        {
            "groupIndex": 0,
            "source": "style-runtime",
            "gate": "required",
            "runtimeProof": {
                "source": "style-runtime",
                "rendererBackend": "native-python",
                "styleOpsPresent": True,
                "styleOpsMatchesRenderTree": True,
                "styledNodes": 1,
                "layoutBoxes": 1,
                "paintCommands": 1,
                "phases": ["layout", "paint"],
                "layoutObservationCount": 1,
                "layoutObservationHash": _sha_uri("style-layout"),
                "paintObservationCount": 1,
                "paintObservationHash": _sha_uri("style-paint"),
            },
        },
    )

    verify_backend_coverage_contract(payload, "otoe-backend-coverage.json")


def test_backend_coverage_contract_rejects_inconsistent_section_sets():
    payload = _backend_coverage_payload()
    payload["coverage"]["widgets"]["covered"] = ["Button"]
    payload["coverage"]["widgets"]["summary"]["covered"] = 1

    with pytest.raises(
        ValueError,
        match="coverage.widgets.covered inconsistent",
    ):
        verify_backend_coverage_contract(payload, "otoe-backend-coverage.json")


def test_backend_coverage_contract_rejects_external_render_tree_hash_drift():
    payload = _backend_coverage_payload()
    payload["trace"]["path0"]["externalBackend"] = {
        "backend": "path0",
        "packageHash": _sha_uri("package"),
        "renderTreeHash": _sha_uri("wrong-render-tree"),
        "layoutOutputHash": _sha_uri("external-layout"),
        "paintOutputHash": _sha_uri("external-paint"),
        "semanticValidation": {"passed": True, "errors": []},
    }

    with pytest.raises(
        ValueError,
        match="externalBackend.renderTreeHash must match trace.path0.renderTreeHash",
    ):
        verify_backend_coverage_contract(payload, "otoe-backend-coverage.json")


def test_backend_coverage_contract_reports_failed_blockers():
    payload = _backend_coverage_payload()
    payload["passed"] = False
    payload["blockers"] = ["widgets missing: Button", "inputs missing: click"]

    with pytest.raises(
        ValueError,
        match="backend coverage failed: widgets missing: Button, inputs missing: click",
    ):
        verify_backend_coverage_contract(payload, "otoe-backend-coverage.json")


def test_backend_coverage_contract_rejects_duplicate_section_names():
    payload = _backend_coverage_payload()
    payload["coverage"]["inputs"]["required"] = ["click", "click"]

    with pytest.raises(
        ValueError,
        match="coverage.inputs.required must not contain duplicate names",
    ):
        verify_backend_coverage_contract(payload, "otoe-backend-coverage.json")


def test_backend_coverage_contract_rejects_evidence_map_key_drift():
    payload = _backend_coverage_payload()
    payload["coverage"]["widgets"] = _covered_section(
        "Text",
        {
            "groupIndex": 0,
            "source": "widget-audit",
            "gate": "required",
            "capabilityProof": {
                "source": "widget-audit",
                "auditHash": _sha_uri("widgets"),
                "itemCount": 1,
                "observedWidgets": ["Text"],
            },
        },
    )
    payload["coverage"]["widgets"]["evidenceMap"]["Button"] = (
        payload["coverage"]["widgets"]["evidenceMap"].pop("Text")
    )

    with pytest.raises(
        ValueError,
        match="coverage.widgets.evidenceMap keys mismatch: missing Text; extra Button",
    ):
        verify_backend_coverage_contract(payload, "otoe-backend-coverage.json")


def test_backend_coverage_contract_rejects_malformed_capability_proof():
    payload = _backend_coverage_payload()
    payload["coverage"]["widgets"] = _covered_section(
        "Button",
        {
            "groupIndex": 0,
            "source": "widget-audit",
            "gate": "required",
            "capabilityProof": {
                "source": "widget-audit",
                "auditHash": _sha_uri("widgets"),
                "itemCount": 1,
                "observedWidgets": ["Text"],
            },
        },
    )

    with pytest.raises(
        ValueError,
        match=r"capabilityProof.observedWidgets must include 'Button'",
    ):
        verify_backend_coverage_contract(payload, "otoe-backend-coverage.json")


def test_backend_coverage_contract_rejects_malformed_runtime_proof():
    payload = _backend_coverage_payload()
    payload["coverage"]["styles"] = _covered_section(
        "background",
        {
            "groupIndex": 0,
            "source": "style-runtime",
            "gate": "required",
            "runtimeProof": {
                "source": "style-runtime",
                "rendererBackend": "native-python",
                "styleOpsPresent": True,
                "styleOpsMatchesRenderTree": True,
                "styledNodes": 1,
                "layoutBoxes": 1,
                "paintCommands": 1,
                "phases": ["layout", "composite"],
                "layoutObservationCount": 1,
                "layoutObservationHash": _sha_uri("style-layout"),
            },
        },
    )

    with pytest.raises(
        ValueError,
        match="runtimeProof.phases must include layout/paint phase names",
    ):
        verify_backend_coverage_contract(payload, "otoe-backend-coverage.json")


def test_build_runner_rejects_path_traversal_manifest_entry():
    with pytest.raises(ValueError, match="bundle path '../secret.py' is not safe"):
        runner._verify_manifest_file_entry(
            {"path": "../secret.py", "size": 0, "sha256": "0" * 64},
            path_key="path",
            label="artifacts[0]",
        )


def test_build_runner_rejects_missing_schema_version():
    with pytest.raises(
        ValueError,
        match="manifest.json: missing schemaVersion; expected 1",
    ):
        runner._verify_schema_version({}, "manifest.json")


def test_build_runner_detects_manifest_file_sha_mismatch(tmp_path, monkeypatch):
    artifact = tmp_path / "otoe-plan.json"
    artifact.write_text("plan", encoding="utf-8")
    monkeypatch.setattr(runner, "ROOT", tmp_path)

    with pytest.raises(ValueError, match="otoe-plan.json: sha256 mismatch"):
        runner._verify_manifest_file(
            {
                "path": "otoe-plan.json",
                "size": artifact.stat().st_size,
                "sha256": "0" * 64,
            },
            path_key="path",
            label="artifacts[0]",
        )


def test_build_runner_requires_manifest_artifact_references():
    manifest = {
        "plan": "otoe-plan.json",
        "deps": "otoe-deps.json",
        "styles": "otoe-styles.json",
        "renderTree": "otoe-render-tree.json",
        "artifacts": [{"path": "otoe-plan.json"}],
    }

    with pytest.raises(
        ValueError,
        match="manifest.json: artifacts missing 'otoe-deps.json'",
    ):
        runner._verify_manifest_artifact_references(manifest)


def test_build_runner_accepts_minimal_manifest_contract():
    runner._verify_manifest_contract(_runner_manifest())


def test_build_runner_manifest_contract_rejects_duplicate_bundle_paths():
    manifest = _runner_manifest()
    manifest["artifacts"].append(
        {"path": "otoe-run.py", "size": 1, "sha256": "0" * 64}
    )

    with pytest.raises(
        ValueError,
        match="duplicate bundle path 'otoe-run.py'",
    ):
        runner._verify_manifest_contract(manifest)


def test_bundle_backend_package_rejects_unsafe_descriptor_path(tmp_path):
    manifest = {"backendPackage": {"path": "../backend-package.json"}}

    with pytest.raises(
        ValueError,
        match="bundle path '../backend-package.json' is not safe",
    ):
        verify_backend_package(manifest, root=tmp_path)


def test_bundle_backend_package_allows_missing_package_section(tmp_path):
    verify_backend_package({}, root=tmp_path)


def test_bundle_backend_package_rejects_non_object_package_section(tmp_path):
    with pytest.raises(
        ValueError,
        match="manifest.json: backendPackage must be an object",
    ):
        verify_backend_package({"backendPackage": []}, root=tmp_path)


def test_bundle_backend_package_rejects_missing_descriptor_file(tmp_path):
    manifest = {"backendPackage": {"path": "backend/path0/backend-package.json"}}

    with pytest.raises(
        FileNotFoundError,
        match="bundle file 'backend/path0/backend-package.json' does not exist",
    ):
        verify_backend_package(manifest, root=tmp_path)


def test_bundle_backend_package_rejects_descriptor_schema_mismatch(tmp_path):
    descriptor = tmp_path / "backend/path0/backend-package.json"
    descriptor.parent.mkdir(parents=True)
    _write_json(descriptor, {"schemaVersion": 2, "format": "backend-package"})

    with pytest.raises(
        ValueError,
        match="unsupported schemaVersion 2; expected 1",
    ):
        verify_backend_package(
            {"backendPackage": {"path": "backend/path0/backend-package.json"}},
            root=tmp_path,
        )


def test_bundle_backend_package_rejects_invalid_descriptor_payload(tmp_path):
    descriptor = tmp_path / "backend/path0/backend-package.json"
    descriptor.parent.mkdir(parents=True)
    _write_json(
        descriptor,
        {
            "schemaVersion": 1,
            "format": "not-a-backend-package",
            "files": [],
        },
    )

    with pytest.raises(
        ValueError,
        match="backend package format must be 'backend-package'",
    ):
        verify_backend_package(
            {"backendPackage": {"path": "backend/path0/backend-package.json"}},
            root=tmp_path,
        )


def test_bundle_backend_package_rejects_manifest_descriptor_metadata_drift(tmp_path):
    manifest = _write_backend_package_bundle(tmp_path)
    manifest["backendPackage"]["label"] = "Wrong Label"

    with pytest.raises(
        ValueError,
        match="manifest.json.backendPackage.label must match",
    ):
        verify_backend_package(manifest, root=tmp_path)


def test_bundle_backend_package_requires_file_artifact_entry(tmp_path):
    manifest = _write_backend_package_bundle(tmp_path)
    manifest["artifacts"] = [{"path": manifest["backendPackage"]["path"]}]

    with pytest.raises(
        ValueError,
        match="manifest.json: artifacts missing 'backend/path0/runner.py'",
    ):
        verify_backend_package(manifest, root=tmp_path)


def test_bundle_backend_package_rejects_missing_declared_file(tmp_path):
    manifest = _write_backend_package_bundle(tmp_path)
    (tmp_path / "backend/path0/runner.py").unlink()

    with pytest.raises(
        FileNotFoundError,
        match="bundle file 'backend/path0/runner.py' does not exist",
    ):
        verify_backend_package(manifest, root=tmp_path)


def test_bundle_backend_package_detects_descriptor_file_hash_mismatch(tmp_path):
    manifest = _write_backend_package_bundle(tmp_path, descriptor_file_sha="0" * 64)

    with pytest.raises(
        ValueError,
        match="backend/path0/backend-package.json: file "
        "'backend/path0/runner.py' sha256 mismatch",
    ):
        verify_backend_package(manifest, root=tmp_path)


def test_bundle_backend_package_report_rejects_style_hash_drift(tmp_path):
    manifest = _write_backend_package_report_bundle(tmp_path)
    report_path = tmp_path / manifest["externalBackendReport"]
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["input"]["styleOps"]["artifactHash"] = _sha_uri("wrong-styles")
    _write_json(report_path, report)

    with pytest.raises(
        ValueError,
        match="backend package report style artifact hash mismatch",
    ):
        verify_backend_package_report(manifest, root=tmp_path)


def _backend_coverage_payload() -> dict:
    return {
        "format": "backend-coverage-report",
        "passed": True,
        "backend": "native-python",
        "readiness": {
            "candidate": {"backend": "native-python"},
            "candidateScope": {"level": "path0"},
        },
        "trace": {
            "candidateScope": {"level": "path0"},
            "path0": {
                "renderTreeHash": _sha_uri("render-tree"),
                "layoutOutputHash": _sha_uri("layout"),
                "paintOutputHash": _sha_uri("paint"),
                "semanticValidation": {"passed": True, "errors": []},
            },
        },
        "coverage": {
            section: _empty_coverage_section()
            for section in (
                "rendererBoundaries",
                "widgets",
                "inputs",
                "styles",
                "declaredStyleOmissions",
            )
        },
    }


def _empty_coverage_section() -> dict:
    return {
        "required": [],
        "exercised": [],
        "declared": [],
        "covered": [],
        "missing": [],
        "unevidenced": [],
        "extra": [],
        "summary": {
            "required": 0,
            "exercised": 0,
            "declared": 0,
            "covered": 0,
            "missing": 0,
            "unevidenced": 0,
            "extra": 0,
            "unproven": 0,
        },
        "evidence": {"unproven": []},
        "evidenceMap": {},
    }


def _covered_section(name: str, source: dict) -> dict:
    return {
        "required": [name],
        "exercised": [name],
        "declared": [name],
        "covered": [name],
        "missing": [],
        "unevidenced": [],
        "extra": [],
        "summary": {
            "required": 1,
            "exercised": 1,
            "declared": 1,
            "covered": 1,
            "missing": 0,
            "unevidenced": 0,
            "extra": 0,
            "unproven": 0,
        },
        "evidence": {"unproven": []},
        "evidenceMap": {
            name: {
                "required": True,
                "declared": True,
                "exercised": True,
                "covered": True,
                "missing": False,
                "unevidenced": False,
                "unproven": False,
                "sources": [source],
            }
        },
    }


def _runner_manifest() -> dict:
    artifact_paths = (
        "otoe-plan.json",
        "otoe-deps.json",
        "otoe-styles.json",
        "otoe-render-tree.json",
    )
    return {
        "schemaVersion": 1,
        "target": "app:app",
        "profile": "cage",
        "backend": "native",
        "backendCapability": "native-python",
        "plan": "otoe-plan.json",
        "deps": "otoe-deps.json",
        "styles": "otoe-styles.json",
        "renderTree": "otoe-render-tree.json",
        "runtimeInstallsAllowed": False,
        "status": "ok",
        "runner": {"path": "otoe-run.py", "size": 1, "sha256": "0" * 64},
        "artifacts": [
            {"path": path, "size": 1, "sha256": "0" * 64}
            for path in artifact_paths
        ],
        "assets": [],
        "frameworkFiles": [],
        "runtimeFiles": [],
    }


def _write_backend_package_bundle(
    root: Path,
    *,
    descriptor_file_sha: str | None = None,
) -> dict:
    package_root = root / "backend/path0"
    package_root.mkdir(parents=True)
    runner_path = package_root / "runner.py"
    runner_path.write_text("print('ok')\n", encoding="utf-8")
    runner_data = runner_path.read_bytes()
    file_sha = descriptor_file_sha or hashlib.sha256(runner_data).hexdigest()
    descriptor = {
        "schemaVersion": 1,
        "format": "backend-package",
        "name": "path0",
        "label": "Path0",
        "kind": "path0-external-json",
        "entrypoint": "runner.py",
        "contracts": {
            "inputs": ["otoe-render-tree"],
            "outputs": ["path0-layout-output", "path0-paint-output"],
        },
        "runtime": {
            "language": "python",
            "runtimeInstallsAllowed": False,
        },
        "files": [
            {
                "path": "runner.py",
                "role": "runner",
                "size": len(runner_data),
                "sha256": file_sha,
            }
        ],
    }
    descriptor["packageHash"] = package_hash(descriptor)
    _write_json(package_root / "backend-package.json", descriptor)
    package_hash_value = descriptor["packageHash"]
    return {
        "backendPackage": {
            "name": "path0",
            "label": "Path0",
            "kind": "path0-external-json",
            "path": "backend/path0/backend-package.json",
            "root": "backend/path0",
            "entrypoint": "backend/path0/runner.py",
            "packageHash": package_hash_value,
            "files": ["backend/path0/runner.py"],
        },
        "artifacts": [
            {"path": "backend/path0/backend-package.json"},
            {"path": "backend/path0/runner.py"},
        ],
    }


def _write_backend_package_report_bundle(root: Path) -> dict:
    manifest = _write_backend_package_bundle(root)
    render_tree = {
        "schemaVersion": 1,
        "format": "otoe-render-tree",
        "nodeCount": 1,
    }
    styles = {
        "schemaVersion": 1,
        "format": "otoe-style-artifact",
        "styleOps": {"classes": []},
    }
    layout = {
        "format": "path0-layout-output",
        "boxCount": 1,
    }
    layout["outputHash"] = _contract_hash(layout)
    paint = {
        "format": "path0-paint-output",
        "commandCount": 1,
    }
    paint["outputHash"] = _contract_hash(paint)
    report = {
        "schemaVersion": 1,
        "format": "path0-external-backend-report",
        "backend": "path0",
        "source": "bundle:otoe-render-tree.json",
        "input": {
            "renderTreeHash": _contract_hash(render_tree),
            "nodeCount": 1,
            "styleOps": {
                "present": True,
                "artifactHash": _contract_hash(styles),
            },
        },
        "output": {
            "layout": layout,
            "paint": paint,
        },
    }
    _write_json(root / "otoe-render-tree.json", render_tree)
    _write_json(root / "otoe-styles.json", styles)
    _write_json(root / "otoe-path0-external-backend.json", report)
    manifest.update(
        {
            "renderTree": "otoe-render-tree.json",
            "styles": "otoe-styles.json",
            "externalBackendReport": "otoe-path0-external-backend.json",
        }
    )
    return manifest


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=True, sort_keys=True),
        encoding="utf-8",
    )


def _contract_hash(payload: dict) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


def _sha_uri(label: str) -> str:
    return f"sha256:{hashlib.sha256(label.encode('utf-8')).hexdigest()}"
