from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
MANIFEST_PATH = ROOT / "manifest.json"
EXPECTED_SCHEMA_VERSION = 1
EXPECTED_FRAMEWORK_FILES = "__OTOE_EXPECTED_FRAMEWORK_FILES__"
CACHE_DIR_NAMES = frozenset({"__pycache__", ".pytest_cache"})
CACHE_SUFFIXES = (".pyc", ".pyo")
PACK_TOP_LEVEL_FILES = frozenset(
    {
        "manifest.json",
        "otoe-backend-coverage.json",
        "otoe-plan.json",
        "otoe-deps.json",
        "otoe-styles.json",
        "otoe-run.py",
    }
)
PACK_DIRECTORIES = frozenset({"app", "assets", "framework"})


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="otoe-run")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="load the bundled target")
    mode.add_argument(
        "--layout-check",
        action="store_true",
        help="layout and paint the bundled target without writing output",
    )
    mode.add_argument("--png", help="render one native PNG frame")
    mode.add_argument("--verify", action="store_true", help="verify bundled files")
    parser.add_argument("--background", default="#ffffff", help="PNG background")
    args = parser.parse_args(argv)

    manifest = _load_manifest()
    _verify_manifest_contract(manifest)
    _verify_framework_policy(manifest)
    _install_pythonpath()
    _verify_artifact_schemas(manifest)
    if args.verify:
        _verify_bundle(manifest)
        print("verified: manifest.json")
        return 0

    mounted = _coerce_target(_load_target(manifest["target"]))
    if args.layout_check:
        from otoe import layout_native, paint_native

        stylesheet = _load_stylesheet(manifest)
        layout = layout_native(mounted, stylesheet=stylesheet)
        paint_native(layout, background=args.background)
        print(f"layout checked: {manifest['target']}")
        return 0

    if args.png:
        from otoe import render_native_png

        output = Path(args.png)
        output.parent.mkdir(parents=True, exist_ok=True)
        stylesheet = _load_stylesheet(manifest)
        render_native_png(
            mounted,
            output,
            stylesheet=stylesheet,
            background=args.background,
        )
        print(f"png: {output}")
        return 0

    print(f"loaded: {manifest['target']}")
    return 0


def _install_pythonpath() -> None:
    for relative in reversed(("app", "framework")):
        sys.path.insert(0, str(ROOT / relative))


def _load_manifest() -> dict[str, Any]:
    payload = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    _verify_schema_version(payload, "manifest.json")
    return payload


def _verify_manifest_contract(manifest: dict[str, Any]) -> None:
    for key in (
        "target",
        "profile",
        "backend",
        "backendCapability",
        "plan",
        "deps",
        "styles",
    ):
        _require_manifest_string(manifest, key)
    if manifest.get("runtimeInstallsAllowed") is not False:
        raise ValueError("manifest.json: runtimeInstallsAllowed must be false")
    status = manifest.get("status")
    if status not in {"ok", "warnings"}:
        raise ValueError("manifest.json: status must be 'ok' or 'warnings'")
    if not isinstance(manifest.get("artifacts"), list):
        raise ValueError("manifest.json: artifacts must be a list")
    if not isinstance(manifest.get("runner"), dict):
        raise ValueError("manifest.json: runner must be an object")
    for group in ("assets", "frameworkFiles", "runtimeFiles"):
        if not isinstance(manifest.get(group), list):
            raise ValueError(f"manifest.json: {group} must be a list")
    _verify_manifest_file_entry_contracts(manifest)
    _verify_manifest_artifact_references(manifest)


def _require_manifest_string(manifest: dict[str, Any], key: str) -> str:
    value = manifest.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"manifest.json: {key} must be a non-empty string")
    return value


def _load_stylesheet(manifest: dict[str, Any]):
    styles_path = manifest.get("styles")
    if not styles_path:
        return None
    from otoe.style import stylesheet_from_style_ops_artifact

    payload = _load_json_bundle_file(styles_path, style_artifact=True)
    return stylesheet_from_style_ops_artifact(payload)


def _verify_bundle(manifest: dict[str, Any]) -> None:
    _verify_artifact_schemas(manifest)
    _verify_framework_policy(manifest)
    for key in ("plan", "deps", "styles"):
        _require_bundle_file(manifest[key])
    for index, artifact in enumerate(manifest.get("artifacts", [])):
        _verify_manifest_file(
            artifact,
            path_key="path",
            label=f"artifacts[{index}]",
        )
    runner = manifest.get("runner")
    _verify_manifest_file(runner, path_key="path", label="runner")
    for group in ("assets", "frameworkFiles", "runtimeFiles"):
        for index, entry in enumerate(manifest.get(group, [])):
            _verify_manifest_file(
                entry,
                path_key="bundlePath",
                label=f"{group}[{index}]",
            )
    _reject_unmanifested_bundle_files(manifest)


def _verify_manifest_file_entry_contracts(manifest: dict[str, Any]) -> None:
    for key in ("plan", "deps", "styles"):
        _bundle_path(_require_manifest_string(manifest, key))
    if "backendCoverage" in manifest:
        backend_coverage = manifest.get("backendCoverage")
        if not isinstance(backend_coverage, str) or not backend_coverage:
            raise ValueError("manifest.json: backendCoverage must be a non-empty string")
        _bundle_path(backend_coverage)

    declared: dict[str, str] = {}
    runner = manifest.get("runner")
    runner_path = _verify_manifest_file_entry(
        runner,
        path_key="path",
        label="runner",
    )
    _record_manifest_bundle_path(declared, runner_path, "runner.path")
    for index, artifact in enumerate(manifest.get("artifacts", [])):
        relative = _verify_manifest_file_entry(
            artifact,
            path_key="path",
            label=f"artifacts[{index}]",
        )
        _record_manifest_bundle_path(
            declared,
            relative,
            f"artifacts[{index}].path",
        )
    for group in ("assets", "frameworkFiles", "runtimeFiles"):
        for index, entry in enumerate(manifest.get(group, [])):
            relative = _verify_manifest_file_entry(
                entry,
                path_key="bundlePath",
                label=f"{group}[{index}]",
            )
            _record_manifest_bundle_path(
                declared,
                relative,
                f"{group}[{index}].bundlePath",
            )


def _record_manifest_bundle_path(
    declared: dict[str, str],
    relative: str,
    label: str,
) -> None:
    previous = declared.get(relative)
    if previous is not None:
        raise ValueError(
            "manifest.json: duplicate bundle path "
            f"{relative!r} in {label}; already declared by {previous}"
        )
    declared[relative] = label


def _verify_manifest_artifact_references(manifest: dict[str, Any]) -> None:
    for key in ("plan", "deps", "styles"):
        _require_artifact_entry(manifest, manifest[key])
    if "backendCoverage" in manifest:
        _require_artifact_entry(manifest, manifest["backendCoverage"])


def _reject_unmanifested_bundle_files(manifest: dict[str, Any]) -> None:
    allowed = _manifest_pack_paths(manifest)
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        relative_path = path.relative_to(ROOT)
        if not _is_pack_path(relative_path):
            continue
        if _is_cache_path(relative_path):
            continue
        relative = relative_path.as_posix()
        if relative not in allowed:
            raise ValueError(f"unmanifested bundle file {relative!r}")


def _manifest_pack_paths(manifest: dict[str, Any]) -> set[str]:
    paths = {"manifest.json"}
    for key in ("plan", "deps", "styles", "backendCoverage"):
        value = manifest.get(key)
        if isinstance(value, str):
            paths.add(value)
    runner = manifest.get("runner")
    if isinstance(runner, dict):
        value = runner.get("path")
        if isinstance(value, str):
            paths.add(value)
    for artifact in manifest.get("artifacts", []):
        if isinstance(artifact, dict):
            value = artifact.get("path")
            if isinstance(value, str):
                paths.add(value)
    for group in ("assets", "frameworkFiles", "runtimeFiles"):
        for entry in manifest.get(group, []):
            if isinstance(entry, dict):
                value = entry.get("bundlePath")
                if isinstance(value, str):
                    paths.add(value)
    return paths


def _is_pack_path(relative: Path) -> bool:
    if len(relative.parts) == 1:
        return relative.name in PACK_TOP_LEVEL_FILES
    return relative.parts[0] in PACK_DIRECTORIES


def _is_cache_path(relative: Path) -> bool:
    if any(part in CACHE_DIR_NAMES for part in relative.parts):
        return True
    return relative.suffix in CACHE_SUFFIXES


def _verify_framework_policy(manifest: dict[str, Any]) -> None:
    backend = manifest.get("backend")
    if not backend:
        raise ValueError("manifest.json: missing backend")
    expected_files = EXPECTED_FRAMEWORK_FILES.get(backend)
    if expected_files is None:
        supported = ", ".join(sorted(EXPECTED_FRAMEWORK_FILES))
        raise ValueError(
            f"manifest.json: unsupported backend {backend!r}; supported: {supported}"
        )

    framework_files = manifest.get("frameworkFiles")
    if not isinstance(framework_files, list):
        raise ValueError("manifest.json: frameworkFiles must be a list")
    listed_files = {
        entry.get("bundlePath")
        for entry in framework_files
        if isinstance(entry, dict)
    }
    for expected in expected_files:
        if expected not in listed_files:
            raise ValueError(
                "manifest.json: frameworkFiles missing required file "
                f"{expected!r} for backend {backend!r}"
            )
        _require_bundle_file(expected)


def _verify_artifact_schemas(manifest: dict[str, Any]) -> None:
    plan = _load_json_bundle_file(manifest["plan"])
    if plan.get("hasErrors") is not False or plan.get("status") == "invalid":
        raise ValueError(f"{manifest['plan']}: plan has errors")
    deps = _load_json_bundle_file(manifest["deps"])
    if deps.get("hasErrors") is not False or deps.get("status") == "invalid":
        raise ValueError(f"{manifest['deps']}: dependency audit has errors")
    _verify_dependency_audit_contract(deps, manifest["deps"])
    styles = _load_json_bundle_file(manifest["styles"], style_artifact=True)
    if styles.get("status") == "invalid":
        raise ValueError(f"{manifest['styles']}: style artifact is invalid")
    backend_coverage = manifest.get("backendCoverage")
    if backend_coverage is not None:
        _verify_backend_coverage(backend_coverage)


def _verify_dependency_audit_contract(payload: dict[str, Any], label: str) -> None:
    if payload.get("runtimeInstallsAllowed") is not False:
        raise ValueError(f"{label}: runtimeInstallsAllowed must be false")
    resolution = payload.get("resolution")
    if not isinstance(resolution, dict):
        raise ValueError(f"{label}: resolution must be an object")
    if resolution.get("mode") != "audit-only":
        raise ValueError(f"{label}: resolution.mode must be 'audit-only'")
    if resolution.get("lockfile") is not False:
        raise ValueError(f"{label}: resolution.lockfile must be false")
    if resolution.get("wheelClosure") is not False:
        raise ValueError(f"{label}: resolution.wheelClosure must be false")
    if resolution.get("runtimeInstallsAllowed") is not False:
        raise ValueError(
            f"{label}: resolution.runtimeInstallsAllowed must be false"
        )


def _verify_backend_coverage(relative: Any) -> None:
    if not isinstance(relative, str):
        raise ValueError("manifest.json: backendCoverage must be a string")
    payload = _load_json_bundle_file(relative)
    if payload.get("format") != "backend-coverage-report":
        raise ValueError(f"{relative}: format must be 'backend-coverage-report'")
    if payload.get("passed") is not True:
        blockers = payload.get("blockers", [])
        if isinstance(blockers, list) and blockers:
            details = ", ".join(str(blocker) for blocker in blockers)
        else:
            details = "backend coverage failed"
        raise ValueError(f"{relative}: backend coverage failed: {details}")
    _verify_backend_coverage_traceability(payload, relative)


def _verify_backend_coverage_traceability(
    payload: dict[str, Any],
    label: str,
) -> None:
    _verify_backend_coverage_identity(payload, label)
    coverage_trace = _verify_backend_coverage_trace_contract(payload, label)
    coverage = payload.get("coverage")
    if not isinstance(coverage, dict):
        raise ValueError(f"{label}: coverage must be an object")
    for section in (
        "rendererBoundaries",
        "widgets",
        "inputs",
        "styles",
        "declaredStyleOmissions",
    ):
        _verify_backend_coverage_section_traceability(
            coverage.get(section),
            label=label,
            section=section,
            requires_runtime=section in {"styles", "declaredStyleOmissions"},
            requires_boundary=section == "rendererBoundaries",
            capability_observed_key={
                "widgets": "observedWidgets",
                "inputs": "observedCapabilities",
            }.get(section),
            coverage_trace=coverage_trace,
        )


def _verify_backend_coverage_section_traceability(
    section_payload: Any,
    *,
    label: str,
    section: str,
    requires_runtime: bool,
    requires_boundary: bool,
    capability_observed_key: str | None,
    coverage_trace: dict[str, str],
) -> None:
    prefix = f"{label}: coverage.{section}"
    if not isinstance(section_payload, dict):
        raise ValueError(f"{prefix} must be an object")
    names = {
        key: _coverage_string_set(
            section_payload.get(key),
            f"{prefix}.{key}",
        )
        for key in (
            "required",
            "exercised",
            "declared",
            "covered",
            "missing",
            "unevidenced",
            "extra",
        )
    }
    evidence = section_payload.get("evidence")
    if not isinstance(evidence, dict):
        raise ValueError(f"{prefix}.evidence must be an object")
    names["unproven"] = _coverage_string_set(
        evidence.get("unproven"),
        f"{prefix}.evidence.unproven",
    )
    expected = {
        "covered": names["required"] & names["declared"] & names["exercised"],
        "missing": names["required"] - names["declared"],
        "unevidenced": names["required"] - names["exercised"],
        "extra": names["declared"] - names["required"],
        "unproven": names["declared"] - names["exercised"],
    }
    for key, expected_names in expected.items():
        if names[key] != expected_names:
            raise ValueError(
                f"{prefix}.{key} inconsistent with required/declared/exercised"
            )
    _verify_backend_coverage_summary(
        section_payload,
        label=label,
        section=section,
        counts={key: len(value) for key, value in names.items()},
    )
    evidence_map = section_payload.get("evidenceMap")
    if not isinstance(evidence_map, dict):
        raise ValueError(f"{prefix}.evidenceMap must be an object")
    expected_map_names = names["required"] | names["declared"] | names["exercised"]
    actual_map_names = set(evidence_map)
    if actual_map_names != expected_map_names:
        missing = sorted(expected_map_names - actual_map_names)
        extra = sorted(actual_map_names - expected_map_names)
        details = []
        if missing:
            details.append(f"missing {', '.join(missing)}")
        if extra:
            details.append(f"extra {', '.join(extra)}")
        raise ValueError(
            f"{prefix}.evidenceMap keys mismatch: {'; '.join(details)}"
        )
    for name in sorted(expected_map_names):
        entry = evidence_map[name]
        entry_prefix = f"{prefix}.evidenceMap.{name}"
        _verify_backend_coverage_map_entry(
            entry,
            label=entry_prefix,
            name=name,
            expected_flags={
                "required": name in names["required"],
                "declared": name in names["declared"],
                "exercised": name in names["exercised"],
                "covered": name in names["covered"],
                "missing": name in names["missing"],
                "unevidenced": name in names["unevidenced"],
                "unproven": name in names["unproven"],
            },
            requires_runtime=requires_runtime,
            requires_boundary=requires_boundary,
            capability_observed_key=capability_observed_key,
            coverage_trace=coverage_trace,
        )


def _verify_backend_coverage_identity(payload: dict[str, Any], label: str) -> None:
    backend = payload.get("backend")
    if not isinstance(backend, str) or not backend:
        raise ValueError(f"{label}: backend must be a non-empty string")
    readiness = payload.get("readiness")
    if not isinstance(readiness, dict):
        raise ValueError(f"{label}: readiness must be an object")
    candidate = readiness.get("candidate")
    if not isinstance(candidate, dict):
        raise ValueError(f"{label}: readiness.candidate must be an object")
    candidate_backend = candidate.get("backend")
    if not isinstance(candidate_backend, str) or not candidate_backend:
        raise ValueError(
            f"{label}: readiness.candidate.backend must be a non-empty string"
        )
    if candidate_backend != backend:
        raise ValueError(
            f"{label}: backend must match readiness.candidate.backend"
        )


def _verify_backend_coverage_trace_contract(
    payload: dict[str, Any],
    label: str,
) -> dict[str, str]:
    trace = payload.get("trace")
    if not isinstance(trace, dict):
        raise ValueError(f"{label}: trace must be an object")
    candidate_scope = trace.get("candidateScope")
    if not isinstance(candidate_scope, dict):
        raise ValueError(f"{label}: trace.candidateScope must be an object")
    level = candidate_scope.get("level")
    if not isinstance(level, str) or not level:
        raise ValueError(
            f"{label}: trace.candidateScope.level must be a non-empty string"
        )
    readiness = payload.get("readiness")
    if not isinstance(readiness, dict):
        raise ValueError(f"{label}: readiness must be an object")
    readiness_candidate_scope = readiness.get("candidateScope")
    if not isinstance(readiness_candidate_scope, dict):
        raise ValueError(f"{label}: readiness.candidateScope must be an object")
    if level != readiness_candidate_scope.get("level"):
        raise ValueError(
            f"{label}: trace.candidateScope.level must match "
            "readiness.candidateScope.level"
        )
    path0 = trace.get("path0")
    if not isinstance(path0, dict):
        raise ValueError(f"{label}: trace.path0 must be an object")
    result = {"candidateScopeLevel": level}
    for key in ("renderTreeHash", "layoutOutputHash", "paintOutputHash"):
        value = path0.get(key)
        if not _is_sha256_uri(value):
            raise ValueError(f"{label}: trace.path0.{key} must be a sha256 string")
        result[key] = value
    semantic_validation = path0.get("semanticValidation")
    if not isinstance(semantic_validation, dict):
        raise ValueError(f"{label}: trace.path0.semanticValidation must be an object")
    if semantic_validation.get("passed") is not True:
        raise ValueError(f"{label}: trace.path0.semanticValidation.passed must be true")
    errors = semantic_validation.get("errors")
    if errors != []:
        raise ValueError(f"{label}: trace.path0.semanticValidation.errors must be []")
    return result


def _coverage_string_set(value: Any, label: str) -> set[str]:
    if not isinstance(value, list) or not all(
        isinstance(item, str) and item for item in value
    ):
        raise ValueError(f"{label} must be a list of non-empty strings")
    if len(set(value)) != len(value):
        raise ValueError(f"{label} must not contain duplicate names")
    return set(value)


def _verify_backend_coverage_summary(
    section_payload: dict[str, Any],
    *,
    label: str,
    section: str,
    counts: dict[str, int],
) -> None:
    summary = section_payload.get("summary")
    if not isinstance(summary, dict):
        raise ValueError(f"{label}: coverage.{section}.summary must be an object")
    for key, count in counts.items():
        if summary.get(key) != count:
            raise ValueError(
                f"{label}: coverage.{section}.summary.{key} must be {count}"
            )


def _verify_backend_coverage_map_entry(
    entry: Any,
    *,
    label: str,
    name: str,
    expected_flags: dict[str, bool],
    requires_runtime: bool,
    requires_boundary: bool,
    capability_observed_key: str | None,
    coverage_trace: dict[str, str],
) -> None:
    if not isinstance(entry, dict):
        raise ValueError(f"{label} must be an object")
    for key, expected in expected_flags.items():
        if entry.get(key) is not expected:
            raise ValueError(f"{label}.{key} must be {expected}")
    sources = entry.get("sources")
    if not isinstance(sources, list):
        raise ValueError(f"{label}.sources must be a list")
    if expected_flags["exercised"] and not sources:
        raise ValueError(f"{label}.sources must not be empty for exercised coverage")
    for index, source in enumerate(sources):
        _verify_backend_coverage_source_ref(
            source,
            label=f"{label}.sources[{index}]",
            requires_runtime=requires_runtime,
            boundary_name=name if requires_boundary else None,
            capability_name=name if capability_observed_key is not None else None,
            capability_observed_key=capability_observed_key,
            coverage_trace=coverage_trace,
        )


def _verify_backend_coverage_source_ref(
    source: Any,
    *,
    label: str,
    requires_runtime: bool,
    boundary_name: str | None,
    capability_name: str | None,
    capability_observed_key: str | None,
    coverage_trace: dict[str, str],
) -> None:
    if not isinstance(source, dict):
        raise ValueError(f"{label} must be an object")
    group_index = source.get("groupIndex")
    if type(group_index) is not int or group_index < 0:
        raise ValueError(f"{label}.groupIndex must be a non-negative integer")
    _require_non_empty_string(source, "source", label)
    _require_non_empty_string(source, "gate", label)
    count = source.get("count")
    if count is not None and not _positive_number(count):
        raise ValueError(f"{label}.count must be a positive number")
    if requires_runtime:
        _verify_runtime_proof(source.get("runtimeProof"), f"{label}.runtimeProof")
    if boundary_name is not None:
        _verify_boundary_proof(
            source.get("boundaryProof"),
            f"{label}.boundaryProof",
            boundary_name=boundary_name,
            coverage_trace=coverage_trace,
        )
    if capability_name is not None and capability_observed_key is not None:
        _verify_capability_proof(
            source.get("capabilityProof"),
            f"{label}.capabilityProof",
            capability_name=capability_name,
            observed_key=capability_observed_key,
            expected_source=source.get("source"),
        )


def _verify_boundary_proof(
    proof: Any,
    label: str,
    *,
    boundary_name: str,
    coverage_trace: dict[str, str],
) -> None:
    if not isinstance(proof, dict):
        raise ValueError(f"{label} must be an object")
    _require_non_empty_string(proof, "phase", label)
    _require_non_empty_string(proof, "source", label)
    value = proof.get("outputHash")
    if not _is_sha256_uri(value):
        raise ValueError(f"{label}.outputHash must be a sha256 string")
    if boundary_name == "renderTreeLayout":
        if value != coverage_trace["layoutOutputHash"]:
            raise ValueError(
                f"{label}.outputHash must match trace.path0.layoutOutputHash"
            )
        value = proof.get("renderTreeHash")
        if not _is_sha256_uri(value):
            raise ValueError(f"{label}.renderTreeHash must be a sha256 string")
        if value != coverage_trace["renderTreeHash"]:
            raise ValueError(
                f"{label}.renderTreeHash must match trace.path0.renderTreeHash"
            )
        if proof.get("phase") != "layout":
            raise ValueError(f"{label}.phase must be 'layout'")
        if proof.get("boundary") != "renderTree":
            raise ValueError(f"{label}.boundary must be 'renderTree'")
        if not _positive_number(proof.get("layoutBoxes")):
            raise ValueError(f"{label}.layoutBoxes must be a positive number")
    elif boundary_name == "paint":
        if value != coverage_trace["paintOutputHash"]:
            raise ValueError(
                f"{label}.outputHash must match trace.path0.paintOutputHash"
            )
        if proof.get("phase") != "paint":
            raise ValueError(f"{label}.phase must be 'paint'")
        if not _positive_number(proof.get("paintCommands")):
            raise ValueError(f"{label}.paintCommands must be a positive number")
    else:
        raise ValueError(f"{label}: unsupported renderer boundary {boundary_name!r}")


def _verify_capability_proof(
    proof: Any,
    label: str,
    *,
    capability_name: str,
    observed_key: str,
    expected_source: Any,
) -> None:
    if not isinstance(proof, dict):
        raise ValueError(f"{label} must be an object")
    _require_non_empty_string(proof, "source", label)
    if isinstance(expected_source, str) and proof.get("source") != expected_source:
        raise ValueError(f"{label}.source must match source.source")
    value = proof.get("auditHash")
    if not _is_sha256_uri(value):
        raise ValueError(f"{label}.auditHash must be a sha256 string")
    if not _positive_number(proof.get("itemCount")):
        raise ValueError(f"{label}.itemCount must be a positive number")
    observed = _coverage_string_set(proof.get(observed_key), f"{label}.{observed_key}")
    if capability_name not in observed:
        raise ValueError(
            f"{label}.{observed_key} must include {capability_name!r}"
        )


def _verify_runtime_proof(proof: Any, label: str) -> None:
    if not isinstance(proof, dict):
        raise ValueError(f"{label} must be an object")
    _require_non_empty_string(proof, "source", label)
    _require_non_empty_string(proof, "rendererBackend", label)
    if proof.get("styleOpsPresent") is not True:
        raise ValueError(f"{label}.styleOpsPresent must be true")
    if proof.get("styleOpsMatchesRenderTree") is not True:
        raise ValueError(f"{label}.styleOpsMatchesRenderTree must be true")
    for key in ("styledNodes", "layoutBoxes", "paintCommands"):
        if not _positive_number(proof.get(key)):
            raise ValueError(f"{label}.{key} must be a positive number")
    phases = proof.get("phases")
    if not isinstance(phases, list) or not phases or not all(
        phase in {"layout", "paint"} for phase in phases
    ):
        raise ValueError(f"{label}.phases must include layout/paint phase names")
    for phase in phases:
        count_key = f"{phase}ObservationCount"
        hash_key = f"{phase}ObservationHash"
        if not _positive_number(proof.get(count_key)):
            raise ValueError(f"{label}.{count_key} must be a positive number")
        value = proof.get(hash_key)
        if not _is_sha256_uri(value):
            raise ValueError(f"{label}.{hash_key} must be a sha256 string")


def _is_sha256_uri(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    prefix = "sha256:"
    if len(value) != len(prefix) + 64 or not value.startswith(prefix):
        return False
    digest = value[len(prefix) :]
    return all(char in "0123456789abcdef" for char in digest)


def _require_non_empty_string(payload: dict[str, Any], key: str, label: str) -> None:
    if not isinstance(payload.get(key), str) or not payload.get(key):
        raise ValueError(f"{label}.{key} must be a non-empty string")


def _positive_number(value: Any) -> bool:
    return type(value) in {int, float} and value > 0


def _load_json_bundle_file(
    relative: str,
    *,
    style_artifact: bool = False,
) -> dict[str, Any]:
    payload = json.loads(_require_bundle_file(relative).read_text(encoding="utf-8"))
    _verify_schema_version(payload, relative)
    if style_artifact:
        _verify_style_ops_schema(payload, relative)
    return payload


def _verify_style_ops_schema(payload: dict[str, Any], label: str) -> None:
    from otoe.style_ops import StyleIRError, load_style_ir, validate_style_ops

    try:
        validation = validate_style_ops(load_style_ir(payload))
    except StyleIRError as exc:
        details = str(exc)
        if details.startswith("styleOps:"):
            raise ValueError(f"{label} {details}") from exc
        raise ValueError(f"{label}: {details}") from exc
    if validation.passed:
        return
    details = "; ".join(validation.errors) or "styleOps drift detected"
    raise ValueError(f"{label}: styleOps validation failed: {details}")


def _verify_schema_version(payload: Any, label: str) -> None:
    if not isinstance(payload, dict):
        raise ValueError(f"{label}: expected JSON object")
    if "schemaVersion" not in payload:
        raise ValueError(
            f"{label}: missing schemaVersion; expected {EXPECTED_SCHEMA_VERSION}"
        )
    version = payload["schemaVersion"]
    if version != EXPECTED_SCHEMA_VERSION:
        raise ValueError(
            f"{label}: unsupported schemaVersion {version!r}; "
            f"expected {EXPECTED_SCHEMA_VERSION}"
        )


def _verify_manifest_file(entry: Any, *, path_key: str, label: str) -> None:
    relative = _verify_manifest_file_entry(
        entry,
        path_key=path_key,
        label=label,
    )
    path = _require_bundle_file(relative)
    data = path.read_bytes()
    expected_size = entry["size"]
    if len(data) != expected_size:
        raise ValueError(
            f"{relative}: expected size {expected_size}, got {len(data)}"
        )
    expected_sha = entry["sha256"]
    actual_sha = hashlib.sha256(data).hexdigest()
    if actual_sha != expected_sha:
        raise ValueError(f"{relative}: sha256 mismatch")


def _verify_manifest_file_entry(entry: Any, *, path_key: str, label: str) -> str:
    if not isinstance(entry, dict):
        raise ValueError(f"manifest.json: {label} must be an object")
    relative = entry.get(path_key)
    if not isinstance(relative, str) or not relative:
        raise ValueError(
            f"manifest.json: {label}.{path_key} must be a non-empty string"
        )
    _bundle_path(relative)
    size = entry.get("size")
    if type(size) is not int or size < 0:
        raise ValueError(f"manifest.json: {label}.size must be a non-negative integer")
    sha256 = entry.get("sha256")
    if not _is_sha256_hexdigest(sha256):
        raise ValueError(
            f"manifest.json: {label}.sha256 must be a lowercase sha256 hex digest"
        )
    return relative


def _is_sha256_hexdigest(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    return all(char in "0123456789abcdef" for char in value)


def _require_artifact_entry(manifest: dict[str, Any], relative: Any) -> None:
    if not isinstance(relative, str):
        raise ValueError("manifest.json: backendCoverage must be a string")
    artifacts = manifest.get("artifacts", [])
    if not isinstance(artifacts, list):
        raise ValueError("manifest.json: artifacts must be a list")
    if any(
        isinstance(artifact, dict) and artifact.get("path") == relative
        for artifact in artifacts
    ):
        return
    raise ValueError(f"manifest.json: artifacts missing {relative!r}")


def _require_bundle_file(relative: str) -> Path:
    path = _bundle_path(relative)
    if not path.is_file():
        raise FileNotFoundError(f"bundle file {relative!r} does not exist")
    return path


def _bundle_path(relative: str) -> Path:
    path = Path(relative)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError(f"bundle path {relative!r} is not safe")
    return ROOT / path


def _load_target(spec: str) -> Any:
    module_name, separator, object_path = spec.partition(":")
    if not separator or not module_name or not object_path:
        raise ValueError("manifest target must use MODULE:OBJECT syntax")
    value = importlib.import_module(module_name)
    for part in object_path.split("."):
        value = getattr(value, part)
    return value


def _coerce_target(target: Any):
    from otoe import MountedNode, Node, mount

    if isinstance(target, MountedNode):
        return target
    if isinstance(target, Node):
        return mount(target)
    if callable(target):
        return _coerce_target(target())
    raise TypeError(
        "bundled target must be a Node, MountedNode, or zero-argument callable"
    )


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"otoe-run: {exc}", file=sys.stderr)
        raise SystemExit(1)
