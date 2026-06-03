from __future__ import annotations

from typing import Any

from ._ui_helpers import (
    _active_class,
    _as_node,
    _has_value,
    _list_value,
    _multi_variant_class,
    _slot_node,
    _state_class,
    _value,
    _variant_class,
    class_names,
)
from ._ui_keyboard import (
    _focused_id,
    _menu_key_down,
    _select_option,
    _select_option_key_down,
    _select_trigger_key_down,
    _submit_first_command,
)
from ._ui_models import (
    Command,
    CommandRegistry,
    MenuItem,
    NavRoute,
    SelectOption,
    TableColumn,
    _filter_commands,
    _normalize_column,
    _normalize_menu_item,
    _normalize_route,
    _normalize_select_option,
)
from .component import component
from .control import For, Show
from .events import EventSignature
from .node import Node
from .reactive import computed, is_reactive
from .widgets import (
    Button,
    FocusScope as FocusScopeWidget,
    HStack,
    Input,
    Panel,
    ShortcutScope as ShortcutScopeWidget,
    Text,
    VStack,
)


UI_EVENT_SIGNATURES = {
    "ActionButton.onClick": EventSignature(),
    "CommandPalette.on_query": EventSignature(("value",)),
    "CommandPalette.on_select": EventSignature(("command_id",)),
    "Menu.on_focus": EventSignature(("item_id",)),
    "Menu.on_open_change": EventSignature(("open",)),
    "Menu.on_select": EventSignature(("item_id",)),
    "NavItem.on_navigate": EventSignature(("route_id",)),
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


@component
def ShortcutScope(*children, onKeyDown, className: str | None = None):
    return ShortcutScopeWidget(
        *children,
        className=class_names("ui-shortcut-scope", className),
        onGlobalKeyDown=onKeyDown,
    )


@component
def FocusScope(
    *children,
    trapFocus: bool = True,
    restoreFocus: bool = True,
    className: str | None = None,
):
    return FocusScopeWidget(
        *children,
        className=class_names("ui-focus-scope", className),
        trapFocus=trapFocus,
        restoreFocus=restoreFocus,
    )


@component
def AppShell(
    *,
    sidebar,
    content,
    header=None,
    className: str | None = None,
):
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
    sidebar,
    content,
    topbar=None,
    feedback=None,
    className: str | None = None,
    shellClassName: str | None = None,
    contentClassName: str | None = None,
    max_width: str = "7xl",
):
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
    *items,
    brand,
    subtitle=None,
    footer=None,
    className: str | None = None,
):
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
    label,
    *,
    detail=None,
    tone: str = "neutral",
    active=False,
    className: str | None = None,
):
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
def TopBar(
    title,
    *,
    subtitle=None,
    status=None,
    status_tone: str = "neutral",
    actions=None,
    className: str | None = None,
):
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
def DataTable(
    *,
    columns,
    rows,
    key,
    render_cell=None,
    className: str | None = None,
    empty="No rows",
):
    normalized_columns = [_normalize_column(column) for column in columns]
    fallback = empty if isinstance(empty, Node) else Text(empty, className="ui-table-empty")

    return VStack(
        HStack(
            *[
                Text(
                    column.label,
                    className=class_names("ui-table-head-cell", column.className),
                )
                for column in normalized_columns
            ],
            className="ui-table-head",
        ),
        For(
            each=rows,
            key=key,
            children=lambda row: HStack(
                *[
                    _render_cell(row, column, render_cell)
                    for column in normalized_columns
                ],
                className="ui-table-row",
            ),
            fallback=fallback,
        ),
        className=class_names("ui-table", className),
        gap=8,
    )


@component
def Dialog(
    *children,
    open,
    title=None,
    description=None,
    className: str | None = None,
):
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
    title,
    *,
    description=None,
    tone: str = "neutral",
    className: str | None = None,
):
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
    feedback,
    *,
    title_key: str = "title",
    description_key: str = "detail",
    tone_key: str = "tone",
    className: str | None = None,
):
    return Show(
        Toast(
            computed(lambda: _feedback_field(feedback, title_key, "")),
            description=computed(lambda: _feedback_field(feedback, description_key, None)),
            tone=computed(lambda: _feedback_field(feedback, tone_key, "neutral")),
            className=className,
        ),
        when=computed(lambda: _value(feedback) is not None),
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


@component
def CommandPalette(
    *,
    query,
    commands,
    on_query,
    on_select,
    placeholder: str = "Search commands...",
    className: str | None = None,
    empty="No commands",
    autoFocus: bool = False,
):
    visible_commands = computed(
        lambda: _filter_commands(commands, _value(query))
    )
    fallback = empty if isinstance(empty, Node) else Text(empty, className="ui-command-empty")

    return Card(
        VStack(
            Text("Command palette", className="ui-command-title"),
            Input(
                value=query,
                placeholder=placeholder,
                className="ui-command-input",
                autoFocus=autoFocus,
                onChange=on_query,
                onKeyDown=lambda key: _submit_first_command(key, visible_commands.value, on_select),
            ),
            For(
                each=visible_commands,
                key=lambda command: command.id,
                children=lambda command: _command_item(command, on_select),
                fallback=fallback,
            ),
            className="ui-command",
            gap=10,
        ),
        className=class_names("ui-command-card", className),
    )


@component
def Menu(
    *,
    items,
    on_select,
    open=True,
    active=None,
    focused=None,
    on_focus=None,
    on_open_change=None,
    className: str | None = None,
    empty="No actions",
):
    normalized_items = computed(lambda: [_normalize_menu_item(item) for item in _list_value(items)])
    focus_value = focused if focused is not None else active
    fallback = empty if isinstance(empty, Node) else Text(empty, className="ui-menu-empty")

    return Show(
        FocusScope(
            Card(
                VStack(
                    For(
                        each=normalized_items,
                        key=lambda item: item.id,
                        children=lambda item: _menu_item(
                            item,
                            normalized_items,
                            on_select,
                            focus_value,
                            on_focus,
                            on_open_change,
                        ),
                        fallback=fallback,
                    ),
                    className="ui-menu-list",
                    gap=6,
                ),
                className=class_names("ui-menu", className),
            ),
            className="ui-menu-focus-scope",
        ),
        when=open,
    )


@component
def Select(
    *,
    options,
    value,
    on_change,
    open,
    on_open_change,
    placeholder="Select...",
    className: str | None = None,
    empty="No options",
):
    normalized_options = computed(lambda: [_normalize_select_option(option) for option in _list_value(options)])
    selected_option = computed(lambda: _selected_option(normalized_options.value, _value(value)))
    fallback = empty if isinstance(empty, Node) else Text(empty, className="ui-select-empty")

    return VStack(
        Button(
            "",
            HStack(
                VStack(
                    Text(computed(lambda: _select_label(selected_option.value, placeholder)), className="ui-select-label"),
                    Show(
                        Text(
                            computed(lambda: _select_description(selected_option.value)),
                            className="ui-select-description",
                        ),
                        when=computed(lambda: _has_value(_select_description(selected_option.value))),
                    ),
                    className="ui-select-copy",
                    gap=2,
                ),
                Text(computed(lambda: "Close" if _value(open) else "Open"), className="ui-select-state"),
                className="ui-select-trigger-row",
                gap=10,
            ),
            className=_active_class("ui-select-trigger", open, None),
            onClick=lambda: on_open_change(not bool(_value(open))),
            onKeyDown=lambda key: _select_trigger_key_down(
                key,
                normalized_options.value,
                _value(value),
                _value(open),
                on_change,
                on_open_change,
            ),
        ),
        Show(
            FocusScope(
                Card(
                    VStack(
                        For(
                            each=normalized_options,
                            key=lambda option: option.value,
                            children=lambda option: _select_option_button(
                                option,
                                normalized_options,
                                value,
                                on_change,
                                on_open_change,
                            ),
                            fallback=fallback,
                        ),
                        className="ui-select-list",
                        gap=6,
                    ),
                    className="ui-select-popover",
                ),
                className="ui-select-focus-scope",
            ),
            when=open,
        ),
        className=class_names("ui-select", className),
        gap=8,
    )


@component
def SidebarNav(
    *,
    routes,
    active,
    on_navigate,
    brand=None,
    footer=None,
    className: str | None = None,
    empty="No routes",
):
    normalized_routes = computed(lambda: [_normalize_route(route) for route in _list_value(routes)])
    children = []
    if brand is not None:
        children.append(_slot_node(brand, "ui-sidebar-brand"))
    children.append(
        For(
            each=normalized_routes,
            key=lambda route: route.id,
            children=lambda route: NavItem(
                route=route,
                active=computed(lambda route=route: route.id == _value(active)),
                on_navigate=on_navigate,
            ),
            fallback=empty if isinstance(empty, Node) else Text(empty, className="ui-nav-empty"),
        )
    )
    if footer is not None:
        children.append(_slot_node(footer, "ui-sidebar-footer"))
    return VStack(
        *children,
        className=class_names("ui-sidebar-nav", className),
        gap=8,
    )


@component
def NavItem(
    *,
    route,
    active,
    on_navigate,
    className: str | None = None,
):
    normalized = _normalize_route(route)
    return Button(
        "",
        HStack(
            VStack(
                Text(normalized.label, className="ui-nav-label"),
                Show(
                    Text(normalized.description, className="ui-nav-description"),
                    when=computed(lambda: _has_value(normalized.description)),
                ),
                className="ui-nav-copy",
                gap=2,
            ),
            Show(
                Badge(normalized.badge, tone=normalized.tone, className="ui-nav-badge"),
                when=computed(lambda: _has_value(normalized.badge)),
            ),
            className="ui-nav-row",
            gap=10,
        ),
        className=_active_class("ui-nav-item", active, class_names(normalized.className, className)),
        onClick=lambda route_id=normalized.id: on_navigate(route_id),
    )


@component
def RouteView(
    *,
    route,
    routes,
    render,
    className: str | None = None,
    fallback="Route not found",
):
    normalized_routes = computed(lambda: [_normalize_route(item) for item in _list_value(routes)])
    active_routes = computed(lambda: _matching_routes(normalized_routes.value, _value(route)))
    fallback_node = fallback if isinstance(fallback, Node) else Text(fallback, className="ui-route-empty")

    return VStack(
        For(
            each=active_routes,
            key=lambda item: item.id,
            children=lambda item: _render_route(item, render),
            fallback=fallback_node,
        ),
        className=class_names("ui-route-view", className),
        gap=0,
    )


def _render_cell(row: Any, column: TableColumn, render_cell) -> Node:
    if render_cell is not None:
        cell = render_cell(row, column)
        if not isinstance(cell, Node):
            raise TypeError("DataTable render_cell must return a Node.")
        return cell
    value = _row_value(row, column.key)
    return Text(value, className=class_names("ui-table-cell", column.className))


def _row_value(row: Any, key: str) -> Any:
    if isinstance(row, dict):
        return row.get(key, "")
    return getattr(row, key)


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


def _feedback_field(feedback, field: str, default: Any) -> Any:
    value = _value(feedback)
    if value is None:
        return default
    if isinstance(value, dict):
        return value.get(field, default)
    return getattr(value, field, default)


def _command_item(command: Command, on_select) -> Node:
    return Button(
        "",
        HStack(
            VStack(
                Text(command.label, className="ui-command-label"),
                Text(command.description, className="ui-command-description"),
                className="ui-command-copy",
                gap=3,
            ),
            Text(command.shortcut or "", className="ui-command-shortcut"),
            className="ui-command-row",
            gap=12,
        ),
        className=class_names("ui-command-item", command.className),
        onClick=lambda: on_select(command.id),
    )


def _menu_item(item: MenuItem, items, on_select, focused, on_focus, on_open_change) -> Node:
    return Button(
        "",
        HStack(
            VStack(
                Text(item.label, className="ui-menu-label"),
                Show(
                    Text(item.description, className="ui-menu-description"),
                    when=computed(lambda: _has_value(item.description)),
                ),
                className="ui-menu-copy",
                gap=2,
            ),
            Show(
                Text(item.shortcut, className="ui-menu-shortcut"),
                when=computed(lambda: _has_value(item.shortcut)),
            ),
            className="ui-menu-row",
            gap=12,
        ),
        className=_state_class(
            "ui-menu-item",
            active=computed(lambda: item.id == _value(focused)) if focused is not None else False,
            disabled=item.disabled,
            extra=class_names(f"is-{item.tone}", item.className),
        ),
        disabled=item.disabled,
        onClick=lambda item_id=item.id: None if item.disabled else on_select(item_id),
        onKeyDown=lambda key, item_id=item.id: _menu_key_down(
            key,
            items.value,
            _focused_id(focused, item_id),
            on_select,
            on_focus,
            on_open_change,
        ),
    )


def _select_option_button(option: SelectOption, options, value, on_change, on_open_change) -> Node:
    return Button(
        "",
        HStack(
            VStack(
                Text(option.label, className="ui-select-option-label"),
                Show(
                    Text(option.description, className="ui-select-option-description"),
                    when=computed(lambda: _has_value(option.description)),
                ),
                className="ui-select-option-copy",
                gap=2,
            ),
            Show(
                Badge("Current", tone=option.tone, className="ui-select-option-badge"),
                when=computed(lambda: option.value == _value(value)),
            ),
            className="ui-select-option-row",
            gap=10,
        ),
        className=_state_class(
            "ui-select-option",
            active=computed(lambda: option.value == _value(value)),
            disabled=option.disabled,
            extra=option.className,
        ),
        disabled=option.disabled,
        onClick=lambda option_value=option.value: _select_option(option_value, option.disabled, on_change, on_open_change),
        onKeyDown=lambda key, option_value=option.value: _select_option_key_down(
            key,
            options.value,
            option_value,
            option.disabled,
            on_change,
            on_open_change,
        ),
    )


def _matching_routes(routes: list[NavRoute], route_id: str) -> list[NavRoute]:
    return [route for route in routes if route.id == route_id]


def _render_route(route: NavRoute, render) -> Node:
    view = render(route)
    if not isinstance(view, Node):
        raise TypeError("RouteView render must return a Node.")
    return view


def _selected_option(options: list[SelectOption], value: str) -> SelectOption | None:
    for option in options:
        if option.value == value:
            return option
    return None


def _select_label(option: SelectOption | None, placeholder) -> Any:
    if option is not None:
        return option.label
    return _value(placeholder)


def _select_description(option: SelectOption | None) -> Any:
    if option is None:
        return None
    return option.description
