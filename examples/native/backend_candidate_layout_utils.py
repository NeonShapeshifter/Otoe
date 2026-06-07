from __future__ import annotations

from typing import Any

from otoe import LayoutBox


def _layout_candidate_text(widget: Any) -> str:
    if widget.name == "Button":
        return str(widget.props.get("label", ""))
    if widget.name == "Input":
        return str(widget.props.get("value") or widget.props.get("placeholder") or "")
    return str(widget.props.get("content", ""))


def _layout_candidate_offset(box: LayoutBox, *, dx: int = 0, dy: int = 0) -> LayoutBox:
    return LayoutBox(
        path=box.path,
        name=box.name,
        x=box.x + dx,
        y=box.y + dy,
        width=box.width,
        height=box.height,
        id=box.id,
        context=box.context,
        text=box.text,
        events=box.events,
        state=box.state,
        style=box.style,
        children=tuple(
            _layout_candidate_offset(child, dx=dx, dy=dy)
            for child in box.children
        ),
    )


def _layout_candidate_offset_y(box: LayoutBox, delta: int) -> LayoutBox:
    return _layout_candidate_offset(box, dy=delta)


def _candidate_root_widget(target: Any) -> Any:
    if hasattr(target, "root_widget"):
        return target.root_widget()
    return target


def _candidate_flatten(box: LayoutBox) -> list[LayoutBox]:
    boxes = [box]
    for child in box.children:
        boxes.extend(_candidate_flatten(child))
    return boxes


def _candidate_widget_context(widget: Any) -> str:
    stack = getattr(widget, "component_stack", ())
    if not stack:
        return widget.name
    return " > ".join((*stack, widget.name))


def _candidate_widget_state(widget: Any) -> tuple[str, ...]:
    return ("disabled",) if widget.props.get("disabled") else ()


def _candidate_optional_string(value: Any) -> str | None:
    return value if isinstance(value, str) else None
