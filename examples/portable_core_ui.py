from __future__ import annotations

from collections.abc import Callable

from otoe import Button, HStack, Input, Panel, ScrollView, Text, VStack
from otoe.ui import (
    ActionButton,
    AppFrame,
    Badge,
    Card,
    Dialog,
    ListRow,
    MetricTile,
    TabButton,
    Tabs,
)


def text_example():
    return Text("Portable text")


def button_example():
    return Button("Run", onClick=lambda: None)


def input_example():
    return Input(value="A", placeholder="Name", onChange=lambda value: None)


def vstack_example():
    return VStack(Text("One"), Text("Two"), gap=4)


def hstack_example():
    return HStack(Text("Left"), Text("Right"), gap=4)


def panel_example():
    return Panel(Text("Panel body"), title="Panel")


def scrollview_example():
    return ScrollView(
        Button("First", onClick=lambda: None),
        Button("Second", onClick=lambda: None),
        onScroll=lambda next_scroll_y: None,
    )


def card_example():
    return Card(Text("Card body"), padding=8, gap=4)


def badge_example():
    return Badge("Ready", tone="success")


def action_button_example():
    return ActionButton("Execute", onClick=lambda: None)


def tabs_example():
    return Tabs(
        TabButton("Overview", active=True, onClick=lambda: None),
        TabButton("Logs"),
    )


def dialog_example():
    return Dialog(
        Text("Dialog body"),
        open=True,
        title="Confirm",
        description="Proceed safely.",
    )


def list_row_example():
    return ListRow(
        title="Job",
        detail="Queued",
        badge="Ready",
        action_label="Open",
        on_action=lambda: None,
    )


def metric_tile_example():
    return MetricTile(
        label="Latency",
        value="31 ms",
        detail="p95",
        tone="success",
    )


def app_frame_example():
    return AppFrame(
        sidebar=VStack(Text("Navigation")),
        topbar=Text("Top bar"),
        content=VStack(Text("Workspace")),
    )


PORTABLE_CORE_EXAMPLES: dict[str, Callable[[], object]] = {
    "text": text_example,
    "button": button_example,
    "input": input_example,
    "vstack": vstack_example,
    "hstack": hstack_example,
    "panel": panel_example,
    "scrollview": scrollview_example,
    "card": card_example,
    "badge": badge_example,
    "action-button": action_button_example,
    "tabs": tabs_example,
    "list-row": list_row_example,
    "metric-tile": metric_tile_example,
    "app-frame": app_frame_example,
}


def app():
    return VStack(
        Text("Portable Core UI v0", className="portable-title"),
        *[example() for example in PORTABLE_CORE_EXAMPLES.values()],
        gap=8,
        padding=12,
    )
