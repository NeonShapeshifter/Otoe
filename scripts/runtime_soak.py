#!/usr/bin/env python3
from __future__ import annotations

import argparse
import gc
import json
import platform as runtime_platform
import subprocess
import sys
import threading
import tempfile
import weakref
from collections import Counter
from dataclasses import asdict, dataclass, field
from http.client import HTTPConnection
from pathlib import Path
from time import monotonic
from typing import Any, Callable, cast


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from otoe import (  # noqa: E402
    For,
    ReactiveThreadError,
    Show,
    Text,
    VStack,
    component,
    effect,
    mount,
    on_cleanup,
    on_mount,
    render_html,
    root_widget,
    signal,
    unmount,
)
from otoe.live_server import (  # noqa: E402
    LivePreviewConfig,
    _LivePreviewState,
    _LivePreviewServer,
)
from otoe.mount import MountedNode  # noqa: E402
from otoe.node import Node  # noqa: E402
from otoe.owner import Owner, OwnerState, current_owner  # noqa: E402
from otoe.reactive import Signal  # noqa: E402
from otoe.scheduler import drain_posted, post  # noqa: E402
from otoe.window import NativeWindowDriver, TkNativeWindow  # noqa: E402


WORKER_NAME_PREFIX = "otoe-runtime-soak-worker-"
HOST_THREAD_NAME_PREFIX = "otoe-runtime-soak-http-"
WATCHDOG_SECONDS = 10.0
DEFAULT_HOST_CYCLES = 100
DEFAULT_PROCESS_TIMEOUT_SECONDS = 60.0


class RuntimeSoakError(RuntimeError):
    pass


class _ExpectedActivationFailure(RuntimeError):
    pass


@dataclass(frozen=True)
class RuntimeSoakResult:
    cycles: int
    host_cycles: int
    cycles_completed: int
    failing_cycle: int | None
    callbacks_posted: int
    callbacks_run: int
    owners_observed: int
    resources_acquired: int
    resources_released: int
    worker_threads_joined: int
    http_host_starts: int
    http_host_restarts: int
    http_requests: int
    native_host_pumps: int
    elapsed_seconds: float
    python: str
    platform: str
    counters_complete: bool
    counter_scope: str
    failures: tuple[str, ...] = ()

    def as_json_value(self) -> dict[str, Any]:
        value = asdict(self)
        value["format"] = "otoe-runtime-soak"
        value["failures"] = list(self.failures)
        return value


@dataclass(frozen=True)
class _CycleResult:
    callbacks_posted: int
    callbacks_run: int
    owners_observed: int
    resources_acquired: int
    resources_released: int
    worker_threads_joined: int
    owner_refs: tuple[weakref.ReferenceType[Owner], ...]


@dataclass
class _SoakProgress:
    cycles: int
    host_cycles: int
    cycles_completed: int = 0
    failing_cycle: int | None = None
    callbacks_posted: int = 0
    callbacks_run: int = 0
    owners_observed: int = 0
    resources_acquired: int = 0
    resources_released: int = 0
    worker_threads_joined: int = 0
    http_host_starts: int = 0
    http_requests: int = 0
    native_host_pumps: int = 0
    started_at: float = field(default_factory=monotonic)
    progress_path: Path | None = None

    def complete_cycle(self) -> None:
        self.cycles_completed += 1
        self.failing_cycle = None

    def result(self, *, failures: tuple[str, ...] = ()) -> RuntimeSoakResult:
        counters_complete = (
            self.cycles_completed == self.cycles
            and self.http_host_starts == self.host_cycles
            and self.native_host_pumps == self.host_cycles
        )
        return RuntimeSoakResult(
            cycles=self.cycles,
            host_cycles=self.host_cycles,
            cycles_completed=self.cycles_completed,
            failing_cycle=self.failing_cycle,
            callbacks_posted=self.callbacks_posted,
            callbacks_run=self.callbacks_run,
            owners_observed=self.owners_observed,
            resources_acquired=self.resources_acquired,
            resources_released=self.resources_released,
            worker_threads_joined=self.worker_threads_joined,
            http_host_starts=self.http_host_starts,
            http_host_restarts=max(0, self.http_host_starts - 1),
            http_requests=self.http_requests,
            native_host_pumps=self.native_host_pumps,
            elapsed_seconds=max(0.0, monotonic() - self.started_at),
            python=runtime_platform.python_version(),
            platform=runtime_platform.platform(),
            counters_complete=counters_complete,
            counter_scope=("complete" if counters_complete else "current-process-state"),
            failures=failures,
        )

    def checkpoint(self, *, failures: tuple[str, ...] = ()) -> None:
        if self.progress_path is None:
            return
        destination = self.progress_path
        temporary = destination.with_name(f".{destination.name}.tmp")
        temporary.write_text(
            json.dumps(self.result(failures=failures).as_json_value(), sort_keys=True),
            encoding="utf-8",
        )
        temporary.replace(destination)


class _ResourceLedger:
    def __init__(self, cycle: int, progress: _SoakProgress) -> None:
        self._cycle = cycle
        self._progress = progress
        self._serial = 0
        self.active: dict[str, str] = {}
        self.acquired = 0
        self.released = 0

    def acquire(self, label: str) -> Callable[[], None]:
        token = f"cycle-{self._cycle}:{self._serial}:{label}"
        self._serial += 1
        _require(token not in self.active, f"resource {token!r} was acquired twice")
        self.active[token] = label
        self.acquired += 1
        self._progress.resources_acquired += 1
        released = False

        def release() -> None:
            nonlocal released
            _require(not released, f"resource {token!r} was released twice")
            _require(token in self.active, f"resource {token!r} disappeared before release")
            released = True
            del self.active[token]
            self.released += 1
            self._progress.resources_released += 1

        return release

    def assert_phase(
        self,
        phase: str,
        *,
        active: tuple[str, ...],
        acquired: int,
        released: int,
    ) -> None:
        actual_active = Counter(self.active.values())
        expected_active = Counter(active)
        _require(
            actual_active == expected_active,
            f"{phase}: active resources differ: "
            f"expected {dict(expected_active)}, got {dict(actual_active)}",
        )
        _require(
            self.acquired == acquired,
            f"{phase}: expected {acquired} acquisitions, got {self.acquired}",
        )
        _require(
            self.released == released,
            f"{phase}: expected {released} releases, got {self.released}",
        )


class _MountedSoakApp:
    def __init__(self, mounted: MountedNode, tick: Signal) -> None:
        self.mounted = mounted
        self.tick = tick

    def render_fragment(self) -> str:
        return render_html(self.mounted)

    def dispatch_event(self, event_id: str, *args: Any) -> str:
        _require(event_id == "increment", f"unexpected live event {event_id!r}")
        _require(not args, "increment event unexpectedly received arguments")
        self.tick.set(self.tick.value + 1)
        return self.render_fragment()

    def dispose(self) -> None:
        unmount(self.mounted)


class _HttpProbeApp:
    def __init__(self, generation: int) -> None:
        self.tick = signal(generation * 10)
        self.owner: Owner | None = None
        self.cleanup_count = 0

        @component
        def ProbeRoot() -> Node:
            owner = current_owner()
            if owner is None:
                raise RuntimeSoakError("HTTP probe component rendered without an owner")
            self.owner = owner
            on_cleanup(self._record_cleanup)
            return Text(self.tick)

        self.mounted = mount(ProbeRoot())

    def _record_cleanup(self) -> None:
        self.cleanup_count += 1

    def render_fragment(self) -> str:
        return render_html(self.mounted)

    def dispatch_event(self, event_id: str, *args: Any) -> str:
        _require(event_id == "increment", f"unexpected HTTP probe event {event_id!r}")
        _require(not args, "HTTP probe increment unexpectedly received arguments")
        self.tick.set(self.tick.value + 1)
        return self.render_fragment()

    def dispose(self) -> None:
        unmount(self.mounted)


def _run_http_restart_probe(progress: _SoakProgress) -> None:
    port = 0
    for generation in range(progress.host_cycles):
        port, generation_requests = _exercise_http_host(generation, port=port)
        progress.http_host_starts += 1
        progress.http_requests += generation_requests
        progress.checkpoint()


def _exercise_http_host(generation: int, *, port: int) -> tuple[int, int]:
    ready = threading.Event()
    errors: list[BaseException] = []
    shared: dict[str, Any] = {}

    def host_target() -> None:
        server: _LivePreviewServer | None = None
        try:
            server = _LivePreviewServer(
                app_factory=lambda: _HttpProbeApp(generation),
                config=LivePreviewConfig(
                    title="HTTP runtime soak",
                    css_route="/runtime-soak.css",
                    css_path=None,
                ),
                host="127.0.0.1",
                port=port,
            )
            shared.update(
                app=server.app,
                server=server,
                port=server.server_address[1],
                runtime_thread=threading.get_ident(),
            )
            ready.set()
            server.serve_forever(poll_interval=0.01)
        except BaseException as exc:
            errors.append(exc)
            ready.set()
        finally:
            if server is not None:
                try:
                    server.close()
                except BaseException as exc:
                    errors.append(exc)

    host = threading.Thread(
        target=host_target,
        name=f"{HOST_THREAD_NAME_PREFIX}{generation}",
        daemon=True,
    )
    host.start()
    _require(
        ready.wait(timeout=WATCHDOG_SECONDS),
        f"HTTP host generation {generation} did not start",
    )
    if errors or "server" not in shared:
        host.join(timeout=WATCHDOG_SECONDS)
        if errors:
            raise errors[0]
        raise RuntimeSoakError(f"HTTP host generation {generation} did not expose a server")

    server = cast(_LivePreviewServer, shared["server"])
    probe_app = cast(_HttpProbeApp, shared["app"])
    actual_port = int(shared["port"])
    callback_threads: list[int] = []
    requests = 0
    try:
        expected_tick = generation * 10 + 1

        def update_from_queue(app: _HttpProbeApp = probe_app) -> None:
            callback_threads.append(threading.get_ident())
            app.tick.set(expected_tick)

        post(update_from_queue)
        status, body = _http_request(actual_port, "GET", "/")
        requests += 1
        _require(status == 200, f"HTTP host generation {generation} GET failed: {status}")
        _require(
            str(expected_tick).encode() in body,
            f"HTTP host generation {generation} rendered stale queued state",
        )
        _require(
            callback_threads == [shared["runtime_thread"]],
            f"HTTP host generation {generation} drained outside its runtime thread",
        )

        event_payload = json.dumps(
            {
                "id": "increment",
                "args": [],
                "clientId": f"http-soak-{generation}",
                "sequence": 1,
            }
        ).encode()
        status, body = _http_request(actual_port, "POST", "/event", event_payload)
        requests += 1
        _require(status == 200, f"HTTP host generation {generation} event failed: {status}")
        event_result = json.loads(body)
        _require(event_result["ok"] is True, "HTTP host event did not return ok")
        _require(
            str(expected_tick + 1) in event_result["html"],
            "HTTP host event returned stale HTML",
        )

        status, body = _http_request(actual_port, "POST", "/event", b'{"id":')
        requests += 1
        _require(status == 400, f"HTTP host invalid request returned {status}")
        _require(
            json.loads(body)["error"] == "invalid JSON event payload",
            "HTTP host invalid request returned the wrong diagnostic",
        )

        status, body = _http_request(actual_port, "GET", "/health")
        requests += 1
        _require(status == 200, "HTTP host did not recover after a failed request")
        _require(json.loads(body) == {"ok": True}, "HTTP host health payload drifted")
    finally:
        server.shutdown()
        host.join(timeout=WATCHDOG_SECONDS)

    _require(not host.is_alive(), f"HTTP host generation {generation} did not stop")
    if errors:
        raise errors[0]
    _require(probe_app.cleanup_count == 1, "HTTP host app cleanup did not run exactly once")
    _require(probe_app.owner is not None, "HTTP host app owner was not captured")
    owner = probe_app.owner
    if owner is None:
        raise RuntimeSoakError("HTTP host app owner was not captured")
    _require(owner.state is OwnerState.DISPOSED, "HTTP host app owner was not disposed")
    _require(not probe_app.tick._subscribers, "HTTP host app retained a signal subscriber")
    _require(drain_posted() == 0, "HTTP host shutdown left callbacks queued")
    retained: dict[str, weakref.ReferenceType[Any]] = {
        "app": weakref.ref(probe_app),
        "owner": weakref.ref(owner),
        "server": weakref.ref(server),
        "http_server": weakref.ref(server._server),
        "host_thread": weakref.ref(host),
    }
    shared.clear()
    del update_from_queue, probe_app, owner, server, host
    gc.collect()
    _assert_collected(retained, f"HTTP host generation {generation}")
    return actual_port, requests


def _http_request(
    port: int,
    method: str,
    path: str,
    body: bytes | None = None,
) -> tuple[int, bytes]:
    connection = HTTPConnection("127.0.0.1", port, timeout=WATCHDOG_SECONDS)
    try:
        headers = {"content-type": "application/json"} if body is not None else {}
        connection.request(method, path, body=body, headers=headers)
        response = connection.getresponse()
        return response.status, response.read()
    finally:
        connection.close()


def _run_native_host_probe(progress: _SoakProgress) -> None:
    for generation in range(progress.host_cycles):
        _exercise_native_host_pump(generation, progress=progress)
        progress.native_host_pumps += 1
        progress.checkpoint()


def _exercise_native_host_pump(
    generation: int,
    *,
    progress: _SoakProgress,
) -> None:
    runtime_thread = threading.get_ident()
    callback_threads: list[int] = []
    cleanup_count = 0
    owner: Owner | None = None
    tick = signal(generation)

    @component
    def NativeProbe() -> Node:
        nonlocal cleanup_count, owner
        current = current_owner()
        if current is None:
            raise RuntimeSoakError("Tk probe component rendered without an owner")
        owner = current

        def cleanup() -> None:
            nonlocal cleanup_count
            cleanup_count += 1

        on_cleanup(cleanup)
        return Text(tick)

    driver = NativeWindowDriver.from_target(NativeProbe())
    tk_module = _FakeTkModule()
    window = TkNativeWindow(driver, _tk_module=tk_module)

    def apply_update() -> None:
        callback_threads.append(threading.get_ident())
        tick.set(generation + 1)

    def enqueue_update() -> None:
        post(apply_update)

    _run_workers(
        -1,
        generation,
        (enqueue_update,),
        progress=progress,
    )
    window.run()

    _require(callback_threads == [runtime_thread], "Tk host drained outside runtime thread")
    _require(tick.value == generation + 1, "Tk host lost its queued update")
    root = tk_module.root
    if root is None:
        raise RuntimeSoakError("Tk host did not create a root")
    _require(root.mainloop_calls == 1, "Tk host did not run exactly one main loop")
    _require(len(root.scheduled) == 1, "Tk host did not leave exactly one deferred poll")
    window.close()
    window.close()
    _require(root.destroy_calls == 1, "Tk host root was not destroyed exactly once")
    _, deferred_poll = root.scheduled.pop(0)
    deferred_poll()
    _require(not root.scheduled, "closed Tk host scheduled work after close")
    _require(cleanup_count == 0, "Tk window disposed a borrowed driver")
    driver.dispose()
    driver.dispose()
    _require(cleanup_count == 1, "Tk driver cleanup did not run exactly once")
    if owner is None:
        raise RuntimeSoakError("Tk probe owner was not captured")
    _require(owner.state is OwnerState.DISPOSED, "Tk probe owner was not disposed")
    _require(not tick._subscribers, "Tk probe signal retained a subscriber")
    _require(drain_posted() == 0, "Tk host pump left callbacks queued")
    retained: dict[str, weakref.ReferenceType[Any]] = {
        "window": weakref.ref(window),
        "driver": weakref.ref(driver),
        "owner": weakref.ref(owner),
        "root": weakref.ref(root),
    }
    tk_module.root = None
    owner = None
    del deferred_poll, window, driver, root, tk_module, NativeProbe
    gc.collect()
    _assert_collected(retained, f"Tk host generation {generation}")


class _FakeTkRoot:
    def __init__(self) -> None:
        self.scheduled: list[tuple[int, Callable[[], None]]] = []
        self.mainloop_calls = 0
        self.destroy_calls = 0

    def title(self, value: str) -> None:
        return

    def bind(self, event: str, handler: Callable[..., Any]) -> None:
        return

    def geometry(self, value: str) -> None:
        return

    def after(self, delay: int, callback: Callable[[], None]) -> None:
        self.scheduled.append((delay, callback))

    def mainloop(self) -> None:
        self.mainloop_calls += 1
        _require(bool(self.scheduled), "Tk fake root entered mainloop without a pump")
        _, callback = self.scheduled.pop(0)
        callback()

    def destroy(self) -> None:
        self.destroy_calls += 1


class _FakeTkCanvas:
    def __init__(self, root: _FakeTkRoot, **kwargs: Any) -> None:
        self.root = root

    def pack(self, **kwargs: Any) -> None:
        return

    def bind(self, event: str, handler: Callable[..., Any]) -> None:
        return

    def delete(self, tag: str) -> None:
        return

    def create_rectangle(self, *args: Any, **kwargs: Any) -> None:
        return

    def create_text(self, *args: Any, **kwargs: Any) -> None:
        return

    def focus_set(self) -> None:
        return


class _FakeTkModule:
    def __init__(self) -> None:
        self.root: _FakeTkRoot | None = None

    def Tk(self) -> _FakeTkRoot:
        self.root = _FakeTkRoot()
        return self.root

    def Canvas(self, root: _FakeTkRoot, **kwargs: Any) -> _FakeTkCanvas:
        return _FakeTkCanvas(root, **kwargs)


def _assert_collected(
    references: dict[str, weakref.ReferenceType[Any]],
    context: str,
) -> None:
    retained = [name for name, reference in references.items() if reference() is not None]
    _require(not retained, f"{context} retained objects after cleanup: {retained}")


def run_runtime_soak(
    *,
    cycles: int = 1_000,
    host_cycles: int = DEFAULT_HOST_CYCLES,
    _progress: _SoakProgress | None = None,
) -> RuntimeSoakResult:
    """Exercise the runtime/host lifecycle repeatedly and assert quiescence.

    Synchronization uses events, bounded joins, and the scheduler queue itself.
    Wall-clock sleeps are intentionally absent; timeouts are deadlock watchdogs.
    """
    if cycles < 1:
        raise ValueError("cycles must be >= 1")
    if host_cycles < 1:
        raise ValueError("host_cycles must be >= 1")

    progress = _progress or _SoakProgress(cycles=cycles, host_cycles=host_cycles)
    _require(progress.cycles == cycles, "soak progress has a different cycle target")
    _require(
        progress.host_cycles == host_cycles,
        "soak progress has a different host-cycle target",
    )
    progress.checkpoint()
    _require(drain_posted() == 0, "posted callback queue was dirty before the soak")
    baseline_threads = {id(thread) for thread in threading.enumerate()}

    _run_http_restart_probe(progress)
    _run_native_host_probe(progress)

    for cycle in range(cycles):
        progress.failing_cycle = cycle
        progress.checkpoint()
        cycle_result = _run_cycle(cycle, progress=progress)

        gc.collect()
        retained_owners = [
            owner.name
            for ref in cycle_result.owner_refs
            if (owner := ref()) is not None
        ]
        _require(
            not retained_owners,
            f"cycle {cycle}: owners remained reachable after restart: {retained_owners}",
        )
        progress.complete_cycle()
        progress.checkpoint()

    _require(drain_posted() == 0, "posted callback queue was not empty after the soak")
    leaked_threads = [
        thread.name
        for thread in threading.enumerate()
        if id(thread) not in baseline_threads
    ]
    _require(not leaked_threads, f"threads remained alive after the soak: {leaked_threads}")
    _require(
        not any(
            thread.name.startswith((WORKER_NAME_PREFIX, HOST_THREAD_NAME_PREFIX))
            for thread in threading.enumerate()
        ),
        "a runtime soak worker or host remained alive",
    )

    result = progress.result()
    progress.checkpoint()
    return result


def _run_cycle(cycle: int, *, progress: _SoakProgress) -> _CycleResult:
    runtime_thread = threading.get_ident()
    ledger = _ResourceLedger(cycle, progress)
    owners: list[Owner] = []
    callback_labels: list[str] = []
    callback_threads: list[int] = []
    callbacks_posted = 0
    workers_joined = 0
    base = cycle * 100

    tick = signal(base)
    items = signal((0, 1, 2))
    visible = signal(False)
    fail_activation = signal(True)

    def track_owner() -> Owner:
        owner = current_owner()
        if owner is None:
            raise RuntimeSoakError("component rendered without an owner")
        owners.append(owner)
        progress.owners_observed += 1
        return owner

    @component
    def Item(item_id: int) -> Node:
        track_owner()
        on_cleanup(ledger.acquire(f"item:{item_id}"))
        return Text(f"item:{item_id}")

    @component
    def Fallback() -> Node:
        track_owner()
        on_cleanup(ledger.acquire("fallback"))
        return Text("fallback")

    @component
    def ActiveBranch() -> Node:
        track_owner()
        on_cleanup(ledger.acquire("active-branch"))

        def activate() -> None:
            if fail_activation.value:
                raise _ExpectedActivationFailure("expected activation failure")

        on_mount(activate)
        return Text("active")

    @component
    def SoakRoot() -> Node:
        track_owner()
        on_cleanup(ledger.acquire("root"))

        def observe_tick() -> Callable[[], None]:
            value = tick.value
            return ledger.acquire(f"effect:{value}")

        effect(observe_tick)
        return VStack(
            Text(tick),
            Show(ActiveBranch(), when=visible, fallback=Fallback()),
            For(each=items, key=lambda item: item, children=Item),
        )

    mounted = mount(SoakRoot())
    app = _MountedSoakApp(mounted, tick)
    state = _LivePreviewState(
        app,
        LivePreviewConfig(
            title="Runtime soak",
            css_route="/runtime-soak.css",
            css_path=ROOT / "preview" / "runtime-soak.css",
        ),
    )

    _assert_branch(mounted, "fallback")
    _require(tick.value == base, f"cycle {cycle}: initial signal changed")
    ledger.assert_phase(
        f"cycle {cycle} post-mount",
        active=(
            "root",
            "fallback",
            "item:0",
            "item:1",
            "item:2",
            f"effect:{base}",
        ),
        acquired=6,
        released=0,
    )
    _assert_owner_states(cycle, "post-mount", owners, mounted=5, disposed=0)

    def enqueue(label: str, action: Callable[[], None]) -> None:
        nonlocal callbacks_posted

        def callback() -> None:
            callback_labels.append(label)
            callback_threads.append(threading.get_ident())
            progress.callbacks_run += 1
            action()

        state.posted_callbacks.post(callback)
        callbacks_posted += 1
        progress.callbacks_posted += 1

    foreign_errors: list[Exception] = []

    first_posted = threading.Event()
    second_posted = threading.Event()

    def enqueue_failure_wave_first() -> None:
        try:
            tick.set(-1)
        except Exception as exc:
            foreign_errors.append(exc)
        enqueue("tick-1", lambda: tick.set(base + 1))
        first_posted.set()
        _wait_for_event(second_posted, cycle=cycle, label="second failure-wave worker")
        enqueue("branch-failure", lambda: visible.set(True))
        enqueue("tick-after-failure", lambda: tick.set(base + 2))
        enqueue(
            "post-during-drain",
            lambda: enqueue("nested-after-drain", lambda: None),
        )

    def enqueue_failure_wave_second() -> None:
        _wait_for_event(first_posted, cycle=cycle, label="first failure-wave worker")
        enqueue("items-1", lambda: items.set((2, 0, 3)))
        second_posted.set()

    joined = _run_workers(
        cycle,
        0,
        (enqueue_failure_wave_first, enqueue_failure_wave_second),
        progress=progress,
    )
    workers_joined += joined
    _require(
        len(foreign_errors) == 1 and isinstance(foreign_errors[0], ReactiveThreadError),
        f"cycle {cycle}: direct foreign-thread mutation was not rejected exactly once",
    )
    _require(tick.value == base, f"cycle {cycle}: rejected foreign mutation changed state")

    try:
        state.render_page()
    except _ExpectedActivationFailure:
        pass
    else:
        raise RuntimeSoakError(f"cycle {cycle}: activation failure did not reach the host")

    _require(
        callback_labels
        == [
            "tick-1",
            "items-1",
            "branch-failure",
            "tick-after-failure",
            "post-during-drain",
        ],
        f"cycle {cycle}: callback order/work was lost after failure: {callback_labels}",
    )
    _require(
        all(thread_id == runtime_thread for thread_id in callback_threads),
        f"cycle {cycle}: a posted callback ran outside the runtime thread",
    )
    _require(tick.value == base + 2, f"cycle {cycle}: later callback did not run")
    _require(items.value == (2, 0, 3), f"cycle {cycle}: keyed update was lost")
    _require(visible.value is False, f"cycle {cycle}: failed branch did not roll back")
    _assert_branch(mounted, "fallback")
    ledger.assert_phase(
        f"cycle {cycle} post-rollback",
        active=(
            "root",
            "fallback",
            "item:0",
            "item:2",
            "item:3",
            f"effect:{base + 2}",
        ),
        acquired=10,
        released=4,
    )
    _assert_owner_states(cycle, "post-rollback", owners, mounted=5, disposed=2)
    _require(
        drain_posted(queue=state.posted_callbacks) == 1,
        f"cycle {cycle}: callback posted during drain was not deferred exactly once",
    )
    _require(
        callback_labels[-1] == "nested-after-drain",
        f"cycle {cycle}: nested callback was lost",
    )
    ledger.assert_phase(
        f"cycle {cycle} post-nested-drain",
        active=(
            "root",
            "fallback",
            "item:0",
            "item:2",
            "item:3",
            f"effect:{base + 2}",
        ),
        acquired=10,
        released=4,
    )
    _require(
        drain_posted(queue=state.posted_callbacks) == 0,
        f"cycle {cycle}: failure wave left callbacks queued",
    )

    recovery_ready = threading.Event()

    def enqueue_recovery_first() -> None:
        enqueue("disable-failure", lambda: fail_activation.set(False))
        recovery_ready.set()

    def enqueue_recovery_second() -> None:
        _wait_for_event(recovery_ready, cycle=cycle, label="recovery worker")
        enqueue("branch-recovery", lambda: visible.set(True))
        enqueue("items-2", lambda: items.set((3, 4)))

    joined = _run_workers(
        cycle,
        1,
        (enqueue_recovery_first, enqueue_recovery_second),
        progress=progress,
    )
    workers_joined += joined
    response = state.dispatch_payload(
        {
            "id": "increment",
            "args": [],
            "clientId": f"soak-{cycle}",
            "sequence": 1,
        }
    )

    _require(response["ok"] is True, f"cycle {cycle}: live recovery event failed")
    _require(response["stale"] is False, f"cycle {cycle}: live recovery event was stale")
    _require("active" in response["html"], f"cycle {cycle}: recovered HTML is stale")
    _require(
        callback_labels[-3:] == ["disable-failure", "branch-recovery", "items-2"],
        f"cycle {cycle}: recovery callbacks ran out of order",
    )
    _require(
        all(thread_id == runtime_thread for thread_id in callback_threads),
        f"cycle {cycle}: recovery ran outside the runtime thread",
    )
    _require(tick.value == base + 3, f"cycle {cycle}: live event update was lost")
    _require(items.value == (3, 4), f"cycle {cycle}: recovery list update was lost")
    _require(visible.value is True, f"cycle {cycle}: branch did not recover")
    _assert_branch(mounted, "active")
    ledger.assert_phase(
        f"cycle {cycle} post-reorder",
        active=(
            "root",
            "active-branch",
            "item:3",
            "item:4",
            f"effect:{base + 3}",
        ),
        acquired=13,
        released=8,
    )
    _assert_owner_states(cycle, "post-reorder", owners, mounted=4, disposed=5)
    ledger.assert_phase(
        f"cycle {cycle} pre-unmount",
        active=(
            "root",
            "active-branch",
            "item:3",
            "item:4",
            f"effect:{base + 3}",
        ),
        acquired=13,
        released=8,
    )

    state.posted_callbacks.close()
    _require(
        state.posted_callbacks.closed,
        f"cycle {cycle}: posted callback queue did not close",
    )
    try:
        state.posted_callbacks.post(lambda: None)
    except RuntimeError:
        pass
    else:
        raise RuntimeSoakError(
            f"cycle {cycle}: closed posted callback queue accepted late work"
        )

    app.dispose()
    ledger.assert_phase(
        f"cycle {cycle} post-unmount",
        active=(),
        acquired=13,
        released=13,
    )
    app.dispose()
    ledger.assert_phase(
        f"cycle {cycle} post-idempotent-unmount",
        active=(),
        acquired=13,
        released=13,
    )
    _require(not ledger.active, f"cycle {cycle}: resources leaked: {sorted(ledger.active)}")
    _require(
        ledger.acquired == ledger.released,
        f"cycle {cycle}: resource acquire/release counts differ",
    )
    _require(
        all(owner.state is OwnerState.DISPOSED for owner in owners),
        f"cycle {cycle}: an owner did not reach disposed state",
    )
    _assert_owner_states(cycle, "post-unmount", owners, mounted=0, disposed=9)
    for source_name, source in (
        ("tick", tick),
        ("items", items),
        ("visible", visible),
        ("fail_activation", fail_activation),
    ):
        _require(
            not source._subscribers,
            f"cycle {cycle}: {source_name} retained reactive subscribers",
        )
    _require(
        drain_posted(queue=state.posted_callbacks) == 0,
        f"cycle {cycle}: shutdown left callbacks queued",
    )
    _require(
        callbacks_posted == len(callback_labels),
        f"cycle {cycle}: posted/run callback counts differ",
    )

    owner_refs = tuple(weakref.ref(owner) for owner in owners)
    owners_observed = len(owners)
    owners.clear()
    result = _CycleResult(
        callbacks_posted=callbacks_posted,
        callbacks_run=len(callback_labels),
        owners_observed=owners_observed,
        resources_acquired=ledger.acquired,
        resources_released=ledger.released,
        worker_threads_joined=workers_joined,
        owner_refs=owner_refs,
    )
    del app, mounted
    return result


def _assert_branch(mounted: MountedNode, expected: str) -> None:
    root = root_widget(mounted)
    branch_control = root.children[1]
    _require(len(branch_control.children) == 1, "Show did not expose exactly one branch")
    actual = branch_control.children[0].props.get("content")
    _require(actual == expected, f"expected branch {expected!r}, got {actual!r}")


def _assert_owner_states(
    cycle: int,
    phase: str,
    owners: list[Owner],
    *,
    mounted: int,
    disposed: int,
) -> None:
    states = Counter(owner.state for owner in owners)
    _require(
        states[OwnerState.MOUNTED] == mounted,
        f"cycle {cycle} {phase}: expected {mounted} mounted owners, "
        f"got {states[OwnerState.MOUNTED]}",
    )
    _require(
        states[OwnerState.DISPOSED] == disposed,
        f"cycle {cycle} {phase}: expected {disposed} disposed owners, "
        f"got {states[OwnerState.DISPOSED]}",
    )
    _require(
        len(owners) == mounted + disposed,
        f"cycle {cycle} {phase}: owners remained in a transitional state",
    )


def _wait_for_event(event: threading.Event, *, cycle: int, label: str) -> None:
    _require(
        event.wait(timeout=WATCHDOG_SECONDS),
        f"cycle {cycle}: timed out waiting for {label}",
    )


def _run_workers(
    cycle: int,
    wave: int,
    targets: tuple[Callable[[], None], ...],
    *,
    progress: _SoakProgress | None = None,
) -> int:
    errors: list[BaseException] = []
    errors_lock = threading.Lock()

    def guarded_target(target: Callable[[], None]) -> None:
        try:
            target()
        except BaseException as exc:
            with errors_lock:
                errors.append(exc)

    workers = [
        threading.Thread(
            target=guarded_target,
            args=(target,),
            name=f"{WORKER_NAME_PREFIX}{cycle}-{wave}-{index}",
            daemon=True,
        )
        for index, target in enumerate(targets)
    ]
    for worker in workers:
        worker.start()

    deadline = monotonic() + WATCHDOG_SECONDS
    for worker in workers:
        worker.join(timeout=max(0.0, deadline - monotonic()))
    alive = [worker.name for worker in workers if worker.is_alive()]
    joined = len(workers) - len(alive)
    if progress is not None:
        progress.worker_threads_joined += joined
    _require(not alive, f"cycle {cycle}: workers did not terminate: {alive}")
    if errors:
        raise errors[0]
    return joined


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeSoakError(message)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run deterministic Otoe runtime/thread/host lifecycle soak checks."
    )
    parser.add_argument("--cycles", type=int, default=1_000)
    parser.add_argument("--host-cycles", type=int, default=DEFAULT_HOST_CYCLES)
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=DEFAULT_PROCESS_TIMEOUT_SECONDS,
    )
    parser.add_argument("--_worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--_progress-path", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args._worker:
        return _worker_main(
            cycles=args.cycles,
            host_cycles=args.host_cycles,
            progress_path=args._progress_path,
        )
    try:
        return _supervise_cli(
            cycles=args.cycles,
            host_cycles=args.host_cycles,
            timeout_seconds=args.timeout_seconds,
        )
    except (KeyboardInterrupt, SystemExit):
        raise
    except BaseException as exc:
        detail = _exception_detail(exc)
        result = _SoakProgress(
            cycles=args.cycles,
            host_cycles=args.host_cycles,
        ).result(failures=(detail,))
        _print_result(result.as_json_value())
        return 1


def _worker_main(
    *,
    cycles: int,
    host_cycles: int,
    progress_path: Path | None,
) -> int:
    progress = _SoakProgress(
        cycles=cycles,
        host_cycles=host_cycles,
        progress_path=progress_path,
    )

    try:
        result = run_runtime_soak(
            cycles=cycles,
            host_cycles=host_cycles,
            _progress=progress,
        )
    except BaseException as exc:
        detail = _exception_detail(exc)
        result = progress.result(failures=(detail,))
        progress.checkpoint(failures=(detail,))
        _print_result(result.as_json_value())
        if isinstance(exc, (KeyboardInterrupt, SystemExit)):
            raise
        return 1

    _print_result(result.as_json_value())
    return 0


def _supervise_cli(
    *,
    cycles: int,
    host_cycles: int,
    timeout_seconds: float,
) -> int:
    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be > 0")

    started_at = monotonic()
    with tempfile.TemporaryDirectory(prefix="otoe-runtime-soak-") as temporary:
        progress_path = Path(temporary) / "progress.json"
        command = [
            sys.executable,
            str(Path(__file__).resolve()),
            "--_worker",
            "--cycles",
            str(cycles),
            "--host-cycles",
            str(host_cycles),
            "--_progress-path",
            str(progress_path),
        ]
        process = subprocess.Popen(
            command,
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            stdout, stderr = process.communicate(timeout=timeout_seconds)
        except subprocess.TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate()
            payload = _load_progress_payload(
                progress_path,
                cycles=cycles,
                host_cycles=host_cycles,
            )
            payload["elapsed_seconds"] = max(0.0, monotonic() - started_at)
            payload["counter_scope"] = "last-persisted-checkpoint"
            _append_failure(
                payload,
                f"TimeoutError: soak exceeded {timeout_seconds:g} seconds; child terminated",
            )
            _print_result(payload)
            return 1
        except (KeyboardInterrupt, SystemExit):
            process.kill()
            process.wait()
            raise

        try:
            payload = _json_object(stdout)
        except (json.JSONDecodeError, TypeError, ValueError):
            payload = _load_progress_payload(
                progress_path,
                cycles=cycles,
                host_cycles=host_cycles,
            )
            diagnostic = stderr.strip()[-500:]
            detail = f": {diagnostic}" if diagnostic else ""
            _append_failure(
                payload,
                f"ChildProcessError: soak emitted invalid JSON{detail}",
            )

        if process.returncode != 0 and not payload.get("failures"):
            _append_failure(
                payload,
                f"ChildProcessError: soak worker exited with {process.returncode}",
            )
        _print_result(payload)
        return 0 if process.returncode == 0 and not payload.get("failures") else 1


def _load_progress_payload(
    path: Path,
    *,
    cycles: int,
    host_cycles: int,
) -> dict[str, Any]:
    try:
        return _json_object(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, json.JSONDecodeError, TypeError, ValueError):
        return _SoakProgress(
            cycles=cycles,
            host_cycles=host_cycles,
        ).result().as_json_value()


def _json_object(value: str) -> dict[str, Any]:
    parsed: object = json.loads(value)
    if not isinstance(parsed, dict):
        raise TypeError("soak JSON must be an object")
    return {str(key): item for key, item in parsed.items()}


def _append_failure(payload: dict[str, Any], detail: str) -> None:
    failures = payload.get("failures")
    if not isinstance(failures, list):
        failures = []
        payload["failures"] = failures
    failures.append(detail)


def _exception_detail(exc: BaseException) -> str:
    return f"{type(exc).__name__}: {exc}" if str(exc) else type(exc).__name__


def _print_result(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True), flush=True)


if __name__ == "__main__":
    raise SystemExit(main())
