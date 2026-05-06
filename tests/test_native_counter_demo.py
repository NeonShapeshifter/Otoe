from examples.native.counter_demo import NativeCounterDemo, render_demo_frames


def test_native_counter_demo_renders_framework_neutral_surface(tmp_path):
    demo = NativeCounterDemo()
    output = tmp_path / "counter.png"

    paint = demo.render(output)
    layout = demo.layout()

    assert output.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    assert paint.width == 280
    assert layout.by_path((0,)).text == "Native Counter"
    assert layout.by_path((1,)).text == "Count: 0"
    assert layout.by_path((2, 0)).text == "Decrement"
    assert layout.by_path((2, 1)).text == "Increment"


def test_native_counter_demo_clicks_update_state_and_render_output(tmp_path):
    demo = NativeCounterDemo()
    before = tmp_path / "before.png"
    after = tmp_path / "after.png"
    final = tmp_path / "final.png"

    demo.render(before)
    demo.click_increment()
    demo.render(after)
    demo.click_decrement()
    demo.render(final)

    assert demo.count.value == 0
    assert before.read_bytes() != after.read_bytes()
    assert before.read_bytes() == final.read_bytes()


def test_native_counter_demo_frame_writer_creates_before_after_images(tmp_path):
    before, after = render_demo_frames(tmp_path)

    assert before.exists()
    assert after.exists()
    assert before.read_bytes() != after.read_bytes()
