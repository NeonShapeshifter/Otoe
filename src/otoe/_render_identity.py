from __future__ import annotations

import json
from typing import Any


def render_node_id(
    *,
    parent_id: str | None,
    name: str,
    path: tuple[int, ...],
    widget_id: str | None,
    key_label: str | None,
) -> str:
    if parent_id is None:
        return f"root:{widget_id or name}"
    if widget_id is not None:
        segment = f"id:{widget_id}"
    elif key_label is not None:
        segment = f"key:{key_label}"
    else:
        segment = f"index:{path[-1] if path else 0}"
    return f"{parent_id}/{segment}:{name}"


def render_key_label(value: Any) -> str | None:
    if value is None:
        return None
    try:
        return json.dumps(value, sort_keys=True)
    except TypeError:
        return repr(value)


def optional_string(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None


def mounted_child_key(mounted: Any, child: Any) -> Any:
    if mounted is None or child is None:
        return None
    keyed_children = getattr(mounted, "_keyed_children", None)
    if not isinstance(keyed_children, dict):
        return None
    child_identity = id(child)
    for key, keyed_child in keyed_children.items():
        if id(keyed_child) == child_identity:
            return key
    return None
