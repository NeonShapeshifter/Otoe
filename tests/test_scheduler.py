import threading
from collections.abc import Callable

import otoe.scheduler as scheduler_module
import pytest

from otoe import batch, effect, signal
from otoe.errors import ReactiveThreadError
from otoe.scheduler import (
    PostedCallbackQueue,
    capture_post,
    drain_posted,
    post,
)


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


def test_single_active_runtime_routes_legacy_worker_post_without_loss():
    queue = PostedCallbackQueue()
    runtime_ready = threading.Event()
    drain_now = threading.Event()
    callback_threads: list[int] = []
    runtime_thread: list[int] = []

    def run_runtime() -> None:
        with queue.activate():
            runtime_thread.append(threading.get_ident())
            runtime_ready.set()
            assert drain_now.wait(timeout=2)
            assert drain_posted(queue=queue) == 1

    host = threading.Thread(target=run_runtime)
    host.start()
    assert runtime_ready.wait(timeout=2)

    worker = threading.Thread(
        target=lambda: post(lambda: callback_threads.append(threading.get_ident()))
    )
    worker.start()
    worker.join(timeout=2)
    drain_now.set()
    host.join(timeout=2)

    assert not worker.is_alive()
    assert not host.is_alive()
    assert callback_threads == runtime_thread


def test_first_runtime_adopts_legacy_callbacks_posted_before_start():
    assert drain_posted() == 0
    seen: list[str] = []
    post(lambda: seen.append("pre-start"))
    queue = PostedCallbackQueue()

    with queue.activate():
        assert drain_posted(queue=queue) == 1

    assert seen == ["pre-start"]
    assert drain_posted() == 0


def test_two_active_runtimes_require_targeting_and_never_cross_drain():
    queues = (PostedCallbackQueue(), PostedCallbackQueue())
    ready = threading.Barrier(3)
    drain_now = threading.Event()
    posters: list[Callable[[Callable[[], None]], None] | None] = [None, None]
    runtime_threads: list[int | None] = [None, None]
    callback_threads: list[list[int]] = [[], []]
    drained: list[int | None] = [None, None]

    def run_runtime(index: int) -> None:
        with queues[index].activate():
            runtime_threads[index] = threading.get_ident()
            posters[index] = capture_post()
            ready.wait(timeout=2)
            assert drain_now.wait(timeout=2)
            drained[index] = drain_posted(queue=queues[index])

    hosts = [
        threading.Thread(target=run_runtime, args=(index,)) for index in range(2)
    ]
    for host in hosts:
        host.start()
    ready.wait(timeout=2)

    with pytest.raises(RuntimeError, match="multiple active runtimes"):
        post(lambda: None)
    for index, poster in enumerate(posters):
        assert poster is not None
        poster(lambda index=index: callback_threads[index].append(threading.get_ident()))

    drain_now.set()
    for host in hosts:
        host.join(timeout=2)

    assert all(not host.is_alive() for host in hosts)
    assert drained == [1, 1]
    assert callback_threads == [[runtime_threads[0]], [runtime_threads[1]]]


def test_active_queue_rejects_foreign_drain_without_consuming_work():
    queue = PostedCallbackQueue()
    ready = threading.Event()
    drain_now = threading.Event()
    seen: list[str] = []

    def run_runtime() -> None:
        with queue.activate():
            ready.set()
            assert drain_now.wait(timeout=2)
            assert queue.drain() == 1

    host = threading.Thread(target=run_runtime)
    host.start()
    assert ready.wait(timeout=2)
    queue.post(lambda: seen.append("runtime"))

    with pytest.raises(RuntimeError, match="owning runtime thread"):
        queue.drain()
    assert seen == []

    drain_now.set()
    host.join(timeout=2)
    assert not host.is_alive()
    assert seen == ["runtime"]


def test_post_and_first_runtime_activation_select_and_enqueue_atomically(
    monkeypatch,
):
    assert drain_posted() == 0
    entered_default_post = threading.Event()
    release_default_post = threading.Event()
    runtime_ready = threading.Event()
    drain_now = threading.Event()
    seen: list[str] = []
    errors: list[BaseException] = []
    queue = PostedCallbackQueue()
    default_queue = scheduler_module._DEFAULT_POSTED_CALLBACKS
    original_post = default_queue.post

    def delayed_default_post(callback: Callable[[], None]) -> None:
        entered_default_post.set()
        assert release_default_post.wait(timeout=2)
        original_post(callback)

    monkeypatch.setattr(default_queue, "post", delayed_default_post)

    def produce() -> None:
        try:
            post(lambda: seen.append("adopted"))
        except BaseException as exc:
            errors.append(exc)

    def run_runtime() -> None:
        try:
            with queue.activate():
                runtime_ready.set()
                assert drain_now.wait(timeout=2)
                assert queue.drain() == 1
        except BaseException as exc:
            errors.append(exc)

    producer = threading.Thread(target=produce)
    host = threading.Thread(target=run_runtime)
    producer.start()
    assert entered_default_post.wait(timeout=2)
    host.start()
    assert not runtime_ready.wait(timeout=0.05)

    release_default_post.set()
    producer.join(timeout=2)
    assert runtime_ready.wait(timeout=2)
    drain_now.set()
    host.join(timeout=2)

    assert not producer.is_alive()
    assert not host.is_alive()
    assert errors == []
    assert seen == ["adopted"]
    assert drain_posted() == 0


def test_capture_post_before_runtime_uses_dynamic_router_after_activation():
    assert drain_posted() == 0
    poster = capture_post()
    queue = PostedCallbackQueue()
    ready = threading.Event()
    drain_now = threading.Event()
    seen: list[str] = []

    def run_runtime() -> None:
        with queue.activate():
            ready.set()
            assert drain_now.wait(timeout=2)
            assert queue.drain() == 1

    host = threading.Thread(target=run_runtime)
    host.start()
    assert ready.wait(timeout=2)
    poster(lambda: seen.append("routed"))
    drain_now.set()
    host.join(timeout=2)

    assert not host.is_alive()
    assert seen == ["routed"]
    assert drain_posted() == 0


def test_runtime_shutdown_drains_accepted_work_and_rejects_late_bound_posts():
    queue = PostedCallbackQueue()
    seen: list[str] = []

    with queue.activate():
        poster = capture_post()

        def first() -> None:
            seen.append("first")
            post(lambda: seen.append("second"))

        poster(first)

    assert seen == ["first", "second"]
    with pytest.raises(RuntimeError, match="not accepting work"):
        poster(lambda: seen.append("late"))
    assert seen == ["first", "second"]


def test_drain_continues_after_base_exception_without_losing_the_snapshot():
    queue = PostedCallbackQueue()
    seen: list[str] = []

    def interrupt() -> None:
        raise KeyboardInterrupt("callback interrupted")

    queue.post(interrupt)
    queue.post(lambda: seen.append("later"))

    with pytest.raises(KeyboardInterrupt, match="callback interrupted"):
        queue.drain()

    assert seen == ["later"]
    assert queue.drain() == 0


def test_runtime_shutdown_continues_after_base_exception_and_then_seals_queue():
    queue = PostedCallbackQueue()
    seen: list[str] = []

    def stop() -> None:
        raise SystemExit("callback stopped")

    with pytest.raises(SystemExit, match="callback stopped"):
        with queue.activate():
            queue.post(stop)
            queue.post(lambda: seen.append("later"))

    assert seen == ["later"]
    with pytest.raises(RuntimeError, match="not accepting work"):
        queue.post(lambda: None)


def test_activate_preserves_runtime_and_shutdown_failures():
    queue = PostedCallbackQueue()

    def fail_shutdown_callback() -> None:
        raise RuntimeError("shutdown callback failed")

    with pytest.raises(BaseExceptionGroup) as caught:
        with queue.activate():
            queue.post(fail_shutdown_callback)
            raise ValueError("runtime failed")

    assert [str(error) for error in caught.value.exceptions] == [
        "runtime failed",
        "shutdown callback failed",
    ]


def test_close_permanently_drains_prestart_and_reentrant_work():
    queue = PostedCallbackQueue()
    seen: list[str] = []

    def first() -> None:
        seen.append("first")
        queue.post(lambda: seen.append("second"))

    poster = queue.post
    poster(first)

    queue.close()
    queue.close()

    assert queue.closed is True
    assert seen == ["first", "second"]
    with pytest.raises(RuntimeError, match="not accepting work"):
        poster(lambda: None)
    with pytest.raises(RuntimeError, match="cannot be activated"):
        with queue.activate():
            pass


def test_close_tries_all_prestart_callbacks_and_stays_closed_after_failure():
    queue = PostedCallbackQueue()
    seen: list[str] = []

    def interrupt() -> None:
        raise KeyboardInterrupt("close interrupted")

    queue.post(interrupt)
    queue.post(lambda: seen.append("later"))

    with pytest.raises(KeyboardInterrupt, match="close interrupted"):
        queue.close()

    assert queue.closed is True
    assert seen == ["later"]
    queue.close()
    with pytest.raises(RuntimeError, match="not accepting work"):
        queue.post(lambda: None)


def test_close_during_activation_seals_then_drains_on_outer_exit():
    queue = PostedCallbackQueue()
    seen: list[str] = []

    with queue.activate():
        queue.post(lambda: seen.append("accepted"))
        queue.close()

        assert queue.closed is True
        assert seen == []
        with pytest.raises(RuntimeError, match="not accepting work"):
            queue.post(lambda: None)

    assert seen == ["accepted"]
    with pytest.raises(RuntimeError, match="cannot be activated"):
        with queue.activate():
            pass


def test_normal_deactivation_does_not_permanently_close_reusable_queue():
    queue = PostedCallbackQueue()
    seen: list[str] = []

    with queue.activate():
        queue.post(lambda: seen.append("first"))
    with queue.activate():
        queue.post(lambda: seen.append("second"))

    assert queue.closed is False
    assert seen == ["first", "second"]


def test_concurrent_close_does_not_steal_owner_during_shutdown_drain():
    queue = PostedCallbackQueue()
    callback_started = threading.Event()
    release_callback = threading.Event()
    runtime_thread: list[int] = []
    callback_threads: list[int] = []
    errors: list[BaseException] = []

    def first() -> None:
        callback_threads.append(threading.get_ident())
        callback_started.set()
        assert release_callback.wait(timeout=2)
        queue.post(lambda: callback_threads.append(threading.get_ident()))

    def run_runtime() -> None:
        try:
            runtime_thread.append(threading.get_ident())
            with queue.activate():
                queue.post(first)
        except BaseException as exc:
            errors.append(exc)

    host = threading.Thread(target=run_runtime)
    host.start()
    assert callback_started.wait(timeout=2)

    queue.close()
    release_callback.set()
    host.join(timeout=2)

    assert not host.is_alive()
    assert errors == []
    assert callback_threads == [runtime_thread[0], runtime_thread[0]]
    assert queue.closed is True


def test_inactive_close_keeps_reentrant_global_posts_on_its_own_queue():
    active_queue = PostedCallbackQueue()
    closing_queue = PostedCallbackQueue()
    runtime_ready = threading.Event()
    release_runtime = threading.Event()
    closing_seen: list[str] = []

    def run_active_runtime() -> None:
        with active_queue.activate():
            runtime_ready.set()
            assert release_runtime.wait(timeout=2)

    host = threading.Thread(target=run_active_runtime)
    host.start()
    assert runtime_ready.wait(timeout=2)

    def first() -> None:
        closing_seen.append("first")
        post(lambda: closing_seen.append("second"))

    closing_queue.post(first)
    closing_queue.close()

    assert closing_seen == ["first", "second"]
    release_runtime.set()
    host.join(timeout=2)
    assert not host.is_alive()
