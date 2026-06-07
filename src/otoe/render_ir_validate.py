from __future__ import annotations

import json
from typing import Any

from .render_ir_types import (
    RENDER_TREE_SCHEMA_VERSION,
    RenderIRError,
    RenderNode,
    RenderTree,
    _jsonable_value,
)
from .style import style_value_to_dict


def validate_render_tree(tree: RenderTree) -> list[str]:
    errors: list[str] = []
    if not isinstance(tree, RenderTree):
        return [f"RenderTree must be a RenderTree instance; got {type(tree).__name__}"]
    if (
        type(tree.schema_version) is not int
        or tree.schema_version != RENDER_TREE_SCHEMA_VERSION
    ):
        errors.append(
            "RenderTree schemaVersion must be "
            f"{RENDER_TREE_SCHEMA_VERSION}; got {tree.schema_version!r}"
        )
    if tree.format != "otoe-render-tree":
        errors.append(
            "RenderTree format must be 'otoe-render-tree'; "
            f"got {tree.format!r}"
        )
    errors.extend(_validate_render_node(tree.root, expected_path=()))
    seen_ids: set[str] = set()
    seen_paths: set[tuple[int, ...]] = set()
    for node in _walk_render_nodes_safe(tree.root):
        if isinstance(node, RenderNode):
            if isinstance(node.node_id, str):
                if node.node_id in seen_ids:
                    errors.append(f"RenderTree node id {node.node_id!r} is duplicated")
                seen_ids.add(node.node_id)
            if _valid_path(node.path) and node.path in seen_paths:
                errors.append(f"RenderTree node path {list(node.path)!r} is duplicated")
            if _valid_path(node.path):
                seen_paths.add(node.path)
    return errors


def assert_render_tree_valid(tree: RenderTree) -> None:
    errors = validate_render_tree(tree)
    if errors:
        raise RenderIRError("; ".join(errors))


def _validate_render_node(
    node: Any,
    *,
    expected_path: tuple[int, ...],
) -> list[str]:
    if not isinstance(node, RenderNode):
        return [
            "RenderTree node at "
            f"{list(expected_path)!r} must be a RenderNode; got {type(node).__name__}"
        ]
    errors: list[str] = []
    prefix = f"RenderTree node {node.node_id!r}"
    if not isinstance(node.node_id, str) or not node.node_id:
        errors.append(f"RenderTree node at {list(expected_path)!r} id must be non-empty")
    if not _valid_path(node.path):
        errors.append(f"{prefix} path must be a tuple of non-negative integers")
    elif node.path != expected_path:
        errors.append(
            f"{prefix} path must be {list(expected_path)!r}; got {list(node.path)!r}"
        )
    if not isinstance(node.name, str) or not node.name:
        errors.append(f"{prefix} name must be a non-empty string")
    for field_name, value in (
        ("widget_id", node.widget_id),
        ("key", node.key),
        ("class_name", node.class_name),
    ):
        if value is not None and (not isinstance(value, str) or not value):
            errors.append(f"{prefix} {field_name} must be a non-empty string or None")
    if not _valid_string_tuple(node.events):
        errors.append(f"{prefix} events must be a tuple of non-empty strings")
    if not _valid_string_tuple(node.state):
        errors.append(f"{prefix} state must be a tuple of non-empty strings")
    if not isinstance(node.context, str):
        errors.append(f"{prefix} context must be a string")
    errors.extend(
        _validate_named_value_tuple(
            node.props,
            prefix=f"{prefix} props",
            value_label="prop",
            serializer=_jsonable_value,
        )
    )
    errors.extend(
        _validate_named_value_tuple(
            node.style,
            prefix=f"{prefix} style",
            value_label="style",
            serializer=style_value_to_dict,
        )
    )
    if not isinstance(node.children, tuple):
        errors.append(f"{prefix} children must be a tuple")
        return errors
    for index, child in enumerate(node.children):
        errors.extend(
            _validate_render_node(
                child,
                expected_path=(*expected_path, index),
            )
        )
    return errors


def _walk_render_nodes_safe(node: Any) -> tuple[Any, ...]:
    nodes = [node]
    if isinstance(node, RenderNode) and isinstance(node.children, tuple):
        for child in node.children:
            nodes.extend(_walk_render_nodes_safe(child))
    return tuple(nodes)


def _valid_path(path: Any) -> bool:
    return (
        isinstance(path, tuple)
        and all(
            isinstance(item, int) and not isinstance(item, bool) and item >= 0
            for item in path
        )
    )


def _valid_string_tuple(value: Any) -> bool:
    return isinstance(value, tuple) and all(
        isinstance(item, str) and item for item in value
    )


def _validate_named_value_tuple(
    values: Any,
    *,
    prefix: str,
    value_label: str,
    serializer,
) -> list[str]:
    if not isinstance(values, tuple):
        return [f"{prefix} must be a tuple of name/value pairs"]
    errors: list[str] = []
    seen: set[str] = set()
    for index, item in enumerate(values):
        if not isinstance(item, tuple) or len(item) != 2:
            errors.append(f"{prefix}[{index}] must be a name/value tuple")
            continue
        name, value = item
        if not isinstance(name, str) or not name:
            errors.append(f"{prefix}[{index}] name must be a non-empty string")
            continue
        if name in seen:
            errors.append(f"{prefix} name {name!r} is duplicated")
        seen.add(name)
        try:
            json.dumps(serializer(value), sort_keys=True)
        except (TypeError, ValueError) as exc:
            errors.append(
                f"{prefix} {value_label} {name!r} must be JSON serializable: {exc}"
            )
    return errors
