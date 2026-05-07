from otoe import (
    Button,
    Input,
    NativeSurface,
    NativeWindowDriver,
    NativeWindowEvent,
    ScrollView,
    ShortcutScope,
    Text,
    VStack,
    edit_native_input_value,
    css,
    run_native,
    signal,
)


def test_native_window_driver_click_dispatches_and_updates_frame():
    value = signal("OFF")
    driver = NativeWindowDriver.from_target(
        VStack(
            Text(value),
            Button("Toggle", onClick=lambda: value.set("ON")),
            padding=4,
            gap=4,
        )
    )
    initial_frame = driver.frame
    button = driver.surface.box((1,))

    driver.dispatch(NativeWindowEvent("click", x=button.x + 2, y=button.y + 2))

    assert value.value == "ON"
    assert driver.surface.box((0,)).text == "ON"
    assert driver.frame > initial_frame
    assert driver.size == (driver.paint.width, driver.paint.height)


def test_native_window_driver_wheel_dispatches_scroll():
    scroll_y = signal(0)
    driver = NativeWindowDriver.from_target(
        ScrollView(
            Button("First", onClick=lambda: None),
            Button("Second", onClick=lambda: None),
            scrollY=scroll_y,
            onScroll=lambda next_scroll_y: scroll_y.set(next_scroll_y),
            className="scroll",
        ),
        stylesheet=css(".scroll { width: 120; height: 40; padding: 4; gap: 4; }"),
    )

    driver.dispatch(NativeWindowEvent("wheel", x=8, y=8, delta_y=38))

    assert scroll_y.value == 38
    assert driver.surface.box((1,)).y == 4


def test_native_window_driver_key_down_activates_focused_button():
    value = signal("OFF")
    surface = NativeSurface(Button("Toggle", onClick=lambda: value.set("ON")))
    driver = NativeWindowDriver(surface)

    driver.surface.focus(())
    driver.key_down("Enter")

    assert value.value == "ON"


def test_native_window_driver_input_text_edits_focused_input():
    value = signal("")
    driver = NativeWindowDriver.from_target(
        Input(value=value, autoFocus=True, onChange=lambda next_value: value.set(next_value))
    )

    driver.dispatch(NativeWindowEvent("input_text", text="search"))

    assert value.value == "search"
    assert driver.surface.input_value() == "search"


def test_native_window_driver_key_input_edits_focused_input():
    value = signal("")
    driver = NativeWindowDriver.from_target(
        Input(value=value, autoFocus=True, onChange=lambda next_value: value.set(next_value))
    )

    driver.key_input("a", text="a")
    driver.dispatch(NativeWindowEvent("key_input", key="b", text="b"))
    driver.key_input("BackSpace")

    assert value.value == "a"
    assert driver.surface.input_value() == "a"


def test_native_window_driver_key_input_falls_back_to_key_down():
    keys = []
    driver = NativeWindowDriver.from_target(Input(value="", autoFocus=True, onKeyDown=keys.append))

    driver.key_input("Enter", text="\r")

    assert keys == ["Enter"]


def test_native_window_driver_key_input_keeps_shortcuts_out_of_text():
    payloads = []
    value = signal("query")
    driver = NativeWindowDriver.from_target(
        ShortcutScope(
            Input(value=value, autoFocus=True, onChange=lambda next_value: value.set(next_value)),
            onKeyDown=payloads.append,
        )
    )

    driver.key_input("k", text="k", ctrl=True)

    assert value.value == "query"
    assert payloads == [
        {
            "key": "k",
            "ctrlKey": True,
            "metaKey": False,
            "altKey": False,
            "shiftKey": False,
        }
    ]


def test_edit_native_input_value_handles_simple_text_keys():
    assert edit_native_input_value("ab", key="c", text="c") == "abc"
    assert edit_native_input_value("ab", key="BackSpace") == "a"
    assert edit_native_input_value("ab", key="Delete") == "ab"
    assert edit_native_input_value("ab", key="Enter", text="\r") is None
    assert edit_native_input_value("ab", key="k", text="k", ctrl=True) is None


def test_native_window_driver_rejects_invalid_events():
    driver = NativeWindowDriver.from_target(Button("Run", onClick=lambda: None))

    try:
        driver.dispatch(NativeWindowEvent("pinch"))
    except ValueError as exc:
        assert "Unknown native window event kind" in str(exc)
    else:
        raise AssertionError("Expected NativeWindowDriver to reject unknown events.")


def test_native_window_driver_rejects_incomplete_wheel_events():
    driver = NativeWindowDriver.from_target(Button("Run", onClick=lambda: None))

    try:
        driver.dispatch(NativeWindowEvent("wheel"))
    except ValueError as exc:
        assert "wheel events require x, y, and delta_y" in str(exc)
    else:
        raise AssertionError("Expected NativeWindowDriver to reject incomplete wheel events.")


def test_run_native_rejects_unknown_backend_without_opening_window():
    try:
        run_native(Button("Run", onClick=lambda: None), backend="skia")
    except ValueError as exc:
        assert "Unsupported native backend" in str(exc)
    else:
        raise AssertionError("Expected run_native to reject unknown backends.")
