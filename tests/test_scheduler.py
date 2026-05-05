from otoe import batch, effect, signal


def test_batch_groups_effect_reruns():
    first = signal("Ale")
    last = signal("Gagnemyr")
    seen = []

    effect(lambda: seen.append(f"{first.value} {last.value}"))

    with batch():
        first.set("Otoe")
        last.set("Runtime")

    assert seen == ["Ale Gagnemyr", "Otoe Runtime"]


def test_batch_function_form_returns_result():
    value = signal(0)
    seen = []
    effect(lambda: seen.append(value.value))

    result = batch(lambda: (value.set(1), value.set(2), "done")[-1])

    assert result == "done"
    assert seen == [0, 2]


def test_nested_batch_flushes_once_at_outer_exit():
    value = signal(0)
    seen = []
    effect(lambda: seen.append(value.value))

    with batch():
        value.set(1)
        with batch():
            value.set(2)
            value.set(3)
        assert seen == [0]
        value.set(4)

    assert seen == [0, 4]

