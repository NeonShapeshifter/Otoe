from otoe import (
    Button,
    HStack,
    Text,
    VStack,
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
