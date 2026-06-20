from __future__ import annotations

from ._widget_contracts import (
    _core_widget_event_signatures,
    _core_widget_events,
    _core_widget_primary_prop,
    _core_widget_props,
)
from .node import Widget


class VStack(Widget):
    props = _core_widget_props("VStack")
    events = _core_widget_events("VStack")


class HStack(Widget):
    props = _core_widget_props("HStack")
    events = _core_widget_events("HStack")


class Text(Widget):
    primary_prop = _core_widget_primary_prop("Text")
    props = _core_widget_props("Text")
    events = _core_widget_events("Text")


class Button(Widget):
    primary_prop = _core_widget_primary_prop("Button")
    props = _core_widget_props("Button")
    events = _core_widget_events("Button")
    event_signatures = _core_widget_event_signatures("Button")


class Input(Widget):
    props = _core_widget_props("Input")
    events = _core_widget_events("Input")
    event_signatures = _core_widget_event_signatures("Input")


class ScrollView(Widget):
    props = _core_widget_props("ScrollView")
    events = _core_widget_events("ScrollView")
    event_signatures = _core_widget_event_signatures("ScrollView")


class Panel(Widget):
    props = _core_widget_props("Panel")
    events = _core_widget_events("Panel")


class ShortcutScope(Widget):
    props = _core_widget_props("ShortcutScope")
    events = _core_widget_events("ShortcutScope")
    event_signatures = _core_widget_event_signatures("ShortcutScope")


class FocusScope(Widget):
    props = _core_widget_props("FocusScope")
    events = _core_widget_events("FocusScope")
