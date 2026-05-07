import pytest

from otoe import (
    Button,
    HStack,
    NativeLayoutError,
    ScrollView,
    Text,
    VStack,
    css,
    layout_native,
    mount,
    signal,
)


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


def test_native_layout_rejects_percent_dimensions_for_now():
    sheet = css(".box { width: 50%; }")
    mounted = mount(VStack(Text("Nope"), className="box"))

    with pytest.raises(NativeLayoutError, match="px dimensions"):
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
