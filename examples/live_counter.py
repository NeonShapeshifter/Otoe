from __future__ import annotations

import threading
from collections.abc import Callable
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
        self._lock = threading.RLock()
        self.renderer = LiveHtmlRenderer()
        self.count = signal(0)
        self.count_label = computed(lambda: f"Count: {self.count.value}")
        self.app = mount(
            CounterSurface(
                count_label=self.count_label,
                on_increment=self.increment,
                on_decrement=self.decrement,
            )
        )

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


def app() -> CounterPreview:
    return CounterPreview()
