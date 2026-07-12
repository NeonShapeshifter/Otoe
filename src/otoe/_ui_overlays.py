from __future__ import annotations

from typing import Any

from ._ui_helpers import _has_value, _value, _variant_class, class_names
from ._ui_layout import FocusScope
from ._ui_surfaces import Badge, Card
from .component import component
from .control import Show
from .node import Node
from .reactive import computed, is_reactive
from .widgets import HStack, Text, VStack

__all__ = [
    "Dialog",
    "Toast",
    "FeedbackToast",
]

@component
def Dialog(
    *children: Node,
    open: Any,
    title: Any = None,
    description: Any = None,
    className: str | None = None,
) -> Node:
    return Show(
        HStack(
            FocusScope(
                Card(
                    VStack(
                        Show(
                            Text(title, className="ui-dialog-title"),
                            when=computed(lambda: _has_value(title)),
                        ),
                        Show(
                            Text(description, className="ui-dialog-description"),
                            when=computed(lambda: _has_value(description)),
                        ),
                        *children,
                        className="ui-dialog-body",
                        gap=12,
                    ),
                    className=class_names("ui-dialog-panel", className),
                ),
                className="ui-dialog-focus-scope",
            ),
            className="ui-dialog-backdrop",
        ),
        when=open,
    )

@component
def Toast(
    title: Any,
    *,
    description: Any = None,
    tone: Any = "neutral",
    className: str | None = None,
) -> Node:
    tone_label = computed(lambda: str(_value(tone)).upper()) if is_reactive(tone) else str(tone).upper()
    return HStack(
        VStack(
            Text(title, className="ui-toast-title"),
            Show(
                Text(description, className="ui-toast-description"),
                when=computed(lambda: _has_value(description)),
            ),
            className="ui-toast-copy",
            gap=3,
        ),
        Badge(tone_label, tone=tone, className="ui-toast-badge"),
        className=_variant_class("ui-toast", tone, className),
        gap=12,
    )

@component
def FeedbackToast(
    feedback: Any,
    *,
    title_key: str = "title",
    description_key: str = "detail",
    tone_key: str = "tone",
    className: str | None = None,
) -> Node:
    return Show(
        Toast(
            computed(lambda: _feedback_field(feedback, title_key, "")),
            description=computed(lambda: _feedback_field(feedback, description_key, None)),
            tone=computed(lambda: _feedback_field(feedback, tone_key, "neutral")),
            className=className,
        ),
        when=computed(lambda: _value(feedback) is not None),
    )

def _feedback_field(feedback: Any, field: str, default: Any) -> Any:
    value = _value(feedback)
    if value is None:
        return default
    if isinstance(value, dict):
        return value.get(field, default)
    return getattr(value, field, default)
