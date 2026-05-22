import inspect

import examples.native.task_board_demo as task_board_demo
import otoe.window as window_module
from examples.native.window_demo import NativeWindowDemo
from otoe import NativeSurface, NativeWindowDriver


def test_phase3_window_demo_drives_app_flow_through_driver():
    demo = NativeWindowDemo()
    driver = demo.driver

    assert isinstance(driver, NativeWindowDriver)
    assert isinstance(driver.surface, NativeSurface)
    assert driver.surface is demo.board.surface
    assert driver.surface.focused_box is not None
    assert driver.surface.focused_box.name == "Input"

    initial_frame = driver.frame
    demo.type_search("input")

    assert demo.board.query.value == "input"
    assert demo.visible_titles() == ["Input polish"]
    assert driver.frame > initial_frame

    filtered_frame = driver.frame
    demo.open_first_visible_task()

    assert demo.board.selected_task.value is not None
    assert demo.board.selected_task.value["id"] == "input"
    assert _has_text(driver, "Inspect Input polish")
    assert driver.frame > filtered_frame

    modal_frame = driver.frame
    driver.key_down("Escape")

    assert demo.board.selected_task.value is None
    assert demo.board.shortcut_count.value == 1
    assert driver.frame > modal_frame

    demo.clear_with_shortcut()

    assert demo.board.query.value == ""
    assert demo.visible_titles() == ["Runtime bridge", "Input polish", "Docs pass"]
    assert demo.board.shortcut_count.value == 2

    shortcut_frame = driver.frame
    demo.scroll_list(48)

    scroll_box = demo._first_box("ScrollView")
    assert demo.board.list_scroll_y.value > 0
    assert dict(scroll_box.style)["scrollY"] == demo.board.list_scroll_y.value
    assert driver.frame > shortcut_frame

    scrolled_frame = driver.frame
    demo.clear_with_shortcut()

    assert demo.board.list_scroll_y.value == 0
    assert demo.board.shortcut_count.value == 3
    assert driver.frame > scrolled_frame


def test_phase3_window_demo_writes_distinct_sequence_frames(tmp_path):
    demo = NativeWindowDemo()
    initial = tmp_path / "initial.png"
    scrolled = tmp_path / "scrolled.png"
    filtered = tmp_path / "filtered.png"
    modal = tmp_path / "modal.png"

    demo.render(initial)
    demo.scroll_list(48)
    demo.render(scrolled)
    demo.type_search("input")
    demo.render(filtered)
    demo.open_first_visible_task()
    demo.render(modal)

    assert initial.read_bytes() != scrolled.read_bytes()
    assert scrolled.read_bytes() != filtered.read_bytes()
    assert filtered.read_bytes() != modal.read_bytes()


def test_phase3_demo_app_code_uses_surface_boundary_not_manual_pipeline():
    source = inspect.getsource(task_board_demo)

    assert "NativeSurface(" in source
    for forbidden in (
        "dispatch_native_click",
        "hit_test_native",
        "layout_native",
        "paint_native",
        "write_native_png",
    ):
        assert forbidden not in source


def test_phase3_run_native_accepts_driver_without_real_window(monkeypatch):
    calls = []

    class FakeTkNativeWindow:
        def __init__(self, driver, *, title="Otoe", frame_path=None):
            self.driver = driver
            calls.append(("init", driver, title, frame_path))

        def run(self):
            calls.append(("run", self.driver))

    monkeypatch.setattr(window_module, "TkNativeWindow", FakeTkNativeWindow)
    demo = NativeWindowDemo()

    result = window_module.run_native(demo.driver, title="Closeout")

    assert result is None
    assert calls == [
        ("init", demo.driver, "Closeout", None),
        ("run", demo.driver),
    ]


def test_phase3_repeated_driver_sequence_is_frame_stable(tmp_path):
    first = NativeWindowDemo()
    second = NativeWindowDemo()

    first_summary = _drive_repeated_sequence(first)
    second_summary = _drive_repeated_sequence(second)
    first_frame = first.driver.frame
    second_frame = second.driver.frame

    first_final = tmp_path / "first-final.png"
    first_repeat = tmp_path / "first-repeat.png"
    second_final = tmp_path / "second-final.png"

    first.render(first_final)
    first.render(first_repeat)
    second.render(second_final)

    assert first_summary == second_summary
    assert first_summary[:5] == (
        "",
        0,
        3,
        None,
        ("Runtime bridge", "Input polish", "Docs pass"),
    )
    assert first.driver.surface.focused_box is not None
    assert first.driver.surface.focused_box.name == "Button"
    assert first.driver.surface.focused_box.text == "New"
    assert _layout_summary(first.driver) == _layout_summary(second.driver)
    assert first_final.read_bytes() == first_repeat.read_bytes()
    assert first_final.read_bytes() == second_final.read_bytes()
    assert first_frame == second_frame


def _drive_repeated_sequence(demo: NativeWindowDemo) -> tuple[object, ...]:
    driver = demo.driver

    for char in "input":
        driver.key_input(char, text=char)
    demo.open_first_visible_task()
    driver.key_down("Escape")
    demo.scroll_list(48)
    driver.key_down("k", ctrl=True)

    input_box = _first_box(driver, "Input")
    driver.click(input_box.x + 2, input_box.y + 2)
    for char in "docs":
        driver.key_input(char, text=char)
    driver.key_down("Tab")
    driver.key_down("Enter")
    driver.key_down("Tab")
    driver.key_down("Enter")
    driver.key_down("Escape")

    return (
        demo.board.query.value,
        demo.board.list_scroll_y.value,
        demo.board.shortcut_count.value,
        demo.board.selected_task_id.value,
        tuple(demo.visible_titles()),
        driver.focused_path,
    )


def _layout_summary(driver: NativeWindowDriver) -> tuple[tuple[object, ...], ...]:
    return tuple(
        (
            box.path,
            box.name,
            box.x,
            box.y,
            box.width,
            box.height,
            box.text,
            box.state,
            box.style,
        )
        for box in driver.surface.layout.boxes
    )


def _first_box(driver: NativeWindowDriver, name: str):
    for box in driver.surface.layout.boxes:
        if box.name == name:
            return box
    raise KeyError(f"No native box named {name!r}.")


def _has_text(driver: NativeWindowDriver, text: str) -> bool:
    return any(box.text == text for box in driver.surface.layout.boxes)
