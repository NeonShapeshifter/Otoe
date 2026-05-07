import pytest

from otoe import (
    ReactiveDisposedError,
    Text,
    component,
    computed,
    effect,
    mount,
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
