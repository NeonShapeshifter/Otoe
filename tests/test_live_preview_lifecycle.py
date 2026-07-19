import ast
from importlib import import_module
from pathlib import Path

import pytest

import examples.live_counter as live_counter_module
import examples.saas.live_preview as saas_live_preview_module
import examples.wraith.live_preview as wraith_live_preview_module
from examples.live_counter import CounterPreview
from examples.saas.live_preview import SaaSLivePreview
from examples.wraith.live_preview import WraithLivePreview
from otoe.mount import MountedNode
from otoe.owner import Owner, OwnerState
from otoe.reactive import Computed, ReactiveValue


ROOT = Path(__file__).resolve().parents[1]
_PREVIEW_METHODS = {"render_fragment", "dispatch_event"}


def _shipped_live_preview_factories() -> tuple[type, ...]:
    factories: list[type] = []
    for path in sorted((ROOT / "examples").rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        class_names = []
        for node in tree.body:
            if not isinstance(node, ast.ClassDef):
                continue
            methods = {
                child.name
                for child in node.body
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
            }
            if _PREVIEW_METHODS <= methods:
                class_names.append(node.name)
        if not class_names:
            continue

        module_name = ".".join(path.relative_to(ROOT).with_suffix("").parts)
        module = import_module(module_name)
        for class_name in class_names:
            factory = getattr(module, class_name)
            assert isinstance(factory, type)
            factories.append(factory)

    assert factories
    return tuple(factories)


@pytest.mark.parametrize(
    "factory",
    _shipped_live_preview_factories(),
    ids=lambda factory: f"{factory.__module__}.{factory.__name__}",
)
def test_live_preview_dispose_is_complete_and_idempotent(factory):
    preview = factory()
    rendered = preview.render_fragment()
    mounted = [
        value for value in vars(preview).values() if isinstance(value, MountedNode)
    ]
    owners = [owner for root in mounted for owner in _owners(root)]
    reactive_values = [
        value
        for value in vars(preview).values()
        if isinstance(value, ReactiveValue)
    ]

    assert isinstance(rendered, str)
    assert rendered.strip()

    dispose = getattr(preview, "dispose", None)
    assert callable(dispose)
    dispose()
    dispose()

    assert owners
    assert all(owner.state is OwnerState.DISPOSED for owner in owners)
    assert all(not value._subscribers for value in reactive_values)
    assert all(not value._deps for value in reactive_values if isinstance(value, Computed))


def test_saas_live_preview_dispose_attempts_every_cleanup(monkeypatch):
    calls = []
    preview = object.__new__(SaaSLivePreview)
    preview.app = object()
    preview.filtered_customers = _FailingDisposable(
        "customers",
        calls,
        SystemExit("customers failed"),
    )
    preview.filtered_deals = _FailingDisposable("deals", calls)
    preview.workspace = _FailingDisposable("workspace", calls)

    def fail_unmount(mounted):
        assert mounted is preview.app
        calls.append("app")
        raise KeyboardInterrupt("app failed")

    monkeypatch.setattr(saas_live_preview_module, "unmount", fail_unmount)

    with pytest.raises(BaseExceptionGroup) as caught:
        preview.dispose()

    assert calls == ["app", "customers", "deals", "workspace"]
    assert [str(error) for error in caught.value.exceptions] == [
        "app failed",
        "customers failed",
    ]
    assert preview._disposed is True

    preview.dispose()
    assert calls == ["app", "customers", "deals", "workspace"]


def test_wraith_live_preview_dispose_attempts_every_cleanup(monkeypatch):
    calls = []
    preview = object.__new__(WraithLivePreview)
    preview.arsenal = object()
    preview.status = object()
    preview.topbar = object()
    preview.page_label = _FailingDisposable("page-label", calls)
    preview.visible_missions = _FailingDisposable(
        "visible-missions",
        calls,
        SystemExit("missions failed"),
    )

    mounts = {
        id(preview.arsenal): "arsenal",
        id(preview.status): "status",
        id(preview.topbar): "topbar",
    }

    def sometimes_fail_unmount(mounted):
        label = mounts[id(mounted)]
        calls.append(label)
        if label == "status":
            raise KeyboardInterrupt("status failed")

    monkeypatch.setattr(wraith_live_preview_module, "unmount", sometimes_fail_unmount)

    with pytest.raises(BaseExceptionGroup) as caught:
        preview.dispose()

    assert calls == [
        "arsenal",
        "status",
        "topbar",
        "page-label",
        "visible-missions",
    ]
    assert [str(error) for error in caught.value.exceptions] == [
        "status failed",
        "missions failed",
    ]
    assert preview._disposed is True

    preview.dispose()
    assert calls == [
        "arsenal",
        "status",
        "topbar",
        "page-label",
        "visible-missions",
    ]


def test_saas_live_preview_computed_construction_failure_cleans_partial_state(
    monkeypatch,
):
    calls = []
    preview = object.__new__(SaaSLivePreview)
    workspace = _FailingDisposable("workspace", calls)
    primary_error = KeyboardInterrupt("computed construction failed")
    computed_calls = 0

    def fail_second_computed(fn):
        nonlocal computed_calls
        computed_calls += 1
        if computed_calls == 1:
            return workspace
        raise primary_error

    monkeypatch.setattr(saas_live_preview_module, "computed", fail_second_computed)

    with pytest.raises(KeyboardInterrupt) as caught:
        SaaSLivePreview.__init__(preview)

    assert caught.value is primary_error
    assert calls == ["workspace"]
    assert preview._disposed is True

    preview.dispose()
    assert calls == ["workspace"]


def test_saas_live_preview_mount_failure_disposes_all_computeds(monkeypatch):
    calls = []
    preview = object.__new__(SaaSLivePreview)
    computeds = [
        _FailingDisposable("workspace", calls),
        _FailingDisposable("filtered-deals", calls),
        _FailingDisposable("filtered-customers", calls),
    ]
    primary_error = KeyboardInterrupt("app mount interrupted")

    def fake_computed(fn):
        return computeds.pop(0)

    def interrupt_mount(node):
        raise primary_error

    monkeypatch.setattr(saas_live_preview_module, "computed", fake_computed)
    monkeypatch.setattr(saas_live_preview_module, "mount", interrupt_mount)

    with pytest.raises(KeyboardInterrupt) as caught:
        SaaSLivePreview.__init__(preview)

    assert caught.value is primary_error
    assert calls == ["filtered-customers", "filtered-deals", "workspace"]
    assert preview._disposed is True

    preview.dispose()
    assert calls == ["filtered-customers", "filtered-deals", "workspace"]


def test_wraith_live_preview_computed_failure_cleans_partial_state(monkeypatch):
    calls = []
    preview = object.__new__(WraithLivePreview)
    visible_missions = _FailingDisposable("visible-missions", calls)
    primary_error = SystemExit("page label construction failed")
    computed_calls = 0

    def fail_second_computed(fn):
        nonlocal computed_calls
        computed_calls += 1
        if computed_calls == 1:
            return visible_missions
        raise primary_error

    monkeypatch.setattr(wraith_live_preview_module, "computed", fail_second_computed)

    with pytest.raises(SystemExit) as caught:
        WraithLivePreview.__init__(preview)

    assert caught.value is primary_error
    assert calls == ["visible-missions"]
    assert preview._disposed is True

    preview.dispose()
    assert calls == ["visible-missions"]


def test_wraith_live_preview_mount_failure_preserves_cleanup_failures(monkeypatch):
    calls = []
    preview = object.__new__(WraithLivePreview)
    cleanup_error = SystemExit("computed cleanup failed")
    computeds = [
        _FailingDisposable("visible-missions", calls, cleanup_error),
        _FailingDisposable("page-label", calls),
    ]
    topbar = object()
    status = object()
    primary_error = RuntimeError("arsenal mount failed")
    unmount_error = KeyboardInterrupt("topbar cleanup failed")
    mount_calls = 0

    def fake_computed(fn):
        return computeds.pop(0)

    def fail_third_mount(node):
        nonlocal mount_calls
        mount_calls += 1
        if mount_calls == 1:
            return topbar
        if mount_calls == 2:
            return status
        raise primary_error

    def fail_unmount(mounted):
        if mounted is status:
            calls.append("status")
            return
        assert mounted is topbar
        calls.append("topbar")
        raise unmount_error

    monkeypatch.setattr(wraith_live_preview_module, "computed", fake_computed)
    monkeypatch.setattr(wraith_live_preview_module, "mount", fail_third_mount)
    monkeypatch.setattr(wraith_live_preview_module, "unmount", fail_unmount)

    with pytest.raises(BaseExceptionGroup) as caught:
        WraithLivePreview.__init__(preview)

    assert caught.value.exceptions == (
        primary_error,
        unmount_error,
        cleanup_error,
    )
    assert calls == ["status", "topbar", "page-label", "visible-missions"]
    assert preview._disposed is True

    preview.dispose()
    assert calls == ["status", "topbar", "page-label", "visible-missions"]


def test_counter_preview_interrupted_mount_releases_computed_dependencies(
    monkeypatch,
):
    preview = object.__new__(CounterPreview)
    primary_error = KeyboardInterrupt("counter mount interrupted")
    cleanup_error = SystemExit("count label cleanup failed")
    original_dispose = Computed.dispose

    def interrupt_mount(node):
        count_label = node.props["kwargs"]["count_label"]
        assert count_label.value == "Count: 0"
        raise primary_error

    def dispose_then_fail(computed):
        original_dispose(computed)
        raise cleanup_error

    monkeypatch.setattr(live_counter_module, "mount", interrupt_mount)
    monkeypatch.setattr(Computed, "dispose", dispose_then_fail)

    with pytest.raises(BaseExceptionGroup) as caught:
        CounterPreview.__init__(preview)

    assert caught.value.exceptions == (primary_error, cleanup_error)
    assert preview._disposed is True
    assert preview.count_label._deps == {}
    assert preview.count._subscribers == {}

    preview.dispose()
    assert preview.count_label._deps == {}
    assert preview.count._subscribers == {}


def _owners(mounted: MountedNode) -> list[Owner]:
    owners = [mounted.owner] if mounted.owner is not None else []
    for child in mounted.children:
        owners.extend(_owners(child))
    return owners


class _FailingDisposable:
    def __init__(self, label, calls, error=None):
        self._label = label
        self._calls = calls
        self._error = error

    def dispose(self):
        self._calls.append(self._label)
        if self._error is not None:
            raise self._error
