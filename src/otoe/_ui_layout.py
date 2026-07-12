from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ._ui_helpers import _as_node, _has_value, _slot_node, _state_class, class_names
from ._ui_surfaces import StatusPill, Toolbar
from .component import component
from .control import Show
from .node import Node
from .reactive import computed
from .widgets import (
    FocusScope as FocusScopeWidget,
    HStack,
    ShortcutScope as ShortcutScopeWidget,
    Text,
    VStack,
)

__all__ = [
    "ShortcutScope",
    "FocusScope",
    "AppShell",
    "AppFrame",
    "SidebarFrame",
    "SidebarItem",
    "TopBar",
]

@component
def ShortcutScope(
    *children: Node,
    onKeyDown: Callable[[dict[str, Any]], Any],
    className: str | None = None,
) -> Node:
    return ShortcutScopeWidget(
        *children,
        className=class_names("ui-shortcut-scope", className),
        onGlobalKeyDown=onKeyDown,
    )

@component
def FocusScope(
    *children: Node,
    trapFocus: bool = True,
    restoreFocus: bool = True,
    className: str | None = None,
) -> Node:
    return FocusScopeWidget(
        *children,
        className=class_names("ui-focus-scope", className),
        trapFocus=trapFocus,
        restoreFocus=restoreFocus,
    )

@component
def AppShell(
    *,
    sidebar: Any,
    content: Any,
    header: Any = None,
    className: str | None = None,
) -> Node:
    children = []
    if header is not None:
        children.append(HStack(_as_node(header), className="ui-app-header"))
    children.append(
        HStack(
            VStack(_as_node(sidebar), className="ui-app-sidebar"),
            VStack(_as_node(content), className="ui-app-content"),
            className="ui-app-main",
            gap=0,
        )
    )
    return VStack(
        *children,
        className=class_names("ui-app-shell", className),
        gap=0,
    )

@component
def AppFrame(
    *,
    sidebar: Any,
    content: Any,
    topbar: Any = None,
    feedback: Any = None,
    className: str | None = None,
    shellClassName: str | None = None,
    contentClassName: str | None = None,
    max_width: str = "7xl",
) -> Node:
    main_children = []
    if topbar is not None:
        main_children.append(_as_node(topbar))
    if feedback is not None:
        main_children.append(_as_node(feedback))
    main_children.append(_as_node(content))

    return VStack(
        HStack(
            _as_node(sidebar),
            VStack(
                *main_children,
                className=class_names("ui-frame-content flex-1 min-w-0 gap-4", contentClassName),
            ),
            className=class_names(
                "ui-frame-shell",
                f"max-w-{max_width}",
                "mx-auto w-full p-6 gap-4 items-start flex-wrap",
                shellClassName,
            ),
        ),
        className=class_names("ui-frame min-h-screen bg-bg text-ink", className),
    )

@component
def SidebarFrame(
    *items: Node,
    brand: Any,
    subtitle: Any = None,
    footer: Any = None,
    className: str | None = None,
) -> Node:
    children = [
        VStack(
            Text(brand, className="text-xl font-bold text-white"),
            Show(
                Text(subtitle, className="text-sm text-accent-soft"),
                when=computed(lambda: _has_value(subtitle)),
            ),
            gap=1,
        ),
        VStack(*items, gap=2),
    ]
    if footer is not None:
        children.append(_slot_node(footer, "ui-sidebar-frame-footer"))
    return VStack(
        *children,
        className=class_names(
            "ui-sidebar-frame w-72 shrink-0 p-4 gap-5 bg-ink rounded-xl shadow-md",
            className,
        ),
    )

@component
def SidebarItem(
    label: Any,
    *,
    detail: Any = None,
    tone: str = "neutral",
    active: Any = False,
    className: str | None = None,
) -> Node:
    return HStack(
        StatusPill(" ", tone=tone),
        VStack(
            Text(label, className="text-sm font-semibold text-white"),
            Show(
                Text(detail, className="text-xs text-accent-soft"),
                when=computed(lambda: _has_value(detail)),
            ),
            gap=1,
            className="min-w-0",
        ),
        className=_state_class(
            "ui-sidebar-item p-3 gap-3 rounded-md bg-muted",
            active=active,
            extra=className,
        ),
    )

@component
def TopBar(
    title: Any,
    *,
    subtitle: Any = None,
    status: Any = None,
    status_tone: str = "neutral",
    actions: Any = None,
    className: str | None = None,
) -> Node:
    side_children = []
    if status is not None:
        side_children.append(StatusPill(status, tone=status_tone))
    if actions is not None:
        side_children.append(_as_node(actions))
    return Toolbar(
        VStack(
            Text(title, className="text-xl font-bold text-ink"),
            Show(
                Text(subtitle, className="text-sm text-muted"),
                when=computed(lambda: _has_value(subtitle)),
            ),
            gap=1,
            className="min-w-0 flex-1",
        ),
        HStack(
            *side_children,
            className="gap-2 items-center shrink-0",
        ),
        className=class_names(
            "ui-topbar justify-between p-5 bg-panel border border-line rounded-xl shadow-md",
            className,
        ),
    )
