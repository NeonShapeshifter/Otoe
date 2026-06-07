from __future__ import annotations

from typing import Any

from otoe.style import style_value_to_dict

from .backend_candidate_compact_snapshots import contract_hash


def path0_layout_output_to_dict(layout: Any) -> dict[str, Any]:
    payload = {
        "schemaVersion": 1,
        "format": "path0-layout-output",
        "boxCount": len(layout.boxes),
        "rootPath": list(layout.root.path),
        "boxes": [_layout_box_to_dict(box) for box in layout.boxes],
    }
    return {**payload, "outputHash": contract_hash(payload)}


def path0_paint_output_to_dict(paint: Any) -> dict[str, Any]:
    payload = {
        "schemaVersion": 1,
        "format": "path0-paint-output",
        "width": paint.width,
        "height": paint.height,
        "commandCount": len(paint.commands),
        "commands": [_paint_command_to_dict(command) for command in paint.commands],
    }
    return {**payload, "outputHash": contract_hash(payload)}


def _layout_box_to_dict(box: Any) -> dict[str, Any]:
    return {
        "path": list(box.path),
        "name": box.name,
        "bounds": [box.x, box.y, box.width, box.height],
        "id": box.id,
        "context": box.context,
        "text": box.text,
        "events": list(box.events),
        "state": list(box.state),
        "style": _style_to_dict(box.style),
        "children": [list(child.path) for child in box.children],
    }


def _paint_command_to_dict(command: Any) -> dict[str, Any]:
    return {
        "kind": command.kind,
        "path": list(command.path),
        "bounds": [command.x, command.y, command.width, command.height],
        "fill": command.fill,
        "stroke": command.stroke,
        "strokeWidth": command.stroke_width,
        "radius": command.radius,
        "text": command.text,
        "color": command.color,
        "fontSize": command.font_size,
        "clip": list(command.clip) if command.clip is not None else None,
        "context": command.context,
    }


def _style_to_dict(style: Any) -> dict[str, Any]:
    if not isinstance(style, tuple):
        return {}
    result: dict[str, Any] = {}
    for item in style:
        if not isinstance(item, tuple) or len(item) != 2:
            continue
        key, value = item
        if isinstance(key, str):
            result[key] = style_value_to_dict(value)
    return result
