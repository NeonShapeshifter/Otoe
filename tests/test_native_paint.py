import pytest

from otoe import (
    Button,
    NativePaintError,
    Text,
    VStack,
    css,
    layout_native,
    mount,
    paint_native,
    render_native_png,
    signal,
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
