from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Iterable

from .node import Node


@dataclass(frozen=True)
class ShowTag:
    name: str = "Show"


@dataclass(frozen=True)
class ForTag:
    name: str = "For"


SHOW_TAG = ShowTag()
FOR_TAG = ForTag()


def Show(*children: Node, when: Any, fallback: Node | None = None) -> Node:
    return Node(
        tag=SHOW_TAG,
        props={
            "when": when,
            "fallback": fallback,
        },
        children=list(children),
    )


def For(
    *,
    each: Any,
    key: Callable[[Any], Any],
    children: Callable[[Any], Node],
    fallback: Node | None = None,
) -> Node:
    if not callable(key):
        raise TypeError("For key must be callable.")
    if not callable(children):
        raise TypeError("For children must be callable.")
    return Node(
        tag=FOR_TAG,
        props={
            "each": each,
            "key": key,
            "render": children,
            "fallback": fallback,
        },
        children=[],
    )


def is_control_tag(tag: Any) -> bool:
    return tag in {SHOW_TAG, FOR_TAG}


def is_show_tag(tag: Any) -> bool:
    return tag == SHOW_TAG


def is_for_tag(tag: Any) -> bool:
    return tag == FOR_TAG


def resolve_value(value: Any) -> Any:
    from .reactive import ReactiveValue

    if isinstance(value, ReactiveValue):
        return value.value
    return value


def list_from_value(value: Any) -> list[Any]:
    resolved = resolve_value(value)
    if resolved is None:
        return []
    if isinstance(resolved, list):
        return resolved
    if isinstance(resolved, tuple):
        return list(resolved)
    if isinstance(resolved, Iterable) and not isinstance(resolved, (str, bytes, dict)):
        return list(resolved)
    raise TypeError(f"For each must resolve to an iterable; got {type(resolved).__name__}.")

