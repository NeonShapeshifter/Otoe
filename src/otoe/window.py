from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .mount import FakeWidget, MountedNode
from .native import NativePaint, NativeSurface
from .node import Node
from .style import StyleSheet


@dataclass(frozen=True)
class NativeWindowEvent:
    kind: str
    x: int | None = None
    y: int | None = None
    key: str | None = None
    text: str | None = None
    shift: bool = False
    ctrl: bool = False
    meta: bool = False
    alt: bool = False


class NativeWindowDriver:
    def __init__(self, surface: NativeSurface) -> None:
        self.surface = surface

    @classmethod
    def from_target(
        cls,
        target: Node | FakeWidget | MountedNode,
        *,
        stylesheet: StyleSheet | None = None,
        strict_styles: bool = True,
        background: str = "#ffffff",
    ) -> "NativeWindowDriver":
        return cls(
            NativeSurface(
                target,
                stylesheet=stylesheet,
                strict_styles=strict_styles,
                background=background,
            )
        )

    @property
    def frame(self) -> int:
        return self.surface.frame

    @property
    def focused_path(self) -> tuple[int, ...] | None:
        return self.surface.focused_path

    @property
    def paint(self) -> NativePaint:
        return self.surface.paint

    @property
    def size(self) -> tuple[int, int]:
        paint = self.surface.paint
        return (paint.width, paint.height)

    def dispatch(self, event: NativeWindowEvent) -> Any:
        if event.kind == "click":
            if event.x is None or event.y is None:
                raise ValueError("click events require x and y coordinates.")
            return self.click(event.x, event.y)
        if event.kind == "key_down":
            if event.key is None:
                raise ValueError("key_down events require a key.")
            return self.key_down(
                event.key,
                shift=event.shift,
                ctrl=event.ctrl,
                meta=event.meta,
                alt=event.alt,
            )
        if event.kind == "input_text":
            if event.text is None:
                raise ValueError("input_text events require text.")
            return self.input_text(event.text)
        raise ValueError(f"Unknown native window event kind {event.kind!r}.")

    def click(self, x: int, y: int) -> Any:
        return self.surface.click(x, y)

    def key_down(
        self,
        key: str,
        *,
        shift: bool = False,
        ctrl: bool = False,
        meta: bool = False,
        alt: bool = False,
    ) -> Any:
        return self.surface.key_down(
            key,
            shift=shift,
            ctrl=ctrl,
            meta=meta,
            alt=alt,
        )

    def input_text(self, value: str) -> Any:
        return self.surface.input_text(value)

    def render_png(self, path: str | Path) -> NativePaint:
        return self.surface.render_png(path)


class TkNativeWindow:
    def __init__(
        self,
        driver: NativeWindowDriver | NativeSurface,
        *,
        title: str = "Otoe",
        frame_path: str | Path | None = None,
    ) -> None:
        try:
            import tkinter as tk
        except ImportError as exc:  # pragma: no cover - platform dependent.
            raise RuntimeError("TkNativeWindow requires tkinter.") from exc

        self._tk = tk
        self.driver = driver if isinstance(driver, NativeWindowDriver) else NativeWindowDriver(driver)
        if frame_path is None:
            handle = tempfile.NamedTemporaryFile(prefix="otoe-native-", suffix=".png", delete=False)
            handle.close()
            self.frame_path = Path(handle.name)
        else:
            self.frame_path = Path(frame_path)

        self.root = tk.Tk()
        self.root.title(title)
        self._image: Any | None = None
        self._label = tk.Label(self.root, bd=0, highlightthickness=0)
        self._label.pack()
        self._label.bind("<Button-1>", self._on_click)
        self.root.bind("<KeyPress>", self._on_key_press)
        self._render()

    def run(self) -> None:
        self.root.mainloop()

    def close(self) -> None:
        self.root.destroy()

    def _on_click(self, event: Any) -> str:
        self.driver.click(int(event.x), int(event.y))
        self._render()
        return "break"

    def _on_key_press(self, event: Any) -> str:
        shift = bool(event.state & 0x0001)
        ctrl = bool(event.state & 0x0004)
        alt = bool(event.state & 0x0008)
        meta = bool(event.state & 0x0040)
        key = _tk_key_name(event)

        if ctrl or meta or alt:
            self.driver.key_down(key, shift=shift, ctrl=ctrl, meta=meta, alt=alt)
        elif key == "BackSpace":
            self._edit_focused_input(lambda value: value[:-1], fallback_key=key, shift=shift)
        elif key == "Return":
            self.driver.key_down("Enter", shift=shift)
        elif key == "Tab":
            self.driver.key_down("Tab", shift=shift)
        elif event.char:
            self._edit_focused_input(lambda value: value + event.char, fallback_key=key, shift=shift)
        else:
            self.driver.key_down(key, shift=shift)

        self._render()
        return "break"

    def _edit_focused_input(
        self,
        edit: Any,
        *,
        fallback_key: str,
        shift: bool = False,
    ) -> None:
        try:
            next_value = edit(self.driver.surface.input_value())
        except KeyError:
            self.driver.key_down(fallback_key, shift=shift)
        else:
            self.driver.input_text(next_value)

    def _render(self) -> None:
        self.driver.render_png(self.frame_path)
        self._image = self._tk.PhotoImage(file=str(self.frame_path))
        self._label.configure(image=self._image)
        width, height = self.driver.size
        self.root.geometry(f"{width}x{height}")


def _tk_key_name(event: Any) -> str:
    if event.keysym == "space":
        return " "
    return str(event.keysym)
