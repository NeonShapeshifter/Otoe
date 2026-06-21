from __future__ import annotations

from pathlib import Path

from examples.admin.settings_console import MemoryAdminSettingsProvider, app as admin_app
from examples.data_workflow.workbench import (
    MemoryDataWorkflowProvider,
    app as data_workflow_app,
)
from examples.hardware.control_panel import FakeHardwareProvider, app as hardware_app
from otoe import LayoutBox, NativeLayout, NativePaint, NativeSurface, PaintCommand


PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def test_hardware_reference_app_native_evidence_click_and_png(tmp_path):
    provider = FakeHardwareProvider()
    surface = NativeSurface(hardware_app(provider=provider))

    layout, paint = _assert_native_evidence(
        surface,
        tmp_path,
        "hardware",
        expected_texts=("Otoe Hardware Lab", "Bench Controller A17", "Refresh"),
    )
    refresh = _box_with_text(layout, "Refresh", name="Button")

    surface.click(refresh.x + 1, refresh.y + 1)

    assert provider.snapshot().mode == "Telemetry refreshed"
    assert _has_paint_text(paint, "Refresh")


def test_admin_reference_app_native_evidence_input_focus_and_png(tmp_path):
    provider = MemoryAdminSettingsProvider()
    surface = NativeSurface(admin_app(route="settings", provider=provider))

    layout, paint = _assert_native_evidence(
        surface,
        tmp_path,
        "admin-settings",
        expected_texts=("Otoe Admin Console", "Workspace settings", "Local Workspace"),
    )
    workspace_input = _first_box(layout, name="Input")

    surface.focus(workspace_input.path)
    surface.input_text("Native Evidence Workspace")

    assert surface.focused_path == workspace_input.path
    assert surface.input_value() == "Native Evidence Workspace"
    assert provider.snapshot().pending_changes == 1
    assert provider.snapshot().status == "Unsaved changes"
    assert _has_paint_text(paint, "Local Workspace")


def test_data_workflow_reference_app_native_evidence_search_input_and_png(tmp_path):
    provider = MemoryDataWorkflowProvider()
    surface = NativeSurface(data_workflow_app(route="queue", provider=provider))

    layout, paint = _assert_native_evidence(
        surface,
        tmp_path,
        "data-workflow",
        expected_texts=("Data Workflow Console", "Search records", "Arcadia Finance"),
    )
    search_input = _first_box(layout, name="Input")

    surface.input_text("helio", path=search_input.path)

    assert provider.snapshot().query == "helio"
    assert _box_with_text(surface.layout, "Helio Works") is not None
    assert not _has_layout_text(surface.layout, "Arcadia Finance")
    assert _has_paint_text(paint, "Search records")


def _assert_native_evidence(
    surface: NativeSurface,
    tmp_path: Path,
    name: str,
    *,
    expected_texts: tuple[str, ...],
) -> tuple[NativeLayout, NativePaint]:
    layout = surface.layout
    paint = surface.paint

    assert layout.root.width > 0
    assert layout.root.height > 0
    assert len(layout.boxes) >= len(expected_texts)
    assert any(box.name == "Button" for box in layout.boxes)
    assert any(command.kind == "rect" for command in paint.commands)
    assert any(command.kind == "text" for command in paint.commands)
    for text in expected_texts:
        assert _has_layout_text(layout, text)
        assert _has_paint_text(paint, text)

    output = tmp_path / f"{name}.png"
    rendered = surface.render_png(output)
    data = output.read_bytes()

    assert rendered.width == surface.paint.width
    assert rendered.height == surface.paint.height
    assert rendered.commands
    assert data.startswith(PNG_SIGNATURE)
    assert len(data) > 100

    return layout, paint


def _first_box(layout: NativeLayout, *, name: str) -> LayoutBox:
    return next(box for box in layout.boxes if box.name == name)


def _box_with_text(
    layout: NativeLayout,
    text: str,
    *,
    name: str | None = None,
) -> LayoutBox:
    return next(
        box
        for box in layout.boxes
        if box.text == text and (name is None or box.name == name)
    )


def _has_layout_text(layout: NativeLayout, text: str) -> bool:
    return any(box.text == text for box in layout.boxes)


def _has_paint_text(paint: NativePaint, text: str) -> bool:
    return any(_command_text_matches(command, text) for command in paint.commands)


def _command_text_matches(command: PaintCommand, text: str) -> bool:
    return command.kind == "text" and command.text == text
