from __future__ import annotations

import asyncio
import inspect
from typing import Any, Callable


def dispatch_event(handler: Callable[..., Any], *args: Any) -> Any:
    if inspect.iscoroutinefunction(handler):
        return _schedule_coroutine(handler(*args))

    result = handler(*args)
    if asyncio.iscoroutine(result):
        return _schedule_coroutine(result)
    return result


def _schedule_coroutine(coro: Any) -> Any:
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    return loop.create_task(coro)

