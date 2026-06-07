from __future__ import annotations

from typing import Any

from .backend_evidence_common import (
    evidence_error,
    is_sha256_uri,
    positive_number,
    required_string_errors,
)


def render_tree_boundary_evidence_errors(
    boundary: Any,
    *,
    blocker: str,
    prefix: str,
    expected_source: Any,
    expected_layout_boxes: Any,
    expected_output_hash: Any = None,
    expected_render_tree_hash: Any = None,
) -> list[dict[str, str]]:
    if not isinstance(boundary, dict):
        return [evidence_error(blocker, f"{prefix} must be a JSON object")]
    errors: list[dict[str, str]] = []
    errors.extend(
        required_string_errors(
            boundary,
            blocker=blocker,
            prefix=prefix,
            keys=("phase", "boundary", "source", "outputHash", "renderTreeHash"),
        )
    )
    if boundary.get("phase") != "layout":
        errors.append(evidence_error(blocker, f"{prefix}.phase must be 'layout'"))
    if boundary.get("boundary") != "renderTree":
        errors.append(
            evidence_error(blocker, f"{prefix}.boundary must be 'renderTree'")
        )
    if (
        isinstance(expected_source, str)
        and expected_source
        and boundary.get("source") != expected_source
    ):
        errors.append(
            evidence_error(
                blocker,
                f"{prefix}.source must match evidence.path0.source",
            )
        )
    if not positive_number(boundary.get("layoutBoxes")):
        errors.append(
            evidence_error(
                blocker,
                f"{prefix}.layoutBoxes must be a positive number",
            )
        )
    elif (
        positive_number(expected_layout_boxes)
        and boundary.get("layoutBoxes") != expected_layout_boxes
    ):
        errors.append(
            evidence_error(
                blocker,
                f"{prefix}.layoutBoxes must match evidence.path0.layoutBoxes",
            )
        )
    output_hash = boundary.get("outputHash")
    if not is_sha256_uri(output_hash):
        errors.append(
            evidence_error(blocker, f"{prefix}.outputHash must be a sha256 string")
        )
    elif (
        isinstance(expected_output_hash, str)
        and expected_output_hash
        and output_hash != expected_output_hash
    ):
        errors.append(
            evidence_error(
                blocker,
                f"{prefix}.outputHash must match path0.output.layout.outputHash",
            )
        )
    render_tree_hash = boundary.get("renderTreeHash")
    if not is_sha256_uri(render_tree_hash):
        errors.append(
            evidence_error(
                blocker,
                f"{prefix}.renderTreeHash must be a sha256 string",
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
                f"{prefix}.renderTreeHash must match path0.input.renderTreeHash",
            )
        )
    return errors


def paint_boundary_evidence_errors(
    proof: Any,
    *,
    blocker: str,
    prefix: str,
    expected_output_hash: Any = None,
) -> list[dict[str, str]]:
    if not isinstance(proof, dict):
        return [evidence_error(blocker, f"{prefix} must be a JSON object")]
    errors: list[dict[str, str]] = []
    errors.extend(
        required_string_errors(
            proof,
            blocker=blocker,
            prefix=prefix,
            keys=("phase", "source", "outputHash"),
        )
    )
    if proof.get("phase") != "paint":
        errors.append(evidence_error(blocker, f"{prefix}.phase must be 'paint'"))
    if not positive_number(proof.get("paintCommands")):
        errors.append(
            evidence_error(
                blocker,
                f"{prefix}.paintCommands must be a positive number",
            )
        )
    output_hash = proof.get("outputHash")
    if not is_sha256_uri(output_hash):
        errors.append(
            evidence_error(blocker, f"{prefix}.outputHash must be a sha256 string")
        )
    elif (
        isinstance(expected_output_hash, str)
        and expected_output_hash
        and output_hash != expected_output_hash
    ):
        errors.append(
            evidence_error(
                blocker,
                f"{prefix}.outputHash must match path0.output.paint.outputHash",
            )
        )
    return errors
