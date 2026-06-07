from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any


BACKEND_NAME = "path0-external-json-backend"
SUPPORTED_LEAVES = frozenset({"Button", "Input", "Text"})
SUPPORTED_CONTAINERS = frozenset(
    {
        "FocusScope",
        "For",
        "HStack",
        "Panel",
        "ScrollView",
        "ShortcutScope",
        "Show",
        "VStack",
    }
)
SUPPORTED_WIDGETS = SUPPORTED_LEAVES | SUPPORTED_CONTAINERS
RENDER_TREE_KEYS = frozenset({"schemaVersion", "format", "nodeCount", "root"})
RENDER_NODE_KEYS = frozenset(
    {
        "children",
        "className",
        "context",
        "events",
        "id",
        "key",
        "name",
        "path",
        "props",
        "state",
        "style",
        "widgetId",
    }
)


class ExternalPath0BackendError(ValueError):
    pass


def run_external_path0_backend(
    render_tree_payload: Mapping[str, Any],
    *,
    source: str = "render-tree",
    style_artifact: Mapping[str, Any] | None = None,
    background: str = "#ffffff",
) -> dict[str, Any]:
    render_tree = _normalize_render_tree(render_tree_payload)
    style_ops = _style_ops_metadata(style_artifact)
    root_box = _layout_node(render_tree["root"], x=0, y=0)
    boxes = list(_flatten_boxes(root_box))
    layout = _layout_output(root_box, boxes)
    paint = _paint_output(root_box, background=background)
    return {
        "schemaVersion": 1,
        "format": "path0-external-backend-report",
        "backend": BACKEND_NAME,
        "source": source,
        "input": {
            "renderTreeHash": _contract_hash(render_tree),
            "nodeCount": render_tree["nodeCount"],
            "styleOps": style_ops,
        },
        "output": {
            "layout": layout,
            "paint": paint,
        },
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the experimental Path0 external JSON backend."
    )
    parser.add_argument(
        "--render-tree",
        required=True,
        help="Path to an otoe-render-tree JSON artifact.",
    )
    parser.add_argument(
        "--styles",
        help="Optional otoe-styles.json artifact to bind to the report.",
    )
    parser.add_argument(
        "--layout-out",
        required=True,
        help="Path to write path0-layout-output JSON.",
    )
    parser.add_argument(
        "--paint-out",
        required=True,
        help="Path to write path0-paint-output JSON.",
    )
    parser.add_argument(
        "--contract-out",
        help="Optional path to write the combined external backend report.",
    )
    parser.add_argument(
        "--source",
        default="render-tree",
        help="Human-readable input source label recorded in the report.",
    )
    parser.add_argument(
        "--background",
        default="#ffffff",
        help="Surface background color for the paint output.",
    )
    args = parser.parse_args(argv)

    try:
        render_tree = _load_json(Path(args.render_tree), label="render tree")
        styles = (
            _load_json(Path(args.styles), label="style artifact")
            if args.styles
            else None
        )
        report = run_external_path0_backend(
            render_tree,
            source=args.source,
            style_artifact=styles,
            background=args.background,
        )
        _write_json(Path(args.layout_out), report["output"]["layout"])
        _write_json(Path(args.paint_out), report["output"]["paint"])
        if args.contract_out:
            _write_json(Path(args.contract_out), report)
    except ExternalPath0BackendError as exc:
        parser.exit(2, f"path0 external backend error: {exc}\n")
    return 0


def _normalize_render_tree(payload: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        raise ExternalPath0BackendError(
            f"render tree must be a JSON object; got {type(payload).__name__}"
        )
    _reject_unexpected_keys(payload, RENDER_TREE_KEYS, context="render tree")
    _require_keys(payload, RENDER_TREE_KEYS, context="render tree")
    if payload["schemaVersion"] != 1:
        raise ExternalPath0BackendError(
            f"render tree schemaVersion must be 1; got {payload['schemaVersion']!r}"
        )
    if payload["format"] != "otoe-render-tree":
        raise ExternalPath0BackendError(
            "render tree format must be 'otoe-render-tree'; "
            f"got {payload['format']!r}"
        )
    node_count = _positive_int(payload["nodeCount"], context="render tree nodeCount")
    seen_ids: set[str] = set()
    seen_paths: set[tuple[int, ...]] = set()
    root = _normalize_node(
        payload["root"],
        expected_path=(),
        seen_ids=seen_ids,
        seen_paths=seen_paths,
    )
    actual_node_count = len(seen_paths)
    if actual_node_count != node_count:
        raise ExternalPath0BackendError(
            "render tree nodeCount must match nodes; "
            f"got {node_count}, expected {actual_node_count}"
        )
    return {
        "schemaVersion": 1,
        "format": "otoe-render-tree",
        "nodeCount": node_count,
        "root": root,
    }


def _normalize_node(
    payload: Any,
    *,
    expected_path: tuple[int, ...],
    seen_ids: set[str],
    seen_paths: set[tuple[int, ...]],
) -> dict[str, Any]:
    label = f"render node {list(expected_path)!r}"
    if not isinstance(payload, Mapping):
        raise ExternalPath0BackendError(
            f"{label} must be a JSON object; got {type(payload).__name__}"
        )
    _reject_unexpected_keys(payload, RENDER_NODE_KEYS, context=label)
    _require_keys(payload, RENDER_NODE_KEYS, context=label)
    node_id = _required_string(payload["id"], context=f"{label}.id")
    if node_id in seen_ids:
        raise ExternalPath0BackendError(f"render node id {node_id!r} is duplicated")
    seen_ids.add(node_id)
    path = _path(payload["path"], context=f"{label}.path")
    if path != expected_path:
        raise ExternalPath0BackendError(
            f"{label}.path must be {list(expected_path)!r}; got {list(path)!r}"
        )
    if path in seen_paths:
        raise ExternalPath0BackendError(f"render node path {list(path)!r} is duplicated")
    seen_paths.add(path)
    name = _required_string(payload["name"], context=f"{label}.name")
    if name not in SUPPORTED_WIDGETS:
        supported = ", ".join(sorted(SUPPORTED_WIDGETS))
        raise ExternalPath0BackendError(
            f"{label}.name {name!r} is not supported by {BACKEND_NAME}; "
            f"supported widgets: {supported}"
        )
    props = _json_object(payload["props"], context=f"{label}.props")
    style = _style_object(payload["style"], context=f"{label}.style")
    children_payload = payload["children"]
    if not isinstance(children_payload, list):
        raise ExternalPath0BackendError(f"{label}.children must be a list")
    children = [
        _normalize_node(
            child,
            expected_path=(*expected_path, index),
            seen_ids=seen_ids,
            seen_paths=seen_paths,
        )
        for index, child in enumerate(children_payload)
    ]
    if name in SUPPORTED_LEAVES and children:
        raise ExternalPath0BackendError(
            f"{label}.children must be empty for leaf widget {name!r}"
        )
    return {
        "id": node_id,
        "path": list(path),
        "name": name,
        "widgetId": _optional_string(payload["widgetId"], context=f"{label}.widgetId"),
        "key": _optional_string(payload["key"], context=f"{label}.key"),
        "className": _optional_string(
            payload["className"],
            context=f"{label}.className",
        ),
        "props": dict(sorted(props.items())),
        "events": list(_string_list(payload["events"], context=f"{label}.events")),
        "state": list(_string_list(payload["state"], context=f"{label}.state")),
        "context": _required_string(payload["context"], context=f"{label}.context"),
        "style": dict(sorted(style.items())),
        "children": children,
    }


def _layout_node(node: dict[str, Any], *, x: int, y: int) -> dict[str, Any]:
    if node["name"] in SUPPORTED_LEAVES:
        return _layout_leaf(node, x=x, y=y)
    return _layout_container(node, x=x, y=y)


def _layout_leaf(node: dict[str, Any], *, x: int, y: int) -> dict[str, Any]:
    style = node["style"]
    text = _node_text(node)
    font_size = _style_dimension(style, "fontSize", default=14)
    default_padding = 8 if node["name"] in {"Button", "Input"} else 0
    padding = _style_dimension(style, "padding", default=default_padding)
    border_width = _style_dimension(style, "borderWidth", default=0)
    width = max(1, math.ceil(len(text) * font_size * 0.55))
    height = max(1, math.ceil(font_size * 1.25))
    width += padding * 2 + border_width * 2
    height += padding * 2 + border_width * 2
    if node["name"] == "Input":
        width = max(width, 180)
    width = _style_dimension(style, "width", default=width)
    height = _style_dimension(style, "height", default=height)
    width = _style_constrain(width, style, min_name="minWidth", max_name="maxWidth")
    height = _style_constrain(height, style, min_name="minHeight", max_name="maxHeight")
    return _layout_box(node, x=x, y=y, width=width, height=height, text=text)


def _layout_container(node: dict[str, Any], *, x: int, y: int) -> dict[str, Any]:
    style = node["style"]
    padding = _style_dimension(style, "padding", default=0)
    gap = _style_dimension(style, "gap", default=0)
    scroll_y = (
        _style_dimension(style, "scrollY", default=0)
        if node["name"] == "ScrollView"
        else 0
    )
    direction = "row" if node["name"] == "HStack" else "column"
    cursor_x = x + padding
    cursor_y = y + padding - scroll_y
    content_width = 0
    content_height = 0
    children: list[dict[str, Any]] = []
    for index, child in enumerate(node["children"]):
        if index:
            if direction == "row":
                cursor_x += gap
            else:
                cursor_y += gap
        child_box = _layout_node(child, x=cursor_x, y=cursor_y)
        children.append(child_box)
        _child_x, _child_y, child_width, child_height = child_box["bounds"]
        if direction == "row":
            cursor_x += child_width
            content_width += child_width + (gap if index else 0)
            content_height = max(content_height, child_height)
        else:
            cursor_y += child_height
            content_width = max(content_width, child_width)
            content_height += child_height + (gap if index else 0)
    width = _style_dimension(style, "width", default=content_width + padding * 2)
    height = _style_dimension(style, "height", default=content_height + padding * 2)
    width = _style_constrain(width, style, min_name="minWidth", max_name="maxWidth")
    height = _style_constrain(height, style, min_name="minHeight", max_name="maxHeight")
    return _layout_box(
        node,
        x=x,
        y=y,
        width=width,
        height=height,
        children=children,
    )


def _layout_box(
    node: dict[str, Any],
    *,
    x: int,
    y: int,
    width: int,
    height: int,
    text: str | None = None,
    children: Sequence[dict[str, Any]] = (),
) -> dict[str, Any]:
    return {
        "path": list(node["path"]),
        "name": node["name"],
        "bounds": [x, y, width, height],
        "id": node["widgetId"],
        "context": node["context"],
        "text": text,
        "events": list(node["events"]),
        "state": list(node["state"]),
        "style": dict(node["style"]),
        "children": [list(child["path"]) for child in children],
        "_children": list(children),
    }


def _layout_output(
    root_box: dict[str, Any],
    boxes: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    payload = {
        "schemaVersion": 1,
        "format": "path0-layout-output",
        "boxCount": len(boxes),
        "rootPath": list(root_box["path"]),
        "boxes": [_public_box(box) for box in boxes],
    }
    return {**payload, "outputHash": _contract_hash(payload)}


def _paint_output(
    root_box: dict[str, Any],
    *,
    background: str,
) -> dict[str, Any]:
    root_bounds = root_box["bounds"]
    commands = [
        {
            "kind": "rect",
            "path": list(root_box["path"]),
            "bounds": [0, 0, max(root_bounds[2], 1), max(root_bounds[3], 1)],
            "fill": _color(background, default="#ffffff"),
            "stroke": None,
            "strokeWidth": 0,
            "radius": 0,
            "text": None,
            "color": None,
            "fontSize": 14,
            "clip": None,
            "context": f"{BACKEND_NAME} surface",
        }
    ]
    commands.extend(_paint_box(root_box, clip=None))
    payload = {
        "schemaVersion": 1,
        "format": "path0-paint-output",
        "width": max(root_bounds[2], 1),
        "height": max(root_bounds[3], 1),
        "commandCount": len(commands),
        "commands": commands,
    }
    return {**payload, "outputHash": _contract_hash(payload)}


def _paint_box(
    box: dict[str, Any],
    *,
    clip: list[int] | None,
) -> list[dict[str, Any]]:
    commands: list[dict[str, Any]] = []
    rect = _paint_rect(box, clip=clip)
    if rect is not None:
        commands.append(rect)
    if box["text"]:
        commands.append(_paint_text(box, clip=clip))
    child_clip = (
        _intersect_rects(clip, box["bounds"])
        if box["name"] == "ScrollView"
        else clip
    )
    for child in box["_children"]:
        commands.extend(_paint_box(child, clip=child_clip))
    return commands


def _paint_rect(
    box: dict[str, Any],
    *,
    clip: list[int] | None,
) -> dict[str, Any] | None:
    style = box["style"]
    fill = _paint_fill(box, style)
    stroke = _paint_stroke(box, style)
    stroke_width = _style_dimension(
        style,
        "borderWidth",
        default=1 if box["name"] in {"Button", "Input"} else 0,
    )
    radius = _style_dimension(
        style,
        "borderRadius",
        default=8 if box["name"] in {"Button", "Input"} else 0,
    )
    if fill is None and (stroke is None or stroke_width <= 0):
        return None
    return {
        "kind": "rect",
        "path": list(box["path"]),
        "bounds": list(box["bounds"]),
        "fill": fill,
        "stroke": stroke,
        "strokeWidth": stroke_width,
        "radius": radius,
        "text": None,
        "color": None,
        "fontSize": 14,
        "clip": list(clip) if clip is not None else None,
        "context": f"{BACKEND_NAME} {box['name']}",
    }


def _paint_text(box: dict[str, Any], *, clip: list[int] | None) -> dict[str, Any]:
    style = box["style"]
    font_size = _style_dimension(style, "fontSize", default=14)
    padding = (
        min(8, max(0, box["bounds"][2] // 4))
        if box["name"] in {"Button", "Input"}
        else 0
    )
    height = max(8, int(font_size * 0.85))
    return {
        "kind": "text",
        "path": list(box["path"]),
        "bounds": [
            box["bounds"][0] + padding,
            box["bounds"][1] + max(0, (box["bounds"][3] - height) // 2),
            max(1, box["bounds"][2] - padding * 2),
            height,
        ],
        "fill": None,
        "stroke": None,
        "strokeWidth": 0,
        "radius": 0,
        "text": box["text"],
        "color": _paint_text_color(box, style),
        "fontSize": font_size,
        "clip": list(clip) if clip is not None else None,
        "context": f"{BACKEND_NAME} {box['name']}",
    }


def _paint_fill(box: dict[str, Any], style: Mapping[str, Any]) -> str | None:
    background = _style_color(style, "background")
    if background is not None:
        return background
    if "disabled" in box["state"]:
        if box["name"] == "Button":
            return "#d1d5db"
        if box["name"] == "Input":
            return "#f3f4f6"
    if box["name"] == "Button":
        return "#1f2937"
    if box["name"] == "Input":
        return "#ffffff"
    return None


def _paint_stroke(box: dict[str, Any], style: Mapping[str, Any]) -> str | None:
    border_color = _style_color(style, "borderColor")
    if border_color is not None:
        return border_color
    if box["name"] == "Button":
        return "#111827"
    if box["name"] == "Input":
        return "#94a3b8"
    return None


def _paint_text_color(box: dict[str, Any], style: Mapping[str, Any]) -> str:
    color = _style_color(style, "color")
    if color is not None:
        return color
    if "disabled" in box["state"]:
        return "#64748b"
    if box["name"] == "Button":
        return "#ffffff"
    return "#111827"


def _style_ops_metadata(style_artifact: Mapping[str, Any] | None) -> dict[str, Any]:
    if style_artifact is None:
        return {"present": False}
    if not isinstance(style_artifact, Mapping):
        raise ExternalPath0BackendError(
            f"style artifact must be a JSON object; got {type(style_artifact).__name__}"
        )
    style_ops = style_artifact.get("styleOps")
    if not isinstance(style_ops, Mapping):
        raise ExternalPath0BackendError("style artifact must include a styleOps object")
    schema_version = style_ops.get("schemaVersion")
    format_name = style_ops.get("format")
    if schema_version != 1:
        raise ExternalPath0BackendError(
            f"styleOps schemaVersion must be 1; got {schema_version!r}"
        )
    if format_name != "otoe-style-ops":
        raise ExternalPath0BackendError(
            "styleOps format must be 'otoe-style-ops'; "
            f"got {format_name!r}"
        )
    return {
        "present": True,
        "schemaVersion": schema_version,
        "format": format_name,
        "artifactHash": _contract_hash(style_artifact),
    }


def _flatten_boxes(box: dict[str, Any]) -> tuple[dict[str, Any], ...]:
    result = [box]
    for child in box["_children"]:
        result.extend(_flatten_boxes(child))
    return tuple(result)


def _public_box(box: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in box.items() if key != "_children"}


def _node_text(node: Mapping[str, Any]) -> str:
    props = node["props"]
    if node["name"] == "Button":
        return str(props.get("label", ""))
    if node["name"] == "Input":
        return str(props.get("value") or props.get("placeholder") or "")
    return str(props.get("content", ""))


def _style_dimension(style: Mapping[str, Any], name: str, *, default: int) -> int:
    value = _style_raw_value(style.get(name))
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if math.isfinite(value):
            return max(0, int(value))
    return default


def _style_constrain(
    value: int,
    style: Mapping[str, Any],
    *,
    min_name: str,
    max_name: str,
) -> int:
    if max_name in style:
        value = min(value, _style_dimension(style, max_name, default=value))
    if min_name in style:
        value = max(value, _style_dimension(style, min_name, default=value))
    return value


def _style_color(style: Mapping[str, Any], name: str) -> str | None:
    value = _style_raw_value(style.get(name))
    return _color(value, default=None)


def _color(value: Any, *, default: str | None) -> str | None:
    if isinstance(value, str) and value.startswith("#"):
        return value
    return default


def _style_raw_value(value: Any) -> Any:
    if not isinstance(value, Mapping):
        return value
    kind = value.get("type")
    if kind == "size":
        if value.get("unit", "px") != "px":
            return None
        return value.get("value")
    if kind == "literal":
        return value.get("value")
    return None


def _intersect_rects(first: list[int] | None, second: list[int]) -> list[int]:
    if first is None:
        return list(second)
    ax, ay, aw, ah = first
    bx, by, bw, bh = second
    x1 = max(ax, bx)
    y1 = max(ay, by)
    x2 = min(ax + aw, bx + bw)
    y2 = min(ay + ah, by + bh)
    return [x1, y1, max(0, x2 - x1), max(0, y2 - y1)]


def _load_json(path: Path, *, label: str) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ExternalPath0BackendError(f"{label} file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ExternalPath0BackendError(f"{label} must be valid JSON: {exc}") from exc


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _reject_unexpected_keys(
    payload: Mapping[str, Any],
    expected: frozenset[str],
    *,
    context: str,
) -> None:
    extra = sorted(repr(key) for key in set(payload) - expected)
    if extra:
        raise ExternalPath0BackendError(
            f"{context} has unexpected fields: {', '.join(extra)}"
        )


def _require_keys(
    payload: Mapping[str, Any],
    expected: frozenset[str],
    *,
    context: str,
) -> None:
    missing = sorted(expected - set(payload))
    if missing:
        raise ExternalPath0BackendError(
            f"{context} missing required fields: "
            + ", ".join(repr(key) for key in missing)
        )


def _required_string(value: Any, *, context: str) -> str:
    if not isinstance(value, str) or not value:
        raise ExternalPath0BackendError(f"{context} must be a non-empty string")
    return value


def _optional_string(value: Any, *, context: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value:
        raise ExternalPath0BackendError(
            f"{context} must be a non-empty string or null"
        )
    return value


def _positive_int(value: Any, *, context: str) -> int:
    if type(value) is not int or value <= 0:
        raise ExternalPath0BackendError(f"{context} must be a positive integer")
    return value


def _path(value: Any, *, context: str) -> tuple[int, ...]:
    if not isinstance(value, list) or not all(
        type(item) is int and item >= 0
        for item in value
    ):
        raise ExternalPath0BackendError(
            f"{context} must be a list of non-negative integers"
        )
    return tuple(value)


def _json_object(value: Any, *, context: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ExternalPath0BackendError(f"{context} must be a JSON object")
    if not all(isinstance(key, str) and key for key in value):
        raise ExternalPath0BackendError(f"{context} keys must be non-empty strings")
    return dict(value)


def _style_object(value: Any, *, context: str) -> dict[str, Any]:
    style = _json_object(value, context=context)
    for name, item in style.items():
        if not isinstance(item, Mapping):
            raise ExternalPath0BackendError(
                f"{context}.{name} must be a serialized style value"
            )
        kind = item.get("type")
        if kind not in {"literal", "size", "token"}:
            raise ExternalPath0BackendError(
                f"{context}.{name}.type must be literal, size, or token"
            )
    return style


def _string_list(value: Any, *, context: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(
        isinstance(item, str) and item
        for item in value
    ):
        raise ExternalPath0BackendError(f"{context} must be a list of non-empty strings")
    return tuple(value)


def _contract_hash(payload: Any) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


if __name__ == "__main__":
    raise SystemExit(main())
