from __future__ import annotations

from typing import Any

from ._native_shared import walk_widgets, widget_by_path, widget_context
from .mount import FakeWidget


def enabled_input_widget(
    root: FakeWidget,
    path: tuple[int, ...] | None,
) -> FakeWidget:
    if path is None:
        raise KeyError("NativeSurface has no focused input for text entry.")
    try:
        widget = widget_by_path(root, path)
    except KeyError as exc:
        raise KeyError(
            f"No enabled native input exists at path {path!r}: "
            "no native widget exists at that path."
        ) from exc
    if widget.name != "Input":
        raise KeyError(
            f"No enabled native input exists at path {path!r}: "
            f"{widget_context(widget)} is {widget.name}, not Input."
        )
    if widget.props.get("disabled"):
        raise KeyError(
            f"No enabled native input exists at path {path!r}: "
            f"{widget_context(widget)} is disabled."
        )
    return widget


def trigger_path_event(
    root: FakeWidget,
    path: tuple[int, ...],
    event: str,
    *args: Any,
) -> Any:
    try:
        widget = widget_by_path(root, path)
    except KeyError:
        return None
    if event not in widget.events:
        return None
    return widget.trigger(event, *args)


def trigger_global_key_down(root: FakeWidget, payload: dict[str, Any]) -> Any:
    for widget in walk_widgets(root):
        if "onGlobalKeyDown" in widget.events:
            return widget.trigger("onGlobalKeyDown", payload)
    return None


def should_send_global_key(
    root: FakeWidget,
    focused_path: tuple[int, ...] | None,
    key: str,
    *,
    shift: bool,
    ctrl: bool,
    meta: bool,
    alt: bool,
) -> bool:
    has_global = any("onGlobalKeyDown" in widget.events for widget in walk_widgets(root))
    if not has_global:
        return False
    if ctrl or meta or key == "Escape":
        return True
    if len(key) != 1:
        return False
    if focused_path is None:
        return True
    focused = widget_by_path(root, focused_path)
    if focused.name == "Input":
        return False
    return True


def global_key_payload(
    key: str,
    *,
    shift: bool,
    ctrl: bool,
    meta: bool,
    alt: bool,
) -> dict[str, Any]:
    return {
        "key": key,
        "ctrlKey": ctrl,
        "metaKey": meta,
        "altKey": alt,
        "shiftKey": shift,
    }


def should_activate_button_with_key(widget: FakeWidget, key: str) -> bool:
    return widget.name == "Button" and key in {"Enter", " ", "Spacebar"}
