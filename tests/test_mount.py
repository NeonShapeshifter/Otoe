import asyncio

import pytest

from otoe import (
    Button,
    DuplicatePrimaryPropError,
    EventHandlerError,
    HStack,
    Text,
    UnknownPropError,
    component,
    computed,
    effect,
    mount,
    on_cleanup,
    on_mount,
    root_widget,
    signal,
    unmount,
)


def test_widget_schema_classifies_events_before_reactive_props():
    clicks = []
    node = Button("Save", onClick=lambda: clicks.append("clicked"))

    mounted = mount(node)
    widget = root_widget(mounted)

    widget.trigger("onClick")

    assert widget.props["label"] == "Save"
    assert clicks == ["clicked"]


def test_async_event_handler_runs_to_completion_without_running_loop():
    events = []

    async def handle_click(label):
        await asyncio.sleep(0)
        events.append(label)
        return "done"

    widget = root_widget(mount(Button("Run", onClick=handle_click)))

    result = widget.trigger("onClick", "async")

    assert result == "done"
    assert events == ["async"]


def test_sync_event_handler_returning_coroutine_runs_to_completion():
    events = []

    async def record():
        await asyncio.sleep(0)
        events.append("recorded")
        return "done"

    widget = root_widget(mount(Button("Run", onClick=lambda: record())))

    result = widget.trigger("onClick")

    assert result == "done"
    assert events == ["recorded"]


def test_async_event_handler_returns_task_inside_running_loop():
    events = []

    async def handle_click():
        await asyncio.sleep(0)
        events.append("done")
        return "result"

    async def run_in_loop():
        widget = root_widget(mount(Button("Run", onClick=handle_click)))
        task = widget.trigger("onClick")

        assert isinstance(task, asyncio.Task)
        assert await task == "result"

    asyncio.run(run_in_loop())

    assert events == ["done"]


def test_unknown_props_raise_developer_facing_error():
    with pytest.raises(UnknownPropError, match="unknown prop"):
        mount(Text("Hello", typo=True))


def test_non_callable_event_raises():
    with pytest.raises(EventHandlerError, match="must be callable"):
        mount(Button("Save", onClick="not-callable"))


def test_primary_prop_duplicate_raises_at_node_creation():
    with pytest.raises(DuplicatePrimaryPropError):
        Text("Hello", content="World")


def test_reactive_props_update_fake_widget_directly():
    label = signal("READY")
    node = HStack(Text(label))

    mounted = mount(node)
    root = root_widget(mounted)
    child = root.children[0]

    assert child.props["content"] == "READY"

    label.set("ARMED")

    assert child.props["content"] == "ARMED"


def test_component_owner_runs_mount_cleanup_and_disposes_subscriptions():
    label = signal("READY")
    events = []

    @component
    def Status():
        on_mount(lambda: events.append("mounted"))
        on_cleanup(lambda: events.append("cleanup"))
        effect(lambda: events.append(f"effect:{label.value}"))
        return Text(label)

    mounted = mount(Status())
    widget = root_widget(mounted)

    assert events == ["effect:READY", "mounted"]
    assert widget.props["content"] == "READY"

    label.set("ARMED")

    assert events == ["effect:READY", "mounted", "effect:ARMED"]
    assert widget.props["content"] == "ARMED"

    unmount(mounted)
    label.set("DONE")

    assert events == ["effect:READY", "mounted", "effect:ARMED", "cleanup"]
    assert widget.props["content"] == "ARMED"


def test_computed_prop_updates_when_dependency_changes():
    active = signal(False)
    node = Button("ST", className=computed(lambda: "on" if active.value else "off"))

    mounted = mount(node)
    widget = root_widget(mounted)

    assert widget.props["className"] == "off"

    active.set(True)

    assert widget.props["className"] == "on"
