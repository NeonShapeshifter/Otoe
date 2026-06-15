from otoe import (
    Button,
    HStack,
    Input,
    Panel,
    ScrollView,
    Text,
    VStack,
    mount,
    render_html,
)
from otoe.experimental.native import layout_native, paint_native
from otoe.ui import FocusScope, ShortcutScope


WIDGET_SAMPLES = {
    "Text": lambda: Text("hello"),
    "Button": lambda: Button("Run", onClick=lambda: None),
    "Input": lambda: Input(value="", placeholder="Type"),
    "VStack": lambda: VStack(Text("child")),
    "HStack": lambda: HStack(Text("child")),
    "Panel": lambda: Panel(Text("child"), title="Panel"),
    "ScrollView": lambda: ScrollView(Text("child")),
    "ShortcutScope": lambda: ShortcutScope(
        Text("child"),
        onKeyDown=lambda event: None,
    ),
    "FocusScope": lambda: FocusScope(Text("child")),
}


def test_public_widget_samples_render_across_current_renderers():
    for name, factory in WIDGET_SAMPLES.items():
        mounted = mount(factory())
        html = render_html(mounted)
        layout = layout_native(mounted)
        paint = paint_native(layout)

        assert html, name
        assert layout.boxes, name
        assert paint.commands, name
