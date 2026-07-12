from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Protocol


class Disposable(Protocol):
    def dispose(self) -> None: ...


CURRENT_OWNER: ContextVar["Owner | None"] = ContextVar("otoe_current_owner", default=None)
CURRENT_MOUNT_PHASE: ContextVar[str | None] = ContextVar(
    "otoe_current_mount_phase",
    default=None,
)


class OwnerState(Enum):
    CREATED = "created"
    MOUNTING = "mounting"
    MOUNTED = "mounted"
    DISPOSING = "disposing"
    DISPOSED = "disposed"


@dataclass
class Owner:
    name: str
    cleanups: list[Callable[[], None]] = field(default_factory=list)
    mount_callbacks: list[Callable[[], None]] = field(default_factory=list)
    pending_effects: list[Disposable] = field(default_factory=list)
    disposables: list[Disposable] = field(default_factory=list)
    state: OwnerState = OwnerState.CREATED

    @property
    def disposed(self) -> bool:
        return self.state is OwnerState.DISPOSED

    def add_cleanup(self, callback: Callable[[], None]) -> None:
        if self.state in {OwnerState.DISPOSING, OwnerState.DISPOSED}:
            callback()
            return
        self.cleanups.append(callback)

    def add_mount_callback(self, callback: Callable[[], None]) -> None:
        if self.state in {OwnerState.DISPOSING, OwnerState.DISPOSED}:
            raise RuntimeError(f"{self.name}: cannot register on_mount after disposal.")
        self.mount_callbacks.append(callback)

    def add_disposable(self, disposable: Disposable) -> None:
        if self.state in {OwnerState.DISPOSING, OwnerState.DISPOSED}:
            disposable.dispose()
            return
        self.disposables.append(disposable)

    def add_pending_effect(self, effect: Disposable) -> None:
        if self.state in {OwnerState.DISPOSING, OwnerState.DISPOSED}:
            effect.dispose()
            return
        self.pending_effects.append(effect)

    def run_mount(self) -> None:
        if self.state is OwnerState.MOUNTED:
            return
        if self.state is not OwnerState.CREATED:
            raise RuntimeError(
                f"{self.name}: cannot mount owner while state is {self.state.value!r}."
            )

        self.state = OwnerState.MOUNTING
        token = CURRENT_OWNER.set(self)
        try:
            self._drain_pending_effects()
            while self.mount_callbacks and self.state is OwnerState.MOUNTING:
                callbacks = list(self.mount_callbacks)
                self.mount_callbacks.clear()
                for callback in callbacks:
                    if self.state is not OwnerState.MOUNTING:
                        break
                    callback()
                if self.state is OwnerState.MOUNTING:
                    self._drain_pending_effects()
        except Exception:
            raise
        else:
            if self.state is OwnerState.MOUNTING:
                self.state = OwnerState.MOUNTED
        finally:
            CURRENT_OWNER.reset(token)

    def _drain_pending_effects(self) -> None:
        while self.pending_effects:
            effects = list(self.pending_effects)
            self.pending_effects.clear()
            for effect in effects:
                if self.state is not OwnerState.MOUNTING:
                    break
                run = getattr(effect, "run", None)
                if run is not None:
                    run()

    def dispose(self) -> None:
        if self.state in {OwnerState.DISPOSING, OwnerState.DISPOSED}:
            return
        self.state = OwnerState.DISPOSING

        cleanups = list(reversed(self.cleanups))
        self.cleanups.clear()
        disposables = list(reversed(self.disposables))
        self.disposables.clear()
        self.pending_effects.clear()
        self.mount_callbacks.clear()

        errors: list[Exception] = []
        for callback in cleanups:
            try:
                callback()
            except Exception as exc:
                errors.append(exc)

        for disposable in disposables:
            try:
                disposable.dispose()
            except Exception as exc:
                errors.append(exc)

        self.state = OwnerState.DISPOSED
        if errors:
            raise ExceptionGroup(f"{self.name}: errors while disposing owner.", errors)


def current_owner() -> Owner | None:
    return CURRENT_OWNER.get()


def current_mount_phase() -> str | None:
    return CURRENT_MOUNT_PHASE.get()
