from __future__ import annotations

from ._ui_helpers import _value, class_names
from .events import EventSignature
from .reactive import computed, is_reactive

__all__ = [
    "UI_EVENT_SIGNATURES",
    "_surface_class",
]

UI_EVENT_SIGNATURES = {
    "ActionButton.onClick": EventSignature(),
    "CommandPalette.on_query": EventSignature(("value",)),
    "CommandPalette.on_select": EventSignature(("command_id",)),
    "EmptyState.on_action": EventSignature(),
    "ListRow.on_action": EventSignature(),
    "Menu.on_focus": EventSignature(("item_id",)),
    "Menu.on_open_change": EventSignature(("open",)),
    "Menu.on_select": EventSignature(("item_id",)),
    "NavItem.on_navigate": EventSignature(("route_id",)),
    "SectionHeader.on_action": EventSignature(),
    "Select.on_change": EventSignature(("value",)),
    "Select.on_open_change": EventSignature(("open",)),
    "ShortcutScope.onKeyDown": EventSignature(("event",)),
    "SidebarNav.on_navigate": EventSignature(("route_id",)),
    "TabButton.onClick": EventSignature(),
}

_SURFACE_CLASSES = {
    "default": "bg-panel border border-line",
    "neutral": "bg-panel border border-line",
    "soft": "bg-panel-soft border border-line",
    "info": "bg-accent-soft border border-accent",
    "success": "bg-success-soft border border-success",
    "good": "bg-success-soft border border-success",
    "warn": "bg-warn-soft border border-warn",
    "danger": "bg-danger-soft border border-danger",
}

def _surface_class(base: str, tone, extra: str | None = None):
    if is_reactive(tone) or is_reactive(extra):
        return computed(
            lambda: class_names(
                base,
                _SURFACE_CLASSES.get(str(_value(tone)), _SURFACE_CLASSES["default"]),
                _value(extra),
            )
        )
    return class_names(base, _SURFACE_CLASSES.get(str(tone), _SURFACE_CLASSES["default"]), extra)
