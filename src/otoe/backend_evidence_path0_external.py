from __future__ import annotations

import hashlib
import json
from typing import Any

from .backend_evidence_common import (
    evidence_error,
    is_sha256_uri,
    positive_number,
)
from .backend_evidence_path0_semantics import path0_output_semantic_errors


def external_path0_evidence_errors(
    path0: Any,
    gates: Any,
) -> list[dict[str, str]]:
    if not isinstance(path0, dict):
        return []
    external = path0.get("externalBackend")
    if external is None:
        return []
    blocker = "path0ExternalJsonBackend"
    prefix = "path0.externalBackend"
    if not isinstance(external, dict):
        return [evidence_error(blocker, f"{prefix} must be a JSON object")]

    errors: list[dict[str, str]] = []
    if isinstance(gates, dict) and gates.get("path0ExternalJsonBackend") is not True:
        errors.append(
            evidence_error(
                blocker,
                "gates.path0ExternalJsonBackend must be true when "
                "path0.externalBackend is present",
            )
        )
    if external.get("schemaVersion") != 1:
        errors.append(evidence_error(blocker, f"{prefix}.schemaVersion must be 1"))
    if external.get("format") != "path0-external-backend-evidence":
        errors.append(
            evidence_error(
                blocker,
                f"{prefix}.format must be 'path0-external-backend-evidence'",
            )
        )
    if external.get("passed") is not True:
        errors.append(evidence_error(blocker, f"{prefix}.passed must be true"))
    if not isinstance(external.get("backend"), str) or not external.get("backend"):
        errors.append(
            evidence_error(blocker, f"{prefix}.backend must be a non-empty string")
        )
    if external.get("source") != _path0_source(path0):
        errors.append(
            evidence_error(blocker, f"{prefix}.source must match path0.input.source")
        )

    process = external.get("process")
    if not isinstance(process, dict):
        errors.append(evidence_error(blocker, f"{prefix}.process must be an object"))
    elif process.get("exitCode") != 0:
        errors.append(evidence_error(blocker, f"{prefix}.process.exitCode must be 0"))

    external_input = external.get("input")
    if not isinstance(external_input, dict):
        errors.append(evidence_error(blocker, f"{prefix}.input must be an object"))
    else:
        errors.extend(_external_input_errors(external_input, path0, prefix=prefix))

    output = external.get("output")
    errors.extend(_external_output_errors(output, path0, prefix=prefix))
    semantic_errors = path0_output_semantic_errors(output)
    errors.extend(
        evidence_error(blocker, f"{prefix}.output: {message}")
        for message in semantic_errors
    )
    semantic_validation = external.get("semanticValidation")
    if not isinstance(semantic_validation, dict):
        errors.append(
            evidence_error(
                blocker,
                f"{prefix}.semanticValidation must be a JSON object",
            )
        )
    else:
        expected_passed = not semantic_errors
        if semantic_validation.get("passed") is not expected_passed:
            errors.append(
                evidence_error(
                    blocker,
                    f"{prefix}.semanticValidation.passed must match output audit",
                )
            )
        if semantic_validation.get("errors") != semantic_errors:
            errors.append(
                evidence_error(
                    blocker,
                    f"{prefix}.semanticValidation.errors must match output audit",
                )
            )
    raw_errors = external.get("errors")
    if raw_errors != []:
        errors.append(evidence_error(blocker, f"{prefix}.errors must be []"))
    return errors


def _external_input_errors(
    external_input: dict[str, Any],
    path0: dict[str, Any],
    *,
    prefix: str,
) -> list[dict[str, str]]:
    blocker = "path0ExternalJsonBackend"
    errors: list[dict[str, str]] = []
    render_tree_hash = external_input.get("renderTreeHash")
    expected_render_tree_hash = _path0_render_tree_hash(path0)
    if not is_sha256_uri(render_tree_hash):
        errors.append(
            evidence_error(
                blocker,
                f"{prefix}.input.renderTreeHash must be a sha256 string",
            )
        )
    elif render_tree_hash != expected_render_tree_hash:
        errors.append(
            evidence_error(
                blocker,
                f"{prefix}.input.renderTreeHash must match path0.input.renderTreeHash",
            )
        )
    node_count = external_input.get("nodeCount")
    if not positive_number(node_count):
        errors.append(
            evidence_error(blocker, f"{prefix}.input.nodeCount must be positive")
        )
    elif node_count != _path0_node_count(path0):
        errors.append(
            evidence_error(
                blocker,
                f"{prefix}.input.nodeCount must match path0.input.nodeCount",
            )
        )
    style_ops = external_input.get("styleOps")
    if not isinstance(style_ops, dict):
        errors.append(
            evidence_error(blocker, f"{prefix}.input.styleOps must be an object")
        )
    elif _path0_style_ops_present(path0):
        if style_ops.get("present") is not True:
            errors.append(
                evidence_error(
                    blocker,
                    f"{prefix}.input.styleOps.present must be true",
                )
            )
        artifact_hash = style_ops.get("artifactHash")
        if not is_sha256_uri(artifact_hash):
            errors.append(
                evidence_error(
                    blocker,
                    f"{prefix}.input.styleOps.artifactHash must be a sha256 string",
                )
            )
    return errors


def _external_output_errors(
    output: Any,
    path0: dict[str, Any],
    *,
    prefix: str,
) -> list[dict[str, str]]:
    blocker = "path0ExternalJsonBackend"
    if not isinstance(output, dict):
        return [evidence_error(blocker, f"{prefix}.output must be a JSON object")]
    errors: list[dict[str, str]] = []
    errors.extend(
        _output_section_errors(
            output.get("layout"),
            prefix=f"{prefix}.output.layout",
            expected_format="path0-layout-output",
            count_key="boxCount",
            items_key="boxes",
            expected_count=_path0_node_count(path0),
        )
    )
    errors.extend(
        _output_section_errors(
            output.get("paint"),
            prefix=f"{prefix}.output.paint",
            expected_format="path0-paint-output",
            count_key="commandCount",
            items_key="commands",
            expected_count=None,
        )
    )
    return errors


def _output_section_errors(
    section: Any,
    *,
    prefix: str,
    expected_format: str,
    count_key: str,
    items_key: str,
    expected_count: Any,
) -> list[dict[str, str]]:
    blocker = "path0ExternalJsonBackend"
    if not isinstance(section, dict):
        return [evidence_error(blocker, f"{prefix} must be a JSON object")]
    errors: list[dict[str, str]] = []
    if section.get("schemaVersion") != 1:
        errors.append(evidence_error(blocker, f"{prefix}.schemaVersion must be 1"))
    if section.get("format") != expected_format:
        errors.append(
            evidence_error(blocker, f"{prefix}.format must be {expected_format!r}")
        )
    count = section.get(count_key)
    if not positive_number(count):
        errors.append(evidence_error(blocker, f"{prefix}.{count_key} must be positive"))
    elif positive_number(expected_count) and count != expected_count:
        errors.append(
            evidence_error(
                blocker,
                f"{prefix}.{count_key} must match path0.input.nodeCount",
            )
        )
    items = section.get(items_key)
    if not isinstance(items, list):
        errors.append(evidence_error(blocker, f"{prefix}.{items_key} must be a list"))
    elif positive_number(count) and len(items) != count:
        errors.append(
            evidence_error(
                blocker,
                f"{prefix}.{items_key} length must match {prefix}.{count_key}",
            )
        )
    output_hash = section.get("outputHash")
    if not is_sha256_uri(output_hash):
        errors.append(
            evidence_error(blocker, f"{prefix}.outputHash must be a sha256 string")
        )
    elif output_hash != _output_hash(section):
        errors.append(evidence_error(blocker, f"{prefix}.outputHash must match payload"))
    return errors


def _path0_source(path0: dict[str, Any]) -> Any:
    path0_input = path0.get("input")
    return path0_input.get("source") if isinstance(path0_input, dict) else None


def _path0_render_tree_hash(path0: dict[str, Any]) -> Any:
    path0_input = path0.get("input")
    return (
        path0_input.get("renderTreeHash")
        if isinstance(path0_input, dict)
        else None
    )


def _path0_node_count(path0: dict[str, Any]) -> Any:
    path0_input = path0.get("input")
    return path0_input.get("nodeCount") if isinstance(path0_input, dict) else None


def _path0_style_ops_present(path0: dict[str, Any]) -> bool:
    path0_input = path0.get("input")
    if not isinstance(path0_input, dict):
        return False
    style_ops = path0_input.get("styleOps")
    return isinstance(style_ops, dict) and style_ops.get("present") is True


def _output_hash(payload: dict[str, Any]) -> str:
    payload_without_hash = {
        key: value for key, value in payload.items() if key != "outputHash"
    }
    encoded = json.dumps(
        payload_without_hash,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"
