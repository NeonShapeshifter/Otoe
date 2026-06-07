from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .render_ir_types import (
    RenderIRError,
    RenderNode,
    RenderTree,
    _jsonable_value,
)
from .render_ir_validate import assert_render_tree_valid
from .style import style_value_from_dict, style_value_to_dict


_RENDER_TREE_KEYS = frozenset({"schemaVersion", "format", "nodeCount", "root"})
_RENDER_NODE_KEYS = frozenset(
    {
        "id",
        "path",
        "name",
        "widgetId",
        "key",
        "className",
        "props",
        "events",
        "state",
        "context",
        "style",
        "children",
    }
)


def render_tree_to_dict(tree: RenderTree) -> dict[str, Any]:
    return {
        "schemaVersion": tree.schema_version,
        "format": tree.format,
        "nodeCount": tree.node_count,
        "root": render_node_to_dict(tree.root),
    }


def render_tree_from_dict(payload: Mapping[str, Any]) -> RenderTree:
    if not isinstance(payload, Mapping):
        raise RenderIRError(
            "RenderTree payload must be a JSON object; "
            f"got {type(payload).__name__}"
        )
    _reject_unexpected_keys(payload, _RENDER_TREE_KEYS, context="RenderTree")
    _require_keys(payload, _RENDER_TREE_KEYS, context="RenderTree")
    schema_version = _integer_from_payload(
        payload["schemaVersion"],
        context="RenderTree schemaVersion",
    )
    format_name = payload["format"]
    if not isinstance(format_name, str):
        raise RenderIRError("RenderTree format must be a string")
    node_count = _integer_from_payload(
        payload["nodeCount"],
        context="RenderTree nodeCount",
        non_negative=True,
    )
    root = _render_node_from_dict(payload["root"], path="root")
    tree = RenderTree(
        root=root,
        schema_version=schema_version,
        format=format_name,
    )
    assert_render_tree_valid(tree)
    if tree.node_count != node_count:
        raise RenderIRError(
            f"RenderTree nodeCount must match nodes; got {node_count}, "
            f"expected {tree.node_count}"
        )
    return tree


def load_render_tree_artifact(path: str | Path) -> RenderTree:
    artifact_path = Path(path)
    payload = json.loads(artifact_path.read_text(encoding="utf-8"))
    try:
        return render_tree_from_dict(payload)
    except RenderIRError as exc:
        raise RenderIRError(f"{artifact_path}: {exc}") from exc


def render_node_to_dict(node: RenderNode) -> dict[str, Any]:
    return {
        "id": node.node_id,
        "path": list(node.path),
        "name": node.name,
        "widgetId": node.widget_id,
        "key": node.key,
        "className": node.class_name,
        "props": {name: _jsonable_value(value) for name, value in node.props},
        "events": list(node.events),
        "state": list(node.state),
        "context": node.context,
        "style": {
            name: style_value_to_dict(value)
            for name, value in node.style
        },
        "children": [render_node_to_dict(child) for child in node.children],
    }


def _render_node_from_dict(payload: Any, *, path: str) -> RenderNode:
    if not isinstance(payload, Mapping):
        raise RenderIRError(
            f"RenderTree {path} must be a JSON object; got {type(payload).__name__}"
        )
    _reject_unexpected_keys(payload, _RENDER_NODE_KEYS, context=f"RenderTree {path}")
    _require_keys(payload, _RENDER_NODE_KEYS, context=f"RenderTree {path}")
    node_id = _required_string(payload["id"], context=f"RenderTree {path}.id")
    node_path = _path_from_payload(payload["path"], context=f"RenderTree {path}.path")
    name = _required_string(payload["name"], context=f"RenderTree {path}.name")
    widget_id = _optional_string_payload(
        payload["widgetId"],
        context=f"RenderTree {path}.widgetId",
    )
    key = _optional_string_payload(payload["key"], context=f"RenderTree {path}.key")
    class_name = _optional_string_payload(
        payload["className"],
        context=f"RenderTree {path}.className",
    )
    props = _props_from_payload(payload["props"], context=f"RenderTree {path}.props")
    events = _string_tuple_from_payload(
        payload["events"],
        context=f"RenderTree {path}.events",
    )
    state = _string_tuple_from_payload(
        payload["state"],
        context=f"RenderTree {path}.state",
    )
    context = _required_string(payload["context"], context=f"RenderTree {path}.context")
    style = _style_from_payload(payload["style"], context=f"RenderTree {path}.style")
    children_payload = payload["children"]
    if not isinstance(children_payload, list):
        raise RenderIRError(f"RenderTree {path}.children must be a list")
    children = tuple(
        _render_node_from_dict(child, path=f"{path}.children[{index}]")
        for index, child in enumerate(children_payload)
    )
    return RenderNode(
        node_id=node_id,
        path=node_path,
        name=name,
        widget_id=widget_id,
        key=key,
        class_name=class_name,
        props=props,
        events=events,
        state=state,
        context=context,
        style=style,
        children=children,
    )


def _reject_unexpected_keys(
    payload: Mapping[str, Any],
    expected: frozenset[str],
    *,
    context: str,
) -> None:
    extra = sorted(repr(key) for key in set(payload) - expected)
    if extra:
        raise RenderIRError(
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
        raise RenderIRError(
            f"{context} missing required fields: "
            + ", ".join(repr(key) for key in missing)
        )


def _required_string(value: Any, *, context: str) -> str:
    if not isinstance(value, str) or not value:
        raise RenderIRError(f"{context} must be a non-empty string")
    return value


def _optional_string_payload(value: Any, *, context: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value:
        raise RenderIRError(f"{context} must be a non-empty string or null")
    return value


def _integer_from_payload(
    value: Any,
    *,
    context: str,
    non_negative: bool = False,
) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        suffix = "a non-negative integer" if non_negative else "an integer"
        raise RenderIRError(f"{context} must be {suffix}")
    if non_negative and value < 0:
        raise RenderIRError(f"{context} must be a non-negative integer")
    return value


def _path_from_payload(value: Any, *, context: str) -> tuple[int, ...]:
    if not isinstance(value, list) or not all(
        isinstance(item, int) and not isinstance(item, bool) and item >= 0
        for item in value
    ):
        raise RenderIRError(f"{context} must be a list of non-negative integers")
    return tuple(value)


def _props_from_payload(value: Any, *, context: str) -> tuple[tuple[str, Any], ...]:
    if not isinstance(value, Mapping):
        raise RenderIRError(f"{context} must be a JSON object")
    props: list[tuple[str, Any]] = []
    for name, item in value.items():
        if not isinstance(name, str) or not name:
            raise RenderIRError(f"{context} keys must be non-empty strings")
        _assert_json_value(item, context=f"{context}.{name}")
        props.append((name, _freeze_json_value(item)))
    return tuple(sorted(props))


def _string_tuple_from_payload(value: Any, *, context: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(
        isinstance(item, str) and item for item in value
    ):
        raise RenderIRError(f"{context} must be a list of non-empty strings")
    return tuple(value)


def _style_from_payload(value: Any, *, context: str) -> tuple[tuple[str, Any], ...]:
    if not isinstance(value, Mapping):
        raise RenderIRError(f"{context} must be a JSON object")
    style: list[tuple[str, Any]] = []
    for name, item in value.items():
        if not isinstance(name, str) or not name:
            raise RenderIRError(f"{context} keys must be non-empty strings")
        if not isinstance(item, Mapping):
            raise RenderIRError(f"{context}.{name} must be a serialized style value")
        try:
            style.append((name, style_value_from_dict(dict(item))))
        except Exception as exc:
            raise RenderIRError(f"{context}.{name}: {exc}") from exc
    return tuple(sorted(style))


def _assert_json_value(value: Any, *, context: str) -> None:
    if value is None or isinstance(value, (str, int, float, bool)):
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _assert_json_value(item, context=f"{context}[{index}]")
        return
    if isinstance(value, Mapping):
        for key, item in value.items():
            if not isinstance(key, str):
                raise RenderIRError(f"{context} object keys must be strings")
            _assert_json_value(item, context=f"{context}.{key}")
        return
    raise RenderIRError(f"{context} must be a JSON value; got {type(value).__name__}")


def _freeze_json_value(value: Any) -> Any:
    if isinstance(value, list):
        return tuple(_freeze_json_value(item) for item in value)
    if isinstance(value, Mapping):
        return tuple(
            sorted((str(key), _freeze_json_value(item)) for key, item in value.items())
        )
    return value
