from __future__ import annotations

from .events import EventSignature
from .node import Widget


class VStack(Widget):
    props = {"className", "gap", "padding", "id"}
    events = set()


class HStack(Widget):
    props = {"className", "gap", "padding", "id"}
    events = set()


class Text(Widget):
    primary_prop = "content"
    props = {"content", "className", "color", "id"}
    events = set()


class Button(Widget):
    primary_prop = "label"
    props = {"label", "className", "disabled", "id"}
    events = {"onClick", "onKeyDown", "onFocus", "onBlur"}
    event_signatures = {
        "onBlur": EventSignature(),
        "onClick": EventSignature(),
        "onFocus": EventSignature(),
        "onKeyDown": EventSignature(("key",)),
    }


class Input(Widget):
    props = {"value", "placeholder", "className", "disabled", "autoFocus", "id"}
    events = {"onChange", "onKeyDown", "onFocus", "onBlur"}
    event_signatures = {
        "onBlur": EventSignature(),
        "onChange": EventSignature(("value",)),
        "onFocus": EventSignature(),
        "onKeyDown": EventSignature(("key",)),
    }


class ScrollView(Widget):
    props = {"className", "id", "scrollY"}
    events = {"onScroll"}
    event_signatures = {
        "onScroll": EventSignature(("next_scroll_y",)),
    }


class Panel(Widget):
    props = {"className", "title", "id"}
    events = set()


class ShortcutScope(Widget):
    props = {"className", "id"}
    events = {"onGlobalKeyDown"}
    event_signatures = {
        "onGlobalKeyDown": EventSignature(("event",)),
    }


class FocusScope(Widget):
    props = {"className", "trapFocus", "restoreFocus", "id"}
    events = set()
