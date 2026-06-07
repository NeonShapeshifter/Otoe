from __future__ import annotations

from pathlib import Path
from typing import Any

from otoe.backend_evidence_path0_semantics import path0_output_semantic_validation

from .backend_candidate_snapshot_payloads import renderer_call_to_dict
from .backend_candidate_render_tree_types import Path0RenderTreeEvidenceReport


def path0_render_tree_evidence_report_to_dict(
    report: Path0RenderTreeEvidenceReport,
) -> dict[str, Any]:
    png_path = Path(report.png_path).name if report.png_path is not None else None
    return {
        "schemaVersion": 1,
        "format": "path0-render-tree-evidence",
        "passed": report.passed,
        "rendererBackend": report.renderer_backend,
        "input": {
            "source": report.source,
            "format": "otoe-render-tree",
            "renderTreeHash": report.render_tree_hash,
            "nodeCount": report.node_count,
            "styledNodes": report.styled_nodes,
            "styleOps": {
                "present": report.style_ops_present,
                "schemaVersion": report.style_ops_schema_version,
                "format": report.style_ops_format,
                "matchesRenderTree": report.style_ops_matches_render_tree,
            },
        },
        "render": {
            "layoutBoxes": report.layout_boxes,
            "paintCommands": report.paint_commands,
            "pngPath": png_path,
        },
        "output": {
            "layout": dict(report.layout_output),
            "paint": dict(report.paint_output),
        },
        "semanticValidation": path0_output_semantic_validation(
            {
                "layout": report.layout_output,
                "paint": report.paint_output,
            }
        ),
        "evidence": {
            "layout": {
                "layoutBoxes": report.layout_boxes,
                "styleProperties": list(report.layout_style_properties),
                "observations": list(report.layout_style_observations),
            },
            "paint": {
                "paintCommands": report.paint_commands,
                "styleProperties": list(report.paint_style_properties),
                "observations": list(report.paint_style_observations),
            },
            "raster": {
                "pngWritten": report.png_sha256 is not None,
                "pngPath": png_path,
                "sha256": report.png_sha256,
                "byteSize": report.png_bytes,
            },
        },
        "calls": [renderer_call_to_dict(call) for call in report.calls],
        "errors": list(report.errors),
    }


def path0_report_has_style_phase_evidence(
    report: Path0RenderTreeEvidenceReport,
) -> bool:
    return (
        report.passed
        and path0_output_semantic_validation(
            {
                "layout": report.layout_output,
                "paint": report.paint_output,
            }
        )["passed"]
        and report.style_ops_present
        and _path0_report_has_render_tree_boundary_evidence(report)
        and _path0_observations_cover(
            report.layout_style_properties,
            report.layout_style_observations,
            phase="layout",
        )
        and _path0_observations_cover(
            report.paint_style_properties,
            report.paint_style_observations,
            phase="paint",
        )
    )


def _path0_report_has_render_tree_boundary_evidence(
    report: Path0RenderTreeEvidenceReport,
) -> bool:
    return any(
        call.phase == "layout"
        and call.boundary == "renderTree"
        and call.subject == report.source
        and call.layout_boxes == report.layout_boxes
        and call.layout_boxes > 0
        for call in report.calls
    )


def _path0_observations_cover(
    properties: tuple[str, ...],
    observations: tuple[dict[str, Any], ...],
    *,
    phase: str,
) -> bool:
    if not properties:
        return False

    observed = set()
    for observation in observations:
        property_name = observation.get("property")
        samples = observation.get("samples")
        if property_name not in properties or not isinstance(samples, list):
            continue
        if not samples:
            continue
        if not any(
            _path0_sample_proves_style_effect(
                property_name,
                sample,
                phase=phase,
            )
            for sample in samples
        ):
            continue
        observed.add(property_name)
    return set(properties) <= observed


def _path0_sample_proves_style_effect(
    property_name: str,
    sample: Any,
    *,
    phase: str,
) -> bool:
    if not isinstance(sample, dict):
        return False
    if phase == "layout":
        return _path0_layout_sample_proves_style_effect(property_name, sample)
    if phase == "paint":
        return _path0_paint_sample_proves_style_effect(property_name, sample)
    return False


def _path0_layout_sample_proves_style_effect(
    property_name: str,
    sample: dict[str, Any],
) -> bool:
    bounds = _path0_bounds_value(sample)
    if bounds is None:
        return False
    _x, _y, width, height = bounds
    if width <= 0 or height <= 0:
        return False

    value = _path0_style_numeric_value(sample)
    if property_name in {"width", "minWidth"}:
        return value is None or width >= value
    if property_name == "maxWidth":
        return value is None or width <= value
    if property_name in {"height", "minHeight"}:
        return value is None or height >= value
    if property_name == "maxHeight":
        return value is None or height <= value
    if property_name in {"alignItems", "gap", "justifyContent", "padding"}:
        return bool(sample.get("children")) or sample.get("name") in {
            "Button",
            "Input",
            "Text",
        }
    if property_name == "scrollY":
        return sample.get("name") == "ScrollView"
    if property_name in {"borderWidth", "fontSize"}:
        return value is None or value >= 0
    return True


def _path0_paint_sample_proves_style_effect(
    property_name: str,
    sample: dict[str, Any],
) -> bool:
    commands = sample.get("commands")
    if not isinstance(commands, list) or not commands:
        return False
    value = _path0_style_literal_or_numeric_value(sample)

    if property_name == "background":
        return any(command.get("fill") == value for command in commands)
    if property_name == "borderColor":
        return any(command.get("stroke") == value for command in commands)
    if property_name == "color":
        return any(command.get("color") == value for command in commands)
    if property_name == "borderRadius":
        return any(command.get("radius") == value for command in commands)
    if property_name == "borderWidth":
        return any(command.get("strokeWidth") == value for command in commands)
    if property_name == "fontSize":
        return any(command.get("fontSize") == value for command in commands)
    return sample.get("commandCount", 0) > 0


def _path0_bounds_value(sample: dict[str, Any]) -> tuple[int, int, int, int] | None:
    bounds = sample.get("bounds")
    if not isinstance(bounds, list) or len(bounds) != 4:
        return None
    if not all(type(item) is int for item in bounds):
        return None
    return (bounds[0], bounds[1], bounds[2], bounds[3])


def _path0_style_numeric_value(sample: dict[str, Any]) -> int | float | None:
    value = _path0_style_literal_or_numeric_value(sample)
    return value if type(value) in {int, float} else None


def _path0_style_literal_or_numeric_value(sample: dict[str, Any]) -> Any:
    value = sample.get("value")
    if not isinstance(value, dict):
        return None
    kind = value.get("type")
    if kind == "size":
        return value.get("value")
    if kind == "literal":
        return value.get("value")
    return None
