import zlib
from dataclasses import replace

import pytest

from otoe import (
    Button,
    HStack,
    Input,
    NativePaint,
    NativePaintError,
    PaintCommand,
    ScrollView,
    Text,
    VStack,
    css,
    component,
    layout_native,
    mount,
    paint_native,
    render_native_png,
    signal,
    write_native_png,
)


def test_native_paint_generates_rect_and_text_commands():
    sheet = css(
        """
        .panel {
          padding: 8;
          gap: 4;
          background: surface;
          border-color: border;
          border-width: 1;
          border-radius: 6;
        }
        .title {
          color: ink;
          font-size: 16;
        }
        """,
        tokens={
            "border": "#d0d7de",
            "ink": "#111827",
            "surface": "#f8fafc",
        },
    )
    mounted = mount(
        VStack(
            Text("Hello", className="title"),
            Button("Run", onClick=lambda: None),
            className="panel",
        )
    )

    paint = paint_native(layout_native(mounted, stylesheet=sheet))

    surface = paint.commands[0]
    panel_rect = next(
        command
        for command in paint.commands
        if command.kind == "rect" and command.path == () and command.stroke == "#d0d7de"
    )
    button_rect = next(
        command
        for command in paint.commands
        if command.kind == "rect" and command.path == (1,)
    )
    text_commands = [command for command in paint.commands if command.kind == "text"]

    assert (paint.width, paint.height) == (60, 74)
    assert surface.fill == "#ffffff"
    assert panel_rect.fill == "#f8fafc"
    assert panel_rect.stroke_width == 1
    assert panel_rect.radius == 6
    assert button_rect.fill == "#2563eb"
    assert button_rect.stroke == "#1d4ed8"
    assert [(command.path, command.text) for command in text_commands] == [
        ((0,), "Hello"),
        ((1,), "Run"),
    ]
    assert text_commands[0].width == paint.by_path((0,))[0].width
    assert text_commands[1].width == button_rect.width - 16


def test_native_layout_marks_disabled_widget_state():
    mounted = mount(Button("Run", disabled=True, onClick=lambda: None))

    layout = layout_native(mounted)

    assert layout.root.state == ("disabled",)


def test_native_paint_uses_disabled_control_defaults():
    mounted = mount(
        HStack(
            Button("Run", disabled=True, onClick=lambda: None),
            Input(value="Locked", disabled=True),
            gap=4,
        )
    )

    paint = paint_native(layout_native(mounted))
    button_rect = next(
        command
        for command in paint.commands
        if command.kind == "rect" and command.path == (0,)
    )
    input_rect = next(
        command
        for command in paint.commands
        if command.kind == "rect" and command.path == (1,)
    )
    button_text = next(
        command
        for command in paint.commands
        if command.kind == "text" and command.path == (0,)
    )
    input_text = next(
        command
        for command in paint.commands
        if command.kind == "text" and command.path == (1,)
    )

    assert button_rect.fill == "#e5e7eb"
    assert button_rect.stroke == "#d1d5db"
    assert button_text.color == "#6b7280"
    assert input_rect.fill == "#f3f4f6"
    assert input_rect.stroke == "#d1d5db"
    assert input_text.color == "#9ca3af"


def test_native_paint_adds_focus_ring_for_focused_control():
    mounted = mount(HStack(Button("Run", onClick=lambda: None), Input(value=""), gap=4))
    layout = layout_native(mounted)

    paint = paint_native(layout, focused_path=(1,))

    focus_ring = next(
        command
        for command in paint.commands
        if command.path == (1,) and command.stroke == "#38bdf8"
    )
    assert focus_ring.fill is None
    assert focus_ring.stroke_width == 2
    assert focus_ring.x == layout.by_path((1,)).x - 2


def test_native_paint_skips_focus_ring_for_disabled_control():
    mounted = mount(Button("Run", disabled=True, onClick=lambda: None))

    paint = paint_native(layout_native(mounted), focused_path=())

    assert not [
        command
        for command in paint.commands
        if command.path == () and command.stroke == "#38bdf8"
    ]


def test_native_png_writer_creates_non_empty_png(tmp_path):
    mounted = mount(
        VStack(
            Text("Hello"),
            Button("Run", onClick=lambda: None),
            padding=8,
            gap=4,
        )
    )
    output = tmp_path / "native.png"

    paint = render_native_png(mounted, output)
    data = output.read_bytes()

    assert paint.commands
    assert data.startswith(b"\x89PNG\r\n\x1a\n")
    assert len(data) > 100


def test_native_png_writer_scales_raster_without_changing_logical_paint(tmp_path):
    mounted = mount(VStack(Text("Scale"), padding=4))
    output = tmp_path / "native-2x.png"

    paint = render_native_png(mounted, output, scale=2)

    assert paint.width > 0
    assert paint.height > 0
    assert _png_size(output.read_bytes()) == (paint.width * 2, paint.height * 2)


def test_native_png_writer_rejects_invalid_scale(tmp_path):
    paint = NativePaint(width=8, height=8, commands=())

    with pytest.raises(NativePaintError, match="scale must be a positive integer"):
        write_native_png(paint, tmp_path / "invalid-scale.png", scale=0)


def test_native_png_changes_when_reactive_text_changes(tmp_path):
    label = signal("A")
    mounted = mount(VStack(Text(label), padding=4))

    first = tmp_path / "first.png"
    second = tmp_path / "second.png"

    render_native_png(mounted, first)
    label.set("AAAAAA")
    render_native_png(mounted, second)

    assert first.read_bytes() != second.read_bytes()


def test_native_paint_rejects_unresolved_color_tokens():
    sheet = css(".panel { background: missing; }")
    mounted = mount(VStack(Text("Nope"), className="panel"))

    with pytest.raises(NativePaintError, match="Unresolved paint color token"):
        paint_native(layout_native(mounted, stylesheet=sheet))


def test_native_paint_accepts_css_color_keywords():
    sheet = css(".panel { background: white; } .label { color: red; }")
    mounted = mount(VStack(Text("Keyword", className="label"), className="panel"))

    paint = paint_native(layout_native(mounted, stylesheet=sheet))

    panel_rect = next(
        command
        for command in paint.commands
        if command.kind == "rect" and command.path == () and command.fill == "white"
    )
    label_text = next(
        command
        for command in paint.commands
        if command.kind == "text" and command.path == (0,)
    )
    assert panel_rect.fill == "white"
    assert label_text.color == "red"


def test_native_paint_errors_include_component_context():
    sheet = css(".panel { background: missing; }")

    @component
    def PaintPanel():
        return VStack(Text("Nope"), className="panel")

    with pytest.raises(
        NativePaintError,
        match=r"PaintPanel > VStack: Unresolved paint color token 'missing'",
    ):
        paint_native(layout_native(mount(PaintPanel()), stylesheet=sheet))


def test_native_paint_rejects_invalid_surface_background():
    layout = layout_native(mount(Text("Surface")))

    with pytest.raises(
        NativePaintError,
        match=r"NativePaint surface: Unsupported paint color 'not-a-color'",
    ):
        paint_native(layout, background="not-a-color")


def test_native_paint_clips_scrollview_descendant_commands():
    sheet = css(
        """
        .shell {
          gap: 4;
          padding: 4;
          width: 160;
        }
        .scroll {
          background: #f8fafc;
          gap: 4;
          height: 40;
          padding: 4;
          width: 120;
        }
        """
    )
    mounted = mount(
        VStack(
            ScrollView(
                Button("Visible", onClick=lambda: None),
                Button("Clipped", onClick=lambda: None),
                className="scroll",
            ),
            Text("Below"),
            className="shell",
        )
    )

    layout = layout_native(mounted, stylesheet=sheet)
    paint = paint_native(layout)
    scroll = layout.by_path((0,))
    clip = (scroll.x, scroll.y, scroll.width, scroll.height)

    visible_rect = next(
        command
        for command in paint.commands
        if command.path == (0, 0) and command.kind == "rect"
    )
    clipped_rect = next(
        command
        for command in paint.commands
        if command.path == (0, 1) and command.kind == "rect"
    )

    assert layout.by_path((0, 1)).y >= scroll.y + scroll.height
    assert visible_rect.clip == clip
    assert clipped_rect.clip == clip


def test_native_paint_applies_text_overflow_ellipsis_and_clip():
    sheet = css(
        """
        .label {
          width: 48;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }
        """
    )
    mounted = mount(Text("Long overflowing label", className="label"))

    layout = layout_native(mounted, stylesheet=sheet)
    paint = paint_native(layout)
    text = next(command for command in paint.by_path(()) if command.kind == "text")

    assert layout.root.text == "Long overflowing label"
    assert layout.root.width == 48
    assert text.text != "Long overflowing label"
    assert text.text.endswith("...")
    assert text.width == 48
    assert text.clip == (0, 0, 48, layout.root.height)


def test_native_paint_commands_follow_tree_painter_order():
    sheet = css(".row { background: #f8fafc; }")
    mounted = mount(
        VStack(
            Button("First", onClick=lambda: None),
            HStack(
                Button("Nested", onClick=lambda: None),
                Text("Label"),
                className="row",
                gap=4,
            ),
            Button("Last", onClick=lambda: None),
            gap=4,
        )
    )

    paint = paint_native(layout_native(mounted, stylesheet=sheet))

    first_command_indexes = {}
    for index, command in enumerate(paint.commands):
        first_command_indexes.setdefault(command.path, index)

    assert [
        path
        for path in first_command_indexes
        if path in {(), (0,), (1,), (1, 0), (1, 1), (2,)}
    ] == [(), (0,), (1,), (1, 0), (1, 1), (2,)]


def test_native_paint_commands_keep_component_context():
    sheet = css(".panel { background: #ffffff; }")

    @component
    def PaintPanel():
        return VStack(Text("Hello"), className="panel")

    paint = paint_native(layout_native(mount(PaintPanel()), stylesheet=sheet))

    assert paint.by_path(())[1].context == "PaintPanel > VStack"
    assert paint.by_path((0,))[0].context == "PaintPanel > Text"


def test_native_png_writer_respects_command_clips(tmp_path):
    output = tmp_path / "clip.png"
    paint = NativePaint(
        width=8,
        height=8,
        commands=(
            PaintCommand(
                kind="rect",
                path=(),
                x=0,
                y=0,
                width=8,
                height=8,
                fill="#ff0000",
                clip=(0, 0, 8, 4),
            ),
        ),
    )

    write_native_png(paint, output)
    pixels = _png_pixels(output.read_bytes(), width=8, height=8)

    assert pixels[1][1] == (255, 0, 0, 255)
    assert pixels[6][1] == (0, 0, 0, 0)


def test_native_png_writer_unknown_command_errors_include_path(tmp_path):
    paint = NativePaint(
        width=8,
        height=8,
        commands=(
            PaintCommand(
                kind="oval",
                path=(2,),
                x=0,
                y=0,
                width=8,
                height=8,
            ),
        ),
    )

    with pytest.raises(
        NativePaintError,
        match=r"Unknown paint command kind 'oval' at path \(2,\)",
    ):
        write_native_png(paint, tmp_path / "invalid.png")


def test_native_png_writer_color_errors_include_command_path(tmp_path):
    paint = NativePaint(
        width=8,
        height=8,
        commands=(
            PaintCommand(
                kind="rect",
                path=(3,),
                x=0,
                y=0,
                width=8,
                height=8,
                fill="not-a-color",
            ),
        ),
    )

    with pytest.raises(
        NativePaintError,
        match=r"Paint command 'rect' at path \(3,\) has invalid fill",
    ):
        write_native_png(paint, tmp_path / "bad-color.png")


def test_native_png_writer_color_errors_include_command_context(tmp_path):
    sheet = css(".panel { background: #ffffff; }")

    @component
    def BadPaintPanel():
        return VStack(Text("Bad"), className="panel")

    paint = paint_native(layout_native(mount(BadPaintPanel()), stylesheet=sheet))
    commands = tuple(
        replace(command, fill="not-a-color")
        if command.kind == "rect" and command.context == "BadPaintPanel > VStack"
        else command
        for command in paint.commands
    )

    with pytest.raises(
        NativePaintError,
        match=(
            r"Paint command 'rect' for BadPaintPanel > VStack at path \(\) "
            r"has invalid fill"
        ),
    ):
        write_native_png(
            NativePaint(width=paint.width, height=paint.height, commands=commands),
            tmp_path / "bad-context-color.png",
        )


def _png_pixels(
    data: bytes,
    *,
    width: int,
    height: int,
) -> list[list[tuple[int, int, int, int]]]:
    idat = []
    offset = 8
    while offset < len(data):
        length = int.from_bytes(data[offset : offset + 4], "big")
        kind = data[offset + 4 : offset + 8]
        payload = data[offset + 8 : offset + 8 + length]
        if kind == b"IDAT":
            idat.append(payload)
        offset += length + 12

    raw = zlib.decompress(b"".join(idat))
    rows = []
    stride = width * 4
    for y in range(height):
        start = y * (stride + 1)
        row = raw[start + 1 : start + 1 + stride]
        rows.append([tuple(row[index : index + 4]) for index in range(0, len(row), 4)])
    return rows


def _png_size(data: bytes) -> tuple[int, int]:
    assert data.startswith(b"\x89PNG\r\n\x1a\n")
    return (
        int.from_bytes(data[16:20], "big"),
        int.from_bytes(data[20:24], "big"),
    )
