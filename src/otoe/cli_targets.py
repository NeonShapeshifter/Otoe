from __future__ import annotations

from typing import Any

from .cli_common import CliError
from .mount import MountedNode, mount
from .node import Node


def coerce_render_target(target: Any) -> MountedNode:
    if isinstance(target, MountedNode):
        return target
    if isinstance(target, Node):
        return mount(target)
    if callable(target):
        return coerce_render_target(target())
    raise CliError(
        "render target must be a Node, MountedNode, or zero-argument callable "
        f"returning one; got {type(target).__name__}"
    )
