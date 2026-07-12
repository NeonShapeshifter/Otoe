import pytest

from otoe import (
    ReactiveDisposedError,
    ReactiveMutationError,
    Text,
    component,
    computed,
    effect,
    mount,
    on_mount,
    root_widget,
    signal,
    unmount,
)


def test_signal_updates_effect_dependencies():
    count = signal(0)
    seen = []

    effect(lambda: seen.append(count.value))

    count.set(1)
    count.value = 2

    assert seen == [0, 1, 2]


class _ExplodingEq:
    def __eq__(self, other):
        raise RuntimeError("equality failed")


class _NonBoolEq:
    def __eq__(self, other):
        return object()


def test_signal_setter_handles_equality_exceptions_as_identity_checks():
    initial = _ExplodingEq()
    updated = _ExplodingEq()
    value = signal(initial)
    seen = []
    value.subscribe(lambda: seen.append(value.value))

    value.set(updated)
    value.set(updated)

    assert value.value is updated
    assert seen == [updated]


def test_signal_setter_treats_non_bool_equality_results_as_identity_checks():
    initial = _NonBoolEq()
    updated = _NonBoolEq()
    value = signal(initial)
    seen = []
    value.subscribe(lambda: seen.append(value.value))

    value.set(updated)
    value.set(updated)

    assert value.value is updated
    assert seen == [updated]


def test_signal_notifies_subscribers_when_value_changes_normally():
    value = signal({"count": 1})
    seen = []
    value.subscribe(lambda: seen.append(value.value))

    value.set({"count": 2})

    assert seen == [{"count": 2}]


def test_signal_attempts_every_subscriber_and_reconciles_after_failure():
    value = signal(0)
    seen = []

    def broken_subscriber():
        seen.append(("broken", value.value))
        if value.value == 1:
            raise RuntimeError("subscriber failed")

    value.subscribe(broken_subscriber)
    value.subscribe(lambda: seen.append(("healthy", value.value)))

    with pytest.raises(RuntimeError, match="subscriber failed"):
        value.set(1)

    assert value.value == 0
    assert seen == [
        ("broken", 1),
        ("healthy", 1),
        ("broken", 0),
        ("healthy", 0),
    ]


def test_signal_does_not_notify_subscribers_for_normally_equal_values():
    value = signal({"count": 1})
    seen = []
    value.subscribe(lambda: seen.append(value.value))

    value.set({"count": 1})

    assert seen == []


def test_computed_is_lazy_and_memoized_until_dependency_changes():
    first = signal("Ale")
    last = signal("Gagnemyr")
    calls = []

    full = computed(
        lambda: calls.append((first.value, last.value))
        or f"{first.value} {last.value}"
    )

    assert calls == []
    assert full.value == "Ale Gagnemyr"
    assert full.value == "Ale Gagnemyr"
    assert calls == [("Ale", "Gagnemyr")]

    last.set("Forvara")

    assert full.value == "Ale Forvara"
    assert calls == [("Ale", "Gagnemyr"), ("Ale", "Forvara")]


def test_effect_cleanup_runs_before_rerun_and_dispose():
    value = signal("a")
    events = []

    def watch():
        current = value.value
        events.append(f"run:{current}")
        return lambda: events.append(f"cleanup:{current}")

    handle = effect(watch)
    value.set("b")
    handle.dispose()

    assert events == ["run:a", "cleanup:a", "run:b", "cleanup:b"]


def test_failed_global_effect_construction_releases_collected_dependencies():
    value = signal("ready")

    def broken_effect():
        _ = value.value
        raise RuntimeError("effect failed")

    with pytest.raises(RuntimeError, match="effect failed"):
        effect(broken_effect)

    assert len(value._subscribers) == 0


def test_effect_created_during_on_mount_runs_and_tracks_dependencies():
    value = signal("ready")
    seen = []

    @component
    def MountedEffect():
        on_mount(lambda: effect(lambda: seen.append(value.value)))
        return Text(value)

    mounted = mount(MountedEffect())

    assert seen == ["ready"]

    value.set("armed")
    assert seen == ["ready", "armed"]

    unmount(mounted)
    value.set("done")
    assert seen == ["ready", "armed"]


def test_disposed_computed_read_is_developer_facing():
    label = computed(lambda: "ready")

    label.dispose()

    with pytest.raises(
        ReactiveDisposedError,
        match="Computed value was read after it was disposed",
    ):
        _ = label.value


def test_disposed_computed_read_includes_owner_context():
    leaked = []

    @component
    def StatusLabel():
        label = computed(lambda: "ready")
        leaked.append(label)
        return Text(label)

    mounted = mount(StatusLabel())
    unmount(mounted)

    with pytest.raises(
        ReactiveDisposedError,
        match="StatusLabel: Computed value was read after it was disposed",
    ):
        _ = leaked[0].value


def test_mutating_subscribed_signal_during_component_render_is_developer_facing():
    status = signal("ready")
    mounted = mount(Text(status))

    @component
    def BadRenderMutation():
        status.set("armed")
        return Text("bad")

    with pytest.raises(
        ReactiveMutationError,
        match="BadRenderMutation: Signal value was mutated during component render",
    ):
        mount(BadRenderMutation())

    assert root_widget(mounted).props["content"] == "ready"


def test_local_signal_initialization_during_component_render_stays_allowed():
    @component
    def LocalStatus():
        status = signal("starting")
        status.set("ready")
        return Text(status)

    mounted = mount(LocalStatus())

    assert root_widget(mounted).props["content"] == "ready"


def test_on_mount_can_mutate_subscribed_signal_after_render_phase():
    status = signal("starting")

    @component
    def MountedStatus():
        on_mount(lambda: status.set("ready"))
        return Text(status)

    mounted = mount(MountedStatus())

    assert root_widget(mounted).props["content"] == "ready"
