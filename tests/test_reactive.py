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
