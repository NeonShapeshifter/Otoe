from __future__ import annotations

from otoe import Button, EventSignature, HStack, Input, Panel, ScrollView, Text, VStack
from otoe._widget_contracts import (
    known_widget_names,
    widget_contract_for_name,
    widget_contract_for_tag,
    widget_event_signatures,
    widget_events,
    widget_props,
)
from otoe.mount import mount, root_widget
from otoe.node import Widget
from otoe.widgets import FocusScope, ShortcutScope


CORE_WIDGETS = (
    Text,
    Button,
    Input,
    VStack,
    HStack,
    Panel,
    ScrollView,
    ShortcutScope,
    FocusScope,
)


def test_known_widget_names_are_core_widget_contracts() -> None:
    assert known_widget_names() == tuple(widget.__name__ for widget in CORE_WIDGETS)


def test_widget_contract_registry_matches_widget_classes() -> None:
    for widget in CORE_WIDGETS:
        contract = widget_contract_for_tag(widget)

        assert contract is not None
        assert contract is widget_contract_for_name(widget.__name__)
        assert contract.name == widget.__name__
        assert contract.widget is widget
        assert contract.props == frozenset(widget.props)
        assert contract.events == frozenset(widget.events)
        assert dict(contract.event_signatures) == widget.event_signatures
        assert contract.primary_prop == widget.primary_prop


def test_widget_contract_helpers_return_registered_values() -> None:
    assert widget_props(Button) == frozenset({"label", "className", "disabled", "id"})
    assert widget_events(Button) == frozenset(
        {"onClick", "onKeyDown", "onFocus", "onBlur"}
    )
    assert widget_event_signatures(Button) == {
        "onBlur": EventSignature(),
        "onClick": EventSignature(),
        "onFocus": EventSignature(),
        "onKeyDown": EventSignature(("key",)),
    }


def test_widget_contract_helpers_fall_back_for_custom_widgets() -> None:
    events: list[str] = []

    class Hero(Widget):
        primary_prop = "title"
        props = {"title", "className"}
        events = {"onHero"}
        event_signatures = {"onHero": EventSignature(("value",))}

    assert widget_contract_for_tag(Hero) is None
    assert widget_contract_for_name("Hero") is None
    assert widget_props(Hero) == frozenset({"title", "className"})
    assert widget_events(Hero) == frozenset({"onHero"})
    assert widget_event_signatures(Hero) == {"onHero": EventSignature(("value",))}

    widget = root_widget(mount(Hero("Launch", onHero=lambda value: events.append(value))))

    assert widget.props == {"title": "Launch"}
    widget.trigger("onHero", "armed")
    assert events == ["armed"]


def test_widget_contract_helpers_do_not_treat_subclasses_as_core_contracts() -> None:
    class DangerButton(Button):
        props = {"label", "severity"}
        events = {"onDanger"}
        event_signatures = {"onDanger": EventSignature()}

    assert widget_contract_for_tag(DangerButton) is None
    assert widget_props(DangerButton) == frozenset({"label", "severity"})
    assert widget_events(DangerButton) == frozenset({"onDanger"})
    assert widget_event_signatures(DangerButton) == {"onDanger": EventSignature()}
