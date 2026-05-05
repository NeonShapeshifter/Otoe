from __future__ import annotations

from contextvars import ContextVar
from typing import Any, Callable

from .owner import current_owner
from .scheduler import schedule


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
        self._subscribers: set[Callable[[], None]] = set()

    def subscribe(self, callback: Callable[[], None]) -> Subscription:
        self._subscribers.add(callback)
        return Subscription(lambda: self._subscribers.discard(callback))

    def _track_read(self) -> None:
        collector = CURRENT_COLLECTOR.get()
        if collector is not None:
            collector._depend_on(self)

    def _notify(self) -> None:
        for callback in list(self._subscribers):
            schedule(callback)


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
        if next_value == self._value:
            return
        self._value = next_value
        self._notify()

    def set(self, next_value: Any) -> None:
        self.value = next_value


class Computed(ReactiveValue):
    def __init__(self, fn: Callable[[], Any]):
        super().__init__()
        self._fn = fn
        self._value: Any = None
        self._dirty = True
        self._deps: dict[ReactiveValue, Subscription] = {}
        self._disposed = False

        owner = current_owner()
        if owner is not None:
            owner.add_disposable(self)

    @property
    def value(self) -> Any:
        if self._disposed:
            raise RuntimeError("Cannot read a disposed computed value.")
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
            self.run()

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
        self._run_cleanup()
        self._clear_deps()


def signal(initial: Any) -> Signal:
    return Signal(initial)


def computed(fn: Callable[[], Any]) -> Computed:
    return Computed(fn)


def effect(fn: Callable[[], Any]) -> Effect:
    return Effect(fn, autorun=True)


def is_reactive(value: Any) -> bool:
    return isinstance(value, ReactiveValue)
