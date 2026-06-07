from __future__ import annotations

from typing import Any


def _candidate_style_dimension(
    style: dict[str, Any],
    name: str,
    *,
    default: int,
) -> int:
    value = style.get(name)
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return max(0, int(value))
    raw_value = getattr(value, "value", None)
    if isinstance(raw_value, (int, float)):
        return max(0, int(raw_value))
    return default


def _candidate_style_constrain(
    value: int,
    style: dict[str, Any],
    *,
    min_name: str,
    max_name: str,
) -> int:
    if max_name in style:
        value = min(value, _candidate_style_dimension(style, max_name, default=value))
    if min_name in style:
        value = max(value, _candidate_style_dimension(style, min_name, default=value))
    return value


def _candidate_style_color(value: Any, *, default: str) -> str:
    return value if isinstance(value, str) and value.startswith("#") else default


def _candidate_intersect_rects(
    first: tuple[int, int, int, int] | None,
    second: tuple[int, int, int, int],
) -> tuple[int, int, int, int]:
    if first is None:
        return second
    ax, ay, aw, ah = first
    bx, by, bw, bh = second
    x1 = max(ax, bx)
    y1 = max(ay, by)
    x2 = min(ax + aw, bx + bw)
    y2 = min(ay + ah, by + bh)
    return (x1, y1, max(0, x2 - x1), max(0, y2 - y1))


def _target_name(target: Any) -> str:
    widget = getattr(target, "widget", None)
    if widget is not None:
        return str(getattr(widget, "name", type(widget).__name__))
    return str(getattr(target, "name", type(target).__name__))
