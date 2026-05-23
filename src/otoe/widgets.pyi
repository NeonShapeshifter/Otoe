from __future__ import annotations

from typing import Any, Callable

from .node import Node

ClickHandler = Callable[[], Any]
KeyHandler = Callable[[str], Any]
ChangeHandler = Callable[[Any], Any]
ScrollHandler = Callable[[int | float], Any]
GlobalKeyHandler = Callable[[dict[str, Any]], Any]


def VStack(
    *children: Node,
    className: Any = ...,
    gap: Any = ...,
    padding: Any = ...,
    id: Any = ...,
) -> Node: ...


def HStack(
    *children: Node,
    className: Any = ...,
    gap: Any = ...,
    padding: Any = ...,
    id: Any = ...,
) -> Node: ...


def Text(
    content: Any = ...,
    *,
    className: Any = ...,
    color: Any = ...,
    id: Any = ...,
) -> Node: ...


def Button(
    label: Any = ...,
    *children: Node,
    className: Any = ...,
    disabled: Any = ...,
    id: Any = ...,
    onClick: ClickHandler | None = ...,
    onKeyDown: KeyHandler | None = ...,
    onFocus: ClickHandler | None = ...,
    onBlur: ClickHandler | None = ...,
) -> Node: ...


def Input(
    *,
    value: Any = ...,
    placeholder: Any = ...,
    className: Any = ...,
    disabled: Any = ...,
    autoFocus: Any = ...,
    id: Any = ...,
    onChange: ChangeHandler | None = ...,
    onKeyDown: KeyHandler | None = ...,
    onFocus: ClickHandler | None = ...,
    onBlur: ClickHandler | None = ...,
) -> Node: ...


def ScrollView(
    *children: Node,
    className: Any = ...,
    id: Any = ...,
    scrollY: Any = ...,
    onScroll: ScrollHandler | None = ...,
) -> Node: ...


def Panel(
    *children: Node,
    className: Any = ...,
    title: Any = ...,
    id: Any = ...,
) -> Node: ...


def ShortcutScope(
    *children: Node,
    className: Any = ...,
    id: Any = ...,
    onGlobalKeyDown: GlobalKeyHandler | None = ...,
) -> Node: ...


def FocusScope(
    *children: Node,
    className: Any = ...,
    trapFocus: Any = ...,
    restoreFocus: Any = ...,
    id: Any = ...,
) -> Node: ...
