from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable

from ._native_contracts import NativeLayout, NativePaint
from ._native_layout import layout_native
from ._native_paint import paint_native
from .mount import FakeWidget, MountedNode
from .style import StyleSheet


@runtime_checkable
class NativeLayoutBackend(Protocol):
    """Internal mounted-tree layout SPI for the current native renderer path."""

    name: str

    def layout(
        self,
        target: FakeWidget | MountedNode,
        *,
        stylesheet: StyleSheet | None = None,
        strict_styles: bool = True,
    ) -> NativeLayout:
        ...


@runtime_checkable
class NativePaintBackend(Protocol):
    """Internal paint SPI over Otoe's current NativeLayout output."""

    name: str

    def paint(
        self,
        layout: NativeLayout,
        *,
        background: str = "#ffffff",
        focused_path: tuple[int, ...] | None = None,
    ) -> NativePaint:
        ...


@runtime_checkable
class NativeRasterBackend(Protocol):
    """Internal raster SPI over Otoe's current NativePaint command stream."""

    name: str

    def write_png(self, paint: NativePaint, path: str | Path) -> None:
        ...


@runtime_checkable
class NativeRendererBackend(
    NativeLayoutBackend,
    NativePaintBackend,
    NativeRasterBackend,
    Protocol,
):
    """Internal mounted-tree renderer SPI, not the external backend ABI."""

    pass


@dataclass(frozen=True)
class PythonNativeRendererBackend:
    name: str = "python-native"

    def layout(
        self,
        target: FakeWidget | MountedNode,
        *,
        stylesheet: StyleSheet | None = None,
        strict_styles: bool = True,
    ) -> NativeLayout:
        return layout_native(
            target,
            stylesheet=stylesheet,
            strict_styles=strict_styles,
        )

    def paint(
        self,
        layout: NativeLayout,
        *,
        background: str = "#ffffff",
        focused_path: tuple[int, ...] | None = None,
    ) -> NativePaint:
        return paint_native(
            layout,
            background=background,
            focused_path=focused_path,
        )

    def write_png(self, paint: NativePaint, path: str | Path) -> None:
        from ._native_png import write_native_png

        write_native_png(paint, path)


@dataclass(frozen=True)
class ComposedNativeRendererBackend:
    layout_backend: NativeLayoutBackend
    paint_backend: NativePaintBackend
    raster_backend: NativeRasterBackend
    name: str = "composed-native"

    def layout(
        self,
        target: FakeWidget | MountedNode,
        *,
        stylesheet: StyleSheet | None = None,
        strict_styles: bool = True,
    ) -> NativeLayout:
        return self.layout_backend.layout(
            target,
            stylesheet=stylesheet,
            strict_styles=strict_styles,
        )

    def paint(
        self,
        layout: NativeLayout,
        *,
        background: str = "#ffffff",
        focused_path: tuple[int, ...] | None = None,
    ) -> NativePaint:
        return self.paint_backend.paint(
            layout,
            background=background,
            focused_path=focused_path,
        )

    def write_png(self, paint: NativePaint, path: str | Path) -> None:
        self.raster_backend.write_png(paint, path)


PYTHON_NATIVE_RENDERER_BACKEND = PythonNativeRendererBackend()


__all__ = [
    "ComposedNativeRendererBackend",
    "NativeLayoutBackend",
    "NativePaintBackend",
    "NativeRasterBackend",
    "NativeRendererBackend",
    "PYTHON_NATIVE_RENDERER_BACKEND",
    "PythonNativeRendererBackend",
]
