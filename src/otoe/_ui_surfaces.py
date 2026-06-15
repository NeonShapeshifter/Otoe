from __future__ import annotations

from typing import Any

from ._ui_helpers import (
    _active_class,
    _as_node,
    _has_value,
    _multi_variant_class,
    _slot_node,
    _value,
    _variant_class,
    class_names,
)
from ._ui_theme import _surface_class
from .component import component
from .control import Show
from .reactive import computed, is_reactive
from .widgets import Button, HStack, Panel, Text, VStack

__all__ = [
    "Card",
    "StatusPill",
    "Surface",
    "MetricGrid",
    "MetricTile",
    "Badge",
    "ActionButton",
    "Toolbar",
    "Tabs",
    "TabButton",
    "StatCard",
    "SectionHeader",
    "EmptyState",
    "ListRow",
]

@component
def Card(
    *children,
    className: str | None = None,
    tone: str = "default",
    title=None,
    padding=None,
    gap=None,
):
    if padding is not None or gap is not None:
        body_props: dict[str, Any] = {"className": "ui-card-body"}
        if padding is not None:
            body_props["padding"] = padding
        if gap is not None:
            body_props["gap"] = gap
        children = (VStack(*children, **body_props),)
    return Panel(
        *children,
        className=_variant_class("ui-card", tone, className),
        title=title,
    )

@component
def StatusPill(label, *, tone: str = "neutral", className: str | None = None):
    return Badge(
        label,
        tone=tone,
        className=class_names("ui-status-pill shrink-0", className),
    )

@component
def Surface(
    *children,
    title=None,
    detail=None,
    badge=None,
    badge_tone: str = "neutral",
    actions=None,
    tone: str = "default",
    padding: int = 16,
    gap: int = 12,
    className: str | None = None,
):
    body = []
    if title is not None:
        body.append(
            SectionHeader(
                title,
                detail=detail,
                badge=badge,
                badge_tone=badge_tone,
                actions=actions,
            )
        )
    body.extend(children)
    return Card(
        *body,
        padding=padding,
        gap=gap,
        className=_surface_class("ui-surface rounded-xl shadow-sm", tone, className),
    )

@component
def MetricGrid(*children, className: str | None = None):
    return HStack(
        *children,
        className=class_names("ui-metric-grid gap-3 flex-wrap", className),
    )

@component
def MetricTile(
    *,
    label,
    value,
    detail=None,
    tone: str = "neutral",
    className: str | None = None,
):
    return StatCard(
        label=label,
        value=value,
        detail=detail,
        tone=tone,
        className=_surface_class("ui-metric-tile flex-1 min-w-0 rounded-xl shadow-sm", tone, className),
    )

@component
def Badge(label, *, tone: str = "neutral", className: str | None = None):
    return Text(
        label,
        className=_variant_class("ui-badge", tone, className),
    )

@component
def ActionButton(
    label,
    *,
    variant: str = "primary",
    size: str = "md",
    className: str | None = None,
    disabled: bool = False,
    leading=None,
    trailing=None,
    full_width: bool = False,
    onClick=None,
):
    button_class = _multi_variant_class("ui-button", variant, size, className)
    if full_width:
        if is_reactive(button_class):
            base_class = button_class
            button_class = computed(lambda: class_names(base_class.value, "is-full"))
        else:
            button_class = class_names(button_class, "is-full")
    props = {
        "className": button_class,
        "disabled": disabled,
    }
    if onClick is not None:
        props["onClick"] = onClick
    if leading is not None or trailing is not None:
        content = []
        if leading is not None:
            content.append(_slot_node(leading, "ui-button-leading"))
        content.append(Text(label, className="ui-button-label"))
        if trailing is not None:
            content.append(_slot_node(trailing, "ui-button-trailing"))
        return Button(
            label,
            HStack(*content, className="ui-button-content", gap=8),
            **props,
        )
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
        className=_variant_class("ui-tabs", orientation, className),
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
    detail_class = (
        computed(lambda: class_names("ui-stat-detail", f"is-{_value(tone)}"))
        if is_reactive(tone)
        else class_names("ui-stat-detail", f"is-{tone}")
    )
    return Card(
        VStack(
            Text(label, className="ui-stat-label"),
            Text(value, className="ui-stat-value"),
            Show(
                Text(detail, className=detail_class),
                when=computed(lambda: _has_value(detail)),
            ),
            className="ui-stat-body",
        ),
        className=class_names("ui-stat-card", className),
    )

@component
def SectionHeader(
    title,
    *,
    detail=None,
    badge=None,
    badge_tone: str = "neutral",
    actions=None,
    action_label=None,
    on_action=None,
    action_variant: str = "ghost",
    className: str | None = None,
):
    if actions is None and action_label is not None:
        actions = ActionButton(
            action_label,
            variant=action_variant,
            size="sm",
            onClick=on_action,
        )
    children = [
        VStack(
            Text(title, className="ui-section-title"),
            Show(
                Text(detail, className="ui-section-detail"),
                when=computed(lambda: _has_value(detail)),
            ),
            className="ui-section-copy",
            gap=2,
        ),
        Show(
            Badge(badge, tone=badge_tone, className="ui-section-badge"),
            when=computed(lambda: _has_value(badge)),
        ),
    ]
    if actions is not None:
        children.append(_slot_node(actions, "ui-section-actions"))
    return HStack(
        *children,
        className=class_names("ui-section-header", className),
        gap=10,
    )

@component
def EmptyState(
    title,
    *,
    description=None,
    action=None,
    action_label=None,
    on_action=None,
    action_variant: str = "ghost",
    className: str | None = None,
):
    if action is None and action_label is not None:
        action = ActionButton(
            action_label,
            variant=action_variant,
            size="sm",
            onClick=on_action,
        )
    children = [
        Text(title, className="ui-empty-title"),
        Show(
            Text(description, className="ui-empty-description"),
            when=computed(lambda: _has_value(description)),
        ),
    ]
    if action is not None:
        children.append(_slot_node(action, "ui-empty-action"))
    return VStack(
        *children,
        className=class_names("ui-empty-state", className),
        gap=4,
    )

@component
def ListRow(
    *,
    title,
    detail=None,
    meta=None,
    badge=None,
    badge_tone: str = "neutral",
    tone: str = "default",
    action=None,
    action_label=None,
    on_action=None,
    action_variant: str = "ghost",
    className: str | None = None,
):
    resolved_action = action
    if resolved_action is None and action_label is not None:
        resolved_action = ActionButton(
            action_label,
            variant=action_variant,
            size="sm",
            onClick=on_action,
        )
    children = [
        VStack(
            Text(title, className="font-semibold text-ink"),
            Show(
                Text(detail, className="text-sm text-muted truncate"),
                when=computed(lambda: _has_value(detail)),
            ),
            gap=1,
            className="flex-1 min-w-0",
        )
    ]
    if badge is not None:
        children.append(StatusPill(badge, tone=badge_tone))
    if meta is not None:
        children.append(Text(meta, className="text-sm text-muted shrink-0"))
    if resolved_action is not None:
        children.append(_as_node(resolved_action))
    return HStack(
        *children,
        className=_surface_class("ui-list-row p-3 gap-3 rounded-lg items-center", tone, className),
    )
