from pathlib import Path

import pytest

from otoe import (
    Button,
    HStack,
    Input,
    NativeLayoutError,
    StyleRule,
    StyleSheet,
    Text,
    VStack,
    Widget,
    css,
    layout_native,
    mount,
)
from otoe._native_shared import (
    NATIVE_CONTAINER_WIDGETS,
    NATIVE_CONTROL_WIDGETS,
    NATIVE_IGNORED_STYLE_PROPERTIES,
    NATIVE_INPUT_SUPPORT,
    NATIVE_LAYOUT_STYLE_PROPERTIES,
    NATIVE_PAINT_STYLE_PROPERTIES,
    NATIVE_STYLE_SUPPORT,
    NATIVE_TEXT_WIDGETS,
    NATIVE_WIDGET_SUPPORT,
    native_input_support,
    native_style_support,
    native_widget_support,
)
from otoe.style import SUPPORTED_PROPERTIES


EXPECTED_LAYOUT_ONLY_STYLES = frozenset(
    {
        "alignItems",
        "gap",
        "height",
        "justifyContent",
        "maxHeight",
        "maxWidth",
        "minHeight",
        "minWidth",
        "padding",
        "scrollY",
        "width",
    }
)
EXPECTED_PAINT_ONLY_STYLES = frozenset(
    {
        "background",
        "borderColor",
        "borderRadius",
        "color",
    }
)
EXPECTED_LAYOUT_AND_PAINT_STYLES = frozenset({"borderWidth", "fontSize"})
EXPECTED_IGNORED_STYLES = frozenset(
    {
        "borderStyle",
        "display",
        "fontWeight",
        "margin",
        "opacity",
    }
)
EXPECTED_TEXT_WIDGETS = frozenset({"Text"})
EXPECTED_CONTROL_WIDGETS = frozenset({"Button", "Input"})
EXPECTED_CONTAINER_WIDGETS = frozenset(
    {
        "FocusScope",
        "For",
        "HStack",
        "Panel",
        "ScrollView",
        "ShortcutScope",
        "Show",
        "VStack",
    }
)
EXPECTED_SUPPORTED_INPUT = frozenset(
    {
        "click",
        "focus",
        "input_text",
        "key_down",
        "key_input",
        "shortcut",
        "tab_focus",
        "wheel",
    }
)
EXPECTED_DEFERRED_INPUT = frozenset(
    {
        "caret_movement",
        "drag",
        "gesture",
        "ime",
        "inertial_scroll",
        "pointer_move",
        "text_selection",
        "uncontrolled_input",
    }
)


def test_native_style_support_matrix_is_complete_and_categorized():
    assert NATIVE_LAYOUT_STYLE_PROPERTIES == (
        EXPECTED_LAYOUT_ONLY_STYLES | EXPECTED_LAYOUT_AND_PAINT_STYLES
    )
    assert NATIVE_PAINT_STYLE_PROPERTIES == (
        EXPECTED_PAINT_ONLY_STYLES | EXPECTED_LAYOUT_AND_PAINT_STYLES
    )
    assert NATIVE_IGNORED_STYLE_PROPERTIES == EXPECTED_IGNORED_STYLES
    assert set(NATIVE_STYLE_SUPPORT) == set(SUPPORTED_PROPERTIES.values()) | {"scrollY"}

    for name in EXPECTED_LAYOUT_ONLY_STYLES:
        assert native_style_support(name) == "layout"
    for name in EXPECTED_PAINT_ONLY_STYLES:
        assert native_style_support(name) == "paint"
    for name in EXPECTED_LAYOUT_AND_PAINT_STYLES:
        assert native_style_support(name) == "layout+paint"
    for name in EXPECTED_IGNORED_STYLES:
        assert native_style_support(name) == "ignored"
    assert native_style_support("lineHeight") is None


def test_native_style_matrix_matches_layout_acceptance_behavior():
    sheet = css(
        """
        .box {
          align-items: center;
          background: #ffffff;
          border-color: #d0d7de;
          border-radius: 4;
          border-style: solid;
          border-width: 1;
          color: #111827;
          display: flex;
          font-size: 16;
          font-weight: 700;
          gap: 4;
          height: 80;
          justify-content: center;
          margin: 10;
          max-height: 100;
          max-width: 220;
          min-height: 40;
          min-width: 120;
          opacity: 0.9;
          padding: 8;
          width: 180;
        }
        """
    )

    layout = layout_native(
        mount(HStack(Text("Matrix"), className="box")),
        stylesheet=sheet,
    )
    style = dict(layout.root.style)

    assert style["alignItems"] == "center"
    assert style["justifyContent"] == "center"
    assert style["borderStyle"] == "solid"
    assert style["margin"].value == 10
    assert layout.root.width == 180
    assert layout.root.height == 80
    assert layout.by_path((0,)).x > 8
    assert layout.by_path((0,)).y > 8

    unsupported_sheet = StyleSheet(
        rules={".box": StyleRule(".box", {"lineHeight": 20})},
        tokens={},
    )
    with pytest.raises(NativeLayoutError, match="Unsupported native style properties"):
        layout_native(mount(VStack(Text("Nope"), className="box")), stylesheet=unsupported_sheet)


def test_native_widget_support_matrix_is_complete_and_categorized():
    assert NATIVE_TEXT_WIDGETS == EXPECTED_TEXT_WIDGETS
    assert NATIVE_CONTROL_WIDGETS == EXPECTED_CONTROL_WIDGETS
    assert NATIVE_CONTAINER_WIDGETS == EXPECTED_CONTAINER_WIDGETS
    assert set(NATIVE_WIDGET_SUPPORT) == (
        EXPECTED_TEXT_WIDGETS | EXPECTED_CONTROL_WIDGETS | EXPECTED_CONTAINER_WIDGETS
    )

    for name in EXPECTED_TEXT_WIDGETS:
        assert native_widget_support(name) == "text"
    for name in EXPECTED_CONTROL_WIDGETS:
        assert native_widget_support(name) == "control"
    for name in EXPECTED_CONTAINER_WIDGETS:
        assert native_widget_support(name) == "container"
    assert native_widget_support("Hero") == "fallback-container"


def test_native_widget_matrix_matches_layout_fallback_behavior():
    class Hero(Widget):
        props = {"className"}

    layout = layout_native(mount(Hero(HStack(Text("Launch")), className="hero")))

    assert layout.root.name == "Hero"
    assert layout.root.children[0].name == "HStack"
    assert layout.root.children[0].children[0].text == "Launch"

    controls = layout_native(mount(HStack(Button("Run", onClick=lambda: None), Input(value=""))))
    assert controls.by_path((0,)).events == ("onClick",)
    assert controls.by_path((1,)).name == "Input"


def test_native_input_support_matrix_is_complete_and_categorized():
    assert set(NATIVE_INPUT_SUPPORT) == EXPECTED_SUPPORTED_INPUT | EXPECTED_DEFERRED_INPUT

    for name in EXPECTED_SUPPORTED_INPUT:
        assert native_input_support(name) == "supported"
    for name in EXPECTED_DEFERRED_INPUT:
        assert native_input_support(name) == "deferred"
    assert native_input_support("pinch") is None


def test_native_support_matrix_is_reflected_in_renderer_spike_doc():
    doc = Path("NATIVE_RENDERER_SPIKE.md").read_text(encoding="utf-8")

    for name in EXPECTED_LAYOUT_ONLY_STYLES | EXPECTED_LAYOUT_AND_PAINT_STYLES:
        assert f"`{name}`" in doc
    for name in EXPECTED_PAINT_ONLY_STYLES | EXPECTED_LAYOUT_AND_PAINT_STYLES:
        assert f"`{name}`" in doc
    for name in EXPECTED_IGNORED_STYLES:
        assert f"`{name}`" in doc
    for name in EXPECTED_SUPPORTED_INPUT | EXPECTED_DEFERRED_INPUT:
        assert f"`{name}`" in doc
    for name in EXPECTED_TEXT_WIDGETS | EXPECTED_CONTROL_WIDGETS | EXPECTED_CONTAINER_WIDGETS:
        assert f"`{name}`" in doc
    assert "`Hero`" in doc
    assert "`lineHeight`" in doc
