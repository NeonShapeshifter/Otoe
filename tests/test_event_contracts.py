from otoe import (
    Button,
    EventSignature,
    Input,
    ScrollView,
    UI_EVENT_SIGNATURES,
    event_signature_for,
    format_event_signature,
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
    assert UI_EVENT_SIGNATURES["ActionButton.onClick"] == EventSignature()
    assert UI_EVENT_SIGNATURES["CommandPalette.on_query"] == EventSignature(("value",))
    assert UI_EVENT_SIGNATURES["CommandPalette.on_select"] == EventSignature(
        ("command_id",)
    )
    assert UI_EVENT_SIGNATURES["Select.on_change"] == EventSignature(("value",))
    assert UI_EVENT_SIGNATURES["SidebarNav.on_navigate"] == EventSignature(
        ("route_id",)
    )
