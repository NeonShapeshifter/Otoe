from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from .events import dispatch_event
from .html import render_html
from .mount import FakeWidget, MountedNode


@dataclass(frozen=True)
class LiveEvent:
    id: str
    widget_name: str
    event_name: str
    handler: Callable[..., Any]


class LiveHtmlRenderer:
    def __init__(self) -> None:
        self.events: dict[str, LiveEvent] = {}

    def clear(self) -> None:
        self.events.clear()

    def render(
        self,
        target: FakeWidget | MountedNode,
        *,
        pretty: bool = False,
        indent: int = 0,
    ) -> str:
        return render_html(
            target,
            pretty=pretty,
            indent=indent,
            attributes=self._attributes_for,
        )

    def dispatch(self, event_id: str, *args: Any) -> Any:
        if event_id not in self.events:
            raise KeyError(f"Unknown live event id {event_id!r}.")
        event = self.events[event_id]
        return dispatch_event(event.handler, *args)

    def _attributes_for(self, widget: FakeWidget) -> dict[str, str]:
        attrs = {}
        if "onClick" in widget.events:
            attrs["data-otoe-click"] = self._register(widget, "onClick")
        if "onChange" in widget.events:
            attrs["data-otoe-change"] = self._register(widget, "onChange")
        if "onKeyDown" in widget.events:
            attrs["data-otoe-keydown"] = self._register(widget, "onKeyDown")
        if "onGlobalKeyDown" in widget.events:
            attrs["data-otoe-global-keydown"] = self._register(widget, "onGlobalKeyDown")
        return attrs

    def _register(self, widget: FakeWidget, event_name: str) -> str:
        event_id = f"{id(widget):x}:{event_name}"
        self.events[event_id] = LiveEvent(
            id=event_id,
            widget_name=widget.name,
            event_name=event_name,
            handler=widget.events[event_name],
        )
        return event_id
