from __future__ import annotations

from typing import Any

from .node import Node
from .reactive import computed, is_reactive
from .widgets import Text, VStack


def class_names(*parts: Any) -> str:
    names: list[str] = []
    for part in parts:
        if not part:
            continue
        names.extend(str(part).split())
    return " ".join(dict.fromkeys(names))


def _active_class(base: str, active, extra: str | None):
    if is_reactive(active):
        return computed(lambda: class_names(base, extra, "is-active" if active.value else None))
    return class_names(base, extra, "is-active" if active else None)


def _variant_class(base: str, variant, extra: str | None = None):
    if is_reactive(variant) or is_reactive(extra):
        return computed(lambda: class_names(base, f"is-{_value(variant)}", _value(extra)))
    return class_names(base, f"is-{variant}", extra)


def _multi_variant_class(base: str, variant, size, extra: str | None = None):
    if is_reactive(variant) or is_reactive(size) or is_reactive(extra):
        return computed(
            lambda: class_names(
                base,
                f"is-{_value(variant)}",
                f"is-{_value(size)}",
                _value(extra),
            )
        )
    return class_names(base, f"is-{variant}", f"is-{size}", extra)


def _state_class(base: str, *, active=False, disabled=False, extra: str | None = None):
    if is_reactive(active) or is_reactive(disabled) or is_reactive(extra):
        return computed(
            lambda: class_names(
                base,
                _value(extra),
                "is-active" if _value(active) else None,
                "is-disabled" if _value(disabled) else None,
            )
        )
    return class_names(
        base,
        extra,
        "is-active" if active else None,
        "is-disabled" if disabled else None,
    )


def _value(value):
    if is_reactive(value):
        return value.value
    return value


def _has_value(value: Any) -> bool:
    if is_reactive(value):
        return value.value is not None
    return value is not None


def _slot_node(value, className: str) -> Node:
    return VStack(_as_node(value), className=className)


def _as_node(value) -> Node:
    if isinstance(value, Node):
        return value
    return Text(value)


def _list_value(value) -> list[Any]:
    resolved = _value(value)
    if resolved is None:
        return []
    return list(resolved)
