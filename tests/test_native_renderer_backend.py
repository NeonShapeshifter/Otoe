from pathlib import Path

import pytest

from otoe import (
    Button,
    ComposedNativeRendererBackend,
    Input,
    NativeLayout,
    NativeLayoutBackend,
    NativePaint,
    NativePaintBackend,
    NativeRasterBackend,
    NativeRendererBackend,
    NativeSurface,
    NativeWindowDriver,
    PYTHON_NATIVE_RENDERER_BACKEND,
    PillowNativeRendererBackend,
    PythonNativeRendererBackend,
    Text,
    VStack,
    component,
    layout_native,
    mount,
    on_cleanup,
    paint_native,
    render_native_png,
    run_native,
    signal,
    unmount,
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


class ConstructorFailingRendererBackend(RecordingRendererBackend):
    def __init__(self, failure_stage: str) -> None:
        super().__init__()
        self.failure_stage = failure_stage

    def layout(
        self,
        target: FakeWidget | MountedNode,
        *,
        stylesheet: StyleSheet | None = None,
        strict_styles: bool = True,
    ) -> NativeLayout:
        if self.failure_stage == "layout":
            raise RuntimeError("layout failed")
        return super().layout(
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
        if self.failure_stage == "paint":
            raise RuntimeError("paint failed")
        return super().paint(
            layout,
            background=background,
            focused_path=focused_path,
        )


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


@pytest.mark.parametrize("failure_stage", ["layout", "paint"])
def test_native_surface_constructor_failure_unmounts_owned_node(failure_stage):
    cleanups = []

    @component
    def App():
        on_cleanup(lambda: cleanups.append("cleanup"))
        return Text("Owned")

    with pytest.raises(RuntimeError, match=f"{failure_stage} failed"):
        NativeSurface(
            App(),
            renderer_backend=ConstructorFailingRendererBackend(failure_stage),
        )

    assert cleanups == ["cleanup"]


def test_native_surface_constructor_preserves_primary_and_cleanup_failures():
    @component
    def App():
        def fail_cleanup():
            raise OSError("cleanup failed")

        on_cleanup(fail_cleanup)
        return Text("Owned")

    with pytest.raises(BaseExceptionGroup) as caught:
        NativeSurface(
            App(),
            renderer_backend=ConstructorFailingRendererBackend("layout"),
        )

    primary_error, cleanup_error = caught.value.exceptions
    assert (
        caught.value.message
        == "NativeSurface initialization and mount cleanup both failed."
    )
    assert str(primary_error) == "layout failed"
    assert caught.value.__cause__ is primary_error
    assert isinstance(cleanup_error, ExceptionGroup)
    owner_error = cleanup_error.exceptions[0]
    assert isinstance(owner_error, ExceptionGroup)
    assert str(owner_error.exceptions[0]) == "cleanup failed"


@pytest.mark.parametrize("target_kind", ["mounted", "widget"])
def test_native_surface_constructor_failure_does_not_unmount_borrowed_target(
    target_kind,
):
    cleanups = []

    @component
    def App():
        on_cleanup(lambda: cleanups.append("cleanup"))
        return Text("Borrowed")

    mounted = mount(App())
    target = mounted if target_kind == "mounted" else mounted.root_widget()

    with pytest.raises(RuntimeError, match="layout failed"):
        NativeSurface(
            target,
            renderer_backend=ConstructorFailingRendererBackend("layout"),
        )

    assert cleanups == []
    unmount(mounted)
    assert cleanups == ["cleanup"]


def test_run_native_constructor_failure_unmounts_owned_node_before_backend_run():
    cleanups = []
    backend_calls = []

    @component
    def App():
        on_cleanup(lambda: cleanups.append("cleanup"))
        return Text("Owned")

    class BackendThatMustNotRun:
        name = "must-not-run"

        def run(self, driver, *, title="Otoe"):
            backend_calls.append((driver, title))

    with pytest.raises(RuntimeError, match="layout failed"):
        run_native(
            App(),
            backend=BackendThatMustNotRun(),
            renderer_backend=ConstructorFailingRendererBackend("layout"),
        )

    assert backend_calls == []
    assert cleanups == ["cleanup"]


def test_run_native_owned_surface_blur_failure_still_runs_owner_cleanup():
    cleanups = []
    captured_surfaces = []

    def fail_blur():
        raise RuntimeError("blur failed")

    @component
    def App():
        on_cleanup(lambda: cleanups.append("owner cleanup"))
        return Input(
            value="focused",
            autoFocus=True,
            onBlur=fail_blur,
            onChange=lambda value: None,
        )

    class RecordingBackend:
        name = "recording"

        def run(self, driver, *, title="Otoe"):
            captured_surfaces.append(driver.surface)
            assert driver.paint.width > 0

    with pytest.raises(RuntimeError, match="blur failed"):
        run_native(App(), backend=RecordingBackend())

    assert cleanups == ["owner cleanup"]
    assert len(captured_surfaces) == 1
    assert captured_surfaces[0].disposed is True


def test_native_surface_dispose_preserves_blur_and_owned_mount_cleanup_failures():
    cleanup_attempts = []
    blur_attempts = []

    def fail_blur():
        blur_attempts.append("blur")
        raise RuntimeError("blur failed")

    @component
    def App():
        def fail_owner_cleanup():
            cleanup_attempts.append("failing owner cleanup")
            raise OSError("owner cleanup failed")

        on_cleanup(fail_owner_cleanup)
        on_cleanup(lambda: cleanup_attempts.append("successful owner cleanup"))
        return Input(
            value="focused",
            autoFocus=True,
            onBlur=fail_blur,
            onChange=lambda value: None,
        )

    surface = NativeSurface(App())

    with pytest.raises(BaseExceptionGroup) as caught:
        surface.dispose()

    assert (
        caught.value.message
        == "NativeSurface focus blur and owned mount cleanup both failed."
    )
    blur_error, mount_error = caught.value.exceptions
    assert str(blur_error) == "blur failed"
    assert caught.value.__cause__ is blur_error
    assert isinstance(mount_error, ExceptionGroup)
    assert "owner cleanup failed" in repr(mount_error)
    assert blur_attempts == ["blur"]
    assert cleanup_attempts == [
        "successful owner cleanup",
        "failing owner cleanup",
    ]
    assert surface.disposed is True
    assert surface._layout is None
    assert surface._paint is None
    assert surface._tree_revision is None
    assert surface._target is None
    assert surface._mounted is None

    surface.dispose()
    assert blur_attempts == ["blur"]
    assert cleanup_attempts == [
        "successful owner cleanup",
        "failing owner cleanup",
    ]


@pytest.mark.parametrize("target_kind", ["mounted", "widget"])
def test_native_surface_dispose_never_unmounts_borrowed_target(target_kind):
    cleanups = []

    @component
    def App():
        on_cleanup(lambda: cleanups.append("cleanup"))
        return Text("Borrowed")

    mounted = mount(App())
    target = mounted if target_kind == "mounted" else mounted.root_widget()
    surface = NativeSurface(target)

    surface.dispose()
    surface.dispose()

    assert surface.disposed is True
    assert mounted._unmounted is False
    assert cleanups == []

    unmount(mounted)
    assert cleanups == ["cleanup"]


def test_native_surface_public_api_rejects_use_after_dispose(tmp_path):
    surface = NativeSurface(Button("Run", onClick=lambda: None))
    surface.dispose()

    operations = [
        ("stylesheet getter", lambda: surface.stylesheet),
        ("stylesheet setter", lambda: setattr(surface, "stylesheet", None)),
        ("strict_styles getter", lambda: surface.strict_styles),
        ("strict_styles setter", lambda: setattr(surface, "strict_styles", False)),
        ("background getter", lambda: surface.background),
        ("background setter", lambda: setattr(surface, "background", "#000000")),
        ("renderer_backend getter", lambda: surface.renderer_backend),
        (
            "renderer_backend setter",
            lambda: setattr(
                surface,
                "renderer_backend",
                PYTHON_NATIVE_RENDERER_BACKEND,
            ),
        ),
        ("frame getter", lambda: surface.frame),
        ("frame setter", lambda: setattr(surface, "frame", 99)),
        ("focused_path getter", lambda: surface.focused_path),
        ("focused_path setter", lambda: setattr(surface, "focused_path", None)),
        ("mounted", lambda: surface.mounted),
        ("target", lambda: surface.target),
        ("layout", lambda: surface.layout),
        ("paint", lambda: surface.paint),
        ("focused_box", lambda: surface.focused_box),
        ("refresh", surface.refresh),
        ("render_png", lambda: surface.render_png(tmp_path / "disposed.png")),
        ("hit_test", lambda: surface.hit_test(0, 0)),
        ("click", lambda: surface.click(0, 0)),
        ("focus", lambda: surface.focus(None)),
        ("focus_next", surface.focus_next),
        ("key_down", lambda: surface.key_down("Enter")),
        ("input_text", lambda: surface.input_text("value")),
        ("input_value", surface.input_value),
        ("scroll", lambda: surface.scroll(0, 0, 1)),
        ("box", lambda: surface.box(())),
    ]

    for operation_name, operation in operations:
        with pytest.raises(RuntimeError) as caught:
            operation()
        assert (
            str(caught.value)
            == "NativeSurface has been disposed and cannot be used."
        ), operation_name

    assert surface.disposed is True
    assert not (tmp_path / "disposed.png").exists()


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


def test_pillow_native_renderer_backend_writes_readable_png_when_available(tmp_path):
    pytest.importorskip("PIL")
    mounted = mount(VStack(Text("Readable text"), padding=4))
    marker_output = tmp_path / "marker.png"
    pillow_output = tmp_path / "pillow.png"

    marker_paint = render_native_png(mounted, marker_output)
    pillow_backend = PillowNativeRendererBackend()
    pillow_paint = render_native_png(
        mounted,
        pillow_output,
        renderer_backend=pillow_backend,
    )

    assert pillow_paint.commands
    assert marker_paint.width != pillow_paint.width or marker_output.read_bytes() != (
        pillow_output.read_bytes()
    )
    assert pillow_output.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")


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
