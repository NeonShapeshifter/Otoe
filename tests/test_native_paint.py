import zlib

import pytest

from otoe import (
    Button,
    NativePaint,
    NativePaintError,
    PaintCommand,
    ScrollView,
    Text,
    VStack,
    css,
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
