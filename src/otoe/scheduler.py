from __future__ import annotations

from collections.abc import Callable
from contextlib import ContextDecorator, contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from queue import Empty, SimpleQueue
from threading import RLock, get_ident
from typing import Any, Iterator


__all__ = [
    "PostedCallbackQueue",
    "batch",
    "capture_post",
    "post",
    "drain_posted",
]


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


class PostedCallbackQueue:
    """Thread-safe callback handoff owned by one active runtime thread."""

    def __init__(self) -> None:
        self._callbacks: SimpleQueue[Callable[[], None]] = SimpleQueue()
        self._activation_lock = RLock()
        self._runtime_thread: int | None = None
        self._activation_depth = 0
        self._accepting = True
        self._closing = False
        self._closed = False

    @property
    def closed(self) -> bool:
        """Whether this queue has been permanently closed."""
        with self._activation_lock:
            return self._closed

    def post(self, callback: Callable[[], None]) -> None:
        if not callable(callback):
            raise TypeError("post callback must be callable.")
        with self._activation_lock:
            if not self._accepting and not (
                self._closing and self._runtime_thread == get_ident()
            ):
                raise RuntimeError("The posted callback runtime is not accepting work.")
            self._callbacks.put(callback)

    def drain(self, *, max_callbacks: int | None = None) -> int:
        if max_callbacks is not None and max_callbacks < 1:
            raise ValueError("max_callbacks must be >= 1 when provided.")
        with self._activation_lock:
            runtime_thread = self._runtime_thread
        if runtime_thread is not None and runtime_thread != get_ident():
            raise RuntimeError(
                "Posted callbacks must be drained by their owning runtime thread."
            )

        callbacks: list[Callable[[], None]] = []
        while max_callbacks is None or len(callbacks) < max_callbacks:
            try:
                callbacks.append(self._callbacks.get_nowait())
            except Empty:
                break

        errors: list[BaseException] = []
        for callback in callbacks:
            try:
                callback()
            except BaseException as exc:
                errors.append(exc)
        if len(errors) == 1:
            raise errors[0]
        if errors:
            raise BaseExceptionGroup("Multiple posted callbacks failed.", errors)
        return len(callbacks)

    def close(self) -> None:
        """Permanently stop accepting work and drain accepted callbacks.

        An active queue is sealed immediately and drained by the owning runtime
        when its outermost activation exits. An inactive queue is drained by
        the caller, which must therefore be the thread that owns its callbacks.
        """
        runtime_thread = get_ident()
        with self._activation_lock:
            if self._closed:
                return
            self._closed = True
            self._accepting = False
            if self._activation_depth > 0 or self._closing:
                return
            self._closing = True
            self._runtime_thread = runtime_thread

        try:
            with self.bind():
                self._drain_until_quiescent()
        finally:
            with self._activation_lock:
                self._closing = False
                self._runtime_thread = None

    @contextmanager
    def bind(self) -> Iterator["PostedCallbackQueue"]:
        """Route unqualified posts in this context to this queue."""
        token = _CURRENT_POSTED_CALLBACKS.set(self)
        try:
            yield self
        finally:
            _CURRENT_POSTED_CALLBACKS.reset(token)

    @contextmanager
    def activate(self) -> Iterator["PostedCallbackQueue"]:
        """Register and bind this queue for one runtime event loop."""
        runtime_thread = get_ident()
        with self._activation_lock:
            if self._closed:
                raise RuntimeError("A closed posted callback queue cannot be activated.")
            if (
                self._runtime_thread is not None
                and self._runtime_thread != runtime_thread
            ):
                raise RuntimeError(
                    "A posted callback queue cannot be active on multiple threads."
                )
            self._runtime_thread = runtime_thread
            self._activation_depth += 1
            first_activation = self._activation_depth == 1
            if first_activation:
                self._accepting = True
                self._closing = False
        registered = False
        deactivated = False
        try:
            if first_activation:
                with _ACTIVE_POSTED_CALLBACKS_LOCK:
                    _ACTIVE_POSTED_CALLBACKS.add(self)
                    registered = True
                    if (
                        len(_ACTIVE_POSTED_CALLBACKS) == 1
                        and self is not _DEFAULT_POSTED_CALLBACKS
                    ):
                        _DEFAULT_POSTED_CALLBACKS._move_pending_to(self)
            with self.bind():
                try:
                    yield self
                except BaseException as primary_error:
                    deactivated = True
                    try:
                        self._deactivate(registered=registered)
                    except BaseException as shutdown_error:
                        raise BaseExceptionGroup(
                            "Posted callback runtime and shutdown both failed.",
                            [primary_error, shutdown_error],
                        ) from primary_error
                    raise
                else:
                    deactivated = True
                    self._deactivate(registered=registered)
        finally:
            if not deactivated:
                with self._activation_lock:
                    self._activation_depth -= 1
                    final_deactivation = self._activation_depth == 0
                    if final_deactivation:
                        self._accepting = False
                        self._runtime_thread = None
                if final_deactivation and registered:
                    with _ACTIVE_POSTED_CALLBACKS_LOCK:
                        _ACTIVE_POSTED_CALLBACKS.discard(self)

    def _deactivate(self, *, registered: bool) -> None:
        with self._activation_lock:
            self._activation_depth -= 1
            final_deactivation = self._activation_depth == 0
            if not final_deactivation:
                return
            self._accepting = False
            self._closing = True

        try:
            self._drain_until_quiescent()
        finally:
            with self._activation_lock:
                self._closing = False
                self._runtime_thread = None
            if registered:
                with _ACTIVE_POSTED_CALLBACKS_LOCK:
                    _ACTIVE_POSTED_CALLBACKS.discard(self)

    def _drain_until_quiescent(self) -> None:
        errors: list[BaseException] = []
        while True:
            try:
                drained = self.drain()
            except BaseException as exc:
                errors.append(exc)
                continue
            if drained == 0:
                break
        if len(errors) == 1:
            raise errors[0]
        if errors:
            raise BaseExceptionGroup(
                "Multiple posted callbacks failed during runtime shutdown.",
                errors,
            )

    def _move_pending_to(self, target: "PostedCallbackQueue") -> None:
        while True:
            try:
                callback = self._callbacks.get_nowait()
            except Empty:
                return
            target._callbacks.put(callback)


_DEFAULT_POSTED_CALLBACKS = PostedCallbackQueue()
_CURRENT_POSTED_CALLBACKS: ContextVar[PostedCallbackQueue | None] = ContextVar(
    "otoe_current_posted_callbacks",
    default=None,
)
_ACTIVE_POSTED_CALLBACKS: set[PostedCallbackQueue] = set()
_ACTIVE_POSTED_CALLBACKS_LOCK = RLock()


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


def capture_post() -> Callable[[Callable[[], None]], None]:
    """Capture the current runtime poster, or a safe dynamic legacy router."""
    current = _CURRENT_POSTED_CALLBACKS.get()
    if current is not None:
        return current.post
    with _ACTIVE_POSTED_CALLBACKS_LOCK:
        if not _ACTIVE_POSTED_CALLBACKS:
            return post
        return _unbound_post_queue().post


def post(
    callback: Callable[[], None],
    *,
    queue: PostedCallbackQueue | None = None,
) -> None:
    """Queue work for a runtime thread to execute with ``drain_posted``."""
    if queue is not None:
        queue.post(callback)
        return
    current = _CURRENT_POSTED_CALLBACKS.get()
    if current is not None:
        current.post(callback)
        return
    if not callable(callback):
        raise TypeError("post callback must be callable.")
    with _ACTIVE_POSTED_CALLBACKS_LOCK:
        target = _unbound_post_queue()
        target.post(callback)


def drain_posted(
    *,
    max_callbacks: int | None = None,
    queue: PostedCallbackQueue | None = None,
) -> int:
    """Run queued cross-thread callbacks in the calling runtime thread."""
    target = queue or _CURRENT_POSTED_CALLBACKS.get() or _DEFAULT_POSTED_CALLBACKS
    return target.drain(max_callbacks=max_callbacks)


def _unbound_post_queue() -> PostedCallbackQueue:
    active = tuple(_ACTIVE_POSTED_CALLBACKS)
    if not active:
        return _DEFAULT_POSTED_CALLBACKS
    if len(active) == 1:
        return active[0]
    raise RuntimeError(
        "post() cannot choose between multiple active runtimes; capture a bound "
        "poster on the runtime thread with capture_post(), or pass queue= explicitly."
    )


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
