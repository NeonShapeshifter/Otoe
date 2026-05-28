from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from examples.native.window_demo import NativeWindowDemo
from otoe import (
    Button,
    HStack,
    Input,
    NativeWindowDriver,
    NativeWindowEvent,
    ScrollView,
    ShortcutScope,
    Text,
    VStack,
    component,
    css,
    run_native,
    signal,
)


@dataclass(frozen=True)
class BackendContractPaths:
    root: tuple[int, ...] = ()
    shell: tuple[int, ...] = (0,)
    search: tuple[int, ...] = (0, 0)
    toolbar: tuple[int, ...] = (0, 1)
    one: tuple[int, ...] = (0, 1, 0)
    two: tuple[int, ...] = (0, 1, 1)
    list: tuple[int, ...] = (0, 2)
    first: tuple[int, ...] = (0, 2, 0)
    second: tuple[int, ...] = (0, 2, 1)
    echo: tuple[int, ...] = (0, 3)

    @property
    def painter_order(self) -> tuple[tuple[int, ...], ...]:
        return (
            self.root,
            self.shell,
            self.search,
            self.toolbar,
            self.one,
            self.two,
            self.list,
            self.first,
            self.second,
            self.echo,
        )


@dataclass
class BackendContractHarness:
    driver: NativeWindowDriver
    paths: BackendContractPaths
    query: Any
    scroll_y: Any
    clicks: list[str]
    shortcuts: list[dict[str, object]]


@dataclass
class BackendContractTarget:
    target: Any
    stylesheet: Any
    paths: BackendContractPaths
    query: Any
    scroll_y: Any
    clicks: list[str]
    shortcuts: list[dict[str, object]]

    def driver(self) -> NativeWindowDriver:
        return NativeWindowDriver.from_target(
            self.target,
            stylesheet=self.stylesheet,
        )

    def harness(self, driver: NativeWindowDriver | None = None) -> BackendContractHarness:
        return BackendContractHarness(
            driver=driver if driver is not None else self.driver(),
            paths=self.paths,
            query=self.query,
            scroll_y=self.scroll_y,
            clicks=self.clicks,
            shortcuts=self.shortcuts,
        )


@dataclass(frozen=True)
class TaskBoardBackendReplay:
    filtered_titles: tuple[str, ...]
    selected_task_after_click: str | None
    modal_text_visible: bool
    shortcut_count_after_escape: int
    scroll_y_after_wheel: int
    final_query: str
    final_titles: tuple[str, ...]
    final_selected_task: str | None
    final_shortcut_count: int
    final_frame_advanced: bool
    final_focused_box: tuple[str, str | None] | None


def test_native_backend_acceptance_contract_drives_surface_end_to_end():
    harness = backend_contract_harness()

    assert_backend_contract_initial_state(harness)
    assert_backend_contract_painter_order(harness)
    assert_backend_contract_input_and_shortcut_replay(harness)
    assert_backend_contract_click_and_scroll_replay(harness)


def test_native_backend_app_shaped_contract_replays_task_board_flow():
    demo = NativeWindowDemo()

    replay = replay_task_board_backend_contract(demo)

    assert replay == TaskBoardBackendReplay(
        filtered_titles=("Input polish",),
        selected_task_after_click="input",
        modal_text_visible=True,
        shortcut_count_after_escape=1,
        scroll_y_after_wheel=48,
        final_query="",
        final_titles=("Runtime bridge", "Input polish", "Docs pass"),
        final_selected_task=None,
        final_shortcut_count=2,
        final_frame_advanced=True,
        final_focused_box=("Button", "Inspect"),
    )


def test_native_backend_adapter_receives_driver_that_replays_contract():
    target = backend_contract_target()
    calls: list[tuple[str, str, int]] = []

    class RecordingBackend:
        name = "recording"

        def run(self, driver: NativeWindowDriver, *, title: str = "Otoe") -> None:
            calls.append((self.name, title, driver.frame))
            harness = target.harness(driver)
            assert_backend_contract_initial_state(harness)
            assert_backend_contract_painter_order(harness)
            assert_backend_contract_input_and_shortcut_replay(harness)
            assert_backend_contract_click_and_scroll_replay(harness)

    result = run_native(
        target.target,
        stylesheet=target.stylesheet,
        title="Backend Contract",
        backend=RecordingBackend(),
    )

    assert result is None
    assert calls == [("recording", "Backend Contract", 1)]


def backend_contract_target() -> BackendContractTarget:
    query = signal("seed")
    scroll_y = signal(0)
    clicks: list[str] = []
    shortcuts: list[dict[str, object]] = []

    @component
    def ContractApp():
        return ShortcutScope(
            VStack(
                Input(
                    value=query,
                    placeholder="Search",
                    autoFocus=True,
                    onChange=lambda next_value: query.set(next_value),
                    className="search",
                ),
                HStack(
                    Button("One", onClick=lambda: clicks.append("one")),
                    Button("Two", onClick=lambda: clicks.append("two")),
                    className="toolbar",
                ),
                ScrollView(
                    Button("First", onClick=lambda: clicks.append("first")),
                    Button("Second", onClick=lambda: clicks.append("second")),
                    scrollY=scroll_y,
                    onScroll=lambda next_scroll_y: scroll_y.set(next_scroll_y),
                    className="list",
                ),
                Text(query),
                className="shell",
            ),
            onKeyDown=shortcuts.append,
        )

    return BackendContractTarget(
        target=ContractApp(),
        stylesheet=backend_contract_styles(),
        paths=BackendContractPaths(),
        query=query,
        scroll_y=scroll_y,
        clicks=clicks,
        shortcuts=shortcuts,
    )


def backend_contract_harness() -> BackendContractHarness:
    return backend_contract_target().harness()


def backend_contract_styles():
    return css(
        """
        .ui-shortcut-scope {
        }
        .shell {
          width: 220;
          padding: 8;
          gap: 6;
          background: #f8fafc;
        }
        .search {
          width: 120;
        }
        .toolbar {
          width: 200;
          height: 44;
          gap: 4;
          align-items: center;
          background: #f1f5f9;
          justify-content: space-between;
        }
        .list {
          width: 200;
          height: 44;
          padding: 4;
          gap: 4;
          background: #ffffff;
        }
        """
    )


def assert_backend_contract_initial_state(harness: BackendContractHarness) -> None:
    driver = harness.driver
    surface = driver.surface
    paths = harness.paths

    assert surface.layout.root.name == "ShortcutScope"
    assert surface.box(paths.search).name == "Input"
    assert surface.focused_path == paths.search
    assert driver.size == (driver.paint.width, driver.paint.height)


def assert_backend_contract_painter_order(harness: BackendContractHarness) -> None:
    surface = harness.driver.surface
    first_command_indexes: dict[tuple[int, ...], int] = {}
    for index, command in enumerate(surface.paint.commands):
        first_command_indexes.setdefault(command.path, index)

    expected_painter_paths = set(harness.paths.painter_order)
    actual_order = tuple(
        path
        for path in first_command_indexes
        if path in expected_painter_paths
    )
    assert actual_order == harness.paths.painter_order


def assert_backend_contract_input_and_shortcut_replay(
    harness: BackendContractHarness,
) -> None:
    driver = harness.driver
    surface = driver.surface
    paths = harness.paths
    initial_frame = driver.frame

    driver.dispatch(NativeWindowEvent("input_text", text="alpha"))

    assert harness.query.value == "alpha"
    assert surface.box(paths.echo).text == "alpha"
    assert driver.frame > initial_frame

    driver.dispatch(NativeWindowEvent("key_input", key="k", text="k", ctrl=True))

    assert harness.query.value == "alpha"
    assert harness.shortcuts == [
        {
            "key": "k",
            "ctrlKey": True,
            "metaKey": False,
            "altKey": False,
            "shiftKey": False,
        }
    ]


def assert_backend_contract_click_and_scroll_replay(
    harness: BackendContractHarness,
) -> None:
    driver = harness.driver
    surface = driver.surface
    paths = harness.paths
    second_toolbar_button = surface.box(paths.two)
    hit = surface.hit_test(second_toolbar_button.x + 2, second_toolbar_button.y + 2)

    driver.dispatch(
        NativeWindowEvent(
            "click",
            x=second_toolbar_button.x + 2,
            y=second_toolbar_button.y + 2,
        )
    )

    assert hit is not None
    assert hit.path == paths.two
    assert harness.clicks == ["two"]
    assert surface.focused_path == paths.two

    scroll_box = surface.box(paths.list)
    first_row_before = surface.box(paths.first)
    second_row_before = surface.box(paths.second)

    driver.dispatch(
        NativeWindowEvent(
            "wheel",
            x=scroll_box.x + 2,
            y=scroll_box.y + 2,
            delta_y=100,
        )
    )

    assert harness.scroll_y.value > 0
    assert surface.box(paths.first).y < first_row_before.y
    assert surface.box(paths.second).y < second_row_before.y


def replay_task_board_backend_contract(
    demo: NativeWindowDemo,
) -> TaskBoardBackendReplay:
    initial_frame = demo.driver.frame

    demo.type_search("input")
    filtered_titles = tuple(demo.visible_titles())

    demo.open_first_visible_task()
    selected_task = demo.board.selected_task_id.value
    modal_text_visible = has_layout_text(demo.driver, "Inspect Input polish")

    demo.driver.key_down("Escape")
    shortcut_count_after_escape = demo.board.shortcut_count.value

    demo.clear_with_shortcut()
    demo.scroll_list(48)
    scroll_y_after_wheel = demo.board.list_scroll_y.value

    return TaskBoardBackendReplay(
        filtered_titles=filtered_titles,
        selected_task_after_click=selected_task,
        modal_text_visible=modal_text_visible,
        shortcut_count_after_escape=shortcut_count_after_escape,
        scroll_y_after_wheel=scroll_y_after_wheel,
        final_query=demo.board.query.value,
        final_titles=tuple(demo.visible_titles()),
        final_selected_task=demo.board.selected_task_id.value,
        final_shortcut_count=demo.board.shortcut_count.value,
        final_frame_advanced=demo.driver.frame > initial_frame,
        final_focused_box=focused_box_summary(demo.driver),
    )


def has_layout_text(driver: NativeWindowDriver, text: str) -> bool:
    return any(box.text == text for box in driver.surface.layout.boxes)


def focused_box_summary(driver: NativeWindowDriver) -> tuple[str, str | None] | None:
    focused_box = driver.surface.focused_box
    if focused_box is None:
        return None
    return (focused_box.name, focused_box.text)
