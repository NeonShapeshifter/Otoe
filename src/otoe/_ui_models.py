from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast

from ._ui_helpers import _list_value


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


@dataclass(frozen=True)
class MenuItem:
    id: str
    label: Any
    description: Any = None
    shortcut: Any = None
    tone: Any = "neutral"
    disabled: bool = False
    className: str | None = None


@dataclass(frozen=True)
class SelectOption:
    value: str
    label: Any
    description: Any = None
    tone: Any = "neutral"
    disabled: bool = False
    className: str | None = None


@dataclass(frozen=True)
class NavRoute:
    id: str
    label: Any
    description: Any = None
    badge: Any = None
    tone: Any = "neutral"
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


def _normalize_column(column: Any) -> TableColumn:
    if isinstance(column, TableColumn):
        return column
    if isinstance(column, dict):
        key = cast(str, column["key"])
        return TableColumn(
            key=key,
            label=cast(str, column.get("label", key)),
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


def _normalize_menu_item(item: Any) -> MenuItem:
    if isinstance(item, MenuItem):
        return item
    if isinstance(item, dict):
        item_id = str(item["id"])
        return MenuItem(
            id=item_id,
            label=item.get("label", item_id),
            description=item.get("description"),
            shortcut=item.get("shortcut"),
            tone=item.get("tone", "neutral"),
            disabled=bool(item.get("disabled", False)),
            className=item.get("className"),
        )
    raise TypeError(f"Menu items must be MenuItem or dict; got {type(item).__name__}.")


def _normalize_select_option(option: Any) -> SelectOption:
    if isinstance(option, SelectOption):
        return option
    if isinstance(option, dict):
        option_value = str(option["value"])
        return SelectOption(
            value=option_value,
            label=option.get("label", option_value),
            description=option.get("description"),
            tone=option.get("tone", "neutral"),
            disabled=bool(option.get("disabled", False)),
            className=option.get("className"),
        )
    raise TypeError(f"Select options must be SelectOption or dict; got {type(option).__name__}.")


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


def _shortcut_key(key: str) -> str:
    return key.strip().lower()
