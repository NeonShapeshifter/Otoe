from __future__ import annotations

import asyncio
import inspect
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any, Callable

from .errors import EventHandlerArityError


@dataclass(frozen=True)
class EventSignature:
    parameters: tuple[str, ...] = ()
    description: str = ""

    def __str__(self) -> str:
        return f"({', '.join(self.parameters)})"


def dispatch_event(
    handler: Callable[..., Any],
    *args: Any,
    context: str | None = None,
    event_signature: EventSignature | None = None,
) -> Any:
    _validate_handler_args(
        handler,
        args,
        context=context,
        event_signature=event_signature,
    )
    if inspect.iscoroutinefunction(handler):
        return _schedule_coroutine(handler(*args))

    result = handler(*args)
    if asyncio.iscoroutine(result):
        return _schedule_coroutine(result)
    return result


def event_signature_for(tag: Any, event_name: str) -> EventSignature | None:
    signatures = getattr(tag, "event_signatures", {})
    signature = signatures.get(event_name)
    return signature if isinstance(signature, EventSignature) else None


def format_event_signature(event_name: str, signature: EventSignature | None) -> str:
    return f"{event_name}{signature or EventSignature()}"


def format_event_catalog(
    events: Iterable[str],
    signatures: Mapping[str, EventSignature],
) -> str:
    return ", ".join(
        format_event_signature(name, signatures.get(name)) for name in sorted(events)
    )


def _validate_handler_args(
    handler: Callable[..., Any],
    args: tuple[Any, ...],
    *,
    context: str | None,
    event_signature: EventSignature | None,
) -> None:
    try:
        signature = inspect.signature(handler)
    except (TypeError, ValueError):
        return
    try:
        signature.bind(*args)
    except TypeError as exc:
        event_label = (
            f"{context}{event_signature}"
            if context is not None and event_signature is not None
            else context
        )
        subject = f"{event_label} handler" if event_label is not None else "Event handler"
        raise EventHandlerArityError(
            f"{subject} {_handler_name(handler)} expected {signature}; "
            f"got {len(args)} argument(s)."
        ) from exc


def _handler_name(handler: Callable[..., Any]) -> str:
    return getattr(handler, "__name__", getattr(handler, "__qualname__", repr(handler)))


def _schedule_coroutine(coro: Any) -> Any:
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    return loop.create_task(coro)
