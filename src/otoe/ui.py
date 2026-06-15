from __future__ import annotations

from ._ui_commands import CommandPalette, Menu, Select
from ._ui_data import DataTable
from ._ui_helpers import class_names
from ._ui_layout import (
    AppFrame,
    AppShell,
    FocusScope,
    ShortcutScope,
    SidebarFrame,
    SidebarItem,
    TopBar,
)
from ._ui_models import (
    Command,
    CommandRegistry,
    MenuItem,
    NavRoute,
    SelectOption,
    TableColumn,
)
from ._ui_navigation import NavItem, RouteView, SidebarNav
from ._ui_overlays import Dialog, FeedbackToast, Toast
from ._ui_surfaces import (
    ActionButton,
    Badge,
    Card,
    EmptyState,
    ListRow,
    MetricGrid,
    MetricTile,
    SectionHeader,
    StatCard,
    StatusPill,
    Surface,
    TabButton,
    Tabs,
    Toolbar,
)
from ._ui_theme import UI_EVENT_SIGNATURES

__all__ = [
    "ActionButton",
    "AppFrame",
    "AppShell",
    "Badge",
    "Card",
    "Command",
    "CommandPalette",
    "CommandRegistry",
    "DataTable",
    "Dialog",
    "EmptyState",
    "FeedbackToast",
    "FocusScope",
    "ListRow",
    "Menu",
    "MenuItem",
    "MetricGrid",
    "MetricTile",
    "NavItem",
    "NavRoute",
    "RouteView",
    "SectionHeader",
    "ShortcutScope",
    "Select",
    "SelectOption",
    "SidebarFrame",
    "SidebarItem",
    "SidebarNav",
    "StatCard",
    "StatusPill",
    "Surface",
    "TabButton",
    "TableColumn",
    "Tabs",
    "Toast",
    "TopBar",
    "Toolbar",
    "UI_EVENT_SIGNATURES",
    "class_names",
]


def _mark_public_module() -> None:
    for name in __all__:
        value = globals().get(name)
        if value is None or not hasattr(value, "__module__"):
            continue
        try:
            value.__module__ = __name__
        except Exception:
            continue


_mark_public_module()
