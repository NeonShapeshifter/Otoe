from otoe import (
    Button,
    HStack,
    ScrollView,
    Text,
    VStack,
    css,
    dispatch_native_click,
    hit_test_native,
    layout_native,
    mount,
    render_native_png,
    signal,
)


def test_native_hit_test_finds_deepest_clickable_box():
    mounted = mount(
        VStack(
            Text("Label"),
            Button("Run", onClick=lambda: None),
            padding=8,
            gap=4,
        )
    )
    layout = layout_native(mounted)

    hit = hit_test_native(layout, 12, 34)

    assert hit is not None
    assert hit.path == (1,)
    assert hit.name == "Button"


def test_native_hit_test_returns_none_outside_clickable_area():
    mounted = mount(HStack(Text("Only text"), padding=4))
    layout = layout_native(mounted)

    assert hit_test_native(layout, 2, 2) is None
    assert hit_test_native(layout, 200, 200) is None


def test_native_click_dispatch_runs_button_handler():
    clicks = []
    mounted = mount(
        VStack(
            Text("Label"),
            Button("Run", onClick=lambda: clicks.append("run")),
            padding=8,
            gap=4,
        )
    )
    layout = layout_native(mounted)

    result = dispatch_native_click(mounted, layout, 12, 34)

    assert result is None
    assert clicks == ["run"]


def test_native_click_dispatch_ignores_disabled_button():
    clicks = []
    mounted = mount(Button("Run", disabled=True, onClick=lambda: clicks.append("run")))
    layout = layout_native(mounted)

    result = dispatch_native_click(mounted, layout, 4, 4)

    assert result is None
    assert clicks == []


def test_native_click_dispatch_respects_scrollview_bounds():
    clicks = []
    sheet = css(".scroll { width: 120; height: 40; padding: 4; gap: 4; }")
    mounted = mount(
        ScrollView(
            Button("Visible", onClick=lambda: clicks.append("visible")),
            Button("Clipped", onClick=lambda: clicks.append("clipped")),
            className="scroll",
        )
    )
    layout = layout_native(mounted, stylesheet=sheet)

    visible = layout.by_path((0,))
    clipped = layout.by_path((1,))

    assert hit_test_native(layout, visible.x + 2, visible.y + 2) == visible
    assert hit_test_native(layout, clipped.x + 2, clipped.y + 2) is None

    dispatch_native_click(mounted, layout, visible.x + 2, visible.y + 2)
    dispatch_native_click(mounted, layout, clipped.x + 2, clipped.y + 2)

    assert clicks == ["visible"]


def test_native_click_dispatch_updates_state_and_next_png(tmp_path):
    label = signal("OFF")

    def toggle():
        label.set("ON")

    mounted = mount(
        VStack(
            Text(label),
            Button("Toggle", onClick=toggle),
            padding=8,
            gap=4,
        )
    )
    before = tmp_path / "before.png"
    after = tmp_path / "after.png"

    layout = layout_native(mounted)
    render_native_png(layout, before)
    dispatch_native_click(mounted, layout, 12, 34)
    next_layout = layout_native(mounted)
    render_native_png(next_layout, after)

    assert label.value == "ON"
    assert before.read_bytes() != after.read_bytes()
