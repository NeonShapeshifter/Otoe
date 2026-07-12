from __future__ import annotations

from collections.abc import Callable
from contextlib import ContextDecorator
from contextvars import ContextVar
from dataclasses import dataclass, field
from queue import Empty, SimpleQueue
from typing import Any


__all__ = ["batch", "post", "drain_posted"]


@dataclass
class _RollbackAction:
    restore: Callable[[], None]
    notify: Callable[[], None]


@dataclass
class _BatchState:
    depth: int = 0
    pending_callbacks: list[Callable[[], None]] = field(default_factory=list)
    pending_callback_keys: set[object] = field(default_factory=set)
    rollback_actions: dict[object, _RollbackAction] = field(default_factory=dict)
    flushing: bool = False


_CURRENT_BATCH: ContextVar[_BatchState | None] = ContextVar(
    "otoe_current_batch",
    default=None,
)
_POSTED_CALLBACKS: SimpleQueue[Callable[[], None]] = SimpleQueue()


class Batch(ContextDecorator):
    def __init__(self) -> None:
        self._state: _BatchState | None = None
        self._token: Any = None

    def __enter__(self) -> "Batch":
        state = _CURRENT_BATCH.get()
        if state is None:
            state = _BatchState()
            self._token = _CURRENT_BATCH.set(state)
        self._state = state
        state.depth += 1
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        state = self._state
        if state is None:
            raise RuntimeError("Batch exited without being entered.")
        state.depth -= 1
        try:
            if exc_type is not None:
                _rollback_batch(state, notify=False)
                return None
            if state.depth == 0:
                flush()
            return None
        finally:
            if self._token is not None:
                _CURRENT_BATCH.reset(self._token)
            self._state = None
            self._token = None


def batch(fn: Callable[[], Any] | None = None) -> Any:
    if fn is None:
        return Batch()
    with Batch():
        return fn()


def schedule(callback: Callable[[], None]) -> None:
    state = _CURRENT_BATCH.get()
    if state is None or state.depth <= 0:
        callback()
        return
    callback_key = _callback_key(callback)
    if callback_key in state.pending_callback_keys:
        return
    state.pending_callback_keys.add(callback_key)
    state.pending_callbacks.append(callback)


def _register_rollback(
    key: object,
    *,
    restore: Callable[[], None],
    notify: Callable[[], None],
) -> None:
    state = _CURRENT_BATCH.get()
    if state is None or (state.depth <= 0 and not state.flushing):
        return
    state.rollback_actions.setdefault(key, _RollbackAction(restore, notify))


def post(callback: Callable[[], None]) -> None:
    """Queue work for the runtime thread to execute with ``drain_posted``."""
    if not callable(callback):
        raise TypeError("post callback must be callable.")
    _POSTED_CALLBACKS.put(callback)


def drain_posted(*, max_callbacks: int | None = None) -> int:
    """Run queued cross-thread callbacks in the calling runtime thread."""
    if max_callbacks is not None and max_callbacks < 1:
        raise ValueError("max_callbacks must be >= 1 when provided.")

    callbacks: list[Callable[[], None]] = []
    while max_callbacks is None or len(callbacks) < max_callbacks:
        try:
            callbacks.append(_POSTED_CALLBACKS.get_nowait())
        except Empty:
            break

    errors: list[Exception] = []
    for callback in callbacks:
        try:
            callback()
        except Exception as exc:
            errors.append(exc)
    if len(errors) == 1:
        raise errors[0]
    if errors:
        raise ExceptionGroup("Multiple posted callbacks failed.", errors)
    return len(callbacks)


def flush() -> None:
    state = _CURRENT_BATCH.get()
    if state is None:
        return
    errors: list[Exception] = []
    state.flushing = True
    try:
        while state.pending_callbacks:
            callbacks = list(state.pending_callbacks)
            state.pending_callbacks.clear()
            state.pending_callback_keys.clear()
            for callback in callbacks:
                try:
                    callback()
                except Exception as exc:
                    errors.append(exc)
    finally:
        state.flushing = False
    if errors:
        errors.extend(_rollback_batch(state, notify=True))
    else:
        state.rollback_actions.clear()
    if len(errors) == 1:
        raise errors[0]
    if errors:
        raise ExceptionGroup("Multiple batched callbacks failed.", errors)


def _rollback_batch(state: _BatchState, *, notify: bool) -> list[Exception]:
    actions = list(reversed(state.rollback_actions.values()))
    state.rollback_actions.clear()
    state.pending_callbacks.clear()
    state.pending_callback_keys.clear()

    errors: list[Exception] = []
    for action in actions:
        try:
            action.restore()
        except Exception as exc:
            errors.append(exc)
    if notify:
        for action in reversed(actions):
            try:
                action.notify()
            except Exception as exc:
                errors.append(exc)
    return errors


def _callback_key(callback: Callable[[], None]) -> object:
    instance = getattr(callback, "__self__", None)
    func = getattr(callback, "__func__", None)
    if instance is not None and func is not None:
        return (id(instance), id(func))
    return id(callback)
