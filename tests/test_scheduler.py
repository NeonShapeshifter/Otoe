import threading

import pytest

from otoe import batch, effect, signal
from otoe.errors import ReactiveThreadError
from otoe.scheduler import drain_posted, post


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


def test_batch_rolls_back_signal_values_when_flush_fails():
    value = signal(0)
    seen = []

    def observe():
        seen.append(value.value)
        if value.value == 1:
            raise RuntimeError("render failed")

    effect(observe)

    with pytest.raises(RuntimeError, match="render failed"):
        with batch():
            value.set(1)

    assert value.value == 0
    assert seen == [0, 1, 0]


def test_batch_rolls_back_signal_values_when_body_fails_before_flush():
    value = signal(0)
    seen = []
    effect(lambda: seen.append(value.value))

    with pytest.raises(RuntimeError, match="action failed"):
        with batch():
            value.set(1)
            raise RuntimeError("action failed")

    assert value.value == 0
    assert seen == [0]


def test_failing_batch_in_another_thread_cannot_discard_local_updates():
    value = signal(0)
    seen = []
    worker_started = threading.Event()
    release_worker = threading.Event()
    worker_errors = []
    effect(lambda: seen.append(value.value))

    def fail_in_batch():
        try:
            with batch():
                worker_started.set()
                release_worker.wait(timeout=2)
                raise RuntimeError("worker failed")
        except RuntimeError as exc:
            worker_errors.append(exc)

    worker = threading.Thread(target=fail_in_batch)
    worker.start()
    assert worker_started.wait(timeout=2)

    value.set(1)
    release_worker.set()
    worker.join(timeout=2)

    assert not worker.is_alive()
    assert [str(error) for error in worker_errors] == ["worker failed"]
    assert value.value == 1
    assert seen == [0, 1]


def test_reactive_update_from_foreign_thread_is_rejected_without_mutation():
    value = signal(0)
    seen = []
    errors = []
    effect(lambda: seen.append(value.value))

    def update_from_worker():
        try:
            value.set(1)
        except Exception as exc:
            errors.append(exc)

    worker = threading.Thread(target=update_from_worker)
    worker.start()
    worker.join(timeout=2)

    assert not worker.is_alive()
    assert len(errors) == 1
    assert isinstance(errors[0], ReactiveThreadError)
    assert value.value == 0
    assert seen == [0]


def test_worker_can_post_reactive_update_for_runtime_thread():
    value = signal(0)
    seen = []
    effect(lambda: seen.append(value.value))

    worker = threading.Thread(target=lambda: post(lambda: value.set(1)))
    worker.start()
    worker.join(timeout=2)

    assert not worker.is_alive()
    assert value.value == 0
    assert drain_posted() == 1
    assert value.value == 1
    assert seen == [0, 1]
    assert drain_posted() == 0


def test_drain_posted_validates_callback_limit():
    with pytest.raises(ValueError, match="max_callbacks"):
        drain_posted(max_callbacks=0)
