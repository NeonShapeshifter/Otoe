from __future__ import annotations

from typing import Any, Callable, Iterable, Iterator, Mapping

from .events import EventSignature
from .node import Node

ClickHandler = Callable[[], Any]
GlobalKeyHandler = Callable[[dict[str, Any]], Any]
KeyFn = Callable[[Any], Any]
NodeRenderer = Callable[[Any], Node]
OpenChangeHandler = Callable[[bool], Any]
RouteRenderer = Callable[["NavRoute"], Node]
SelectionHandler = Callable[[str], Any]
TableCellRenderer = Callable[[Any, "TableColumn"], Node]
ValueHandler = Callable[[Any], Any]


class TableColumn:
    key: str
    label: str
    className: str | None

    def __init__(
        self,
        key: str,
        label: str,
        className: str | None = ...,
    ) -> None: ...


class Command:
    id: str
    label: Any
    description: Any
    group: Any
    shortcut: str | None
    className: str | None

    def __init__(
        self,
        id: str,
        label: Any,
        description: Any = ...,
        group: Any = ...,
        shortcut: str | None = ...,
        className: str | None = ...,
    ) -> None: ...


class MenuItem:
    id: str
    label: Any
    description: Any
    shortcut: Any
    tone: Any
    disabled: bool
    className: str | None

    def __init__(
        self,
        id: str,
        label: Any,
        description: Any = ...,
        shortcut: Any = ...,
        tone: Any = ...,
        disabled: bool = ...,
        className: str | None = ...,
    ) -> None: ...


class SelectOption:
    value: str
    label: Any
    description: Any
    tone: Any
    disabled: bool
    className: str | None

    def __init__(
        self,
        value: str,
        label: Any,
        description: Any = ...,
        tone: Any = ...,
        disabled: bool = ...,
        className: str | None = ...,
    ) -> None: ...


class NavRoute:
    id: str
    label: Any
    description: Any
    badge: Any
    tone: Any
    className: str | None

    def __init__(
        self,
        id: str,
        label: Any,
        description: Any = ...,
        badge: Any = ...,
        tone: Any = ...,
        className: str | None = ...,
    ) -> None: ...


ColumnLike = TableColumn | Mapping[str, Any]
CommandLike = Command | Mapping[str, Any]
MenuItemLike = MenuItem | Mapping[str, Any]
RouteLike = NavRoute | Mapping[str, Any]
SelectOptionLike = SelectOption | Mapping[str, Any]


class CommandRegistry:
    def __init__(self, commands: Iterable[CommandLike]) -> None: ...

    @property
    def commands(self) -> list[Command]: ...

    def __iter__(self) -> Iterator[Command]: ...
    def visible(self, query: str) -> list[Command]: ...
    def first(self, query: str = ...) -> Command | None: ...
    def find(self, command_id: str) -> Command | None: ...
    def find_shortcut(self, key: str) -> Command | None: ...


UI_EVENT_SIGNATURES: dict[str, EventSignature]


def class_names(*parts: Any) -> str: ...


def ShortcutScope(
    *children: Node,
    onKeyDown: GlobalKeyHandler,
    className: str | None = ...,
) -> Node: ...


def FocusScope(
    *children: Node,
    trapFocus: bool = ...,
    restoreFocus: bool = ...,
    className: str | None = ...,
) -> Node: ...


def AppShell(
    *,
    sidebar: Any,
    content: Any,
    header: Any = ...,
    className: str | None = ...,
) -> Node: ...


def Card(
    *children: Node,
    className: str | None = ...,
    tone: Any = ...,
    title: Any = ...,
) -> Node: ...


def Badge(
    label: Any,
    *,
    tone: Any = ...,
    className: str | None = ...,
) -> Node: ...


def ActionButton(
    label: Any,
    *,
    variant: Any = ...,
    size: Any = ...,
    className: str | None = ...,
    disabled: Any = ...,
    onClick: ClickHandler | None = ...,
) -> Node: ...


def Toolbar(
    *children: Node,
    className: str | None = ...,
    gap: int = ...,
) -> Node: ...


def Tabs(
    *children: Node,
    className: str | None = ...,
    gap: int = ...,
    orientation: str = ...,
) -> Node: ...


def TabButton(
    label: Any,
    *,
    active: Any = ...,
    className: str | None = ...,
    onClick: ClickHandler | None = ...,
) -> Node: ...


def StatCard(
    *,
    label: Any,
    value: Any,
    detail: Any = ...,
    tone: Any = ...,
    className: str | None = ...,
) -> Node: ...


def DataTable(
    *,
    columns: Iterable[ColumnLike],
    rows: Any,
    key: KeyFn,
    render_cell: TableCellRenderer | None = ...,
    className: str | None = ...,
    empty: Any = ...,
) -> Node: ...


def Dialog(
    *children: Node,
    open: Any,
    title: Any = ...,
    description: Any = ...,
    className: str | None = ...,
) -> Node: ...


def Toast(
    title: Any,
    *,
    description: Any = ...,
    tone: Any = ...,
    className: str | None = ...,
) -> Node: ...


def FeedbackToast(
    feedback: Any,
    *,
    title_key: str = ...,
    description_key: str = ...,
    tone_key: str = ...,
    className: str | None = ...,
) -> Node: ...


def SectionHeader(
    title: Any,
    *,
    detail: Any = ...,
    badge: Any = ...,
    badge_tone: Any = ...,
    actions: Any = ...,
    className: str | None = ...,
) -> Node: ...


def EmptyState(
    title: Any,
    *,
    description: Any = ...,
    action: Any = ...,
    className: str | None = ...,
) -> Node: ...


def CommandPalette(
    *,
    query: Any,
    commands: Iterable[CommandLike],
    on_query: ValueHandler,
    on_select: SelectionHandler,
    placeholder: str = ...,
    className: str | None = ...,
    empty: Any = ...,
    autoFocus: bool = ...,
) -> Node: ...


def Menu(
    *,
    items: Iterable[MenuItemLike],
    on_select: SelectionHandler,
    open: Any = ...,
    active: Any = ...,
    focused: Any = ...,
    on_focus: SelectionHandler | None = ...,
    on_open_change: OpenChangeHandler | None = ...,
    className: str | None = ...,
    empty: Any = ...,
) -> Node: ...


def Select(
    *,
    options: Iterable[SelectOptionLike],
    value: Any,
    on_change: SelectionHandler,
    open: Any,
    on_open_change: OpenChangeHandler,
    placeholder: Any = ...,
    className: str | None = ...,
    empty: Any = ...,
) -> Node: ...


def SidebarNav(
    *,
    routes: Iterable[RouteLike],
    active: Any,
    on_navigate: SelectionHandler,
    brand: Any = ...,
    footer: Any = ...,
    className: str | None = ...,
    empty: Any = ...,
) -> Node: ...


def NavItem(
    *,
    route: RouteLike,
    active: Any,
    on_navigate: SelectionHandler,
    className: str | None = ...,
) -> Node: ...


def RouteView(
    *,
    route: Any,
    routes: Iterable[RouteLike],
    render: RouteRenderer,
    className: str | None = ...,
    fallback: Any = ...,
) -> Node: ...
