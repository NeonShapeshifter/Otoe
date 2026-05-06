from examples.native.task_board_demo import NativeTaskBoardDemo, render_demo_frames


def test_native_task_board_demo_renders_app_shell(tmp_path):
    demo = NativeTaskBoardDemo()
    output = tmp_path / "task-board.png"

    paint = demo.render(output)

    assert output.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    assert paint.width == 420
    assert demo.surface.focused_box is not None
    assert demo.surface.focused_box.name == "Input"
    assert demo.visible_titles() == [
        "Runtime bridge",
        "Input polish",
        "Docs pass",
    ]
    assert demo._box_with_text("Native Task Board").name == "Text"
    assert demo._box_with_text("3 visible").text == "3 visible"


def test_native_task_board_demo_search_filters_and_empty_state():
    demo = NativeTaskBoardDemo()

    demo.type_search("docs")

    assert demo.query.value == "docs"
    assert demo.visible_titles() == ["Docs pass"]
    assert demo._box_with_text("1 visible").text == "1 visible"

    demo.type_search("zzzz")

    assert demo.visible_titles() == []
    assert demo._box_with_text("No tasks match").text == "No tasks match"


def test_native_task_board_demo_modal_opens_closes_and_shortcuts_fire():
    demo = NativeTaskBoardDemo()

    demo.type_search("input")
    demo.click_text("Inspect")

    assert demo.selected_task.value is not None
    assert demo.selected_task.value["id"] == "input"
    assert demo._box_with_text("Inspect Input polish").text == "Inspect Input polish"

    demo.key_down("Escape")

    assert demo.selected_task.value is None
    assert demo.shortcut_count.value == 1


def test_native_task_board_demo_clear_and_global_search_shortcut():
    demo = NativeTaskBoardDemo()

    demo.type_search("runtime")
    demo.click_text("Clear")

    assert demo.query.value == ""
    assert len(demo.visible_titles()) == 3

    demo.type_search("docs")
    demo.key_down("k", ctrl=True)

    assert demo.query.value == ""
    assert demo.shortcut_count.value == 1


def test_native_task_board_demo_frame_writer_creates_distinct_frames(tmp_path):
    initial, filtered, modal = render_demo_frames(tmp_path)

    assert initial.exists()
    assert filtered.exists()
    assert modal.exists()
    assert initial.read_bytes() != filtered.read_bytes()
    assert filtered.read_bytes() != modal.read_bytes()
