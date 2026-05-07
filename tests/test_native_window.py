from otoe import (
    Button,
    Input,
    NativeSurface,
    NativeWindowDriver,
    NativeWindowEvent,
    Text,
    VStack,
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


def test_native_window_driver_rejects_invalid_events():
    driver = NativeWindowDriver.from_target(Button("Run", onClick=lambda: None))

    try:
        driver.dispatch(NativeWindowEvent("wheel"))
    except ValueError as exc:
        assert "Unknown native window event kind" in str(exc)
    else:
        raise AssertionError("Expected NativeWindowDriver to reject unknown events.")
