from pathlib import Path

from otoe import (
    Button,
    ComposedNativeRendererBackend,
    NativeLayout,
    NativeLayoutBackend,
    NativePaint,
    NativePaintBackend,
    NativeRasterBackend,
    NativeRendererBackend,
    NativeSurface,
    NativeWindowDriver,
    PYTHON_NATIVE_RENDERER_BACKEND,
    PythonNativeRendererBackend,
    Text,
    VStack,
    layout_native,
    mount,
    paint_native,
    render_native_png,
    run_native,
    signal,
)
from otoe.mount import FakeWidget, MountedNode
from otoe.style import StyleSheet


class RecordingRendererBackend:
    name = "recording-renderer"

    def __init__(self) -> None:
        self.inner = PythonNativeRendererBackend()
        self.layout_calls = 0
        self.paint_calls = 0
        self.write_png_calls = 0

    def layout(
        self,
        target: FakeWidget | MountedNode,
        *,
        stylesheet: StyleSheet | None = None,
        strict_styles: bool = True,
    ) -> NativeLayout:
        self.layout_calls += 1
        return self.inner.layout(
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
        self.paint_calls += 1
        return self.inner.paint(
            layout,
            background=background,
            focused_path=focused_path,
        )

    def write_png(self, paint: NativePaint, path: str | Path) -> None:
        self.write_png_calls += 1
        self.inner.write_png(paint, path)


def test_python_native_renderer_backend_matches_existing_pipeline(tmp_path):
    mounted = mount(VStack(Text("Hello"), Button("Run", onClick=lambda: None), padding=4))
    output = tmp_path / "native.png"

    layout = PYTHON_NATIVE_RENDERER_BACKEND.layout(mounted)
    paint = PYTHON_NATIVE_RENDERER_BACKEND.paint(layout)
    PYTHON_NATIVE_RENDERER_BACKEND.write_png(paint, output)

    assert isinstance(PYTHON_NATIVE_RENDERER_BACKEND, NativeRendererBackend)
    assert isinstance(PYTHON_NATIVE_RENDERER_BACKEND, NativeLayoutBackend)
    assert isinstance(PYTHON_NATIVE_RENDERER_BACKEND, NativePaintBackend)
    assert isinstance(PYTHON_NATIVE_RENDERER_BACKEND, NativeRasterBackend)
    assert layout == layout_native(mounted)
    assert paint == paint_native(layout_native(mounted))
    assert output.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")


def test_composed_native_renderer_backend_routes_each_capability(tmp_path):
    layout_backend = RecordingRendererBackend()
    paint_backend = RecordingRendererBackend()
    raster_backend = RecordingRendererBackend()
    backend = ComposedNativeRendererBackend(
        layout_backend=layout_backend,
        paint_backend=paint_backend,
        raster_backend=raster_backend,
        name="split-test",
    )
    mounted = mount(VStack(Text("Split"), padding=4))
    output = tmp_path / "split.png"

    layout = backend.layout(mounted)
    paint = backend.paint(layout)
    backend.write_png(paint, output)

    assert isinstance(backend, NativeRendererBackend)
    assert backend.name == "split-test"
    assert layout_backend.layout_calls == 1
    assert layout_backend.paint_calls == 0
    assert paint_backend.layout_calls == 0
    assert paint_backend.paint_calls == 1
    assert raster_backend.write_png_calls == 1
    assert output.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")


def test_native_surface_uses_injected_renderer_backend(tmp_path):
    backend = RecordingRendererBackend()
    surface = NativeSurface(
        VStack(Text("Backend"), Button("Run", onClick=lambda: None), padding=4),
        renderer_backend=backend,
    )

    assert surface.renderer_backend is backend
    assert backend.layout_calls == 1
    assert backend.paint_calls == 1
    assert backend.write_png_calls == 0

    output = tmp_path / "surface.png"
    surface.render_png(output)

    assert backend.layout_calls == 2
    assert backend.paint_calls == 2
    assert backend.write_png_calls == 1
    assert output.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")


def test_native_window_driver_passes_renderer_backend_to_surface():
    label = signal("OFF")
    backend = RecordingRendererBackend()
    driver = NativeWindowDriver.from_target(
        VStack(
            Text(label),
            Button("Toggle", onClick=lambda: label.set("ON")),
            padding=4,
            gap=4,
        ),
        renderer_backend=backend,
    )
    button = driver.surface.box((1,))

    driver.click(button.x + 2, button.y + 2)

    assert driver.surface.renderer_backend is backend
    assert label.value == "ON"
    assert driver.surface.box((0,)).text == "ON"
    assert backend.layout_calls >= 2
    assert backend.paint_calls >= 2


def test_render_native_png_accepts_renderer_backend(tmp_path):
    backend = RecordingRendererBackend()
    mounted = mount(VStack(Text("PNG"), padding=4))
    output = tmp_path / "renderer.png"

    paint = render_native_png(mounted, output, renderer_backend=backend)

    assert paint.commands
    assert backend.layout_calls == 1
    assert backend.paint_calls == 1
    assert backend.write_png_calls == 1
    assert output.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")


def test_run_native_uses_renderer_backend_when_creating_driver():
    renderer_backend = RecordingRendererBackend()
    captured = []

    class CapturingBackendAdapter:
        name = "capturing"

        def run(self, driver: NativeWindowDriver, *, title: str = "Otoe") -> None:
            captured.append((driver.surface.renderer_backend, title))

    run_native(
        Button("Run", onClick=lambda: None),
        title="Renderer Boundary",
        backend=CapturingBackendAdapter(),
        renderer_backend=renderer_backend,
    )

    assert captured == [(renderer_backend, "Renderer Boundary")]
    assert renderer_backend.layout_calls == 1
    assert renderer_backend.paint_calls == 1
