from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .owner import current_owner


class Interval:
    def __init__(self, seconds: float, callback: Callable[[], Any]):
        if seconds <= 0:
            raise ValueError("interval seconds must be > 0.")
        if not callable(callback):
            raise TypeError("interval callback must be callable.")
        self.seconds = float(seconds)
        self.callback = callback
        self.active = True

    def tick(self) -> Any:
        if not self.active:
            return None
        return self.callback()

    def cancel(self) -> None:
        self.active = False

    def dispose(self) -> None:
        self.cancel()


def interval(seconds: float, callback: Callable[[], Any], *, immediate: bool = False) -> Interval:
    handle = Interval(seconds, callback)
    owner = current_owner()
    if owner is not None:
        owner.add_disposable(handle)
    if immediate:
        handle.tick()
    return handle

