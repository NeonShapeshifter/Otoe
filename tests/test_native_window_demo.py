from examples.native.window_demo import NativeWindowDemo, render_demo_frames


def test_native_window_demo_drives_task_board_through_window_driver():
    demo = NativeWindowDemo()

    demo.type_search("input")
    demo.open_first_visible_task()
    demo.clear_with_shortcut()

    assert demo.visible_titles() == ["Runtime bridge", "Input polish", "Docs pass"]
    assert demo.board.selected_task.value["title"] == "Input polish"
    assert demo.board.shortcut_count.value == 1


def test_native_window_demo_frame_writer_creates_distinct_frames(tmp_path):
    frames = render_demo_frames(tmp_path)

    assert len(frames) == 4
    assert all(frame.exists() for frame in frames)
    assert all(frame.read_bytes().startswith(b"\x89PNG\r\n\x1a\n") for frame in frames)
    assert len({frame.read_bytes() for frame in frames}) == 4
