from __future__ import annotations

from collections.abc import Callable
from contextlib import ContextDecorator
from typing import Any


_batch_depth = 0
_pending_callbacks: list[Callable[[], None]] = []
_pending_callback_keys: set[object] = set()


class Batch(ContextDecorator):
    def __enter__(self) -> "Batch":
        global _batch_depth
        _batch_depth += 1
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        global _batch_depth
        _batch_depth -= 1
        if exc_type is not None:
            if _batch_depth == 0:
                _pending_callbacks.clear()
                _pending_callback_keys.clear()
            return None
        if _batch_depth == 0:
            flush()
        return None


def batch(fn: Callable[[], Any] | None = None) -> Any:
    if fn is None:
        return Batch()
    with Batch():
        return fn()


def schedule(callback: Callable[[], None]) -> None:
    if _batch_depth <= 0:
        callback()
        return
    callback_key = _callback_key(callback)
    if callback_key in _pending_callback_keys:
        return
    _pending_callback_keys.add(callback_key)
    _pending_callbacks.append(callback)


def flush() -> None:
    while _pending_callbacks:
        callbacks = list(_pending_callbacks)
        _pending_callbacks.clear()
        _pending_callback_keys.clear()
        for callback in callbacks:
            callback()


def _callback_key(callback: Callable[[], None]) -> object:
    instance = getattr(callback, "__self__", None)
    func = getattr(callback, "__func__", None)
    if instance is not None and func is not None:
        return (id(instance), id(func))
    return id(callback)
