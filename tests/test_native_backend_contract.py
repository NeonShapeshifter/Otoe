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
    signal,
)


def test_native_backend_acceptance_contract_drives_surface_end_to_end():
    query = signal("seed")
    scroll_y = signal(0)
    clicks: list[str] = []
    shortcuts: list[dict[str, object]] = []
    sheet = css(
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

    driver = NativeWindowDriver.from_target(ContractApp(), stylesheet=sheet)
    surface = driver.surface
    shell_path = (0,)
    search_path = (0, 0)
    toolbar_path = (0, 1)
    one_path = (0, 1, 0)
    two_path = (0, 1, 1)
    list_path = (0, 2)
    first_path = (0, 2, 0)
    second_path = (0, 2, 1)
    echo_path = (0, 3)

    assert surface.layout.root.name == "ShortcutScope"
    assert surface.box(search_path).name == "Input"
    assert surface.focused_path == search_path
    assert driver.size == (driver.paint.width, driver.paint.height)

    first_command_indexes: dict[tuple[int, ...], int] = {}
    for index, command in enumerate(surface.paint.commands):
        first_command_indexes.setdefault(command.path, index)

    expected_painter_order = [
        (),
        shell_path,
        search_path,
        toolbar_path,
        one_path,
        two_path,
        list_path,
        first_path,
        second_path,
        echo_path,
    ]
    expected_painter_paths = set(expected_painter_order)
    assert [
        path
        for path in first_command_indexes
        if path in expected_painter_paths
    ] == expected_painter_order

    initial_frame = driver.frame
    driver.dispatch(NativeWindowEvent("input_text", text="alpha"))

    assert query.value == "alpha"
    assert surface.box(echo_path).text == "alpha"
    assert driver.frame > initial_frame

    driver.dispatch(NativeWindowEvent("key_input", key="k", text="k", ctrl=True))

    assert query.value == "alpha"
    assert shortcuts == [
        {
            "key": "k",
            "ctrlKey": True,
            "metaKey": False,
            "altKey": False,
            "shiftKey": False,
        }
    ]

    second_toolbar_button = surface.box(two_path)
    hit = surface.hit_test(second_toolbar_button.x + 2, second_toolbar_button.y + 2)

    driver.dispatch(
        NativeWindowEvent(
            "click",
            x=second_toolbar_button.x + 2,
            y=second_toolbar_button.y + 2,
        )
    )

    assert hit is not None
    assert hit.path == two_path
    assert clicks == ["two"]
    assert surface.focused_path == two_path

    scroll_box = surface.box(list_path)
    first_row_before = surface.box(first_path)
    second_row_before = surface.box(second_path)

    driver.dispatch(
        NativeWindowEvent(
            "wheel",
            x=scroll_box.x + 2,
            y=scroll_box.y + 2,
            delta_y=100,
        )
    )

    assert scroll_y.value > 0
    assert surface.box(first_path).y < first_row_before.y
    assert surface.box(second_path).y < second_row_before.y
