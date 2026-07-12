import pytest

from otoe import (
    Button,
    EventSignature,
    EventHandlerArityError,
    Input,
    ScrollView,
    Text,
    UI_EVENT_SIGNATURES,
    UnknownEventError,
    UnknownPropError,
    event_signature_for,
    format_event_signature,
    mount,
    root_widget,
)
from otoe.widgets import ShortcutScope as ShortcutScopeWidget


def test_builtin_widget_event_signatures_match_declared_events():
    for widget in (Button, Input, ScrollView, ShortcutScopeWidget):
        assert set(widget.event_signatures) == widget.events


def test_builtin_widget_event_signatures_are_introspectable():
    assert event_signature_for(Button, "onClick") == EventSignature()
    assert event_signature_for(Button, "onKeyDown") == EventSignature(("key",))
    assert event_signature_for(Input, "onChange") == EventSignature(("value",))
    assert event_signature_for(ScrollView, "onScroll") == EventSignature(
        ("next_scroll_y",)
    )
    assert event_signature_for(ShortcutScopeWidget, "onGlobalKeyDown") == EventSignature(
        ("event",)
    )
    assert event_signature_for(Button, "onTap") is None


def test_event_signature_formatter_documents_callback_shape():
    assert format_event_signature("onClick", EventSignature()) == "onClick()"
    assert (
        format_event_signature("onChange", EventSignature(("value",)))
        == "onChange(value)"
    )


def test_ui_event_signature_catalog_documents_public_callbacks():
    assert set(UI_EVENT_SIGNATURES) == {
        "ActionButton.onClick",
        "CommandPalette.on_query",
        "CommandPalette.on_select",
        "EmptyState.on_action",
        "ListRow.on_action",
        "Menu.on_focus",
        "Menu.on_open_change",
        "Menu.on_select",
        "NavItem.on_navigate",
        "SectionHeader.on_action",
        "Select.on_change",
        "Select.on_open_change",
        "ShortcutScope.onKeyDown",
        "SidebarNav.on_navigate",
        "TabButton.onClick",
    }
    assert UI_EVENT_SIGNATURES["ActionButton.onClick"] == EventSignature()
    assert UI_EVENT_SIGNATURES["CommandPalette.on_query"] == EventSignature(("value",))
    assert UI_EVENT_SIGNATURES["CommandPalette.on_select"] == EventSignature(
        ("command_id",)
    )
    assert UI_EVENT_SIGNATURES["SectionHeader.on_action"] == EventSignature()
    assert UI_EVENT_SIGNATURES["EmptyState.on_action"] == EventSignature()
    assert UI_EVENT_SIGNATURES["ListRow.on_action"] == EventSignature()
    assert UI_EVENT_SIGNATURES["Select.on_change"] == EventSignature(("value",))
    assert UI_EVENT_SIGNATURES["SidebarNav.on_navigate"] == EventSignature(
        ("route_id",)
    )


def test_unknown_widget_prop_error_lists_widget_and_known_props():
    with pytest.raises(UnknownPropError) as excinfo:
        mount(Text("Hello", clasName="title"))

    message = str(excinfo.value)
    assert "Text received unknown prop 'clasName'." in message
    assert "Known props:" in message
    assert "className" in message
    assert "content" in message


def test_unknown_widget_event_error_lists_widget_and_known_events():
    with pytest.raises(UnknownEventError) as excinfo:
        mount(Button("Save", onClik=lambda: None))

    message = str(excinfo.value)
    assert "Button received unknown event 'onClik'." in message
    assert "Known events:" in message
    assert "onClick()" in message
    assert "onKeyDown(key)" in message


def test_event_handler_arity_error_includes_event_signature():
    mounted = mount(Button("Save", onClick=lambda value: None))
    button = root_widget(mounted)

    with pytest.raises(EventHandlerArityError) as excinfo:
        button.trigger("onClick")

    message = str(excinfo.value)
    assert "Button.onClick() handler" in message
    assert "expected (value)" in message
    assert "got 0 argument(s)" in message
