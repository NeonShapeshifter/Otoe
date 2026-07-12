from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any

from ._ui_helpers import class_names
from ._ui_models import TableColumn, _normalize_column
from .component import component
from .control import For
from .node import Node
from .widgets import HStack, Text, VStack

__all__ = [
    "DataTable",
]

@component
def DataTable(
    *,
    columns: Iterable[Any],
    rows: Any,
    key: Callable[[Any], Any],
    render_cell: Callable[[Any, TableColumn], Any] | None = None,
    className: str | None = None,
    empty: Any = "No rows",
) -> Node:
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

def _render_cell(
    row: Any,
    column: TableColumn,
    render_cell: Callable[[Any, TableColumn], Any] | None,
) -> Node:
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
