from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Callable, Protocol


class Disposable(Protocol):
    def dispose(self) -> None: ...


CURRENT_OWNER: ContextVar["Owner | None"] = ContextVar("otoe_current_owner", default=None)
CURRENT_MOUNT_PHASE: ContextVar[str | None] = ContextVar(
    "otoe_current_mount_phase",
    default=None,
)


@dataclass
class Owner:
    name: str
    cleanups: list[Callable[[], None]] = field(default_factory=list)
    mount_callbacks: list[Callable[[], None]] = field(default_factory=list)
    pending_effects: list[Disposable] = field(default_factory=list)
    disposables: list[Disposable] = field(default_factory=list)
    disposed: bool = False

    def add_cleanup(self, callback: Callable[[], None]) -> None:
        self.cleanups.append(callback)

    def add_mount_callback(self, callback: Callable[[], None]) -> None:
        self.mount_callbacks.append(callback)

    def add_disposable(self, disposable: Disposable) -> None:
        self.disposables.append(disposable)

    def add_pending_effect(self, effect: Disposable) -> None:
        self.pending_effects.append(effect)

    def run_mount(self) -> None:
        for effect in list(self.pending_effects):
            run = getattr(effect, "run", None)
            if run is not None:
                run()
        self.pending_effects.clear()

        for callback in list(self.mount_callbacks):
            callback()

    def dispose(self) -> None:
        if self.disposed:
            return
        self.disposed = True

        for callback in reversed(self.cleanups):
            callback()
        self.cleanups.clear()

        for disposable in reversed(self.disposables):
            disposable.dispose()
        self.disposables.clear()
        self.pending_effects.clear()


def current_owner() -> Owner | None:
    return CURRENT_OWNER.get()


def current_mount_phase() -> str | None:
    return CURRENT_MOUNT_PHASE.get()
