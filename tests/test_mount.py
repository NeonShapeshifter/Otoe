import asyncio

import pytest

from otoe import (
    Button,
    DuplicatePrimaryPropError,
    EventHandlerArityError,
    EventHandlerError,
    For,
    HStack,
    Input,
    Node,
    ReactiveDisposedError,
    Show,
    Text,
    UnknownEventError,
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


def test_node_copies_props_and_children_as_readonly():
    child = Text("Child")
    props = {"id": "root"}
    children = [child]

    node = Node(tag=HStack, props=props, children=children)
    props["id"] = "changed"
    children.append(Text("Other"))

    assert node.props["id"] == "root"
    assert node.children == (child,)
    with pytest.raises(TypeError):
        node.props["id"] = "mutated"
    with pytest.raises(AttributeError):
        node.children.append(child)


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


def test_async_event_handler_error_propagates_without_running_loop():
    async def handle_click():
        await asyncio.sleep(0)
        raise RuntimeError("async failure")

    widget = root_widget(mount(Button("Run", onClick=handle_click)))

    with pytest.raises(RuntimeError, match="async failure"):
        widget.trigger("onClick")


def test_async_event_handler_error_is_observable_from_running_loop():
    async def handle_click():
        await asyncio.sleep(0)
        raise RuntimeError("loop failure")

    async def run_in_loop():
        widget = root_widget(mount(Button("Run", onClick=handle_click)))
        task = widget.trigger("onClick")

        assert isinstance(task, asyncio.Task)
        with pytest.raises(RuntimeError, match="loop failure"):
            await task

    asyncio.run(run_in_loop())


def test_unknown_props_raise_developer_facing_error():
    with pytest.raises(
        UnknownPropError,
        match=r"Text received unknown prop 'typo'. Known props: className, color, content, id",
    ):
        mount(Text("Hello", typo=True))


def test_non_callable_event_raises():
    with pytest.raises(EventHandlerError, match="must be callable"):
        mount(Button("Save", onClick="not-callable"))


def test_event_handler_arity_error_is_event_handler_error():
    assert issubclass(EventHandlerArityError, EventHandlerError)


def test_event_handler_arity_errors_are_developer_facing():
    def handle_change(value):
        return value

    widget = root_widget(mount(Input(value="", onChange=handle_change)))

    with pytest.raises(
        EventHandlerArityError,
        match=r"Input\.onChange\(value\) handler handle_change expected",
    ):
        widget.trigger("onChange")


def test_event_handler_arity_errors_include_widget_context():
    def handle_key():
        return None

    widget = root_widget(mount(Button("Run", onKeyDown=handle_key)))

    with pytest.raises(
        EventHandlerArityError,
        match=r"Button\.onKeyDown\(key\) handler handle_key expected",
    ):
        widget.trigger("onKeyDown", "Enter")


def test_unknown_event_error_lists_known_signatures():
    with pytest.raises(
        UnknownEventError,
        match=r"Known events: onBlur\(\), onClick\(\), onFocus\(\), onKeyDown\(key\)",
    ):
        mount(Button("Save", onTap=lambda: None))


def test_event_handler_errors_include_component_context():
    def handle_change(value):
        return value

    @component
    def SearchBox():
        return Input(value="", onChange=handle_change)

    widget = root_widget(mount(SearchBox()))

    with pytest.raises(
        EventHandlerArityError,
        match=r"SearchBox > Input\.onChange\(value\) handler handle_change expected",
    ):
        widget.trigger("onChange")


def test_unknown_event_errors_include_component_context():
    @component
    def BrokenButton():
        return Button("Run", onTap=lambda: None)

    with pytest.raises(
        UnknownEventError,
        match=r"BrokenButton > Button received unknown event 'onTap'",
    ):
        mount(BrokenButton())


def test_unknown_prop_errors_include_component_context_and_known_props():
    @component
    def BrokenLabel():
        return Text("Run", typo=True)

    with pytest.raises(
        UnknownPropError,
        match=(
            r"BrokenLabel > Text received unknown prop 'typo'. "
            r"Known props: className, color, content, id"
        ),
    ):
        mount(BrokenLabel())


def test_event_handler_internal_type_errors_still_propagate():
    def handle_click():
        raise TypeError("handler body failed")

    widget = root_widget(mount(Button("Run", onClick=handle_click)))

    with pytest.raises(TypeError, match="handler body failed"):
        widget.trigger("onClick")


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


def test_failed_prop_mount_disposes_reactive_subscription():
    label = signal("READY")
    node = Node(tag=Text, props={"content": label, "typo": True})

    with pytest.raises(UnknownPropError):
        mount(node)

    assert len(label._subscribers) == 0


def test_failed_child_mount_unmounts_partially_mounted_children():
    cleanups = []

    @component
    def MountedChild():
        on_cleanup(lambda: cleanups.append("child"))
        return Text("Mounted")

    broken_child = Node(tag=Text, props={"typo": True})

    with pytest.raises(UnknownPropError):
        mount(HStack(MountedChild(), broken_child))

    assert cleanups == ["child"]


def test_failed_component_render_disposes_owner_disposables():
    status = signal("READY")
    leaked = []
    cleanups = []

    @component
    def BrokenStatus():
        label = computed(lambda: status.value)
        leaked.append(label)
        _ = label.value
        on_cleanup(lambda: cleanups.append("component"))
        raise RuntimeError("render failed")

    with pytest.raises(RuntimeError, match="render failed"):
        mount(BrokenStatus())

    assert len(status._subscribers) == 0
    assert cleanups == ["component"]
    with pytest.raises(ReactiveDisposedError):
        _ = leaked[0].value


def test_show_preserves_previous_ui_when_new_branch_mount_fails():
    visible = signal(False)
    cleanups = []

    @component
    def StableFallback():
        on_cleanup(lambda: cleanups.append("fallback"))
        return Text("Fallback")

    mounted = mount(
        Show(
            Node(tag=Text, props={"typo": True}),
            when=visible,
            fallback=StableFallback(),
        )
    )
    widget = root_widget(mounted)

    with pytest.raises(UnknownPropError):
        visible.set(True)

    assert cleanups == []
    assert widget.children[0].props["content"] == "Fallback"

    unmount(mounted)


def test_show_preserves_previous_ui_when_new_branch_on_mount_fails():
    visible = signal(False)
    cleanups = []

    @component
    def StableFallback():
        on_cleanup(lambda: cleanups.append("fallback"))
        return Text("Fallback")

    @component
    def BadBranch():
        on_mount(lambda: (_ for _ in ()).throw(RuntimeError("mount failed")))
        on_cleanup(lambda: cleanups.append("bad"))
        return Text("Bad")

    mounted = mount(Show(BadBranch(), when=visible, fallback=StableFallback()))
    widget = root_widget(mounted)

    with pytest.raises(RuntimeError, match="mount failed"):
        visible.set(True)

    assert cleanups == ["bad"]
    assert widget.children[0].props["content"] == "Fallback"

    unmount(mounted)
    assert cleanups == ["bad", "fallback"]


def test_for_preserves_previous_ui_when_refresh_mount_fails():
    items = signal([{"id": "stable", "label": "Stable"}])
    cleanups = []

    @component
    def StableItem(label: str):
        on_cleanup(lambda: cleanups.append(label))
        return Text(label)

    def render_item(item):
        if item["id"] == "bad":
            return Node(tag=Text, props={"typo": True})
        return StableItem(item["label"])

    mounted = mount(
        For(
            each=items,
            key=lambda item: item["id"],
            children=render_item,
        )
    )
    widget = root_widget(mounted)

    with pytest.raises(UnknownPropError):
        items.set([{"id": "bad", "label": "Bad"}])

    assert cleanups == []
    assert widget.children[0].props["content"] == "Stable"

    unmount(mounted)


def test_for_preserves_previous_ui_when_new_item_on_mount_fails():
    items = signal([{"id": "stable", "label": "Stable"}])
    cleanups = []

    @component
    def StableItem(label: str):
        on_cleanup(lambda: cleanups.append(label))
        return Text(label)

    @component
    def BadItem(label: str):
        on_mount(lambda: (_ for _ in ()).throw(RuntimeError("mount failed")))
        on_cleanup(lambda: cleanups.append(label))
        return Text(label)

    def render_item(item):
        if item["id"] == "bad":
            return BadItem(item["label"])
        return StableItem(item["label"])

    mounted = mount(
        For(
            each=items,
            key=lambda item: item["id"],
            children=render_item,
        )
    )
    widget = root_widget(mounted)

    with pytest.raises(RuntimeError, match="mount failed"):
        items.set([{"id": "bad", "label": "Bad"}])

    assert cleanups == ["Bad"]
    assert widget.children[0].props["content"] == "Stable"

    unmount(mounted)
    assert cleanups == ["Bad", "Stable"]
