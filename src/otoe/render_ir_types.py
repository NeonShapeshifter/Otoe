from __future__ import annotations

from dataclasses import dataclass
from typing import Any


RENDER_TREE_SCHEMA_VERSION = 1


class RenderIRError(ValueError):
    pass


@dataclass(frozen=True)
class RenderNode:
    node_id: str
    path: tuple[int, ...]
    name: str
    widget_id: str | None
    key: str | None
    class_name: str | None
    props: tuple[tuple[str, Any], ...]
    events: tuple[str, ...]
    state: tuple[str, ...]
    context: str
    style: tuple[tuple[str, Any], ...]
    children: tuple["RenderNode", ...] = ()

    def prop_dict(self) -> dict[str, Any]:
        return dict(self.props)

    def style_dict(self) -> dict[str, Any]:
        return dict(self.style)


def walk_render_nodes(node: RenderNode) -> tuple[RenderNode, ...]:
    nodes = [node]
    for child in node.children:
        nodes.extend(walk_render_nodes(child))
    return tuple(nodes)


@dataclass(frozen=True)
class RenderTree:
    root: RenderNode
    schema_version: int = RENDER_TREE_SCHEMA_VERSION
    format: str = "otoe-render-tree"

    @property
    def node_count(self) -> int:
        return sum(1 for _node in walk_render_nodes(self.root))


def _jsonable_value(value: Any) -> Any:
    if isinstance(value, tuple):
        if all(
            isinstance(item, tuple) and len(item) == 2 and isinstance(item[0], str)
            for item in value
        ):
            return {key: _jsonable_value(item) for key, item in value}
        return [_jsonable_value(item) for item in value]
    if isinstance(value, list):
        return [_jsonable_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _jsonable_value(item) for key, item in value.items()}
    return value
