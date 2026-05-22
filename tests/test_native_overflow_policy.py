from otoe import (
    Button,
    ScrollView,
    Text,
    VStack,
    css,
    dispatch_native_click,
    hit_test_native,
    layout_native,
    mount,
    paint_native,
)


def test_native_normal_containers_do_not_clip_overflow_paint():
    sheet = css(
        """
        .shell {
          width: 120;
          height: 40;
          padding: 4;
          gap: 4;
          background: #f8fafc;
        }
        """
    )
    mounted = mount(
        VStack(
            Button("Visible", onClick=lambda: None),
            Button("Overflow", onClick=lambda: None),
            className="shell",
        )
    )

    layout = layout_native(mounted, stylesheet=sheet)
    paint = paint_native(layout)
    overflow = layout.by_path((1,))
    overflow_commands = paint.by_path((1,))

    assert overflow.y >= layout.root.y + layout.root.height
    assert overflow_commands
    assert all(command.clip is None for command in overflow_commands)


def test_native_normal_container_overflow_remains_hit_testable():
    clicks = []
    sheet = css(".shell { width: 120; height: 40; padding: 4; gap: 4; }")
    mounted = mount(
        VStack(
            Button("Visible", onClick=lambda: clicks.append("visible")),
            Button("Overflow", onClick=lambda: clicks.append("overflow")),
            className="shell",
        )
    )
    layout = layout_native(mounted, stylesheet=sheet)
    overflow = layout.by_path((1,))

    hit = hit_test_native(layout, overflow.x + 2, overflow.y + 2)
    dispatch_native_click(mounted, layout, overflow.x + 2, overflow.y + 2)

    assert hit is not None
    assert hit.path == (1,)
    assert clicks == ["overflow"]


def test_native_scrollview_clips_overflow_paint_and_hit_testing():
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
    paint = paint_native(layout)
    scroll = layout.root
    clipped = layout.by_path((1,))
    clip = (scroll.x, scroll.y, scroll.width, scroll.height)

    assert clipped.y >= scroll.y + scroll.height
    assert paint.by_path((1,))
    assert all(command.clip == clip for command in paint.by_path((1,)))
    assert hit_test_native(layout, clipped.x + 2, clipped.y + 2) is None

    dispatch_native_click(mounted, layout, clipped.x + 2, clipped.y + 2)

    assert clicks == []


def test_native_scrollview_clip_applies_through_nested_normal_container():
    clicks = []
    sheet = css(".scroll { width: 150; height: 40; padding: 4; } .inner { gap: 4; }")
    mounted = mount(
        ScrollView(
            VStack(
                Button("Visible", onClick=lambda: clicks.append("visible")),
                Button("Nested clipped", onClick=lambda: clicks.append("clipped")),
                className="inner",
            ),
            className="scroll",
        )
    )
    layout = layout_native(mounted, stylesheet=sheet)
    paint = paint_native(layout)
    scroll = layout.root
    clipped = layout.by_path((0, 1))
    clip = (scroll.x, scroll.y, scroll.width, scroll.height)

    assert clipped.y >= scroll.y + scroll.height
    assert paint.by_path((0, 1))
    assert all(command.clip == clip for command in paint.by_path((0, 1)))
    assert hit_test_native(layout, clipped.x + 2, clipped.y + 2) is None

    dispatch_native_click(mounted, layout, clipped.x + 2, clipped.y + 2)

    assert clicks == []


def test_native_text_overflow_from_normal_container_is_visible_metadata():
    sheet = css(".shell { width: 32; height: 18; padding: 0; }")
    mounted = mount(VStack(Text("Long overflowing text"), className="shell"))

    layout = layout_native(mounted, stylesheet=sheet)
    paint = paint_native(layout)
    text_command = next(command for command in paint.by_path((0,)) if command.kind == "text")

    assert layout.root.width == 32
    assert layout.by_path((0,)).width > layout.root.width
    assert text_command.clip is None
