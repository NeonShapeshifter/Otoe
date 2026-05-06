from __future__ import annotations

from typing import Any

from ._ui_helpers import _value
from ._ui_models import Command, MenuItem, SelectOption


def _submit_first_command(key: str, commands: list[Command], on_select) -> None:
    if key != "Enter" or not commands:
        return
    on_select(commands[0].id)


def _select_option(option_value: str, disabled: bool, on_change, on_open_change) -> None:
    if disabled:
        return
    on_change(option_value)
    on_open_change(False)


def _focused_id(focused, fallback: str) -> str:
    if focused is None:
        return fallback
    value = _value(focused)
    return fallback if value is None else str(value)


def _menu_key_down(
    key: str,
    items: list[MenuItem],
    focused_id: str,
    on_select,
    on_focus,
    on_open_change,
) -> None:
    if key == "Escape":
        _call_optional(on_open_change, False)
        return
    if key in {"ArrowDown", "ArrowUp", "Home", "End"}:
        target = _next_menu_item(items, focused_id, key)
        if target is not None:
            _call_optional(on_focus, target.id)
        return
    if _is_submit_key(key):
        target = _find_menu_item(items, focused_id)
        if target is not None and not target.disabled:
            on_select(target.id)
            _call_optional(on_open_change, False)


def _select_trigger_key_down(
    key: str,
    options: list[SelectOption],
    value: str,
    open: bool,
    on_change,
    on_open_change,
) -> None:
    if key == "Escape":
        on_open_change(False)
        return
    if _is_submit_key(key):
        on_open_change(not open)
        return
    if key in {"ArrowDown", "ArrowUp", "Home", "End"}:
        target = _next_select_option(options, value, key)
        if target is not None:
            on_change(target.value)
        on_open_change(True)


def _select_option_key_down(
    key: str,
    options: list[SelectOption],
    option_value: str,
    disabled: bool,
    on_change,
    on_open_change,
) -> None:
    if key == "Escape":
        on_open_change(False)
        return
    if _is_submit_key(key):
        _select_option(option_value, disabled, on_change, on_open_change)
        return
    if key in {"ArrowDown", "ArrowUp", "Home", "End"}:
        target = _next_select_option(options, option_value, key)
        if target is not None:
            on_change(target.value)
        on_open_change(True)


def _next_menu_item(items: list[MenuItem], focused_id: str, key: str) -> MenuItem | None:
    enabled = [item for item in items if not item.disabled]
    if not enabled:
        return None
    if key == "Home":
        return enabled[0]
    if key == "End":
        return enabled[-1]
    current_index = _item_index(enabled, focused_id, "id")
    if current_index is None:
        return enabled[0]
    step = 1 if key == "ArrowDown" else -1
    return enabled[(current_index + step) % len(enabled)]


def _find_menu_item(items: list[MenuItem], item_id: str) -> MenuItem | None:
    for item in items:
        if item.id == item_id:
            return item
    return None


def _next_select_option(options: list[SelectOption], value: str, key: str) -> SelectOption | None:
    enabled = [option for option in options if not option.disabled]
    if not enabled:
        return None
    if key == "Home":
        return enabled[0]
    if key == "End":
        return enabled[-1]
    current_index = _item_index(enabled, value, "value")
    if current_index is None:
        return enabled[0]
    step = 1 if key == "ArrowDown" else -1
    return enabled[(current_index + step) % len(enabled)]


def _item_index(items: list[Any], value: str, attr: str) -> int | None:
    for index, item in enumerate(items):
        if getattr(item, attr) == value:
            return index
    return None


def _is_submit_key(key: str) -> bool:
    return key in {"Enter", " ", "Spacebar"}


def _call_optional(callback, *args) -> None:
    if callback is not None:
        callback(*args)
