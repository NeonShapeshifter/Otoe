from __future__ import annotations

from typing import Any

from otoe import LayoutBox, NativeLayout, NativePaint, PaintCommand
from otoe.capabilities import (
    NATIVE_LAYOUT_STYLE_PROPERTIES,
    NATIVE_PAINT_STYLE_PROPERTIES,
)
from otoe.render_ir import RenderTree, walk_render_nodes
from otoe.style import style_value_to_dict


_PATH0_OBSERVATION_SAMPLE_LIMIT = 1
_PATH0_CHILD_SAMPLE_LIMIT = 4


def path0_layout_style_properties(render_tree: RenderTree) -> tuple[str, ...]:
    return _path0_style_properties(render_tree, NATIVE_LAYOUT_STYLE_PROPERTIES)


def path0_paint_style_properties(render_tree: RenderTree) -> tuple[str, ...]:
    return _path0_style_properties(render_tree, NATIVE_PAINT_STYLE_PROPERTIES)


def path0_layout_style_observations(
    layout: NativeLayout,
) -> tuple[dict[str, Any], ...]:
    buckets: dict[str, list[dict[str, Any]]] = {}
    for box in layout.boxes:
        for property_name, value in dict(box.style).items():
            if property_name not in NATIVE_LAYOUT_STYLE_PROPERTIES:
                continue
            buckets.setdefault(property_name, []).append(
                _path0_layout_observation(box, value)
            )
    return _path0_style_observation_groups(buckets)


def path0_paint_style_observations(
    layout: NativeLayout,
    paint: NativePaint,
) -> tuple[dict[str, Any], ...]:
    commands_by_path: dict[tuple[int, ...], list[PaintCommand]] = {}
    for command in paint.commands:
        commands_by_path.setdefault(command.path, []).append(command)

    buckets: dict[str, list[dict[str, Any]]] = {}
    for box in layout.boxes:
        commands = tuple(commands_by_path.get(box.path, ()))
        for property_name, value in dict(box.style).items():
            if property_name not in NATIVE_PAINT_STYLE_PROPERTIES:
                continue
            buckets.setdefault(property_name, []).append(
                _path0_paint_observation(box, value, commands)
            )
    return _path0_style_observation_groups(buckets)


def _path0_style_properties(
    render_tree: RenderTree,
    supported_properties: frozenset[str],
) -> tuple[str, ...]:
    properties = {
        property_name
        for node in walk_render_nodes(render_tree.root)
        for property_name in node.style_dict()
        if property_name in supported_properties
    }
    return tuple(sorted(properties))


def _path0_layout_observation(box: LayoutBox, value: Any) -> dict[str, Any]:
    sample: dict[str, Any] = {
        "path": list(box.path),
        "nodeId": box.id,
        "name": box.name,
        "value": style_value_to_dict(value),
        "bounds": _path0_bounds(box),
    }
    if box.children:
        sample["children"] = [
            {
                "path": list(child.path),
                "name": child.name,
                "bounds": _path0_bounds(child),
            }
            for child in box.children[:_PATH0_CHILD_SAMPLE_LIMIT]
        ]
    return sample


def _path0_paint_observation(
    box: LayoutBox,
    value: Any,
    commands: tuple[PaintCommand, ...],
) -> dict[str, Any]:
    return {
        "path": list(box.path),
        "nodeId": box.id,
        "name": box.name,
        "value": style_value_to_dict(value),
        "commandCount": len(commands),
        "commands": [
            _path0_paint_command_observation(command)
            for command in commands[:_PATH0_OBSERVATION_SAMPLE_LIMIT]
        ],
    }


def _path0_paint_command_observation(command: PaintCommand) -> dict[str, Any]:
    return {
        "kind": command.kind,
        "path": list(command.path),
        "bounds": _path0_bounds(command),
        "fill": command.fill,
        "stroke": command.stroke,
        "strokeWidth": command.stroke_width,
        "radius": command.radius,
        "text": command.text,
        "color": command.color,
        "fontSize": command.font_size,
        "clip": list(command.clip) if command.clip is not None else None,
    }


def _path0_style_observation_groups(
    buckets: dict[str, list[dict[str, Any]]],
) -> tuple[dict[str, Any], ...]:
    return tuple(
        {
            "property": property_name,
            "count": len(samples),
            "samples": samples[:_PATH0_OBSERVATION_SAMPLE_LIMIT],
        }
        for property_name, samples in sorted(buckets.items())
    )


def _path0_bounds(value: Any) -> list[int]:
    return [value.x, value.y, value.width, value.height]
