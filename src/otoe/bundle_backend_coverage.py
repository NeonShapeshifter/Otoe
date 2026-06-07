from __future__ import annotations

from typing import Any


def verify_backend_coverage_contract(payload: dict[str, Any], label: str) -> None:
    if payload.get("format") != "backend-coverage-report":
        raise ValueError(f"{label}: format must be 'backend-coverage-report'")
    if payload.get("passed") is not True:
        blockers = payload.get("blockers", [])
        if isinstance(blockers, list) and blockers:
            details = ", ".join(str(blocker) for blocker in blockers)
        else:
            details = "backend coverage failed"
        raise ValueError(f"{label}: backend coverage failed: {details}")
    _verify_backend_coverage_traceability(payload, label)


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
    external = path0.get("externalBackend")
    if external is not None:
        _verify_backend_coverage_external_path0_trace(
            external,
            label=f"{label}: trace.path0.externalBackend",
            expected_render_tree_hash=result["renderTreeHash"],
        )
    return result


def _verify_backend_coverage_external_path0_trace(
    external: Any,
    *,
    label: str,
    expected_render_tree_hash: str,
) -> None:
    if not isinstance(external, dict):
        raise ValueError(f"{label} must be an object")
    backend = external.get("backend")
    if not isinstance(backend, str) or not backend:
        raise ValueError(f"{label}.backend must be a non-empty string")
    package_hash = external.get("packageHash")
    if not _is_sha256_uri(package_hash):
        raise ValueError(f"{label}.packageHash must be a sha256 string")
    render_tree_hash = external.get("renderTreeHash")
    if not _is_sha256_uri(render_tree_hash):
        raise ValueError(f"{label}.renderTreeHash must be a sha256 string")
    if render_tree_hash != expected_render_tree_hash:
        raise ValueError(
            f"{label}.renderTreeHash must match trace.path0.renderTreeHash"
        )
    for key in ("layoutOutputHash", "paintOutputHash"):
        value = external.get(key)
        if not _is_sha256_uri(value):
            raise ValueError(f"{label}.{key} must be a sha256 string")
    semantic_validation = external.get("semanticValidation")
    if not isinstance(semantic_validation, dict):
        raise ValueError(f"{label}.semanticValidation must be an object")
    if semantic_validation.get("passed") is not True:
        raise ValueError(f"{label}.semanticValidation.passed must be true")
    if semantic_validation.get("errors") != []:
        raise ValueError(f"{label}.semanticValidation.errors must be []")


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
