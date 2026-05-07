from otoe import Button, Input, ScrollView, Text, VStack, component, layout_native, mount


def test_layout_box_preserves_accessibility_seed_metadata():
    layout = layout_native(
        mount(
            VStack(
                Text("Settings", id="title"),
                Button("Save", id="save", disabled=True, onClick=lambda: None),
                Input(
                    id="name",
                    value="Ale",
                    onChange=lambda value: None,
                ),
                ScrollView(
                    Text("Log line"),
                    id="log",
                    scrollY=0,
                    onScroll=lambda next_scroll_y: None,
                ),
            )
        )
    )

    title = layout.by_path((0,))
    button = layout.by_path((1,))
    input_box = layout.by_path((2,))
    scroll = layout.by_path((3,))

    assert (title.name, title.id, title.text) == ("Text", "title", "Settings")
    assert (button.name, button.id, button.text) == ("Button", "save", "Save")
    assert button.events == ("onClick",)
    assert button.state == ("disabled",)
    assert (input_box.name, input_box.id, input_box.text) == ("Input", "name", "Ale")
    assert input_box.events == ("onChange",)
    assert scroll.name == "ScrollView"
    assert scroll.id == "log"
    assert scroll.events == ("onScroll",)
    assert scroll.children[0].text == "Log line"


def test_layout_box_accessibility_seed_keeps_component_context():
    @component
    def SettingsPanel():
        return VStack(Button("Save", onClick=lambda: None))

    layout = layout_native(mount(SettingsPanel()))

    assert layout.root.context == "SettingsPanel > VStack"
    assert layout.by_path((0,)).context == "SettingsPanel > Button"
