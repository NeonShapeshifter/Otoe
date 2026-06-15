from __future__ import annotations

from functools import update_wrapper
from typing import Any, Callable

from .node import Node
from .owner import current_owner


class Component:
    def __init__(self, fn: Callable[..., Node]):
        self.fn = fn
        self.__name__ = fn.__name__
        self.name = fn.__name__
        update_wrapper(self, fn)

    def __call__(self, *args: Any, **kwargs: Any) -> Node:
        return Node(
            tag=self,
            props={"args": args, "kwargs": kwargs},
            children=(),
        )


def component(fn: Callable[..., Node]) -> Component:
    return Component(fn)


def on_mount(callback: Callable[[], None]) -> None:
    owner = current_owner()
    if owner is None:
        raise RuntimeError("on_mount() must be called inside a component.")
    owner.add_mount_callback(callback)


def on_cleanup(callback: Callable[[], None]) -> None:
    owner = current_owner()
    if owner is None:
        raise RuntimeError("on_cleanup() must be called inside a component.")
    owner.add_cleanup(callback)


def is_component_tag(tag: Any) -> bool:
    return isinstance(tag, Component)
