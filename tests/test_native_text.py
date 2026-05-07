from otoe import Text, css, layout_native, mount, paint_native
from otoe._native_text import measure_native_text


def test_native_marker_text_metrics_are_deterministic():
    assert measure_native_text("Hello", font_size=14).width == 39
    assert measure_native_text("Hello", font_size=14).height == 18
    assert measure_native_text("", font_size=14).width == 1
    assert measure_native_text("", font_size=14).height == 18


def test_native_layout_and_paint_share_marker_text_metrics():
    sheet = css(".title { font-size: 20; }")
    mounted = mount(Text("Otoe", className="title"))

    layout = layout_native(mounted, stylesheet=sheet)
    paint = paint_native(layout)
    text_command = next(command for command in paint.commands if command.kind == "text")

    assert (layout.root.width, layout.root.height) == (44, 25)
    assert (text_command.width, text_command.height) == (44, 25)
