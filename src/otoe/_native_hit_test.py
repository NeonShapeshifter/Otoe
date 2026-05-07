from __future__ import annotations

from typing import Any

from ._native_contracts import LayoutBox, NativeLayout
from ._native_shared import (
    ancestor_paths,
    visible_through_scroll_ancestors,
    widget_by_path,
)
from .mount import FakeWidget, MountedNode, root_widget


def hit_test_native(
    layout: NativeLayout,
    x: int,
    y: int,
    *,
    event: str = "onClick",
) -> LayoutBox | None:
    containing = [
        box
        for box in layout.boxes
        if box.contains(x, y) and visible_through_scroll_ancestors(layout, box, x, y)
    ]
    if not containing:
        return None

    deepest = max(containing, key=lambda box: len(box.path))
    for path in ancestor_paths(deepest.path):
        box = layout.by_path(path)
        if event in box.events:
            return box
    return None


def dispatch_native_click(
    target: FakeWidget | MountedNode,
    layout: NativeLayout,
    x: int,
    y: int,
) -> Any:
    hit = hit_test_native(layout, x, y, event="onClick")
    if hit is None:
        return None
    widget = root_widget(target) if isinstance(target, MountedNode) else target
    target_widget = widget_by_path(widget, hit.path)
    if target_widget.props.get("disabled"):
        return None
    return target_widget.trigger("onClick")
