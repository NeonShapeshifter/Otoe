from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .component import component
from .control import For, Show
from .node import Node
from .reactive import computed, is_reactive
from .widgets import Button, HStack, Panel, Text, VStack


@dataclass(frozen=True)
class TableColumn:
    key: str
    label: str
    className: str | None = None


def class_names(*parts: Any) -> str:
    names: list[str] = []
    for part in parts:
        if not part:
            continue
        names.extend(str(part).split())
    return " ".join(dict.fromkeys(names))


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
        Badge(tone.upper(), tone=tone, className="ui-toast-badge"),
        className=class_names("ui-toast", f"is-{tone}", className),
        gap=12,
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
