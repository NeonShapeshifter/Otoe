from __future__ import annotations

from contextvars import ContextVar
from threading import get_ident
from typing import Any, Callable

from .errors import ReactiveDisposedError, ReactiveMutationError, ReactiveThreadError
from .owner import current_mount_phase, current_owner
from .scheduler import _register_rollback, schedule


Collector = Any
CURRENT_COLLECTOR: ContextVar[Collector | None] = ContextVar(
    "otoe_current_collector",
    default=None,
)


class Subscription:
    def __init__(self, unsubscribe: Callable[[], None]):
        self._unsubscribe = unsubscribe
        self._active = True

    def dispose(self) -> None:
        if not self._active:
            return
        self._active = False
        self._unsubscribe()


class ReactiveValue:
    def __init__(self) -> None:
        self._subscribers: dict[Callable[[], None], int] = {}

    def subscribe(self, callback: Callable[[], None]) -> Subscription:
        subscriber_thread = get_ident()
        existing_threads = set(self._subscribers.values())
        if existing_threads and existing_threads != {subscriber_thread}:
            raise ReactiveThreadError(
                "Reactive subscribers for one value must belong to one runtime thread."
            )
        self._subscribers[callback] = subscriber_thread

        def unsubscribe() -> None:
            self._subscribers.pop(callback, None)

        return Subscription(unsubscribe)

    def _track_read(self) -> None:
        collector = CURRENT_COLLECTOR.get()
        if collector is not None:
            collector._depend_on(self)

    def _notify(self) -> None:
        self._assert_notification_thread()
        errors: list[Exception] = []
        for callback in tuple(self._subscribers):
            try:
                schedule(callback)
            except Exception as exc:
                errors.append(exc)
        _raise_notification_errors(errors)

    def _assert_notification_thread(self) -> None:
        if not self._subscribers:
            return
        subscriber_thread = next(iter(self._subscribers.values()))
        current_thread = get_ident()
        if current_thread == subscriber_thread:
            return
        raise ReactiveThreadError(
            "Reactive updates must run on the subscriber's runtime thread; "
            "queue worker results with otoe.scheduler.post(...) and call "
            "otoe.scheduler.drain_posted() on the runtime thread."
        )


class Signal(ReactiveValue):
    def __init__(self, initial: Any):
        super().__init__()
        self._value = initial

    @property
    def value(self) -> Any:
        self._track_read()
        return self._value

    @value.setter
    def value(self, next_value: Any) -> None:
        if _values_equal(next_value, self._value):
            return
        _guard_mount_mutation(self)
        self._assert_notification_thread()
        previous_value = self._value
        _register_rollback(
            self,
            restore=lambda: self._restore_value(previous_value),
            notify=self._notify,
        )
        self._value = next_value
        try:
            self._notify()
        except Exception as update_error:
            self._value = previous_value
            try:
                self._notify()
            except Exception as rollback_error:
                raise ExceptionGroup(
                    "Reactive update and rollback notifications failed.",
                    [update_error, rollback_error],
                ) from update_error
            raise

    def set(self, next_value: Any) -> None:
        self.value = next_value

    def _restore_value(self, value: Any) -> None:
        self._value = value


class Computed(ReactiveValue):
    def __init__(self, fn: Callable[[], Any]):
        super().__init__()
        self._fn = fn
        self._value: Any = None
        self._dirty = True
        self._deps: dict[ReactiveValue, Subscription] = {}
        self._disposed = False

        owner = current_owner()
        self._owner_name = owner.name if owner is not None else None
        if owner is not None:
            owner.add_disposable(self)

    @property
    def value(self) -> Any:
        if self._disposed:
            raise ReactiveDisposedError(_disposed_computed_message(self._owner_name))
        self._track_read()
        if self._dirty:
            self._recompute()
        return self._value

    def _recompute(self) -> None:
        self._clear_deps()
        token = CURRENT_COLLECTOR.set(self)
        try:
            self._value = self._fn()
        finally:
            CURRENT_COLLECTOR.reset(token)
        self._dirty = False

    def _depend_on(self, source: ReactiveValue) -> None:
        if source in self._deps:
            return
        self._deps[source] = source.subscribe(self._mark_dirty)

    def _mark_dirty(self) -> None:
        if self._dirty or self._disposed:
            return
        self._dirty = True
        self._notify()

    def _clear_deps(self) -> None:
        for subscription in self._deps.values():
            subscription.dispose()
        self._deps.clear()

    def dispose(self) -> None:
        if self._disposed:
            return
        self._disposed = True
        self._clear_deps()
        self._subscribers.clear()


class Effect:
    def __init__(self, fn: Callable[[], Any], *, autorun: bool = True):
        self._fn = fn
        self._deps: dict[ReactiveValue, Subscription] = {}
        self._cleanup: Callable[[], None] | None = None
        self._disposed = False

        owner = current_owner()
        if owner is not None:
            owner.add_disposable(self)
            if autorun:
                owner.add_pending_effect(self)
        elif autorun:
            try:
                self.run()
            except Exception:
                self.dispose()
                raise

    def run(self) -> None:
        if self._disposed:
            return
        self._run_cleanup()
        self._clear_deps()
        token = CURRENT_COLLECTOR.set(self)
        try:
            result = self._fn()
        finally:
            CURRENT_COLLECTOR.reset(token)
        self._cleanup = result if callable(result) else None

    def _depend_on(self, source: ReactiveValue) -> None:
        if source in self._deps:
            return
        self._deps[source] = source.subscribe(self.run)

    def _run_cleanup(self) -> None:
        if self._cleanup is None:
            return
        cleanup = self._cleanup
        self._cleanup = None
        cleanup()

    def _clear_deps(self) -> None:
        for subscription in self._deps.values():
            subscription.dispose()
        self._deps.clear()

    def dispose(self) -> None:
        if self._disposed:
            return
        self._disposed = True
        errors: list[Exception] = []
        try:
            self._run_cleanup()
        except Exception as exc:
            errors.append(exc)
        try:
            self._clear_deps()
        except Exception as exc:
            errors.append(exc)
        if errors:
            raise ExceptionGroup("Errors while disposing reactive effect.", errors)


def signal(initial: Any) -> Signal:
    return Signal(initial)


def computed(fn: Callable[[], Any]) -> Computed:
    return Computed(fn)


def effect(fn: Callable[[], Any]) -> Effect:
    return Effect(fn, autorun=True)


def is_reactive(value: Any) -> bool:
    return isinstance(value, ReactiveValue)


def _values_equal(left: Any, right: Any) -> bool:
    try:
        result = left == right
    except Exception:
        return left is right
    return result if isinstance(result, bool) else left is right


def _raise_notification_errors(errors: list[Exception]) -> None:
    if not errors:
        return
    if len(errors) == 1:
        raise errors[0]
    raise ExceptionGroup("Multiple reactive subscribers failed.", errors)


def _disposed_computed_message(owner_name: str | None) -> str:
    message = "Computed value was read after it was disposed."
    if owner_name is None:
        return message
    return f"{owner_name}: {message}"


def _guard_mount_mutation(source: ReactiveValue) -> None:
    if current_mount_phase() != "render" or not source._subscribers:
        return
    owner = current_owner()
    owner_name = owner.name if owner is not None else "component render"
    raise ReactiveMutationError(
        f"{owner_name}: Signal value was mutated during component render while "
        "active subscribers exist. Move the mutation to on_mount() or an event handler."
    )
