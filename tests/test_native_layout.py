import pytest

from otoe import (
    Button,
    HStack,
    NativeLayoutError,
    ScrollView,
    StyleRule,
    StyleSheet,
    Text,
    VStack,
    Widget,
    css,
    component,
    layout_native,
    mount,
    signal,
)
from otoe._native_shared import (
    NATIVE_STYLE_SUPPORT,
    NATIVE_WIDGET_SUPPORT,
    native_style_support,
    native_widget_support,
)
from otoe.style import SUPPORTED_PROPERTIES


def test_native_layout_computes_stack_boxes_deterministically():
    mounted = mount(
        VStack(
            Text("Hello"),
            Button("Run", onClick=lambda: None),
            gap=4,
            padding=8,
        )
    )

    layout = layout_native(mounted)

    assert layout.root.name == "VStack"
    assert layout.root.x == 0
    assert layout.root.y == 0
    assert layout.root.width == 56
    assert layout.root.height == 72

    text = layout.by_path((0,))
    button = layout.by_path((1,))

    assert (text.name, text.x, text.y, text.width, text.height) == (
        "Text",
        8,
        8,
        39,
        18,
    )
    assert (button.name, button.x, button.y, button.width, button.height) == (
        "Button",
        8,
        30,
        40,
        34,
    )
    assert button.events == ("onClick",)


def test_native_layout_computes_horizontal_stack_boxes():
    mounted = mount(HStack(Text("A"), Text("BBBB"), gap=3, padding=2))

    layout = layout_native(mounted)

    assert layout.root.width == 46
    assert layout.root.height == 22
    assert (layout.by_path((0,)).x, layout.by_path((0,)).y) == (2, 2)
    assert (layout.by_path((1,)).x, layout.by_path((1,)).y) == (13, 2)


def test_native_layout_resolves_stylesheet_dimensions():
    sheet = css(
        """
        .shell {
          padding: 12;
          gap: 6;
          width: 240;
        }
        .title {
          font-size: 20;
        }
        """
    )
    mounted = mount(VStack(Text("Hi", className="title"), className="shell"))

    layout = layout_native(mounted, stylesheet=sheet)

    assert layout.root.width == 240
    assert layout.root.height == 49
    assert layout.by_path((0,)).width == 22
    assert layout.by_path((0,)).height == 25


def test_native_layout_boxes_keep_component_context():
    @component
    def TaskList():
        return VStack(Text("One"))

    layout = layout_native(mount(TaskList()))

    assert layout.root.context == "TaskList > VStack"
    assert layout.by_path((0,)).context == "TaskList > Text"


def test_native_layout_rejects_percent_dimensions_for_now():
    sheet = css(".box { width: 50%; }")
    mounted = mount(VStack(Text("Nope"), className="box"))

    with pytest.raises(NativeLayoutError, match="px dimensions"):
        layout_native(mounted, stylesheet=sheet)


def test_native_layout_errors_include_component_context():
    sheet = css(".box { width: 50%; }")

    @component
    def PercentBox():
        return VStack(Text("Nope"), className="box")

    with pytest.raises(
        NativeLayoutError,
        match=r"PercentBox > VStack: Native layout only supports px dimensions",
    ):
        layout_native(mount(PercentBox()), stylesheet=sheet)


def test_native_style_support_matrix_covers_css_properties():
    assert set(NATIVE_STYLE_SUPPORT) == set(SUPPORTED_PROPERTIES.values()) | {"scrollY"}
    assert native_style_support("width") == "layout"
    assert native_style_support("background") == "paint"
    assert native_style_support("borderWidth") == "layout+paint"
    assert native_style_support("margin") == "ignored"
    assert native_style_support("lineHeight") is None


def test_native_widget_support_matrix_documents_layout_behavior():
    assert native_widget_support("Text") == "text"
    assert native_widget_support("Button") == "control"
    assert native_widget_support("Input") == "control"
    assert native_widget_support("VStack") == "container"
    assert native_widget_support("HStack") == "container"
    assert native_widget_support("ScrollView") == "container"
    assert native_widget_support("FocusScope") == "container"
    assert native_widget_support("ShortcutScope") == "container"
    assert native_widget_support("Show") == "container"
    assert native_widget_support("For") == "container"
    assert native_widget_support("Hero") == "fallback-container"

    assert set(NATIVE_WIDGET_SUPPORT) == {
        "Button",
        "FocusScope",
        "For",
        "HStack",
        "Input",
        "Panel",
        "ScrollView",
        "ShortcutScope",
        "Show",
        "Text",
        "VStack",
    }


def test_native_layout_unknown_widgets_use_documented_container_fallback():
    class Hero(Widget):
        props = {"className"}

    mounted = mount(Hero(Text("Launch"), className="hero"))

    layout = layout_native(mounted)

    assert layout.root.name == "Hero"
    assert layout.root.children[0].text == "Launch"


def test_native_layout_accepts_documented_ignored_styles_without_effect():
    sheet = css(
        """
        .box {
          display: flex;
          font-weight: 800;
          margin: 99;
          opacity: 0.5;
          padding: 4;
        }
        """
    )
    mounted = mount(VStack(Text("Hi"), className="box"))

    layout = layout_native(mounted, stylesheet=sheet)

    assert layout.root.width == 24
    assert layout.root.height == 26
    assert dict(layout.root.style)["margin"].value == 99


def test_native_layout_rejects_stylesheet_keys_outside_native_matrix():
    sheet = StyleSheet(
        rules={".box": StyleRule(".box", {"lineHeight": 20})},
        tokens={},
    )
    mounted = mount(VStack(Text("Nope"), className="box"))

    with pytest.raises(NativeLayoutError, match="Unsupported native style properties"):
        layout_native(mounted, stylesheet=sheet)


def test_native_layout_reflects_reactive_prop_updates():
    label = signal("Hi")
    mounted = mount(Text(label))

    before = layout_native(mounted)
    label.set("Hello")
    after = layout_native(mounted)

    assert before.root.width == 16
    assert after.root.width == 39


def test_native_layout_scrollview_bounds_do_not_reflow_children():
    sheet = css(".scroll { width: 120; height: 40; padding: 4; gap: 4; }")
    mounted = mount(
        ScrollView(
            Button("Visible", onClick=lambda: None),
            Button("Clipped", onClick=lambda: None),
            className="scroll",
        )
    )

    layout = layout_native(mounted, stylesheet=sheet)
    scroll = layout.root
    clipped = layout.by_path((1,))

    assert (scroll.name, scroll.width, scroll.height) == ("ScrollView", 120, 40)
    assert clipped.y >= scroll.y + scroll.height


def test_native_layout_scrollview_scroll_y_offsets_children():
    sheet = css(".scroll { width: 120; height: 40; padding: 4; gap: 4; }")
    mounted = mount(
        ScrollView(
            Button("First", onClick=lambda: None),
            Button("Second", onClick=lambda: None),
            scrollY=38,
            className="scroll",
        )
    )

    layout = layout_native(mounted, stylesheet=sheet)

    assert layout.by_path((0,)).y == -34
    assert layout.by_path((1,)).y == 4


def test_native_layout_scrollview_scroll_y_is_clamped_to_content():
    sheet = css(".scroll { width: 120; height: 40; padding: 4; gap: 4; }")
    mounted = mount(
        ScrollView(
            Button("First", onClick=lambda: None),
            Button("Second", onClick=lambda: None),
            scrollY=999,
            className="scroll",
        )
    )

    layout = layout_native(mounted, stylesheet=sheet)

    assert dict(layout.root.style)["scrollY"] == 40
    assert layout.by_path((0,)).y == -36
    assert layout.by_path((1,)).y == 2
