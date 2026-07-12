from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ._ui_helpers import _active_class, _has_value, _list_value, _state_class, _value, class_names
from ._ui_keyboard import (
    _focused_id,
    _menu_key_down,
    _select_option,
    _select_option_key_down,
    _select_trigger_key_down,
    _submit_first_command,
)
from ._ui_layout import FocusScope
from ._ui_models import (
    Command,
    MenuItem,
    SelectOption,
    _filter_commands,
    _normalize_menu_item,
    _normalize_select_option,
)
from ._ui_surfaces import Badge, Card
from .component import component
from .control import For, Show
from .node import Node
from .reactive import computed
from .widgets import Button, HStack, Input, Text, VStack

__all__ = [
    "CommandPalette",
    "Menu",
    "Select",
]

@component
def CommandPalette(
    *,
    query: Any,
    commands: Any,
    on_query: Callable[[Any], Any],
    on_select: Callable[[str], Any],
    placeholder: str = "Search commands...",
    className: str | None = None,
    empty: Any = "No commands",
    autoFocus: bool = False,
) -> Node:
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
    items: Any,
    on_select: Callable[[str], Any],
    open: Any = True,
    active: Any = None,
    focused: Any = None,
    on_focus: Callable[[str], Any] | None = None,
    on_open_change: Callable[[bool], Any] | None = None,
    className: str | None = None,
    empty: Any = "No actions",
) -> Node:
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
    options: Any,
    value: Any,
    on_change: Callable[[str], Any],
    open: Any,
    on_open_change: Callable[[bool], Any],
    placeholder: Any = "Select...",
    className: str | None = None,
    empty: Any = "No options",
) -> Node:
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

def _command_item(command: Command, on_select: Callable[[str], Any]) -> Node:
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

def _menu_item(
    item: MenuItem,
    items: Any,
    on_select: Callable[[str], Any],
    focused: Any,
    on_focus: Callable[[str], Any] | None,
    on_open_change: Callable[[bool], Any] | None,
) -> Node:
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
        onClick=lambda: None if item.disabled else on_select(item.id),
        onKeyDown=lambda key: _menu_key_down(
            key,
            items.value,
            _focused_id(focused, item.id),
            on_select,
            on_focus,
            on_open_change,
        ),
    )

def _select_option_button(
    option: SelectOption,
    options: Any,
    value: Any,
    on_change: Callable[[str], Any],
    on_open_change: Callable[[bool], Any],
) -> Node:
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
        onClick=lambda: _select_option(option.value, option.disabled, on_change, on_open_change),
        onKeyDown=lambda key: _select_option_key_down(
            key,
            options.value,
            option.value,
            option.disabled,
            on_change,
            on_open_change,
        ),
    )

def _selected_option(options: list[SelectOption], value: str) -> SelectOption | None:
    for option in options:
        if option.value == value:
            return option
    return None

def _select_label(option: SelectOption | None, placeholder: Any) -> Any:
    if option is not None:
        return option.label
    return _value(placeholder)

def _select_description(option: SelectOption | None) -> Any:
    if option is None:
        return None
    return option.description
