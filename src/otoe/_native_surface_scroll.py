from __future__ import annotations

from typing import Any

from ._native_contracts import NativeLayout
from ._native_hit_test import hit_test_native
from ._native_shared import clamp_scroll_y, max_scroll_y, scroll_y, widget_by_path
from .mount import FakeWidget


def dispatch_scroll(
    root: FakeWidget,
    layout: NativeLayout,
    x: int,
    y: int,
    delta_y: int,
) -> tuple[bool, Any]:
    hit = hit_test_native(layout, x, y, event="onScroll")
    if hit is None:
        return False, None
    widget = widget_by_path(root, hit.path)
    if widget.name != "ScrollView" or "onScroll" not in widget.events:
        return False, None

    current_scroll_y = scroll_y(widget)
    next_scroll_y = clamp_scroll_y(
        current_scroll_y + int(delta_y),
        max_scroll_y=max_scroll_y(hit),
    )
    if next_scroll_y == current_scroll_y:
        return False, None

    return True, widget.trigger("onScroll", next_scroll_y)
