from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, ClassVar, Iterable, cast

from .errors import DuplicatePrimaryPropError
from .events import EventSignature


@dataclass(frozen=True)
class Node:
    tag: Any
    props: Mapping[str, Any] = field(default_factory=dict)
    children: tuple["Node", ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(self, "props", MappingProxyType(dict(self.props)))
        object.__setattr__(self, "children", tuple(self.children))


class Widget:
    props: ClassVar[set[str]] = set()
    events: ClassVar[set[str]] = set()
    event_signatures: ClassVar[dict[str, EventSignature]] = {}
    primary_prop: ClassVar[str | None] = None

    def __new__(cls, *args: Any, **kwargs: Any) -> Any:
        return create_node(cls, *args, **kwargs)


def create_node(tag: Any, *args: Any, **kwargs: Any) -> Node:
    props = dict(kwargs)
    children_args: Iterable[Any] = args

    primary_prop = getattr(tag, "primary_prop", None)
    if primary_prop and args:
        if primary_prop in props:
            raise DuplicatePrimaryPropError(
                f"{_tag_name(tag)} received both positional primary content "
                f"and explicit {primary_prop!r}."
            )
        props[primary_prop] = args[0]
        children_args = args[1:]

    children = tuple(_normalize_child(tag, child) for child in children_args)
    return Node(tag=tag, props=props, children=children)


def _normalize_child(parent_tag: Any, child: Any) -> Node:
    if isinstance(child, Node):
        return child
    raise TypeError(
        f"{_tag_name(parent_tag)} children must be Node instances; "
        f"got {type(child).__name__}."
    )


def _tag_name(tag: Any) -> str:
    return cast(
        str,
        getattr(tag, "__name__", getattr(tag, "name", tag.__class__.__name__)),
    )
