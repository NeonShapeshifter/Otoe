from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Iterable, TypeVar, overload

from .node import Node

_T = TypeVar("_T")


@dataclass(frozen=True)
class ShowTag:
    name: str = ...


@dataclass(frozen=True)
class ForTag:
    name: str = ...


SHOW_TAG: ShowTag
FOR_TAG: ForTag


def Show(*children: Node, when: Any, fallback: Node | None = ...) -> Node: ...


@overload
def For(
    *,
    each: Iterable[_T],
    key: Callable[[_T], Any],
    children: Callable[[_T], Node],
    fallback: Node | None = ...,
) -> Node: ...


@overload
def For(
    *,
    each: Any,
    key: Callable[[Any], Any],
    children: Callable[[Any], Node],
    fallback: Node | None = ...,
) -> Node: ...


def is_control_tag(tag: Any) -> bool: ...
def is_show_tag(tag: Any) -> bool: ...
def is_for_tag(tag: Any) -> bool: ...
def resolve_value(value: Any) -> Any: ...
def list_from_value(value: Any) -> list[Any]: ...
