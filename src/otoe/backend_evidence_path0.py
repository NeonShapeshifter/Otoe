from __future__ import annotations

import hashlib
import json
from typing import Any

from .backend_evidence_boundaries import render_tree_boundary_evidence_errors
from .backend_evidence_common import (
    evidence_error,
    gate_reference_errors,
    is_sha256_uri,
    phase_evidence_errors,
    positive_number,
    required_string_errors,
)
from .backend_evidence_path0_semantics import path0_output_semantic_errors


def path0_evidence_errors(
    path0: Any,
    gates: Any,
    *,
    output: Any = None,
    semantic_validation: Any = None,
    expected_render_tree_hash: Any = None,
) -> list[dict[str, str]]:
    blocker = "path0RenderTreeEvidence"
    if not isinstance(path0, dict):
        return [evidence_error(blocker, "evidence.path0 must be a JSON object")]
    errors: list[dict[str, str]] = []
    errors.extend(
        required_string_errors(
            path0,
            blocker=blocker,
            prefix="evidence.path0",
            keys=("source", "gate", "rendererBackend"),
        )
    )
    gate = path0.get("gate")
    if isinstance(gate, str):
        errors.extend(
            gate_reference_errors(
                gate,
                gates,
                blocker=blocker,
                prefix="evidence.path0.gate",
            )
        )
    if path0.get("styleOpsPresent") is not True:
        errors.append(
            evidence_error(blocker, "evidence.path0.styleOpsPresent must be true")
        )
    if path0.get("styleOpsMatchesRenderTree") is not True:
        errors.append(
            evidence_error(
                blocker,
                "evidence.path0.styleOpsMatchesRenderTree must be true",
            )
        )
    render_tree_hash = path0.get("renderTreeHash")
    if not is_sha256_uri(render_tree_hash):
        errors.append(
            evidence_error(
                blocker,
                "evidence.path0.renderTreeHash must be a sha256 string",
            )
        )
    elif (
        isinstance(expected_render_tree_hash, str)
        and expected_render_tree_hash
        and render_tree_hash != expected_render_tree_hash
    ):
        errors.append(
            evidence_error(
                blocker,
                "evidence.path0.renderTreeHash must match path0.input.renderTreeHash",
            )
        )
    if output is None:
        output = path0.get("output")
    expected_layout_output_hash = _path0_output_hash(output, "layout")
    errors.extend(
        render_tree_boundary_evidence_errors(
            path0.get("renderTreeBoundary"),
            blocker=blocker,
            prefix="evidence.path0.renderTreeBoundary",
            expected_source=path0.get("source"),
            expected_layout_boxes=path0.get("layoutBoxes"),
            expected_output_hash=expected_layout_output_hash,
            expected_render_tree_hash=path0.get("renderTreeHash"),
        )
    )
    for key in ("styledNodes", "layoutBoxes", "paintCommands"):
        if not positive_number(path0.get(key)):
            errors.append(
                evidence_error(
                    blocker,
                    f"evidence.path0.{key} must be a positive number",
                )
            )
    errors.extend(_path0_output_errors(path0, output=output))
    errors.extend(
        _path0_output_semantic_validation_errors(
            output,
            semantic_validation=semantic_validation,
        )
    )
    phases = path0.get("phases")
    if not isinstance(phases, list) or not {"layout", "paint"} <= set(phases):
        errors.append(
            evidence_error(
                blocker,
                "evidence.path0.phases must include layout and paint",
            )
        )
    errors.extend(
        phase_evidence_errors(
            path0.get("layoutEvidence"),
            blocker=blocker,
            prefix="evidence.path0.layoutEvidence",
        )
    )
    errors.extend(
        phase_evidence_errors(
            path0.get("paintEvidence"),
            blocker=blocker,
            prefix="evidence.path0.paintEvidence",
        )
    )
    return errors


def _path0_output_semantic_validation_errors(
    output: Any,
    *,
    semantic_validation: Any,
) -> list[dict[str, str]]:
    blocker = "path0RenderTreeEvidence"
    errors: list[dict[str, str]] = []
    semantic_errors = path0_output_semantic_errors(output)
    errors.extend(evidence_error(blocker, message) for message in semantic_errors)
    if not isinstance(semantic_validation, dict):
        errors.append(
            evidence_error(
                blocker,
                "path0.semanticValidation must be a JSON object",
            )
        )
        return errors
    expected_passed = not semantic_errors
    if semantic_validation.get("passed") is not expected_passed:
        errors.append(
            evidence_error(
                blocker,
                "path0.semanticValidation.passed must match path0.output semantic audit",
            )
        )
    declared_errors = semantic_validation.get("errors")
    if declared_errors != semantic_errors:
        errors.append(
            evidence_error(
                blocker,
                "path0.semanticValidation.errors must match path0.output semantic audit",
            )
        )
    return errors


def _path0_output_hash(output: Any, section_name: str) -> Any:
    if not isinstance(output, dict):
        return None
    section = output.get(section_name)
    if not isinstance(section, dict):
        return None
    return section.get("outputHash")


def _path0_output_errors(
    path0: dict[str, Any],
    *,
    output: Any,
) -> list[dict[str, str]]:
    blocker = "path0RenderTreeEvidence"
    if output is None:
        output = path0.get("output")
    if not isinstance(output, dict):
        return [evidence_error(blocker, "evidence.path0.output must be a JSON object")]
    errors: list[dict[str, str]] = []
    layout = output.get("layout")
    paint = output.get("paint")
    errors.extend(
        _path0_output_section_errors(
            layout,
            blocker=blocker,
            prefix="evidence.path0.output.layout",
            expected_format="path0-layout-output",
            count_key="boxCount",
            items_key="boxes",
            expected_count=path0.get("layoutBoxes"),
            expected_count_label="evidence.path0.layoutBoxes",
        )
    )
    errors.extend(
        _path0_output_section_errors(
            paint,
            blocker=blocker,
            prefix="evidence.path0.output.paint",
            expected_format="path0-paint-output",
            count_key="commandCount",
            items_key="commands",
            expected_count=path0.get("paintCommands"),
            expected_count_label="evidence.path0.paintCommands",
        )
    )
    errors.extend(
        _path0_output_hash_reference_errors(
            path0,
            layout,
            paint,
            blocker=blocker,
        )
    )
    return errors


def _path0_output_hash_reference_errors(
    path0: dict[str, Any],
    layout: Any,
    paint: Any,
    *,
    blocker: str,
) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    references = (
        (
            "layoutOutputHash",
            layout,
            "evidence.path0.layoutOutputHash",
        ),
        (
            "paintOutputHash",
            paint,
            "evidence.path0.paintOutputHash",
        ),
    )
    for key, section, label in references:
        value = path0.get(key)
        if value is None:
            continue
        if not is_sha256_uri(value):
            errors.append(evidence_error(blocker, f"{label} must be a sha256 string"))
            continue
        if isinstance(section, dict) and value != section.get("outputHash"):
            errors.append(evidence_error(blocker, f"{label} must match outputHash"))
    return errors


def _path0_output_section_errors(
    section: Any,
    *,
    blocker: str,
    prefix: str,
    expected_format: str,
    count_key: str,
    items_key: str,
    expected_count: Any,
    expected_count_label: str,
) -> list[dict[str, str]]:
    if not isinstance(section, dict):
        return [evidence_error(blocker, f"{prefix} must be a JSON object")]
    errors: list[dict[str, str]] = []
    if section.get("schemaVersion") != 1:
        errors.append(
            evidence_error(blocker, f"{prefix}.schemaVersion must be 1")
        )
    if section.get("format") != expected_format:
        errors.append(
            evidence_error(
                blocker,
                f"{prefix}.format must be {expected_format!r}",
            )
        )
    count = section.get(count_key)
    if not positive_number(count):
        errors.append(
            evidence_error(blocker, f"{prefix}.{count_key} must be a positive number")
        )
    elif positive_number(expected_count) and count != expected_count:
        errors.append(
            evidence_error(
                blocker,
                f"{prefix}.{count_key} must match {expected_count_label}",
            )
        )
    items = section.get(items_key)
    if not isinstance(items, list):
        errors.append(
            evidence_error(blocker, f"{prefix}.{items_key} must be a list")
        )
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
        errors.append(
            evidence_error(blocker, f"{prefix}.outputHash must match payload")
        )
    return errors


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
