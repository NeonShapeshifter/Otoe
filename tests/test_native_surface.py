from otoe import Button, NativeSurface, Text, VStack, css, mount, signal


def test_native_surface_mounts_and_renders_png(tmp_path):
    surface = NativeSurface(
        VStack(
            Text("Hello"),
            Button("Run", onClick=lambda: None),
            padding=8,
            gap=4,
        )
    )
    output = tmp_path / "surface.png"

    paint = surface.render_png(output)

    assert surface.frame == 2
    assert surface.mounted is not None
    assert surface.layout.root.name == "VStack"
    assert surface.box((1,)).name == "Button"
    assert paint.width == surface.paint.width
    assert output.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")


def test_native_surface_click_dispatches_and_refreshes_after_state_change(tmp_path):
    label = signal("OFF")

    def toggle() -> None:
        label.set("ON")

    surface = NativeSurface(
        VStack(
            Text(label),
            Button("Toggle", onClick=toggle),
            padding=8,
            gap=4,
        )
    )
    before = tmp_path / "before.png"
    after = tmp_path / "after.png"

    surface.render_png(before)
    button = surface.box((1,))
    surface.click(button.x + 4, button.y + 4)
    surface.render_png(after)

    assert label.value == "ON"
    assert surface.box((0,)).text == "ON"
    assert before.read_bytes() != after.read_bytes()


def test_native_surface_refresh_captures_external_signal_updates():
    label = signal("A")
    surface = NativeSurface(VStack(Text(label), padding=4))
    initial_frame = surface.frame

    label.set("AAAA")
    surface.refresh()

    assert surface.frame == initial_frame + 1
    assert surface.box((0,)).text == "AAAA"


def test_native_surface_accepts_existing_mounted_node():
    mounted = mount(VStack(Text("Mounted"), padding=4))
    surface = NativeSurface(mounted)

    assert surface.mounted is mounted
    assert surface.layout.root.width == 62


def test_native_surface_uses_stylesheet_and_background():
    sheet = css(
        """
        .shell {
          width: 120;
          background: surface;
        }
        """,
        tokens={"surface": "#f8fafc"},
    )
    surface = NativeSurface(VStack(Text("Styled"), className="shell"), stylesheet=sheet)

    assert surface.layout.root.width == 120
    assert surface.paint.commands[0].fill == "#ffffff"
    assert surface.paint.by_path(())[0].fill == "#ffffff"
    assert surface.paint.by_path(())[1].fill == "#f8fafc"
