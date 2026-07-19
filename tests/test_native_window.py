import builtins
from threading import Thread
from types import SimpleNamespace

import otoe.window as window_module
import pytest
from otoe import (
    Button,
    Input,
    NativeBackendAdapter,
    PaintCommand,
    NativeSurface,
    TkNativeBackendAdapter,
    TkNativeWindow,
    NativeWindowDriver,
    NativeWindowEvent,
    ScrollView,
    ShortcutScope,
    Text,
    VStack,
    component,
    edit_native_input_value,
    css,
    native_backend_adapter,
    native_backend_names,
    on_cleanup,
    run_native,
    signal,
)
from otoe._native_shared import NATIVE_INPUT_SUPPORT, native_input_support
from otoe.scheduler import PostedCallbackQueue, capture_post, drain_posted, post
from otoe.window import _TkPostedCallbackPump


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


def test_native_window_driver_key_input_dispatches_keydown_before_change():
    events = []
    value = signal("")

    def handle_key(key: str) -> None:
        events.append(("keydown", key, value.value))

    def handle_change(next_value: str) -> None:
        events.append(("change", next_value, value.value))
        value.set(next_value)

    driver = NativeWindowDriver.from_target(
        Input(
            value=value,
            autoFocus=True,
            onChange=handle_change,
            onKeyDown=handle_key,
        )
    )

    driver.key_input("a", text="a")

    assert events == [("keydown", "a", ""), ("change", "a", "")]
    assert value.value == "a"
    assert driver.surface.input_value() == "a"


def test_native_window_driver_key_input_falls_back_to_key_down():
    keys = []
    driver = NativeWindowDriver.from_target(Input(value="", autoFocus=True, onKeyDown=keys.append))

    driver.key_input("Enter", text="\r")
    driver.key_input("Escape")

    assert keys == ["Enter", "Escape"]


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


def test_native_window_driver_records_runtime_input_capabilities():
    payloads = []
    clicked = signal(False)
    value = signal("")
    driver = NativeWindowDriver.from_target(
        ShortcutScope(
            VStack(
                Input(
                    value=value,
                    autoFocus=True,
                    onChange=lambda next_value: value.set(next_value),
                    onKeyDown=payloads.append,
                ),
                Button("Run", onClick=lambda: clicked.set(True)),
            ),
            onKeyDown=payloads.append,
        )
    )
    start = driver.input_capability_event_count

    driver.dispatch(NativeWindowEvent("input_text", text="alpha"))
    driver.dispatch(NativeWindowEvent("key_input", key="k", text="k", ctrl=True))
    driver.dispatch(NativeWindowEvent("key_down", key="Tab"))
    button = driver.surface.box((0, 1))
    driver.click(button.x + 2, button.y + 2)

    assert clicked.value is True
    assert driver.input_capabilities_since(start) == (
        "click",
        "focus",
        "input_text",
        "key_down",
        "key_input",
        "shortcut",
        "tab_focus",
    )
    assert driver.input_capabilities == driver.input_capabilities_since(0)


def test_edit_native_input_value_handles_simple_text_keys():
    assert edit_native_input_value("ab", key="c", text="c") == "abc"
    assert edit_native_input_value("ab", key="BackSpace") == "a"
    assert edit_native_input_value("ab", key="Delete") == "ab"
    assert edit_native_input_value("ab", key="Enter", text="\r") is None
    assert edit_native_input_value("ab", key="k", text="k", ctrl=True) is None


def test_native_input_support_matrix_matches_driver_behavior():
    assert native_input_support("click") == "supported"
    assert native_input_support("wheel") == "supported"
    assert native_input_support("key_down") == "supported"
    assert native_input_support("key_input") == "supported"
    assert native_input_support("input_text") == "supported"
    assert native_input_support("shortcut") == "supported"
    assert native_input_support("focus") == "supported"
    assert native_input_support("tab_focus") == "supported"
    assert native_input_support("ime") == "deferred"
    assert native_input_support("drag") == "deferred"
    assert native_input_support("pinch") is None

    assert set(NATIVE_INPUT_SUPPORT) == {
        "caret_movement",
        "click",
        "drag",
        "focus",
        "gesture",
        "ime",
        "inertial_scroll",
        "input_text",
        "key_down",
        "key_input",
        "pointer_move",
        "shortcut",
        "tab_focus",
        "text_selection",
        "uncontrolled_input",
        "wheel",
    }


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


def test_native_backend_registry_exposes_tk_adapter():
    adapter = native_backend_adapter("tk")

    assert native_backend_names() == ("tk",)
    assert isinstance(adapter, NativeBackendAdapter)
    assert isinstance(adapter, TkNativeBackendAdapter)
    assert adapter.name == "tk"


def test_run_native_accepts_custom_backend_adapter_without_real_window():
    calls = []

    class RecordingBackend:
        name = "recording"

        def run(self, driver, *, title="Otoe"):
            calls.append((driver, title, driver.surface.box(()).text))

    result = run_native(
        Button("Run", onClick=lambda: None),
        title="Adapter Test",
        backend=RecordingBackend(),
    )

    assert result is None
    assert len(calls) == 1
    driver, title, text = calls[0]
    assert isinstance(driver, NativeWindowDriver)
    assert title == "Adapter Test"
    assert text == "Run"


def test_run_native_rejects_invalid_backend_adapter_before_mount():
    mounted = []

    @component
    def App():
        mounted.append(True)
        return Button("Run", onClick=lambda: None)

    try:
        run_native(App(), backend=object())
    except TypeError as exc:
        assert "NativeBackendAdapter" in str(exc)
    else:
        raise AssertionError("Expected run_native to reject invalid backend adapters.")

    assert mounted == []


def test_tk_native_window_canvas_draws_real_text_commands(monkeypatch):
    original_import = builtins.__import__

    class FakeRoot:
        def __init__(self):
            self.title_value = None
            self.geometry_value = None
            self.bindings = {}

        def title(self, value):
            self.title_value = value

        def bind(self, event, handler):
            self.bindings[event] = handler

        def geometry(self, value):
            self.geometry_value = value

        def mainloop(self):
            pass

        def destroy(self):
            pass

    class FakeCanvas:
        def __init__(self, root, **kwargs):
            self.root = root
            self.kwargs = kwargs
            self.bindings = {}
            self.operations = []
            self.focused = False

        def pack(self, **kwargs):
            self.operations.append(("pack", kwargs))

        def bind(self, event, handler):
            self.bindings[event] = handler

        def delete(self, tag):
            self.operations.append(("delete", tag))

        def create_rectangle(self, *args, **kwargs):
            self.operations.append(("rectangle", args, kwargs))

        def create_text(self, *args, **kwargs):
            self.operations.append(("text", args, kwargs))

        def focus_set(self):
            self.focused = True

    class FakeTkModule:
        Tk = FakeRoot
        Canvas = FakeCanvas

    def import_with_fake_tkinter(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "tkinter":
            return FakeTkModule
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", import_with_fake_tkinter)
    driver = NativeWindowDriver.from_target(
        VStack(Text("Hello"), Button("Run", onClick=lambda: None), padding=4)
    )

    window = TkNativeWindow(driver, title="Canvas Proof")

    text_operations = [operation for operation in window._canvas.operations if operation[0] == "text"]
    assert window.root.title_value == "Canvas Proof"
    assert window.root.geometry_value == f"{driver.paint.width}x{driver.paint.height}"
    assert any(operation[2]["text"] == "Hello" for operation in text_operations)
    assert any(operation[2]["text"] == "Run" for operation in text_operations)
    assert all(operation[2]["font"][0] == "TkDefaultFont" for operation in text_operations)
    assert all(operation[2]["width"] > 0 for operation in text_operations)


def test_tk_native_window_canvas_scales_paint_and_maps_pointer_events(monkeypatch):
    original_import = builtins.__import__

    class FakeRoot:
        def __init__(self):
            self.geometry_value = None
            self.bindings = {}

        def title(self, value):
            pass

        def bind(self, event, handler):
            self.bindings[event] = handler

        def geometry(self, value):
            self.geometry_value = value

        def mainloop(self):
            pass

        def destroy(self):
            pass

    class FakeCanvas:
        def __init__(self, root, **kwargs):
            self.root = root
            self.kwargs = kwargs
            self.bindings = {}
            self.operations = []
            self.focused = False

        def pack(self, **kwargs):
            self.operations.append(("pack", kwargs))

        def bind(self, event, handler):
            self.bindings[event] = handler

        def delete(self, tag):
            self.operations.append(("delete", tag))

        def create_rectangle(self, *args, **kwargs):
            self.operations.append(("rectangle", args, kwargs))

        def create_text(self, *args, **kwargs):
            self.operations.append(("text", args, kwargs))

        def focus_set(self):
            self.focused = True

    class FakeTkModule:
        Tk = FakeRoot
        Canvas = FakeCanvas

    def import_with_fake_tkinter(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "tkinter":
            return FakeTkModule
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", import_with_fake_tkinter)
    clicked = signal(False)
    driver = NativeWindowDriver.from_target(
        VStack(
            Text("Scale"),
            Button("Run", onClick=lambda: clicked.set(True)),
            padding=4,
        )
    )
    window = TkNativeWindow(driver)

    window._canvas.operations.clear()
    window._on_configure(SimpleNamespace(width=driver.paint.width * 2, height=driver.paint.height * 2))

    rect_operations = [operation for operation in window._canvas.operations if operation[0] == "rectangle"]
    text_operations = [operation for operation in window._canvas.operations if operation[0] == "text"]
    expected_rect_coords = []
    expected_stroke_widths = []
    for command in driver.paint.commands:
        if command.kind != "rect":
            continue
        coords = (
            command.x * 2,
            command.y * 2,
            (command.x + command.width) * 2,
            (command.y + command.height) * 2,
        )
        if command.fill:
            expected_rect_coords.append(coords)
        if command.stroke and command.stroke_width > 0:
            expected_rect_coords.append(coords)
            expected_stroke_widths.append(command.stroke_width * 2)
    expected_font_sizes = sorted(
        command.font_size * 2
        for command in driver.paint.commands
        if command.kind == "text"
    )
    expected_text_widths = sorted(
        command.width * 2
        for command in driver.paint.commands
        if command.kind == "text"
    )
    assert window._scale == 2
    assert [operation[1] for operation in rect_operations] == expected_rect_coords
    assert [
        operation[2]["width"]
        for operation in rect_operations
        if "width" in operation[2]
    ] == expected_stroke_widths
    assert sorted(operation[2]["font"][1] for operation in text_operations) == expected_font_sizes
    assert sorted(operation[2]["width"] for operation in text_operations) == expected_text_widths

    window._on_configure(SimpleNamespace(width=driver.paint.width * 5, height=driver.paint.height * 5))

    assert window._scale == 2

    button = driver.surface.box((1,))
    window._on_click(
        SimpleNamespace(
            x=window._offset_x + ((button.x + 2) * window._scale),
            y=window._offset_y + ((button.y + 2) * window._scale),
        )
    )

    assert clicked.value is True
    assert window._canvas.focused


def test_tk_posted_callback_poll_reschedules_after_failure():
    scheduled = []

    class FakeRoot:
        def after(self, delay, callback):
            scheduled.append((delay, callback))

    pump = _TkPostedCallbackPump(
        FakeRoot(),
        lambda: None,
        drain=lambda: (_ for _ in ()).throw(RuntimeError("posted callback failed")),
    )

    with pytest.raises(RuntimeError, match="posted callback failed"):
        pump.poll()

    assert scheduled == [(16, pump.poll)]


def test_tk_posted_callback_poll_renders_successful_work_after_peer_failure():
    scheduled = []
    state: list[str] = []
    renders: list[tuple[str, ...]] = []
    queue = PostedCallbackQueue()

    class FakeRoot:
        def after(self, delay, callback):
            scheduled.append((delay, callback))

    def fail_callback():
        raise RuntimeError("posted callback failed")

    queue.post(fail_callback)
    queue.post(lambda: state.append("updated"))
    pump = _TkPostedCallbackPump(
        FakeRoot(),
        lambda: renders.append(tuple(state)),
        drain=queue.drain,
    )

    with pytest.raises(RuntimeError, match="posted callback failed"):
        pump.poll()

    assert state == ["updated"]
    assert renders == [("updated",)]
    assert queue.drain() == 0
    assert scheduled == [(16, pump.poll)]


def test_tk_posted_callback_poll_preserves_drain_and_reschedule_failures():
    class FakeRoot:
        def after(self, delay, callback):
            raise SystemExit("reschedule failed")

    pump = _TkPostedCallbackPump(
        FakeRoot(),
        lambda: (_ for _ in ()).throw(ValueError("render failed")),
        drain=lambda: (_ for _ in ()).throw(KeyboardInterrupt("drain failed")),
    )

    with pytest.raises(BaseExceptionGroup) as caught:
        pump.poll()

    assert [str(error) for error in caught.value.exceptions] == [
        "drain failed",
        "render failed",
        "reschedule failed",
    ]
    assert pump._scheduled is False


@pytest.mark.parametrize("failure_stage", ["canvas", "render"])
def test_tk_native_window_destroys_root_when_startup_fails(
    monkeypatch,
    failure_stage,
):
    cleanups = []

    @component
    def App():
        on_cleanup(lambda: cleanups.append("driver"))
        return Button("Run", onClick=lambda: None)

    class FakeRoot:
        def __init__(self):
            self.destroy_calls = 0

        def title(self, value):
            pass

        def bind(self, event, handler):
            pass

        def geometry(self, value):
            pass

        def destroy(self):
            self.destroy_calls += 1

    class FakeCanvas:
        def __init__(self, root, **kwargs):
            if failure_stage == "canvas":
                raise RuntimeError("canvas failed")

        def pack(self, **kwargs):
            pass

        def bind(self, event, handler):
            pass

        def delete(self, tag):
            pass

        def create_rectangle(self, *args, **kwargs):
            pass

        def create_text(self, *args, **kwargs):
            pass

    root = FakeRoot()
    fake_tk = SimpleNamespace(Tk=lambda: root, Canvas=FakeCanvas)
    driver = NativeWindowDriver.from_target(App())
    if failure_stage == "render":
        monkeypatch.setattr(
            window_module,
            "_draw_tk_canvas_command",
            lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("render failed")),
        )

    with pytest.raises(RuntimeError, match=f"{failure_stage} failed"):
        TkNativeWindow(driver, _tk_module=fake_tk)

    assert root.destroy_calls == 1
    assert cleanups == []

    driver.dispose()
    assert cleanups == ["driver"]


def test_tk_startup_preserves_primary_queue_and_root_cleanup_failures():
    posters = []

    class FakeRoot:
        def title(self, value):
            pass

        def bind(self, event, handler):
            pass

        def geometry(self, value):
            pass

        def destroy(self):
            raise SystemExit("root cleanup failed")

    class FakeCanvas:
        def __init__(self, root, **kwargs):
            pass

        def pack(self, **kwargs):
            pass

        def bind(self, event, handler):
            pass

        def delete(self, tag):
            poster = capture_post()
            posters.append(poster)
            poster(lambda: (_ for _ in ()).throw(KeyboardInterrupt("queue cleanup failed")))
            raise RuntimeError("render failed")

    root = FakeRoot()
    fake_tk = SimpleNamespace(Tk=lambda: root, Canvas=FakeCanvas)
    driver = NativeWindowDriver.from_target(Button("Run", onClick=lambda: None))

    with pytest.raises(BaseExceptionGroup) as caught:
        TkNativeWindow(driver, _tk_module=fake_tk)

    assert [str(error) for error in caught.value.exceptions] == [
        "render failed",
        "queue cleanup failed",
        "root cleanup failed",
    ]
    with pytest.raises(RuntimeError, match="not accepting work"):
        posters[0](lambda: None)
    driver.dispose()


def test_tk_active_close_drains_accepted_work_before_destroying_root():
    events: list[str] = []
    window_holder = {}

    class FakeRoot:
        def __init__(self):
            self.destroy_calls = 0
            self.scheduled = []

        def title(self, value):
            pass

        def bind(self, event, handler):
            pass

        def geometry(self, value):
            pass

        def protocol(self, name, callback):
            pass

        def after(self, delay, callback):
            self.scheduled.append((delay, callback))

        def mainloop(self):
            window = window_holder["window"]
            window.post(lambda: events.append("accepted callback"))
            window.close()
            assert self.destroy_calls == 0
            events.append("mainloop returned")

        def quit(self):
            events.append("quit")

        def destroy(self):
            self.destroy_calls += 1
            events.append("destroy")

    class FakeCanvas:
        def __init__(self, root, **kwargs):
            pass

        def pack(self, **kwargs):
            pass

        def bind(self, event, handler):
            pass

        def delete(self, tag):
            pass

        def create_rectangle(self, *args, **kwargs):
            pass

        def create_text(self, *args, **kwargs):
            pass

    root = FakeRoot()
    fake_tk = SimpleNamespace(Tk=lambda: root, Canvas=FakeCanvas)
    driver = NativeWindowDriver.from_target(Text("Ready"))
    window = TkNativeWindow(driver, _tk_module=fake_tk)
    window_holder["window"] = window

    window.run()

    assert events == [
        "quit",
        "mainloop returned",
        "accepted callback",
        "destroy",
    ]
    assert root.destroy_calls == 1
    assert window._posted_callbacks.closed is True
    driver.dispose()


def test_tk_root_cleanup_posts_cannot_escape_the_closed_window_queue():
    assert drain_posted() == 0
    escaped: list[str] = []

    class FakeRoot:
        def title(self, value):
            pass

        def bind(self, event, handler):
            pass

        def geometry(self, value):
            pass

        def destroy(self):
            post(lambda: escaped.append("escaped"))

    class FakeCanvas:
        def __init__(self, root, **kwargs):
            pass

        def pack(self, **kwargs):
            pass

        def bind(self, event, handler):
            pass

        def delete(self, tag):
            pass

        def create_rectangle(self, *args, **kwargs):
            pass

        def create_text(self, *args, **kwargs):
            pass

    fake_tk = SimpleNamespace(Tk=FakeRoot, Canvas=FakeCanvas)
    driver = NativeWindowDriver.from_target(Text("Ready"))
    window = TkNativeWindow(driver, _tk_module=fake_tk)

    with pytest.raises(RuntimeError, match="not accepting work"):
        window.close()

    assert escaped == []
    assert drain_posted() == 0
    assert window._posted_callbacks.closed is True
    driver.dispose()


def test_tk_close_from_foreign_thread_rejects_before_touching_root_or_queue():
    class FakeRoot:
        def __init__(self):
            self.destroy_calls = 0

        def title(self, value):
            pass

        def bind(self, event, handler):
            pass

        def geometry(self, value):
            pass

        def destroy(self):
            self.destroy_calls += 1

    class FakeCanvas:
        def __init__(self, root, **kwargs):
            pass

        def pack(self, **kwargs):
            pass

        def bind(self, event, handler):
            pass

        def delete(self, tag):
            pass

        def create_rectangle(self, *args, **kwargs):
            pass

        def create_text(self, *args, **kwargs):
            pass

    root = FakeRoot()
    fake_tk = SimpleNamespace(Tk=lambda: root, Canvas=FakeCanvas)
    driver = NativeWindowDriver.from_target(Text("Ready"))
    window = TkNativeWindow(driver, _tk_module=fake_tk)
    errors: list[BaseException] = []

    def close_from_foreign_thread():
        try:
            window.close()
        except BaseException as exc:
            errors.append(exc)

    thread = Thread(target=close_from_foreign_thread)
    thread.start()
    thread.join()

    assert len(errors) == 1
    assert isinstance(errors[0], RuntimeError)
    assert str(errors[0]) == "Tk window must be closed by its owning thread."
    assert root.destroy_calls == 0
    assert window._posted_callbacks.closed is False

    window.close()
    assert root.destroy_calls == 1
    driver.dispose()


def test_tk_close_seals_queue_and_retries_only_failed_root_cleanup():
    class FakeRoot:
        def __init__(self):
            self.destroy_calls = 0

        def title(self, value):
            pass

        def bind(self, event, handler):
            pass

        def geometry(self, value):
            pass

        def destroy(self):
            self.destroy_calls += 1
            if self.destroy_calls == 1:
                raise SystemExit("root cleanup failed")

    class FakeCanvas:
        def __init__(self, root, **kwargs):
            pass

        def pack(self, **kwargs):
            pass

        def bind(self, event, handler):
            pass

        def delete(self, tag):
            pass

        def create_rectangle(self, *args, **kwargs):
            pass

        def create_text(self, *args, **kwargs):
            pass

    root = FakeRoot()
    fake_tk = SimpleNamespace(Tk=lambda: root, Canvas=FakeCanvas)
    driver = NativeWindowDriver.from_target(Button("Run", onClick=lambda: None))
    window = TkNativeWindow(driver, _tk_module=fake_tk)

    window.post(
        lambda: (_ for _ in ()).throw(KeyboardInterrupt("queue cleanup failed"))
    )
    with pytest.raises(BaseExceptionGroup) as caught:
        window.close()

    assert [str(error) for error in caught.value.exceptions] == [
        "queue cleanup failed",
        "root cleanup failed",
    ]
    assert window._posted_callbacks.closed is True
    with pytest.raises(RuntimeError, match="not accepting work"):
        window.post(lambda: None)

    window.close()
    window.close()
    assert root.destroy_calls == 2
    driver.dispose()


def test_tk_native_window_mainloop_and_cleanup_failure_can_retry_root_cleanup():
    cleanups = []

    @component
    def App():
        on_cleanup(lambda: cleanups.append("driver"))
        return Button("Run", onClick=lambda: None)

    class FakeRoot:
        def __init__(self):
            self.scheduled = []
            self.destroy_calls = 0

        def title(self, value):
            pass

        def bind(self, event, handler):
            pass

        def geometry(self, value):
            pass

        def after(self, delay, callback):
            self.scheduled.append((delay, callback))

        def mainloop(self):
            raise RuntimeError("mainloop failed")

        def destroy(self):
            self.destroy_calls += 1
            if self.destroy_calls == 1:
                raise OSError("destroy failed")

    class FakeCanvas:
        def __init__(self, root, **kwargs):
            pass

        def pack(self, **kwargs):
            pass

        def bind(self, event, handler):
            pass

        def delete(self, tag):
            pass

        def create_rectangle(self, *args, **kwargs):
            pass

        def create_text(self, *args, **kwargs):
            pass

    root = FakeRoot()
    fake_tk = SimpleNamespace(Tk=lambda: root, Canvas=FakeCanvas)
    driver = NativeWindowDriver.from_target(App())
    window = TkNativeWindow(driver, _tk_module=fake_tk)

    with pytest.raises(BaseExceptionGroup) as caught:
        window.run()

    assert root.destroy_calls == 1
    assert [str(error) for error in caught.value.exceptions] == [
        "mainloop failed",
        "destroy failed",
    ]
    assert window._posted_callback_pump.closed is True
    assert cleanups == []

    window.close()
    assert root.destroy_calls == 2
    _, deferred_poll = root.scheduled.pop()
    deferred_poll()
    assert root.scheduled == []

    driver.dispose()
    assert cleanups == ["driver"]


def test_tk_native_window_injected_run_and_close_are_idempotent():
    class FakeRoot:
        def __init__(self):
            self.scheduled = []
            self.destroy_calls = 0
            self.mainloop_calls = 0

        def title(self, value):
            pass

        def bind(self, event, handler):
            pass

        def geometry(self, value):
            pass

        def after(self, delay, callback):
            self.scheduled.append((delay, callback))

        def mainloop(self):
            self.mainloop_calls += 1
            _, callback = self.scheduled.pop(0)
            callback()

        def destroy(self):
            self.destroy_calls += 1

    class FakeCanvas:
        def __init__(self, root, **kwargs):
            pass

        def pack(self, **kwargs):
            pass

        def bind(self, event, handler):
            pass

        def delete(self, tag):
            pass

        def create_rectangle(self, *args, **kwargs):
            pass

        def create_text(self, *args, **kwargs):
            pass

    class FakeTk:
        def __init__(self):
            self.root = FakeRoot()

        def Tk(self):
            return self.root

        Canvas = FakeCanvas

    fake_tk = FakeTk()
    driver = NativeWindowDriver.from_target(Button("Run", onClick=lambda: None))
    window = TkNativeWindow(
        driver,
        _tk_module=fake_tk,
        _drain_posted=lambda: 0,
    )

    window.run()
    window.close()
    window.close()

    assert fake_tk.root.mainloop_calls == 1
    assert fake_tk.root.destroy_calls == 1
    assert len(fake_tk.root.scheduled) == 1
    _, deferred_poll = fake_tk.root.scheduled.pop(0)
    deferred_poll()
    assert fake_tk.root.scheduled == []
    driver.dispose()


def test_run_native_disposes_only_the_driver_it_creates():
    cleanups = []

    @component
    def App():
        on_cleanup(lambda: cleanups.append("cleanup"))
        return Button("Run", onClick=lambda: None)

    class RecordingBackend:
        name = "recording"

        def run(self, driver, *, title="Otoe"):
            assert driver.paint.width > 0

    run_native(App(), backend=RecordingBackend())
    assert cleanups == ["cleanup"]

    borrowed = NativeWindowDriver.from_target(App())
    run_native(borrowed, backend=RecordingBackend())
    assert cleanups == ["cleanup"]

    borrowed.dispose()
    borrowed.dispose()
    assert cleanups == ["cleanup", "cleanup"]


def test_run_native_backend_failure_disposes_only_the_driver_it_creates():
    cleanups = []

    @component
    def App():
        on_cleanup(lambda: cleanups.append("cleanup"))
        return Button("Run", onClick=lambda: None)

    class FailingBackend:
        name = "failing"

        def run(self, driver, *, title="Otoe"):
            assert driver.paint.width > 0
            raise RuntimeError("backend failed")

    with pytest.raises(RuntimeError, match="backend failed"):
        run_native(App(), backend=FailingBackend())
    assert cleanups == ["cleanup"]

    borrowed = NativeWindowDriver.from_target(App())
    with pytest.raises(RuntimeError, match="backend failed"):
        run_native(borrowed, backend=FailingBackend())
    assert cleanups == ["cleanup"]

    borrowed_surface = NativeSurface(App())
    with pytest.raises(RuntimeError, match="backend failed"):
        run_native(borrowed_surface, backend=FailingBackend())
    assert cleanups == ["cleanup"]

    borrowed.dispose()
    borrowed_surface.dispose()
    assert cleanups == ["cleanup", "cleanup", "cleanup"]


def test_run_native_preserves_backend_and_owned_driver_cleanup_failures():
    @component
    def App():
        def fail_cleanup():
            raise OSError("driver cleanup failed")

        on_cleanup(fail_cleanup)
        return Button("Run", onClick=lambda: None)

    class FailingBackend:
        name = "failing"

        def run(self, driver, *, title="Otoe"):
            raise RuntimeError("backend failed")

    with pytest.raises(BaseExceptionGroup) as caught:
        run_native(App(), backend=FailingBackend())

    assert str(caught.value.exceptions[0]) == "backend failed"
    assert "driver cleanup failed" in repr(caught.value.exceptions[1])


def test_tk_canvas_text_clipping_is_intersection_only_not_pixel_masked():
    class FakeCanvas:
        def __init__(self):
            self.operations = []

        def create_text(self, *args, **kwargs):
            self.operations.append(("text", args, kwargs))

    canvas = FakeCanvas()
    hidden = PaintCommand(
        kind="text",
        path=(),
        x=40,
        y=40,
        width=20,
        height=12,
        text="Hidden",
        clip=(0, 0, 10, 10),
    )
    partially_clipped = PaintCommand(
        kind="text",
        path=(),
        x=8,
        y=8,
        width=24,
        height=12,
        text="Visible edge",
        font_size=10,
        clip=(10, 10, 8, 8),
    )

    window_module._draw_tk_canvas_command(canvas, hidden, scale=2, offset_x=0, offset_y=0)
    assert canvas.operations == []

    window_module._draw_tk_canvas_command(
        canvas,
        partially_clipped,
        scale=2,
        offset_x=0,
        offset_y=0,
    )

    assert canvas.operations == [
        (
            "text",
            (16, 16),
            {
                "anchor": "nw",
                "text": "Visible edge",
                "fill": "#111827",
                "font": ("TkDefaultFont", 20),
                "width": 48,
            },
        )
    ]


def test_tk_native_window_missing_tkinter_error_is_actionable(monkeypatch):
    original_import = builtins.__import__

    def import_without_tkinter(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "tkinter":
            raise ImportError("No module named 'tkinter'")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", import_without_tkinter)
    driver = NativeWindowDriver.from_target(Button("Run", onClick=lambda: None))

    try:
        TkNativeWindow(driver)
    except RuntimeError as exc:
        message = str(exc)
        assert "TkNativeWindow requires tkinter" in message
        assert "sudo apt install python3-tk" in message
        assert "PYTHONPATH=src:. python -m examples.native.window_demo" in message
    else:
        raise AssertionError("Expected TkNativeWindow to explain missing tkinter.")
