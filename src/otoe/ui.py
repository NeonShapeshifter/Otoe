from __future__ import annotations

from typing import Any

from .component import component
from .control import Show
from .reactive import computed, is_reactive
from .widgets import Button, HStack, Panel, Text, VStack


def class_names(*parts: Any) -> str:
    names: list[str] = []
    for part in parts:
        if not part:
            continue
        names.extend(str(part).split())
    return " ".join(dict.fromkeys(names))


@component
def Card(*children, className: str | None = None, tone: str = "default", title=None):
    return Panel(
        *children,
        className=class_names("ui-card", f"is-{tone}", className),
        title=title,
    )


@component
def Badge(label, *, tone: str = "neutral", className: str | None = None):
    return Text(
        label,
        className=class_names("ui-badge", f"is-{tone}", className),
    )


@component
def ActionButton(
    label,
    *,
    variant: str = "primary",
    size: str = "md",
    className: str | None = None,
    disabled: bool = False,
    onClick=None,
):
    props = {
        "className": class_names("ui-button", f"is-{variant}", f"is-{size}", className),
        "disabled": disabled,
    }
    if onClick is not None:
        props["onClick"] = onClick
    return Button(label, **props)


@component
def Toolbar(*children, className: str | None = None, gap: int = 8):
    return HStack(
        *children,
        className=class_names("ui-toolbar", className),
        gap=gap,
    )


@component
def Tabs(
    *children,
    className: str | None = None,
    gap: int = 6,
    orientation: str = "horizontal",
):
    container = VStack if orientation == "vertical" else HStack
    return container(
        *children,
        className=class_names("ui-tabs", f"is-{orientation}", className),
        gap=gap,
    )


@component
def TabButton(
    label,
    *,
    active=False,
    className: str | None = None,
    onClick=None,
):
    props = {
        "className": _active_class("ui-tab", active, className),
    }
    if onClick is not None:
        props["onClick"] = onClick
    return Button(label, **props)


@component
def StatCard(
    *,
    label,
    value,
    detail=None,
    tone: str = "neutral",
    className: str | None = None,
):
    return Card(
        VStack(
            Text(label, className="ui-stat-label"),
            Text(value, className="ui-stat-value"),
            Show(
                Text(detail, className=class_names("ui-stat-detail", f"is-{tone}")),
                when=computed(lambda: _has_value(detail)),
            ),
            className="ui-stat-body",
        ),
        className=class_names("ui-stat-card", className),
    )


def _active_class(base: str, active, extra: str | None):
    if is_reactive(active):
        return computed(lambda: class_names(base, extra, "is-active" if active.value else None))
    return class_names(base, extra, "is-active" if active else None)


def _has_value(value: Any) -> bool:
    if is_reactive(value):
        return value.value is not None
    return value is not None
