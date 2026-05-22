from html.parser import HTMLParser

from examples.native.task_board_demo import (
    TASK_BOARD_STYLES,
    NativeTaskBoardDemo,
    render_demo_frames,
)
from otoe import render_html
from otoe._native_shared import surface_root_widget, widget_by_path


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


def test_native_task_board_demo_row_content_fits_scroll_view_width():
    demo = NativeTaskBoardDemo()
    scroll_box = demo._first_box("ScrollView")

    for row in [
        box
        for box in demo.surface.layout.boxes
        if box.name == "HStack" and box.path[:4] == scroll_box.path + (0, 0)
    ]:
        assert row.x >= scroll_box.x
        assert row.x + row.width <= scroll_box.x + scroll_box.width
        for child in row.children:
            assert child.x + child.width <= row.x + row.width


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


def test_native_task_board_demo_html_and_native_tree_stay_in_parity_after_native_events():
    demo = NativeTaskBoardDemo()

    _assert_html_native_parity(demo)

    demo.type_search("input")
    _assert_html_native_parity(demo)
    assert _native_input_values(demo) == ["input"]

    demo.click_text("Inspect")
    _assert_html_native_parity(demo)
    assert "Inspect Input polish" in _native_texts(demo)

    demo.key_down("Escape")
    _assert_html_native_parity(demo)
    assert "Inspect Input polish" not in _native_texts(demo)

    demo.key_down("k", ctrl=True)
    _assert_html_native_parity(demo)
    assert _native_input_values(demo) == [""]
    assert "3 visible" in _native_texts(demo)


def test_native_task_board_demo_frame_writer_creates_distinct_frames(tmp_path):
    initial, filtered, modal = render_demo_frames(tmp_path)

    assert initial.exists()
    assert filtered.exists()
    assert modal.exists()
    assert initial.read_bytes() != filtered.read_bytes()
    assert filtered.read_bytes() != modal.read_bytes()


def _assert_html_native_parity(demo: NativeTaskBoardDemo) -> None:
    html = render_html(demo.surface.target, stylesheet=TASK_BOARD_STYLES)
    snapshot = _HtmlSnapshot.from_html(html)

    assert snapshot.texts == _native_texts(demo)
    assert snapshot.input_values == _native_input_values(demo)


def _native_texts(demo: NativeTaskBoardDemo) -> list[str]:
    return [
        box.text
        for box in demo.surface.layout.boxes
        if box.text and box.name != "Input"
    ]


def _native_input_values(demo: NativeTaskBoardDemo) -> list[str]:
    root = surface_root_widget(demo.surface.target)
    return [
        str(widget_by_path(root, box.path).props.get("value") or "")
        for box in demo.surface.layout.boxes
        if box.name == "Input"
    ]


class _HtmlSnapshot(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.texts: list[str] = []
        self.input_values: list[str] = []

    @classmethod
    def from_html(cls, html: str) -> "_HtmlSnapshot":
        parser = cls()
        parser.feed(html)
        return parser

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "input":
            values = dict(attrs)
            self.input_values.append(values.get("value") or "")

    def handle_data(self, data: str) -> None:
        text = data.strip()
        if text:
            self.texts.append(text)
