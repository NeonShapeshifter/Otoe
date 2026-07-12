from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from .events import EventSignature, dispatch_event, event_signature_for
from .html import render_html
from .mount import FakeWidget, MountedNode


@dataclass(frozen=True)
class LiveEvent:
    id: str
    widget_name: str
    event_name: str
    handler: Callable[..., Any]
    widget_tag: Any = None
    event_signature: EventSignature | None = None
    context: str | None = None


class LiveHtmlRenderer:
    def __init__(self) -> None:
        self.events: dict[str, LiveEvent] = {}
        self._frame_events: dict[str, LiveEvent] | None = None
        self._replace_events_on_render = True

    def clear(self) -> None:
        self.events.clear()
        # Existing previews use clear() to compose one live frame from several roots.
        self._replace_events_on_render = False

    def render(
        self,
        target: FakeWidget | MountedNode,
        *,
        pretty: bool = False,
        indent: int = 0,
    ) -> str:
        frame_events: dict[str, LiveEvent] = {}
        previous_frame_events = self._frame_events
        # Without an explicit clear(), each render call owns the active event frame.
        replace_events = self._replace_events_on_render
        self._frame_events = frame_events
        try:
            html = render_html(
                target,
                pretty=pretty,
                indent=indent,
                attributes=self._attributes_for,
            )
        finally:
            self._frame_events = previous_frame_events
        if replace_events:
            self.events.clear()
        self.events.update(frame_events)
        return html

    def dispatch(self, event_id: str, *args: Any) -> Any:
        if event_id not in self.events:
            raise KeyError(f"Unknown live event id {event_id!r}.")
        event = self.events[event_id]
        self._replace_events_on_render = True
        return dispatch_event(
            event.handler,
            *args,
            context=event.context,
            event_signature=event.event_signature,
        )

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
        events = self._frame_events if self._frame_events is not None else self.events
        events[event_id] = LiveEvent(
            id=event_id,
            widget_name=widget.name,
            event_name=event_name,
            handler=widget.events[event_name],
            widget_tag=widget.tag,
            event_signature=event_signature_for(widget.tag, event_name),
            context=_event_context(widget, event_name),
        )
        return event_id


def _event_context(widget: FakeWidget, event_name: str) -> str:
    leaf = f"{widget.name}.{event_name}"
    if not widget.component_stack:
        return leaf
    return " > ".join((*widget.component_stack, leaf))
