from __future__ import annotations

from pathlib import Path
from typing import Any

from ._native_backend import NativeRendererBackend, PYTHON_NATIVE_RENDERER_BACKEND
from ._native_contracts import LayoutBox, NativeLayout, NativePaint
from ._native_hit_test import dispatch_native_click, hit_test_native
from ._native_shared import (
    mounted_or_none,
    native_surface_target,
    surface_root_widget,
    tree_revision,
    widget_by_path,
)
from ._native_surface_focus import (
    first_autofocus_path,
    focus_error_message,
    focusable_paths,
    hit_test_focusable,
    is_focusable_path,
    is_focusable_widget,
)
from ._native_surface_input import (
    enabled_input_widget,
    global_key_payload,
    should_activate_button_with_key,
    should_send_global_key,
    trigger_global_key_down,
    trigger_path_event,
)
from ._native_surface_scroll import dispatch_scroll
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
        renderer_backend: NativeRendererBackend | None = None,
    ) -> None:
        self.stylesheet = stylesheet
        self.strict_styles = strict_styles
        self.background = background
        self.renderer_backend = renderer_backend or PYTHON_NATIVE_RENDERER_BACKEND
        self.frame = 0
        self.focused_path: tuple[int, ...] | None = None
        self._focused_widget: FakeWidget | None = None
        self._focused_identities: frozenset[object] = frozenset()
        self._mounted: MountedNode | None
        if isinstance(target, Node):
            self._owns_mount = True
            self._mounted = mount(target)
        else:
            self._owns_mount = False
            self._mounted = None
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
            self._focused_widget = widget_by_path(self._root_widget(), self.focused_path)
            self._focused_identities = frozenset(self._focused_widget.focus_identities)
            self._paint = self.renderer_backend.paint(
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
        focus_was_lost = self._sync_focused_widget_before_refresh()
        self._layout = self.renderer_backend.layout(
            self._target,
            stylesheet=self.stylesheet,
            strict_styles=self.strict_styles,
        )
        self._tree_revision = tree_revision(self._root_widget())
        self._sync_focus_after_refresh(focus_was_lost=focus_was_lost)
        self._paint = self.renderer_backend.paint(
            self._layout,
            background=self.background,
            focused_path=self.focused_path,
        )
        self.frame += 1
        return self._paint

    def render_png(self, path: str | Path) -> NativePaint:
        paint = self.refresh()
        self.renderer_backend.write_png(paint, path)
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
        self._ensure_fresh()
        next_widget = (
            widget_by_path(self._root_widget(), path) if path is not None else None
        )
        if path == self.focused_path and next_widget is self._focused_widget:
            return
        if path is not None and not self._is_focusable_path(path):
            raise KeyError(focus_error_message(self._root_widget(), path))

        previous_widget = self._focused_widget
        self.focused_path = path
        self._focused_widget = next_widget
        self._focused_identities = (
            frozenset(next_widget.focus_identities)
            if next_widget is not None
            else frozenset()
        )
        if previous_widget is not None:
            _trigger_widget_event(previous_widget, "onBlur")
        if next_widget is not None:
            _trigger_widget_event(next_widget, "onFocus")
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
            widget = widget_by_path(self._root_widget(), self.focused_path)
            if should_activate_button_with_key(widget, key):
                result = self._trigger_path_event(self.focused_path, "onClick")

        if self._should_send_global_key(key, shift=shift, ctrl=ctrl, meta=meta, alt=alt):
            global_result = self._trigger_global_key_down(
                global_key_payload(
                    key,
                    shift=shift,
                    ctrl=ctrl,
                    meta=meta,
                    alt=alt,
                )
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
        assert target_path is not None
        result = self._trigger_path_event(target_path, "onChange", value)
        self.refresh()
        return result

    def input_value(self, *, path: tuple[int, ...] | None = None) -> str:
        target_path = self.focused_path if path is None else path
        widget = self._enabled_input_widget(target_path)
        return str(widget.props.get("value") or "")

    def scroll(self, x: int, y: int, delta_y: int) -> Any:
        did_scroll, result = dispatch_scroll(
            self._root_widget(),
            self.layout,
            x,
            y,
            delta_y,
        )
        if not did_scroll:
            return None
        self.refresh()
        return result

    def box(self, path: tuple[int, ...]) -> LayoutBox:
        return self.layout.by_path(path)

    def dispose(self) -> None:
        if self._focused_widget is not None:
            _trigger_widget_event(self._focused_widget, "onBlur")
        if self._owns_mount and self._mounted is not None:
            unmount(self._mounted)
        self._layout = None
        self._paint = None
        self._tree_revision = None
        self.focused_path = None
        self._focused_widget = None
        self._focused_identities = frozenset()

    def _ensure_fresh(self) -> None:
        current_revision = tree_revision(self._root_widget())
        if (
            self._layout is None
            or self._paint is None
            or current_revision != self._tree_revision
        ):
            self.refresh()

    def _sync_focused_widget_before_refresh(self) -> bool:
        focused_widget = self._focused_widget
        if focused_widget is None:
            return False

        next_path = _path_for_widget(self._root_widget(), focused_widget)
        if next_path is not None and is_focusable_widget(focused_widget):
            self.focused_path = next_path
            return False


        replacement = _widget_for_focus_identities(
            self._root_widget(),
            self._focused_identities,
        )
        if replacement is not None and is_focusable_widget(replacement):
            replacement_path = _path_for_widget(self._root_widget(), replacement)
            assert replacement_path is not None
            self.focused_path = replacement_path
            self._focused_widget = replacement
            return False

        self.focused_path = None
        self._focused_widget = None
        self._focused_identities = frozenset()
        _trigger_widget_event(focused_widget, "onBlur")
        return True

    def _sync_focus_after_refresh(self, *, focus_was_lost: bool) -> None:
        if not focus_was_lost:
            return
        self.focused_path = self._first_autofocus_path()
        if self.focused_path is not None:
            self._focused_widget = widget_by_path(self._root_widget(), self.focused_path)
            self._focused_identities = frozenset(self._focused_widget.focus_identities)

    def _first_autofocus_path(self) -> tuple[int, ...] | None:
        return first_autofocus_path(self.layout, self._root_widget())

    def _focusable_paths(self) -> list[tuple[int, ...]]:
        return focusable_paths(self.layout, self._root_widget())

    def _hit_test_focusable(self, x: int, y: int) -> LayoutBox | None:
        return hit_test_focusable(self.layout, self._root_widget(), x, y)

    def _is_focusable_path(self, path: tuple[int, ...]) -> bool:
        return is_focusable_path(self._root_widget(), path)

    def _enabled_input_widget(self, path: tuple[int, ...] | None) -> FakeWidget:
        return enabled_input_widget(self._root_widget(), path)

    def _trigger_path_event(self, path: tuple[int, ...], event: str, *args: Any) -> Any:
        return trigger_path_event(self._root_widget(), path, event, *args)

    def _trigger_global_key_down(self, payload: dict[str, Any]) -> Any:
        return trigger_global_key_down(self._root_widget(), payload)

    def _should_send_global_key(
        self,
        key: str,
        *,
        shift: bool,
        ctrl: bool,
        meta: bool,
        alt: bool,
    ) -> bool:
        return should_send_global_key(
            self._root_widget(),
            self.focused_path,
            key,
            shift=shift,
            ctrl=ctrl,
            meta=meta,
            alt=alt,
        )

    def _root_widget(self) -> FakeWidget:
        return surface_root_widget(self._target)


def _path_for_widget(
    root: FakeWidget,
    target: FakeWidget,
    path: tuple[int, ...] = (),
) -> tuple[int, ...] | None:
    if root is target:
        return path
    for index, child in enumerate(root.children):
        found = _path_for_widget(child, target, (*path, index))
        if found is not None:
            return found
    return None


def _trigger_widget_event(widget: FakeWidget, event: str, *args: Any) -> Any:
    if event not in widget.events:
        return None
    return widget.trigger(event, *args)


def _widget_for_focus_identities(
    root: FakeWidget,
    identities: frozenset[object],
) -> FakeWidget | None:
    if not identities:
        return None
    if identities.intersection(root.focus_identities):
        return root
    for child in root.children:
        found = _widget_for_focus_identities(child, identities)
        if found is not None:
            return found
    return None
