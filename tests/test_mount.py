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


def test_unmount_attempts_every_cleanup_when_one_fails():
    events = []

    @component
    def CleanupFailures():
        on_cleanup(lambda: events.append("first"))

        def fail_cleanup():
            events.append("failed")
            raise RuntimeError("cleanup failed")

        on_cleanup(fail_cleanup)
        on_cleanup(lambda: events.append("last"))
        return Text("Ready")

    mounted = mount(CleanupFailures())

    with pytest.raises(ExceptionGroup, match="CleanupFailures"):
        unmount(mounted)

    assert events == ["last", "failed", "first"]

    unmount(mounted)
    assert events == ["last", "failed", "first"]


def test_unmount_attempts_every_cleanup_after_process_control_exceptions():
    value = signal("ready")
    events: list[str] = []

    @component
    def CleanupFailures():
        def watch_value():
            _ = value.value

            def cleanup_effect():
                events.append("effect")
                raise SystemExit("effect cleanup stopped")

            return cleanup_effect

        effect(watch_value)
        on_cleanup(lambda: events.append("first"))

        def interrupt_cleanup():
            events.append("interrupted")
            raise KeyboardInterrupt("owner cleanup interrupted")

        on_cleanup(interrupt_cleanup)
        on_cleanup(lambda: events.append("last"))
        return Text(value)

    mounted = mount(CleanupFailures())

    with pytest.raises(BaseExceptionGroup) as caught:
        unmount(mounted)

    errors = _flatten_exceptions(caught.value)
    assert any(isinstance(error, KeyboardInterrupt) for error in errors)
    assert any(isinstance(error, SystemExit) for error in errors)
    assert events == ["last", "interrupted", "first", "effect"]
    assert mounted.owner is not None
    assert mounted.owner.disposed is True
    assert value._subscribers == {}

    unmount(mounted)
    assert events == ["last", "interrupted", "first", "effect"]


def test_process_control_during_mount_still_disposes_partial_owner():
    events: list[str] = []

    @component
    def InterruptedMount():
        on_cleanup(lambda: events.append("cleanup"))

        def interrupt_mount():
            raise KeyboardInterrupt("mount interrupted")

        on_mount(interrupt_mount)
        return Text("Ready")

    with pytest.raises(KeyboardInterrupt, match="mount interrupted"):
        mount(InterruptedMount())

    assert events == ["cleanup"]


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


def test_failed_mount_preserves_primary_and_cleanup_errors():
    @component
    def CleanupFailure():
        def cleanup():
            raise RuntimeError("cleanup failed")

        on_cleanup(cleanup)
        return Text("Mounted")

    broken_child = Node(tag=Text, props={"typo": True})

    with pytest.raises(ExceptionGroup, match="mount and cleanup both failed") as caught:
        mount(HStack(CleanupFailure(), broken_child))

    nested_errors = _flatten_exceptions(caught.value)
    assert any(isinstance(error, UnknownPropError) for error in nested_errors)
    assert any(
        isinstance(error, RuntimeError) and str(error) == "cleanup failed"
        for error in nested_errors
    )


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
    assert visible.value is False
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
    assert visible.value is False
    assert widget.children[0].props["content"] == "Fallback"

    unmount(mounted)
    assert cleanups == ["bad", "fallback"]


def test_show_activates_replacement_when_branch_switches_during_on_mount():
    visible = signal(False)
    events = []

    @component
    def Fallback():
        def reveal_active_branch():
            events.append("mount:fallback")
            visible.set(True)

        on_mount(reveal_active_branch)
        on_mount(lambda: events.append("mount:fallback-after-dispose"))
        on_cleanup(lambda: events.append("cleanup:fallback"))
        return Text("Fallback")

    @component
    def Active():
        on_mount(lambda: events.append("mount:active"))
        on_cleanup(lambda: events.append("cleanup:active"))
        return Text("Active")

    mounted = mount(Show(Active(), when=visible, fallback=Fallback()))

    assert visible.value is True
    assert root_widget(mounted).children[0].props["content"] == "Active"
    assert events == [
        "mount:fallback",
        "mount:active",
        "cleanup:fallback",
    ]

    unmount(mounted)
    assert events == [
        "mount:fallback",
        "mount:active",
        "cleanup:fallback",
        "cleanup:active",
    ]


def test_show_skips_siblings_unmounted_by_reentrant_on_mount_update():
    visible = signal(True)
    events = []

    @component
    def First():
        def hide_branch():
            events.append("mount:first")
            visible.set(False)

        on_mount(hide_branch)
        on_cleanup(lambda: events.append("cleanup:first"))
        return Text("First")

    @component
    def Second():
        on_mount(lambda: events.append("mount:second"))
        on_cleanup(lambda: events.append("cleanup:second"))
        return Text("Second")

    @component
    def Fallback():
        on_mount(lambda: events.append("mount:fallback"))
        return Text("Fallback")

    mounted = mount(Show(First(), Second(), when=visible, fallback=Fallback()))

    assert visible.value is False
    assert root_widget(mounted).children[0].props["content"] == "Fallback"
    assert events == [
        "mount:first",
        "mount:fallback",
        "cleanup:second",
        "cleanup:first",
    ]

    unmount(mounted)


def test_show_reentrant_update_during_refresh_keeps_signal_and_tree_aligned():
    visible = signal(False)
    events = []
    fallback_instance = 0

    @component
    def Fallback():
        nonlocal fallback_instance
        fallback_instance += 1
        instance = fallback_instance
        on_mount(lambda: events.append(f"mount:fallback:{instance}"))
        on_cleanup(lambda: events.append(f"cleanup:fallback:{instance}"))
        return Text("Fallback")

    @component
    def Active():
        def hide_again():
            events.append("mount:active")
            visible.set(False)

        on_mount(hide_again)
        on_cleanup(lambda: events.append("cleanup:active"))
        return Text("Active")

    mounted = mount(Show(Active(), when=visible, fallback=Fallback()))

    visible.set(True)

    assert visible.value is False
    assert root_widget(mounted).children[0].props["content"] == "Fallback"
    assert events == [
        "mount:fallback:1",
        "mount:active",
        "mount:fallback:2",
        "cleanup:active",
        "cleanup:fallback:1",
    ]

    unmount(mounted)
    assert events[-1] == "cleanup:fallback:2"


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
    assert items.value == [{"id": "stable", "label": "Stable"}]
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
    assert items.value == [{"id": "stable", "label": "Stable"}]
    assert widget.children[0].props["content"] == "Stable"

    unmount(mounted)
    assert cleanups == ["Bad", "Stable"]


def test_for_rolls_back_without_leaking_when_previous_item_cleanup_fails():
    items = signal([{"id": "old", "label": "Old"}])
    events = []
    fail_old_cleanup = True

    @component
    def Row(label: str):
        nonlocal fail_old_cleanup
        on_mount(lambda: events.append(f"mount:{label}"))

        def cleanup():
            nonlocal fail_old_cleanup
            events.append(f"cleanup:{label}")
            if label == "Old" and fail_old_cleanup:
                fail_old_cleanup = False
                raise RuntimeError("old cleanup failed")

        on_cleanup(cleanup)
        return Text(label)

    mounted = mount(
        For(
            each=items,
            key=lambda item: item["id"],
            children=lambda item: Row(item["label"]),
        )
    )

    with pytest.raises(ExceptionGroup):
        items.set([{"id": "next", "label": "Next"}])

    assert items.value == [{"id": "old", "label": "Old"}]
    assert root_widget(mounted).children[0].props["content"] == "Old"
    assert events == [
        "mount:Old",
        "mount:Next",
        "cleanup:Old",
        "mount:Old",
        "cleanup:Next",
    ]

    unmount(mounted)
    assert events == [
        "mount:Old",
        "mount:Next",
        "cleanup:Old",
        "mount:Old",
        "cleanup:Next",
        "cleanup:Old",
    ]


def test_for_reentrant_update_during_activation_keeps_latest_items_without_leaks():
    items = signal([{"id": "a", "label": "A"}])
    mounted_labels = []
    cleaned_labels = []

    @component
    def Row(item):
        label = item["label"]

        def activate():
            mounted_labels.append(label)
            if label == "B":
                items.set([{"id": "d", "label": "D"}])

        on_mount(activate)
        on_cleanup(lambda: cleaned_labels.append(label))
        return Text(label)

    mounted = mount(
        For(
            each=items,
            key=lambda item: item["id"],
            children=Row,
        )
    )

    items.set(
        [
            {"id": "b", "label": "B"},
            {"id": "c", "label": "C"},
        ]
    )

    assert items.value == [{"id": "d", "label": "D"}]
    assert [child.props["content"] for child in root_widget(mounted).children] == ["D"]
    assert mounted_labels == ["A", "B", "D"]
    assert sorted(cleaned_labels) == ["A", "B", "C"]

    unmount(mounted)
    assert sorted(cleaned_labels) == ["A", "B", "C", "D"]


def _flatten_exceptions(error):
    if not isinstance(error, BaseExceptionGroup):
        return [error]
    return [
        nested
        for child in error.exceptions
        for nested in _flatten_exceptions(child)
    ]
