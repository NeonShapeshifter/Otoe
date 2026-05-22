from __future__ import annotations

from pathlib import Path
from typing import Any

from ._native_contracts import LayoutBox, NativeLayout, NativePaint
from ._native_hit_test import dispatch_native_click, hit_test_native
from ._native_layout import layout_native
from ._native_paint import paint_native
from ._native_png import write_native_png
from ._native_shared import (
    clamp_scroll_y,
    max_scroll_y,
    mounted_or_none,
    native_surface_target,
    scroll_y,
    surface_root_widget,
    tree_revision,
    visible_through_scroll_ancestors,
    walk_widgets,
    widget_by_path,
    widget_context,
)
from .mount import FakeWidget, MountedNode, mount, unmount
from .node import Node
from .style import StyleSheet


class NativeSurface:
    def __init__(
        self,
        target: Node | FakeWidget | MountedNode,
        *,
        stylesheet: StyleSheet | None = None,
        strict_styles: bool = True,
        background: str = "#ffffff",
    ) -> None:
        self.stylesheet = stylesheet
        self.strict_styles = strict_styles
        self.background = background
        self.frame = 0
        self.focused_path: tuple[int, ...] | None = None
        self._owns_mount = isinstance(target, Node)
        self._mounted = mount(target) if self._owns_mount else None
        self._target: FakeWidget | MountedNode = (
            self._mounted
            if self._mounted is not None
            else native_surface_target(target)
        )
        self._layout: NativeLayout | None = None
        self._paint: NativePaint | None = None
        self._tree_revision: tuple[Any, ...] | None = None
        self.refresh()
        self.focused_path = self._first_autofocus_path()
        if self.focused_path is not None:
            self._paint = paint_native(
                self.layout,
                background=self.background,
                focused_path=self.focused_path,
            )

    @property
    def mounted(self) -> MountedNode | None:
        return (
            self._mounted
            if self._mounted is not None
            else mounted_or_none(self._target)
        )

    @property
    def target(self) -> FakeWidget | MountedNode:
        return self._target

    @property
    def layout(self) -> NativeLayout:
        self._ensure_fresh()
        assert self._layout is not None
        return self._layout

    @property
    def paint(self) -> NativePaint:
        self._ensure_fresh()
        assert self._paint is not None
        return self._paint

    @property
    def focused_box(self) -> LayoutBox | None:
        if self.focused_path is None:
            return None
        try:
            return self.layout.by_path(self.focused_path)
        except KeyError:
            return None

    def refresh(self) -> NativePaint:
        self._layout = layout_native(
            self._target,
            stylesheet=self.stylesheet,
            strict_styles=self.strict_styles,
        )
        self._tree_revision = tree_revision(surface_root_widget(self._target))
        self._sync_focus_after_refresh()
        self._paint = paint_native(
            self._layout,
            background=self.background,
            focused_path=self.focused_path,
        )
        self.frame += 1
        return self._paint

    def render_png(self, path: str | Path) -> NativePaint:
        paint = self.refresh()
        write_native_png(paint, path)
        return paint

    def hit_test(
        self,
        x: int,
        y: int,
        *,
        event: str = "onClick",
    ) -> LayoutBox | None:
        return hit_test_native(self.layout, x, y, event=event)

    def click(self, x: int, y: int) -> Any:
        focus_hit = self._hit_test_focusable(x, y)
        if focus_hit is not None:
            self.focus(focus_hit.path)
        result = dispatch_native_click(self._target, self.layout, x, y)
        self.refresh()
        return result

    def focus(self, path: tuple[int, ...] | None) -> None:
        if path == self.focused_path:
            return
        if path is not None and not self._is_focusable_path(path):
            raise KeyError(self._focus_error_message(path))

        previous_path = self.focused_path
        self.focused_path = path
        if previous_path is not None:
            self._trigger_path_event(previous_path, "onBlur")
        if path is not None:
            self._trigger_path_event(path, "onFocus")
        self.refresh()

    def focus_next(self, *, reverse: bool = False) -> LayoutBox | None:
        focusable = self._focusable_paths()
        if not focusable:
            self.focus(None)
            return None

        if self.focused_path not in focusable:
            next_path = focusable[-1] if reverse else focusable[0]
        else:
            index = focusable.index(self.focused_path)
            step = -1 if reverse else 1
            next_path = focusable[(index + step) % len(focusable)]
        self.focus(next_path)
        return self.focused_box

    def key_down(
        self,
        key: str,
        *,
        shift: bool = False,
        ctrl: bool = False,
        meta: bool = False,
        alt: bool = False,
    ) -> Any:
        if key == "Tab":
            return self.focus_next(reverse=shift)

        if self.focused_path is None:
            self.focus_next()

        result = None
        if self.focused_path is not None:
            result = self._trigger_path_event(self.focused_path, "onKeyDown", key)
            widget = widget_by_path(
                surface_root_widget(self._target),
                self.focused_path,
            )
            if widget.name == "Button" and key in {"Enter", " ", "Spacebar"}:
                result = self._trigger_path_event(self.focused_path, "onClick")

        if self._should_send_global_key(key, shift=shift, ctrl=ctrl, meta=meta, alt=alt):
            global_result = self._trigger_global_key_down(
                {
                    "key": key,
                    "ctrlKey": ctrl,
                    "metaKey": meta,
                    "altKey": alt,
                    "shiftKey": shift,
                }
            )
            if global_result is not None:
                result = global_result

        self.refresh()
        return result

    def input_text(self, value: str, *, path: tuple[int, ...] | None = None) -> Any:
        target_path = self.focused_path if path is None else path
        self._enabled_input_widget(target_path)

        if target_path != self.focused_path:
            assert target_path is not None
            self.focus(target_path)
        result = self._trigger_path_event(target_path, "onChange", value)
        self.refresh()
        return result

    def input_value(self, *, path: tuple[int, ...] | None = None) -> str:
        target_path = self.focused_path if path is None else path
        widget = self._enabled_input_widget(target_path)
        return str(widget.props.get("value") or "")

    def scroll(self, x: int, y: int, delta_y: int) -> Any:
        hit = hit_test_native(self.layout, x, y, event="onScroll")
        if hit is None:
            return None
        widget = widget_by_path(surface_root_widget(self._target), hit.path)
        if widget.name != "ScrollView" or "onScroll" not in widget.events:
            return None

        current_scroll_y = scroll_y(widget)
        next_scroll_y = clamp_scroll_y(
            current_scroll_y + int(delta_y),
            max_scroll_y=max_scroll_y(hit),
        )
        if next_scroll_y == current_scroll_y:
            return None

        result = widget.trigger("onScroll", next_scroll_y)
        self.refresh()
        return result

    def box(self, path: tuple[int, ...]) -> LayoutBox:
        return self.layout.by_path(path)

    def dispose(self) -> None:
        if self._owns_mount and self._mounted is not None:
            unmount(self._mounted)
        self._layout = None
        self._paint = None
        self._tree_revision = None
        self.focused_path = None

    def _ensure_fresh(self) -> None:
        current_revision = tree_revision(surface_root_widget(self._target))
        if self._layout is None or self._paint is None or current_revision != self._tree_revision:
            self.refresh()

    def _sync_focus_after_refresh(self) -> None:
        if self.focused_path is None:
            return
        if self._is_focusable_path(self.focused_path):
            return
        self.focused_path = self._first_autofocus_path()

    def _first_autofocus_path(self) -> tuple[int, ...] | None:
        widget = surface_root_widget(self._target)
        for box in self.layout.boxes:
            candidate = widget_by_path(widget, box.path)
            if candidate.props.get("autoFocus") and self._is_focusable_widget(candidate):
                return box.path
        return None

    def _focusable_paths(self) -> list[tuple[int, ...]]:
        widget = surface_root_widget(self._target)
        return [
            box.path
            for box in self.layout.boxes
            if self._is_focusable_widget(widget_by_path(widget, box.path))
        ]

    def _hit_test_focusable(self, x: int, y: int) -> LayoutBox | None:
        widget = surface_root_widget(self._target)
        containing = [
            box
            for box in self.layout.boxes
            if box.contains(x, y)
            and visible_through_scroll_ancestors(self.layout, box, x, y)
            and self._is_focusable_widget(widget_by_path(widget, box.path))
        ]
        if not containing:
            return None
        return max(
            enumerate(containing),
            key=lambda item: (len(item[1].path), item[0]),
        )[1]

    def _is_focusable_path(self, path: tuple[int, ...]) -> bool:
        try:
            widget = widget_by_path(surface_root_widget(self._target), path)
        except KeyError:
            return False
        return self._is_focusable_widget(widget)

    def _is_focusable_widget(self, widget: FakeWidget) -> bool:
        if widget.props.get("disabled"):
            return False
        return widget.name in {"Button", "Input"}

    def _enabled_input_widget(self, path: tuple[int, ...] | None) -> FakeWidget:
        if path is None:
            raise KeyError("NativeSurface has no focused input for text entry.")
        try:
            widget = widget_by_path(surface_root_widget(self._target), path)
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

    def _focus_error_message(self, path: tuple[int, ...]) -> str:
        try:
            widget = widget_by_path(surface_root_widget(self._target), path)
        except KeyError:
            return f"No focusable native box exists at path {path!r}: no native widget exists."
        if widget.props.get("disabled"):
            return (
                f"No focusable native box exists at path {path!r}: "
                f"{widget_context(widget)} is disabled."
            )
        return (
            f"No focusable native box exists at path {path!r}: "
            f"{widget_context(widget)} is {widget.name}, not a focusable native control."
        )

    def _trigger_path_event(self, path: tuple[int, ...], event: str, *args: Any) -> Any:
        try:
            widget = widget_by_path(surface_root_widget(self._target), path)
        except KeyError:
            return None
        if event not in widget.events:
            return None
        return widget.trigger(event, *args)

    def _trigger_global_key_down(self, payload: dict[str, Any]) -> Any:
        for widget in walk_widgets(surface_root_widget(self._target)):
            if "onGlobalKeyDown" in widget.events:
                return widget.trigger("onGlobalKeyDown", payload)
        return None

    def _should_send_global_key(
        self,
        key: str,
        *,
        shift: bool,
        ctrl: bool,
        meta: bool,
        alt: bool,
    ) -> bool:
        has_global = any(
            "onGlobalKeyDown" in widget.events
            for widget in walk_widgets(surface_root_widget(self._target))
        )
        if not has_global:
            return False
        if ctrl or meta or key == "Escape":
            return True
        if len(key) != 1:
            return False
        if self.focused_path is None:
            return True
        focused = widget_by_path(surface_root_widget(self._target), self.focused_path)
        if focused.name == "Input":
            return False
        return True
