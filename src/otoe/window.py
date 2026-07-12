from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from ._native_backend import NativeRendererBackend
from .mount import FakeWidget, MountedNode
from .native import NativePaint, NativeSurface
from .node import Node
from .scheduler import drain_posted
from .style import StyleSheet


_TKINTER_REQUIRED_MESSAGE = (
    "TkNativeWindow requires tkinter. Install the Tk bindings for your Python "
    "before using the optional --window mode. On Debian/Ubuntu, run "
    "`sudo apt install python3-tk`. The headless PNG demo still works with "
    "`PYTHONPATH=src:. python -m examples.native.window_demo`."
)
_TK_CANVAS_MAX_SCALE = 2.0


@dataclass(frozen=True)
class NativeWindowEvent:
    kind: str
    x: int | None = None
    y: int | None = None
    delta_y: int | None = None
    key: str | None = None
    text: str | None = None
    shift: bool = False
    ctrl: bool = False
    meta: bool = False
    alt: bool = False


class NativeWindowDriver:
    def __init__(self, surface: NativeSurface) -> None:
        self.surface = surface
        self._input_capability_events: list[str] = []

    @classmethod
    def from_target(
        cls,
        target: Node | FakeWidget | MountedNode,
        *,
        stylesheet: StyleSheet | None = None,
        strict_styles: bool = True,
        background: str = "#ffffff",
        renderer_backend: NativeRendererBackend | None = None,
    ) -> "NativeWindowDriver":
        return cls(
            NativeSurface(
                target,
                stylesheet=stylesheet,
                strict_styles=strict_styles,
                background=background,
                renderer_backend=renderer_backend,
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

    @property
    def input_capability_event_count(self) -> int:
        return len(self._input_capability_events)

    @property
    def input_capability_events(self) -> tuple[str, ...]:
        return tuple(self._input_capability_events)

    @property
    def input_capabilities(self) -> tuple[str, ...]:
        return tuple(sorted(set(self._input_capability_events)))

    def input_capabilities_since(self, event_count: int) -> tuple[str, ...]:
        return tuple(sorted(set(self._input_capability_events[event_count:])))

    def dispatch(self, event: NativeWindowEvent) -> Any:
        if event.kind == "click":
            if event.x is None or event.y is None:
                raise ValueError("click events require x and y coordinates.")
            return self.click(event.x, event.y)
        if event.kind == "wheel":
            if event.x is None or event.y is None or event.delta_y is None:
                raise ValueError("wheel events require x, y, and delta_y.")
            return self.wheel(event.x, event.y, event.delta_y)
        if event.kind == "key_input":
            if event.key is None:
                raise ValueError("key_input events require a key.")
            return self.key_input(
                event.key,
                text=event.text or "",
                shift=event.shift,
                ctrl=event.ctrl,
                meta=event.meta,
                alt=event.alt,
            )
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
        focused_before = self.focused_path
        result = self.surface.click(x, y)
        self._record_input_capabilities(
            "click",
            *self._focus_capability(focused_before),
        )
        return result

    def wheel(self, x: int, y: int, delta_y: int) -> Any:
        result = self.surface.scroll(x, y, delta_y)
        self._record_input_capabilities("wheel")
        return result

    def key_down(
        self,
        key: str,
        *,
        shift: bool = False,
        ctrl: bool = False,
        meta: bool = False,
        alt: bool = False,
    ) -> Any:
        focused_before = self.focused_path
        result = self.surface.key_down(
            key,
            shift=shift,
            ctrl=ctrl,
            meta=meta,
            alt=alt,
        )
        capabilities = ["key_down"]
        if key == "Tab":
            capabilities.append("tab_focus")
        if _is_shortcut_key(key, ctrl=ctrl, meta=meta, alt=alt):
            capabilities.append("shortcut")
        capabilities.extend(self._focus_capability(focused_before))
        self._record_input_capabilities(*capabilities)
        return result

    def key_input(
        self,
        key: str,
        *,
        text: str = "",
        shift: bool = False,
        ctrl: bool = False,
        meta: bool = False,
        alt: bool = False,
    ) -> Any:
        self._record_input_capabilities("key_input")
        try:
            current_value = self.surface.input_value()
        except KeyError:
            return self.key_down(key, shift=shift, ctrl=ctrl, meta=meta, alt=alt)

        next_value = edit_native_input_value(
            current_value,
            key=key,
            text=text,
            shift=shift,
            ctrl=ctrl,
            meta=meta,
            alt=alt,
        )
        if next_value is None:
            return self.key_down(key, shift=shift, ctrl=ctrl, meta=meta, alt=alt)
        self.surface.key_down(key, shift=shift, ctrl=ctrl, meta=meta, alt=alt)
        return self.input_text(next_value)

    def input_text(self, value: str) -> Any:
        focused_before = self.focused_path
        result = self.surface.input_text(value)
        self._record_input_capabilities(
            "input_text",
            *self._focus_capability(focused_before),
        )
        return result

    def render_png(self, path: str | Path) -> NativePaint:
        return self.surface.render_png(path)

    def _focus_capability(
        self,
        focused_before: tuple[int, ...] | None,
    ) -> tuple[str, ...]:
        if self.focused_path == focused_before:
            return ()
        return ("focus",)

    def _record_input_capabilities(self, *capabilities: str) -> None:
        self._input_capability_events.extend(
            capability for capability in capabilities if capability
        )


@runtime_checkable
class NativeBackendAdapter(Protocol):
    name: str

    def run(self, driver: NativeWindowDriver, *, title: str = "Otoe") -> None:
        ...


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
            raise RuntimeError(_TKINTER_REQUIRED_MESSAGE) from exc

        self._tk = tk
        self.driver = (
            driver
            if isinstance(driver, NativeWindowDriver)
            else NativeWindowDriver(driver)
        )
        self.frame_path = Path(frame_path) if frame_path is not None else None
        width, height = self.driver.size
        self._logical_width = width
        self._logical_height = height
        self._canvas_width = width
        self._canvas_height = height
        self._scale = 1.0
        self._offset_x = 0.0
        self._offset_y = 0.0

        self.root = tk.Tk()
        self.root.title(title)
        self._canvas = tk.Canvas(
            self.root,
            bd=0,
            highlightthickness=0,
            width=width,
            height=height,
        )
        self._canvas.pack(fill="both", expand=True)
        self._canvas.bind("<Button-1>", self._on_click)
        self._canvas.bind("<MouseWheel>", self._on_wheel)
        self._canvas.bind("<Button-4>", self._on_wheel)
        self._canvas.bind("<Button-5>", self._on_wheel)
        self._canvas.bind("<Configure>", self._on_configure)
        self.root.bind("<KeyPress>", self._on_key_press)
        self.root.geometry(f"{width}x{height}")
        self._render()

    def run(self) -> None:
        self.root.after(16, self._poll_posted_callbacks)
        self.root.mainloop()

    def close(self) -> None:
        self.root.destroy()

    def _on_click(self, event: Any) -> str:
        focus_set = getattr(self._canvas, "focus_set", None)
        if focus_set is not None:
            focus_set()
        x, y = self._event_point(event)
        self.driver.click(x, y)
        self._render()
        return "break"

    def _on_wheel(self, event: Any) -> str:
        x, y = self._event_point(event)
        self.driver.wheel(x, y, _tk_wheel_delta(event))
        self._render()
        return "break"

    def _on_key_press(self, event: Any) -> str:
        shift = bool(event.state & 0x0001)
        ctrl = bool(event.state & 0x0004)
        alt = bool(event.state & 0x0008)
        meta = bool(event.state & 0x0040)
        key = _tk_key_name(event)

        self.driver.key_input(
            key,
            text=str(event.char or ""),
            shift=shift,
            ctrl=ctrl,
            meta=meta,
            alt=alt,
        )

        self._render()
        return "break"

    def _on_configure(self, event: Any) -> None:
        width = max(1, int(event.width))
        height = max(1, int(event.height))
        if width == self._canvas_width and height == self._canvas_height:
            return
        self._canvas_width = width
        self._canvas_height = height
        self._render()

    def _render(self) -> None:
        if self.frame_path is not None:
            self.driver.render_png(self.frame_path)
        paint = self.driver.paint
        self._logical_width = paint.width
        self._logical_height = paint.height
        self._sync_canvas_transform()
        self._canvas.delete("all")
        for command in paint.commands:
            _draw_tk_canvas_command(
                self._canvas,
                command,
                scale=self._scale,
                offset_x=self._offset_x,
                offset_y=self._offset_y,
            )

    def _poll_posted_callbacks(self) -> None:
        try:
            if drain_posted() > 0:
                self._render()
        finally:
            self.root.after(16, self._poll_posted_callbacks)

    def _sync_canvas_transform(self) -> None:
        scale_x = self._canvas_width / max(1, self._logical_width)
        scale_y = self._canvas_height / max(1, self._logical_height)
        self._scale = max(0.01, min(scale_x, scale_y, _TK_CANVAS_MAX_SCALE))
        self._offset_x = (self._canvas_width - (self._logical_width * self._scale)) / 2
        self._offset_y = (self._canvas_height - (self._logical_height * self._scale)) / 2

    def _event_point(self, event: Any) -> tuple[int, int]:
        x = (float(event.x) - self._offset_x) / self._scale
        y = (float(event.y) - self._offset_y) / self._scale
        return (int(x), int(y))


def _draw_tk_canvas_command(
    canvas: Any,
    command: Any,
    *,
    scale: float = 1.0,
    offset_x: float = 0.0,
    offset_y: float = 0.0,
) -> None:
    if command.kind == "rect":
        _draw_tk_canvas_rect(canvas, command, scale=scale, offset_x=offset_x, offset_y=offset_y)
        return
    if command.kind == "text":
        _draw_tk_canvas_text(canvas, command, scale=scale, offset_x=offset_x, offset_y=offset_y)


def _draw_tk_canvas_rect(
    canvas: Any,
    command: Any,
    *,
    scale: float,
    offset_x: float,
    offset_y: float,
) -> None:
    rect = _visible_canvas_rect(command)
    if rect is None:
        return
    transformed = _transform_canvas_rect(rect, scale=scale, offset_x=offset_x, offset_y=offset_y)
    left, top, right, bottom = transformed
    if command.fill:
        canvas.create_rectangle(
            left,
            top,
            right,
            bottom,
            fill=command.fill,
            outline="",
        )
    if command.stroke and command.stroke_width > 0:
        canvas.create_rectangle(
            left,
            top,
            right,
            bottom,
            outline=command.stroke,
            width=command.stroke_width * scale,
        )


def _draw_tk_canvas_text(
    canvas: Any,
    command: Any,
    *,
    scale: float,
    offset_x: float,
    offset_y: float,
) -> None:
    if command.text is None or not _canvas_command_intersects_clip(command):
        return
    x = offset_x + (command.x * scale)
    y = offset_y + (command.y * scale)
    canvas.create_text(
        x,
        y,
        anchor="nw",
        text=command.text,
        fill=command.color or "#111827",
        font=("TkDefaultFont", _scaled_tk_font_size(command.font_size, scale=scale)),
        width=max(1, command.width * scale),
    )


def _scaled_tk_font_size(font_size: int, *, scale: float) -> int:
    return max(1, int(round(font_size * scale)))


def _visible_canvas_rect(command: Any) -> tuple[int, int, int, int] | None:
    rect = (command.x, command.y, command.x + command.width, command.y + command.height)
    if command.clip is None:
        return rect
    return _intersect_canvas_rect(rect, _canvas_clip_rect(command.clip))


def _canvas_command_intersects_clip(command: Any) -> bool:
    if command.clip is None:
        return True
    rect = (command.x, command.y, command.x + command.width, command.y + command.height)
    return _intersect_canvas_rect(rect, _canvas_clip_rect(command.clip)) is not None


def _canvas_clip_rect(clip: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
    x, y, width, height = clip
    return (x, y, x + width, y + height)


def _transform_canvas_rect(
    rect: tuple[int, int, int, int],
    *,
    scale: float,
    offset_x: float,
    offset_y: float,
) -> tuple[float, float, float, float]:
    return (
        offset_x + (rect[0] * scale),
        offset_y + (rect[1] * scale),
        offset_x + (rect[2] * scale),
        offset_y + (rect[3] * scale),
    )


def _intersect_canvas_rect(
    first: tuple[int, int, int, int],
    second: tuple[int, int, int, int],
) -> tuple[int, int, int, int] | None:
    left = max(first[0], second[0])
    top = max(first[1], second[1])
    right = min(first[2], second[2])
    bottom = min(first[3], second[3])
    if right <= left or bottom <= top:
        return None
    return (left, top, right, bottom)


class TkNativeBackendAdapter:
    name = "tk"

    def run(self, driver: NativeWindowDriver, *, title: str = "Otoe") -> None:
        TkNativeWindow(driver, title=title).run()


_NATIVE_BACKENDS: dict[str, NativeBackendAdapter] = {
    TkNativeBackendAdapter.name: TkNativeBackendAdapter(),
}


def native_backend_names() -> tuple[str, ...]:
    return tuple(sorted(_NATIVE_BACKENDS))


def native_backend_adapter(name: str) -> NativeBackendAdapter:
    try:
        return _NATIVE_BACKENDS[name]
    except KeyError as exc:
        raise ValueError(f"Unsupported native backend {name!r}.") from exc


def _tk_key_name(event: Any) -> str:
    if event.keysym == "Return":
        return "Enter"
    if event.keysym == "space":
        return " "
    return str(event.keysym)


def _tk_wheel_delta(event: Any) -> int:
    number = getattr(event, "num", None)
    if number == 4:
        return -48
    if number == 5:
        return 48

    delta = int(getattr(event, "delta", 0) or 0)
    if delta == 0:
        return 0
    return -int(delta / 4)


def _is_shortcut_key(
    key: str,
    *,
    ctrl: bool,
    meta: bool,
    alt: bool,
) -> bool:
    return bool(ctrl or meta or key == "Escape")


def edit_native_input_value(
    value: str,
    *,
    key: str,
    text: str = "",
    shift: bool = False,
    ctrl: bool = False,
    meta: bool = False,
    alt: bool = False,
) -> str | None:
    if ctrl or meta or alt:
        return None
    if key == "BackSpace":
        return value[:-1]
    if key == "Delete":
        return value
    if key in {"Enter", "Tab", "Escape"}:
        return None
    if len(text) == 1 and text not in {"\b", "\r", "\n", "\t"}:
        return value + text
    return None


def run_native(
    target: Node | FakeWidget | MountedNode | NativeSurface | NativeWindowDriver,
    *,
    stylesheet: StyleSheet | None = None,
    strict_styles: bool = True,
    background: str = "#ffffff",
    title: str = "Otoe",
    backend: str | NativeBackendAdapter = "tk",
    renderer_backend: NativeRendererBackend | None = None,
) -> None:
    adapter = _resolve_native_backend(backend)

    if isinstance(target, NativeWindowDriver):
        if renderer_backend is not None:
            raise ValueError(
                "renderer_backend can only be used when run_native creates "
                "the NativeWindowDriver."
            )
        driver = target
    elif isinstance(target, NativeSurface):
        if renderer_backend is not None:
            raise ValueError(
                "renderer_backend can only be used when run_native creates "
                "the NativeSurface."
            )
        driver = NativeWindowDriver(target)
    else:
        driver = NativeWindowDriver.from_target(
            target,
            stylesheet=stylesheet,
            strict_styles=strict_styles,
            background=background,
            renderer_backend=renderer_backend,
        )
    adapter.run(driver, title=title)


def _resolve_native_backend(backend: str | NativeBackendAdapter) -> NativeBackendAdapter:
    if isinstance(backend, str):
        return native_backend_adapter(backend)
    if isinstance(backend, NativeBackendAdapter):
        return backend
    raise TypeError(
        "native backend must be a backend name or an object implementing "
        "NativeBackendAdapter."
    )
