from __future__ import annotations

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
    events = {"onClick", "onFocus", "onBlur"}


class Input(Widget):
    props = {"value", "placeholder", "className", "disabled", "id"}
    events = {"onChange", "onKeyDown", "onFocus", "onBlur"}


class ScrollView(Widget):
    props = {"className", "id"}
    events = set()


class Panel(Widget):
    props = {"className", "title", "id"}
    events = set()

