from __future__ import annotations

import threading
from collections.abc import Callable, Iterable
from typing import Any

from otoe import (
    Button,
    Computed,
    HStack,
    LiveHtmlRenderer,
    Text,
    VStack,
    component,
    computed,
    mount,
    signal,
    unmount,
)


@component
def CounterSurface(
    count_label: Computed,
    on_increment: Callable[[], None],
    on_decrement: Callable[[], None],
):
    return VStack(
        Text("Live counter", className="eyebrow"),
        Text(count_label, className="counter-value"),
        HStack(
            Button("Decrement", onClick=on_decrement),
            Button("Increment", onClick=on_increment),
            gap=8,
        ),
        className="counter-surface",
        gap=12,
        padding=16,
    )


class CounterPreview:
    def __init__(self) -> None:
        self._disposed = False
        owned_cleanups: list[Callable[[], None]] = []
        try:
            self._lock = threading.RLock()
            self.renderer = LiveHtmlRenderer()
            self.count = signal(0)
            self.count_label = computed(lambda: f"Count: {self.count.value}")
            owned_cleanups.append(self.count_label.dispose)
            self.app = mount(
                CounterSurface(
                    count_label=self.count_label,
                    on_increment=self.increment,
                    on_decrement=self.decrement,
                )
            )
            owned_cleanups.append(lambda: unmount(self.app))
        except BaseException as primary_error:
            self._disposed = True
            _cleanup_after_construction_failure(
                primary_error,
                reversed(owned_cleanups),
            )
            raise

    def render_fragment(self) -> str:
        with self._lock:
            self.renderer.clear()
            return self.renderer.render(self.app, pretty=True, indent=4)

    def dispatch_event(self, event_id: str, *args: Any) -> str:
        with self._lock:
            self.renderer.dispatch(event_id, *args)
            return self.render_fragment()

    def increment(self) -> None:
        self.count.set(self.count.value + 1)

    def decrement(self) -> None:
        self.count.set(self.count.value - 1)

    def dispose(self) -> None:
        if self._disposed:
            return
        self._disposed = True

        errors: list[BaseException] = []
        cleanups: tuple[Callable[[], None], ...] = (
            lambda: unmount(self.app),
            self.count_label.dispose,
        )
        for cleanup in cleanups:
            try:
                cleanup()
            except BaseException as exc:
                errors.append(exc)
        if len(errors) == 1:
            raise errors[0]
        if errors:
            raise BaseExceptionGroup("Live counter cleanup failed.", errors)


def _cleanup_after_construction_failure(
    primary_error: BaseException,
    cleanups: Iterable[Callable[[], None]],
) -> None:
    errors: list[BaseException] = [primary_error]
    for cleanup in cleanups:
        try:
            cleanup()
        except BaseException as cleanup_error:
            errors.append(cleanup_error)
    if len(errors) > 1:
        raise BaseExceptionGroup(
            "Live counter construction and cleanup failed.",
            errors,
        ) from primary_error


def app() -> CounterPreview:
    return CounterPreview()
