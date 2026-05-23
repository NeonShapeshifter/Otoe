from __future__ import annotations

from typing import Any, Callable

from .node import Node, Widget

ClickHandler = Callable[[], Any]
KeyHandler = Callable[[str], Any]
ChangeHandler = Callable[[Any], Any]
ScrollHandler = Callable[[int | float], Any]
GlobalKeyHandler = Callable[[dict[str, Any]], Any]


class VStack(Widget):
    def __new__(
        cls,
        *children: Node,
        className: Any = ...,
        gap: Any = ...,
        padding: Any = ...,
        id: Any = ...,
    ) -> Node: ...


class HStack(Widget):
    def __new__(
        cls,
        *children: Node,
        className: Any = ...,
        gap: Any = ...,
        padding: Any = ...,
        id: Any = ...,
    ) -> Node: ...


class Text(Widget):
    def __new__(
        cls,
        content: Any = ...,
        *,
        className: Any = ...,
        color: Any = ...,
        id: Any = ...,
    ) -> Node: ...


class Button(Widget):
    def __new__(
        cls,
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


class Input(Widget):
    def __new__(
        cls,
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


class ScrollView(Widget):
    def __new__(
        cls,
        *children: Node,
        className: Any = ...,
        id: Any = ...,
        scrollY: Any = ...,
        onScroll: ScrollHandler | None = ...,
    ) -> Node: ...


class Panel(Widget):
    def __new__(
        cls,
        *children: Node,
        className: Any = ...,
        title: Any = ...,
        id: Any = ...,
    ) -> Node: ...


class ShortcutScope(Widget):
    def __new__(
        cls,
        *children: Node,
        className: Any = ...,
        id: Any = ...,
        onGlobalKeyDown: GlobalKeyHandler | None = ...,
    ) -> Node: ...


class FocusScope(Widget):
    def __new__(
        cls,
        *children: Node,
        className: Any = ...,
        trapFocus: Any = ...,
        restoreFocus: Any = ...,
        id: Any = ...,
    ) -> Node: ...
