from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .component import component
from .control import For, Show
from .node import Node
from .reactive import computed, is_reactive
from .widgets import Button, HStack, Input, Panel, ShortcutScope as ShortcutScopeWidget, Text, VStack


@dataclass(frozen=True)
class TableColumn:
    key: str
    label: str
    className: str | None = None


@dataclass(frozen=True)
class Command:
    id: str
    label: Any
    description: Any = ""
    group: Any = ""
    shortcut: str | None = None
    className: str | None = None


class CommandRegistry:
    def __init__(self, commands) -> None:
        self._commands = tuple(_normalize_command(command) for command in _list_value(commands))

    @property
    def commands(self) -> list[Command]:
        return list(self._commands)

    def __iter__(self):
        return iter(self._commands)

    def visible(self, query: str) -> list[Command]:
        return _filter_commands(self._commands, query)

    def first(self, query: str = "") -> Command | None:
        visible = self.visible(query)
        return visible[0] if visible else None

    def find(self, command_id: str) -> Command | None:
        for command in self._commands:
            if command.id == command_id:
                return command
        return None

    def find_shortcut(self, key: str) -> Command | None:
        normalized_key = _shortcut_key(key)
        for command in self._commands:
            if command.shortcut and _shortcut_key(command.shortcut) == normalized_key:
                return command
        return None


@dataclass(frozen=True)
class NavRoute:
    id: str
    label: Any
    description: Any = None
    badge: Any = None
    tone: Any = "neutral"
    className: str | None = None


def class_names(*parts: Any) -> str:
    names: list[str] = []
    for part in parts:
        if not part:
            continue
        names.extend(str(part).split())
    return " ".join(dict.fromkeys(names))


@component
def ShortcutScope(*children, onKeyDown, className: str | None = None):
    return ShortcutScopeWidget(
        *children,
        className=class_names("ui-shortcut-scope", className),
        onGlobalKeyDown=onKeyDown,
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
def Card(*children, className: str | None = None, tone: str = "default", title=None):
    return Panel(
        *children,
        className=_variant_class("ui-card", tone, className),
        title=title,
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
    onClick=None,
):
    props = {
        "className": _multi_variant_class("ui-button", variant, size, className),
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
def CommandPalette(
    *,
    query,
    commands,
    on_query,
    on_select,
    placeholder: str = "Search commands...",
    className: str | None = None,
    empty="No commands",
):
    visible_commands = computed(
        lambda: _filter_commands(commands, query.value)
    )
    fallback = empty if isinstance(empty, Node) else Text(empty, className="ui-command-empty")

    return Card(
        VStack(
            Text("Command palette", className="ui-command-title"),
            Input(
                value=query,
                placeholder=placeholder,
                className="ui-command-input",
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


def _active_class(base: str, active, extra: str | None):
    if is_reactive(active):
        return computed(lambda: class_names(base, extra, "is-active" if active.value else None))
    return class_names(base, extra, "is-active" if active else None)


def _variant_class(base: str, variant, extra: str | None = None):
    if is_reactive(variant) or is_reactive(extra):
        return computed(lambda: class_names(base, f"is-{_value(variant)}", _value(extra)))
    return class_names(base, f"is-{variant}", extra)


def _multi_variant_class(base: str, variant, size, extra: str | None = None):
    if is_reactive(variant) or is_reactive(size) or is_reactive(extra):
        return computed(
            lambda: class_names(
                base,
                f"is-{_value(variant)}",
                f"is-{_value(size)}",
                _value(extra),
            )
        )
    return class_names(base, f"is-{variant}", f"is-{size}", extra)


def _value(value):
    if is_reactive(value):
        return value.value
    return value


def _has_value(value: Any) -> bool:
    if is_reactive(value):
        return value.value is not None
    return value is not None


def _normalize_column(column: Any) -> TableColumn:
    if isinstance(column, TableColumn):
        return column
    if isinstance(column, dict):
        key = column["key"]
        return TableColumn(
            key=key,
            label=column.get("label", key),
            className=column.get("className"),
        )
    raise TypeError(f"DataTable columns must be TableColumn or dict; got {type(column).__name__}.")


def _normalize_command(command: Any) -> Command:
    if isinstance(command, Command):
        return command
    if isinstance(command, dict):
        command_id = str(command["id"])
        return Command(
            id=command_id,
            label=command.get("label", command_id),
            description=command.get("description", ""),
            group=command.get("group", ""),
            shortcut=command.get("shortcut"),
            className=command.get("className"),
        )
    raise TypeError(f"Commands must be Command or dict; got {type(command).__name__}.")


def _normalize_route(route: Any) -> NavRoute:
    if isinstance(route, NavRoute):
        return route
    if isinstance(route, dict):
        route_id = str(route["id"])
        return NavRoute(
            id=route_id,
            label=route.get("label", route_id),
            description=route.get("description"),
            badge=route.get("badge"),
            tone=route.get("tone", "neutral"),
            className=route.get("className"),
        )
    raise TypeError(f"Routes must be NavRoute or dict; got {type(route).__name__}.")


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


def _filter_commands(commands, query: str) -> list[Command]:
    items = [_normalize_command(command) for command in _list_value(commands)]
    needle = query.strip().lower()
    if not needle:
        return items
    return [
        command
        for command in items
        if needle in str(command.label).lower()
        or needle in str(command.description).lower()
        or needle in str(command.group).lower()
    ]


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


def _submit_first_command(key: str, commands: list[Command], on_select) -> None:
    if key != "Enter" or not commands:
        return
    on_select(commands[0].id)


def _shortcut_key(key: str) -> str:
    return key.strip().lower()


def _matching_routes(routes: list[NavRoute], route_id: str) -> list[NavRoute]:
    return [route for route in routes if route.id == route_id]


def _render_route(route: NavRoute, render) -> Node:
    view = render(route)
    if not isinstance(view, Node):
        raise TypeError("RouteView render must return a Node.")
    return view


def _slot_node(value, className: str) -> Node:
    return VStack(_as_node(value), className=className)


def _as_node(value) -> Node:
    if isinstance(value, Node):
        return value
    return Text(value)


def _list_value(value) -> list[Any]:
    resolved = _value(value)
    if resolved is None:
        return []
    return list(resolved)
