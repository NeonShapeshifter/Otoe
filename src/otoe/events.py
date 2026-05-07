from __future__ import annotations

import asyncio
import inspect
from typing import Any, Callable

from .errors import EventHandlerError


def dispatch_event(handler: Callable[..., Any], *args: Any) -> Any:
    _validate_handler_args(handler, args)
    if inspect.iscoroutinefunction(handler):
        return _schedule_coroutine(handler(*args))

    result = handler(*args)
    if asyncio.iscoroutine(result):
        return _schedule_coroutine(result)
    return result


def _validate_handler_args(handler: Callable[..., Any], args: tuple[Any, ...]) -> None:
    try:
        signature = inspect.signature(handler)
    except (TypeError, ValueError):
        return
    try:
        signature.bind(*args)
    except TypeError as exc:
        raise EventHandlerError(
            f"Event handler {_handler_name(handler)} expected {signature}; "
            f"got {len(args)} argument(s)."
        ) from exc


def _handler_name(handler: Callable[..., Any]) -> str:
    return getattr(handler, "__qualname__", getattr(handler, "__name__", repr(handler)))


def _schedule_coroutine(coro: Any) -> Any:
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    return loop.create_task(coro)
