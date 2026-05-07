from otoe import (
    Button,
    HStack,
    Input,
    NativeSurface,
    ScrollView,
    ShortcutScope,
    Show,
    Text,
    VStack,
    css,
    mount,
    signal,
)


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


def test_native_surface_auto_refreshes_external_signal_updates():
    label = signal("A")
    surface = NativeSurface(VStack(Text(label), padding=4))
    initial_frame = surface.frame

    label.set("AAAA")

    assert surface.box((0,)).text == "AAAA"
    assert surface.frame == initial_frame + 1

    current_frame = surface.frame
    assert surface.layout.by_path((0,)).text == "AAAA"
    assert surface.frame == current_frame


def test_native_surface_auto_refreshes_external_control_flow_updates():
    visible = signal(False)
    surface = NativeSurface(
        VStack(
            Show(
                Text("Visible"),
                when=visible,
                fallback=Text("Hidden"),
            ),
            padding=4,
        )
    )

    assert surface.box((0, 0)).text == "Hidden"
    initial_frame = surface.frame

    visible.set(True)

    assert surface.box((0, 0)).text == "Visible"
    assert surface.frame == initial_frame + 1


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


def test_native_surface_tracks_autofocus_input():
    surface = NativeSurface(
        VStack(
            Button("Run", onClick=lambda: None),
            Input(value="", autoFocus=True),
            padding=4,
            gap=4,
        )
    )

    assert surface.focused_path == (1,)
    assert surface.focused_box is not None
    assert surface.focused_box.name == "Input"
    assert any(
        command.stroke == "#38bdf8"
        for command in surface.paint.by_path((1,))
    )


def test_native_surface_click_moves_focus_and_runs_focus_events():
    events = []
    surface = NativeSurface(
        VStack(
            Input(
                value="",
                onFocus=lambda: events.append("input-focus"),
                onBlur=lambda: events.append("input-blur"),
            ),
            Button(
                "Run",
                onClick=lambda: events.append("button-click"),
                onFocus=lambda: events.append("button-focus"),
            ),
            padding=4,
            gap=4,
        )
    )

    input_box = surface.box((0,))
    button_box = surface.box((1,))
    surface.click(input_box.x + 2, input_box.y + 2)
    surface.click(button_box.x + 2, button_box.y + 2)

    assert surface.focused_path == (1,)
    assert any(
        command.stroke == "#38bdf8"
        for command in surface.paint.by_path((1,))
    )
    assert events == [
        "input-focus",
        "input-blur",
        "button-focus",
        "button-click",
    ]


def test_native_surface_tab_cycles_focusable_controls_and_skips_disabled():
    surface = NativeSurface(
        HStack(
            Button("One", onClick=lambda: None),
            Button("Disabled", disabled=True, onClick=lambda: None),
            Input(value=""),
            gap=4,
            padding=4,
        )
    )

    first = surface.key_down("Tab")
    second = surface.key_down("Tab")
    third = surface.key_down("Tab")
    reverse = surface.key_down("Tab", shift=True)

    assert first is not None and first.path == (0,)
    assert second is not None and second.path == (2,)
    assert third is not None and third.path == (0,)
    assert reverse is not None and reverse.path == (2,)


def test_native_surface_click_ignores_disabled_button_without_focus_change():
    clicks = []
    surface = NativeSurface(
        HStack(
            Input(value="", autoFocus=True),
            Button("Disabled", disabled=True, onClick=lambda: clicks.append("run")),
            gap=4,
            padding=4,
        )
    )
    button = surface.box((1,))

    surface.click(button.x + 2, button.y + 2)

    assert clicks == []
    assert surface.focused_path == (0,)


def test_native_surface_click_respects_scrollview_bounds_for_focus_and_click():
    clicks = []
    sheet = css(".scroll { width: 120; height: 40; padding: 4; gap: 4; }")
    surface = NativeSurface(
        ScrollView(
            Button("Visible", onClick=lambda: clicks.append("visible")),
            Button("Clipped", onClick=lambda: clicks.append("clipped")),
            className="scroll",
        ),
        stylesheet=sheet,
    )
    clipped = surface.box((1,))

    surface.click(clipped.x + 2, clipped.y + 2)

    assert clicks == []
    assert surface.focused_path is None


def test_native_surface_key_down_dispatches_to_focused_widget():
    keys = []
    surface = NativeSurface(Input(value="", autoFocus=True, onKeyDown=keys.append))

    surface.key_down("Escape")

    assert keys == ["Escape"]


def test_native_surface_enter_activates_focused_button():
    label = signal("OFF")
    surface = NativeSurface(Button("Toggle", onClick=lambda: label.set("ON")))

    surface.focus(())
    surface.key_down("Enter")

    assert label.value == "ON"


def test_native_surface_global_key_down_matches_live_preview_shape():
    payloads = []
    surface = NativeSurface(
        ShortcutScope(
            Input(value="", autoFocus=True),
            Button("Run", onClick=lambda: None),
            onKeyDown=payloads.append,
        )
    )

    surface.key_down("k")
    surface.key_down("k", ctrl=True)
    surface.focus((1,))
    surface.key_down("x")

    assert payloads == [
        {
            "key": "k",
            "ctrlKey": True,
            "metaKey": False,
            "altKey": False,
            "shiftKey": False,
        },
        {
            "key": "x",
            "ctrlKey": False,
            "metaKey": False,
            "altKey": False,
            "shiftKey": False,
        },
    ]


def test_native_surface_input_text_dispatches_change_and_refreshes():
    value = signal("")
    surface = NativeSurface(
        Input(value=value, autoFocus=True, onChange=lambda next_value: value.set(next_value))
    )

    surface.input_text("relay")

    assert value.value == "relay"
    assert surface.box(()).text == "relay"


def test_native_surface_input_value_reads_focused_or_explicit_input():
    first = signal("alpha")
    second = signal("beta")
    surface = NativeSurface(
        VStack(
            Input(
                value=first,
                autoFocus=True,
                onChange=lambda next_value: first.set(next_value),
            ),
            Input(value=second, onChange=lambda next_value: second.set(next_value)),
            padding=4,
            gap=4,
        )
    )

    assert surface.input_value() == "alpha"
    assert surface.input_value(path=(1,)) == "beta"


def test_native_surface_input_text_can_target_an_unfocused_input():
    value = signal("")
    surface = NativeSurface(
        VStack(
            Button("Run", onClick=lambda: None),
            Input(value=value, onChange=lambda next_value: value.set(next_value)),
            padding=4,
            gap=4,
        )
    )

    surface.input_text("search", path=(1,))

    assert surface.focused_path == (1,)
    assert value.value == "search"
    assert surface.box((1,)).text == "search"


def test_native_surface_input_text_rejects_non_input_focus():
    surface = NativeSurface(Button("Run", onClick=lambda: None))

    surface.focus(())

    try:
        surface.input_text("nope")
    except KeyError as exc:
        assert "No enabled native input" in str(exc)
    else:
        raise AssertionError("Expected input_text to reject non-input focus.")
