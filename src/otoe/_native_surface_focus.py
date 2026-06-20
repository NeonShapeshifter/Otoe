from __future__ import annotations

from ._native_contracts import LayoutBox, NativeLayout
from ._native_shared import (
    visible_through_scroll_ancestors,
    widget_by_path,
    widget_context,
)
from .mount import FakeWidget


FOCUSABLE_WIDGETS = frozenset({"Button", "Input"})


def is_focusable_widget(widget: FakeWidget) -> bool:
    if widget.props.get("disabled"):
        return False
    return widget.name in FOCUSABLE_WIDGETS


def is_focusable_path(root: FakeWidget, path: tuple[int, ...]) -> bool:
    try:
        widget = widget_by_path(root, path)
    except KeyError:
        return False
    return is_focusable_widget(widget)


def focusable_paths(
    layout: NativeLayout,
    root: FakeWidget,
) -> list[tuple[int, ...]]:
    return [
        box.path
        for box in layout.boxes
        if is_focusable_widget(widget_by_path(root, box.path))
    ]


def first_autofocus_path(
    layout: NativeLayout,
    root: FakeWidget,
) -> tuple[int, ...] | None:
    for box in layout.boxes:
        candidate = widget_by_path(root, box.path)
        if candidate.props.get("autoFocus") and is_focusable_widget(candidate):
            return box.path
    return None


def hit_test_focusable(
    layout: NativeLayout,
    root: FakeWidget,
    x: int,
    y: int,
) -> LayoutBox | None:
    containing = [
        box
        for box in layout.boxes
        if box.contains(x, y)
        and visible_through_scroll_ancestors(layout, box, x, y)
        and is_focusable_widget(widget_by_path(root, box.path))
    ]
    if not containing:
        return None
    return max(
        enumerate(containing),
        key=lambda item: (len(item[1].path), item[0]),
    )[1]


def focus_error_message(root: FakeWidget, path: tuple[int, ...]) -> str:
    try:
        widget = widget_by_path(root, path)
    except KeyError:
        return f"No focusable native box exists at path {path!r}: no native widget exists."
    if widget.props.get("disabled"):
        return (
            f"No focusable native box exists at path {path!r}: "
            f"{widget_context(widget)} is disabled."
        )
    return (
        f"No focusable native box exists at path {path!r}: "
        f"{widget_context(widget)} is {widget.name}, not a focusable native control."
    )
