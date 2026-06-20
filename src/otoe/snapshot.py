from __future__ import annotations

import json
from typing import Any

from .mount import FakeWidget, MountedNode, root_widget


def snapshot(target: FakeWidget | MountedNode) -> dict[str, Any]:
    widget = root_widget(target) if isinstance(target, MountedNode) else target
    return {
        "name": widget.name,
        "props": _stable_props(widget.props),
        "events": sorted(widget.events),
        "children": [snapshot(child) for child in widget.children],
    }


def snapshot_text(target: FakeWidget | MountedNode) -> str:
    return json.dumps(snapshot(target), indent=2, sort_keys=True)


def _stable_props(props: dict[str, Any]) -> dict[str, Any]:
    return {key: _jsonable(props[key]) for key in sorted(props)}


def _jsonable(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, tuple):
        return [_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {
            str(key): _jsonable(val)
            for key, val in sorted(value.items(), key=lambda item: str(item[0]))
        }
    return repr(value)
