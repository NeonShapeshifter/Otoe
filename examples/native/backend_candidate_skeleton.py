from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import struct
import sys
import zlib
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass
from math import ceil
from pathlib import Path
from typing import Any

from otoe import (
    Button,
    ComposedNativeRendererBackend,
    HStack,
    Input,
    LayoutBox,
    NativeLayout,
    NativePaint,
    NativeRendererBackend,
    NativeWindowDriver,
    NativeWindowEvent,
    PYTHON_NATIVE_RENDERER_BACKEND,
    PaintCommand,
    ScrollView,
    ShortcutScope,
    Text,
    VStack,
    component,
    computed,
    css,
    mount,
    run_native,
    signal,
    unmount,
)
from otoe.capabilities import (
    CapabilityProfileError,
    backend_capability_profile,
    load_backend_capability_profile,
)
from otoe.backend_coverage import (
    backend_coverage_report_to_dict as _backend_coverage_report_to_dict,
)
from otoe.plan import plan_mounted
from otoe.style_ir import compiled_styles_to_dict
from otoe.style_ops import (
    StyleIRError,
    StyleOpsClassReplay,
    StyleOpsDirectReplay,
    apply_style_ops,
    expected_omitted_style_ops,
    load_style_ir,
)
from otoe._native_shared import native_input_support, native_widget_support

from .window_demo import NativeWindowDemo


TASK_BOARD_TITLES = ("Runtime bridge", "Input polish", "Docs pass")
INPUT_EVENT_CAPABILITIES = {
    "onBlur": "focus",
    "onChange": "input_text",
    "onClick": "click",
    "onFocus": "focus",
    "onGlobalKeyDown": "shortcut",
    "onKeyDown": "key_down",
    "onScroll": "wheel",
}


@dataclass(frozen=True)
class MinimalBackendCandidateReplay:
    title: str
    initial_frame: int
    final_frame: int
    initial_focus: tuple[str, str | None] | None
    final_focus: tuple[str, str | None] | None
    echo_visible: bool
    clicked_visible: bool
    shortcut_visible: bool
    scrolled: bool

    @property
    def passed(self) -> bool:
        return (
            self.final_frame > self.initial_frame
            and self.initial_focus == ("Input", "seed")
            and self.echo_visible
            and self.clicked_visible
            and self.shortcut_visible
            and self.scrolled
        )


@dataclass(frozen=True)
class TaskBoardBackendCandidateReplay:
    title: str
    initial_frame: int
    final_frame: int
    filtered_titles: tuple[str, ...]
    modal_visible_after_click: bool
    modal_closed_after_escape: bool
    shortcut_text_after_escape: str | None
    reset_titles: tuple[str, ...]
    scrolled: bool
    final_focus: tuple[str, str | None] | None

    @property
    def passed(self) -> bool:
        return (
            self.final_frame > self.initial_frame
            and self.filtered_titles == ("Input polish",)
            and self.modal_visible_after_click
            and self.modal_closed_after_escape
            and self.shortcut_text_after_escape == "Shortcuts 1"
            and self.reset_titles == TASK_BOARD_TITLES
            and self.scrolled
            and self.final_focus is not None
        )


@dataclass(frozen=True)
class BackendCandidateAcceptanceReport:
    minimal: MinimalBackendCandidateReplay
    task_board: TaskBoardBackendCandidateReplay

    @property
    def passed(self) -> bool:
        return self.minimal.passed and self.task_board.passed


@dataclass(frozen=True)
class RendererCandidateCall:
    phase: str
    subject: str
    layout_boxes: int = 0
    paint_commands: int = 0


@dataclass(frozen=True)
class RendererContractBoxSnapshot:
    path: tuple[int, ...]
    name: str
    bounds: tuple[int, int, int, int]
    text: str | None
    events: tuple[str, ...]
    state: tuple[str, ...]


@dataclass(frozen=True)
class RendererContractPaintSnapshot:
    kind: str
    path: tuple[int, ...]
    bounds: tuple[int, int, int, int]
    fill: str | None
    stroke: str | None
    stroke_width: int
    radius: int
    text: str | None
    color: str | None
    font_size: int
    clip: tuple[int, int, int, int] | None


@dataclass(frozen=True)
class RendererCandidateAcceptanceReport:
    renderer_backend: str
    headless: "HeadlessCandidateAcceptanceReport"
    calls: tuple[RendererCandidateCall, ...]

    @property
    def passed(self) -> bool:
        phases = {call.phase for call in self.calls}
        return (
            self.headless.passed
            and {"layout", "paint"} <= phases
            and any(call.layout_boxes > 0 for call in self.calls)
            and any(call.paint_commands > 0 for call in self.calls)
        )


@dataclass(frozen=True)
class HeadlessCandidateFrameSummary:
    label: str
    frame: int
    size: tuple[int, int]
    root_name: str
    focused: tuple[str, str | None] | None
    layout_boxes: int
    paint_commands: int
    visible_text: tuple[str, ...]
    paint_kinds: tuple[str, ...]
    layout_snapshot: tuple[RendererContractBoxSnapshot, ...]
    paint_snapshot: tuple[RendererContractPaintSnapshot, ...]


@dataclass(frozen=True)
class HeadlessCandidateRunReport:
    backend: str
    renderer_backend: str
    title: str
    before: HeadlessCandidateFrameSummary
    after: HeadlessCandidateFrameSummary
    replay: object

    @property
    def passed(self) -> bool:
        return (
            bool(getattr(self.replay, "passed", False))
            and self.after.frame > self.before.frame
            and self.after.layout_boxes > 0
            and self.after.paint_commands > 0
        )


@dataclass(frozen=True)
class HeadlessCandidateAcceptanceReport:
    minimal: HeadlessCandidateRunReport
    task_board: HeadlessCandidateRunReport

    @property
    def passed(self) -> bool:
        return self.minimal.passed and self.task_board.passed


@dataclass(frozen=True)
class LayoutOnlyCandidateAcceptanceReport:
    renderer_backend: str
    minimal: HeadlessCandidateRunReport
    task_board: HeadlessCandidateRunReport
    calls: tuple[RendererCandidateCall, ...]

    @property
    def passed(self) -> bool:
        phases = {call.phase for call in self.calls}
        return (
            self.minimal.passed
            and self.task_board.passed
            and {"layout", "paint"} <= phases
            and self.minimal.after.root_name == "ShortcutScope"
            and self.task_board.after.root_name == "ShortcutScope"
            and self.minimal.after.layout_boxes > 0
            and self.task_board.after.layout_boxes > 0
        )


@dataclass(frozen=True)
class LayoutOnlyTaskBoardStaticAcceptanceReport:
    renderer_backend: str
    frame: HeadlessCandidateFrameSummary
    calls: tuple[RendererCandidateCall, ...]

    @property
    def passed(self) -> bool:
        phases = {call.phase for call in self.calls}
        return (
            {"layout", "paint"} <= phases
            and self.frame.root_name == "ShortcutScope"
            and self.frame.size == (420, 257)
            and self.frame.focused == ("Input", "Search tasks")
            and self.frame.layout_boxes == 31
            and self.frame.paint_commands == 33
            and "Native Task Board" in self.frame.visible_text
            and "3 visible" in self.frame.visible_text
            and set(TASK_BOARD_TITLES) <= set(self.frame.visible_text)
            and "rect" in self.frame.paint_kinds
            and "text" in self.frame.paint_kinds
        )


@dataclass(frozen=True)
class ComposedRendererCandidateAcceptanceReport:
    renderer_backend: str
    layout_backend: str
    paint_backend: str
    raster_backend: str
    headless: HeadlessCandidateAcceptanceReport
    png_frame: HeadlessCandidateFrameSummary
    png_path: str
    layout_calls: tuple[RendererCandidateCall, ...]
    paint_calls: tuple[RendererCandidateCall, ...]
    raster_calls: tuple[RendererCandidateCall, ...]

    @property
    def passed(self) -> bool:
        return (
            self.headless.passed
            and self.png_frame.root_name == "ShortcutScope"
            and self.png_frame.layout_boxes > 0
            and self.png_frame.paint_commands > 0
            and any(
                call.phase == "layout" and call.layout_boxes > 0
                for call in self.layout_calls
            )
            and any(
                call.phase == "paint" and call.paint_commands > 0
                for call in self.paint_calls
            )
            and any(
                call.phase == "write_png" and call.paint_commands > 0
                for call in self.raster_calls
            )
        )


@dataclass(frozen=True)
class StyleOpsCandidateClassReport:
    class_name: str
    selector: str
    missing: bool
    expected_missing: bool
    applied_declarations: dict[str, Any]
    expected_declarations: dict[str, Any]
    omitted_ops: tuple[dict[str, Any], ...]
    expected_omitted_ops: tuple[dict[str, Any], ...]
    errors: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return (
            not self.errors
            and self.missing is self.expected_missing
            and self.applied_declarations == self.expected_declarations
            and self.omitted_ops == self.expected_omitted_ops
        )


@dataclass(frozen=True)
class StyleOpsCandidateDirectStyleReport:
    path: tuple[int, ...]
    widget: str
    expected_widget: str | None
    applied_declarations: dict[str, Any]
    expected_declarations: dict[str, Any]
    omitted_ops: tuple[dict[str, Any], ...]
    expected_omitted_ops: tuple[dict[str, Any], ...]
    errors: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return (
            not self.errors
            and self.expected_widget == self.widget
            and self.applied_declarations == self.expected_declarations
            and self.omitted_ops == self.expected_omitted_ops
        )


@dataclass(frozen=True)
class StyleOpsCandidateAcceptanceReport:
    backend: Any
    style_ops_schema_version: Any
    style_ops_format: Any
    style_support: dict[str, str]
    classes: tuple[StyleOpsCandidateClassReport, ...]
    errors: tuple[str, ...]
    direct_styles: tuple[StyleOpsCandidateDirectStyleReport, ...] = ()

    @property
    def passed(self) -> bool:
        return (
            not self.errors
            and self.style_ops_schema_version == 1
            and self.style_ops_format == "otoe-style-ops"
            and bool(self.classes)
            and all(class_report.passed for class_report in self.classes)
            and all(
                direct_style_report.passed
                for direct_style_report in self.direct_styles
            )
        )


class RecordingRendererCandidate:
    """Renderer-candidate skeleton that records the SPI calls it receives."""

    name = "recording-renderer-candidate"

    def __init__(
        self,
        *,
        inner: NativeRendererBackend | None = None,
        name: str | None = None,
    ) -> None:
        self.name = name or self.name
        self._inner = inner or PYTHON_NATIVE_RENDERER_BACKEND
        self.calls: list[RendererCandidateCall] = []

    @property
    def layout_calls(self) -> int:
        return self._count("layout")

    @property
    def paint_calls(self) -> int:
        return self._count("paint")

    @property
    def write_png_calls(self) -> int:
        return self._count("write_png")

    def layout(
        self,
        target: Any,
        *,
        stylesheet: Any = None,
        strict_styles: bool = True,
    ) -> NativeLayout:
        layout = self._inner.layout(
            target,
            stylesheet=stylesheet,
            strict_styles=strict_styles,
        )
        self.calls.append(
            RendererCandidateCall(
                phase="layout",
                subject=_target_name(target),
                layout_boxes=len(layout.boxes),
            )
        )
        return layout

    def paint(
        self,
        layout: NativeLayout,
        *,
        background: str = "#ffffff",
        focused_path: tuple[int, ...] | None = None,
    ) -> NativePaint:
        paint = self._inner.paint(
            layout,
            background=background,
            focused_path=focused_path,
        )
        self.calls.append(
            RendererCandidateCall(
                phase="paint",
                subject=layout.root.name,
                layout_boxes=len(layout.boxes),
                paint_commands=len(paint.commands),
            )
        )
        return paint

    def write_png(self, paint: NativePaint, path: str | Path) -> None:
        self._inner.write_png(paint, path)
        self.calls.append(
            RendererCandidateCall(
                phase="write_png",
                subject=Path(path).name,
                paint_commands=len(paint.commands),
            )
        )

    def _count(self, phase: str) -> int:
        return sum(1 for call in self.calls if call.phase == phase)


class RasterOnlyRendererCandidate(RecordingRendererCandidate):
    """Candidate that keeps Python layout/paint and replaces only PNG raster."""

    name = "raster-only-renderer-candidate"

    def write_png(self, paint: NativePaint, path: str | Path) -> None:
        _write_candidate_png(paint, path)
        self.calls.append(
            RendererCandidateCall(
                phase="write_png",
                subject=Path(path).name,
                paint_commands=len(paint.commands),
            )
        )


class PaintOnlyRendererCandidate(RecordingRendererCandidate):
    """Candidate that keeps Python layout/raster and replaces only paint."""

    name = "paint-only-renderer-candidate"

    def paint(
        self,
        layout: NativeLayout,
        *,
        background: str = "#ffffff",
        focused_path: tuple[int, ...] | None = None,
    ) -> NativePaint:
        paint = _paint_candidate_layout(
            layout,
            background=background,
            focused_path=focused_path,
        )
        self.calls.append(
            RendererCandidateCall(
                phase="paint",
                subject=layout.root.name,
                layout_boxes=len(layout.boxes),
                paint_commands=len(paint.commands),
            )
        )
        return paint


class LayoutOnlyRendererCandidate(RecordingRendererCandidate):
    """Minimal replay candidate that replaces only layout."""

    name = "layout-only-renderer-candidate"

    def layout(
        self,
        target: Any,
        *,
        stylesheet: Any = None,
        strict_styles: bool = True,
    ) -> NativeLayout:
        layout = _layout_candidate_target(
            target,
            stylesheet=stylesheet,
            strict_styles=strict_styles,
        )
        self.calls.append(
            RendererCandidateCall(
                phase="layout",
                subject=_target_name(target),
                layout_boxes=len(layout.boxes),
            )
        )
        return layout


class RecordingBackendCandidate:
    """Small adapter skeleton for backend-candidate acceptance replays."""

    name = "recording-candidate"

    def __init__(
        self,
        replay: Callable[..., object],
    ) -> None:
        self._replay = replay
        self.replays: list[object] = []

    def run(self, driver: NativeWindowDriver, *, title: str = "Otoe") -> None:
        self.replays.append(self._replay(driver, title=title))


class HeadlessCandidateBackend:
    """No-window candidate adapter that records replay/layout/paint summaries."""

    name = "headless-candidate"

    def __init__(
        self,
        replay: Callable[..., object],
        *,
        name: str | None = None,
    ) -> None:
        self.name = name or self.name
        self._replay = replay
        self.reports: list[HeadlessCandidateRunReport] = []

    def run(self, driver: NativeWindowDriver, *, title: str = "Otoe") -> None:
        before = summarize_headless_candidate_frame(driver, label="before")
        replay = self._replay(driver, title=title)
        after = summarize_headless_candidate_frame(driver, label="after")
        self.reports.append(
            HeadlessCandidateRunReport(
                backend=self.name,
                renderer_backend=driver.surface.renderer_backend.name,
                title=title,
                before=before,
                after=after,
                replay=replay,
            )
        )


def run_backend_candidate_acceptance(
    *,
    renderer_backend: NativeRendererBackend | None = None,
) -> BackendCandidateAcceptanceReport:
    minimal_backend = RecordingBackendCandidate(replay_minimal_candidate)
    run_native(
        backend_candidate_app(),
        stylesheet=BACKEND_CANDIDATE_STYLES,
        title="Backend Candidate Minimal",
        backend=minimal_backend,
        renderer_backend=renderer_backend,
    )

    task_board_backend = RecordingBackendCandidate(replay_task_board_candidate)
    run_native(
        NativeWindowDemo(renderer_backend=renderer_backend).driver,
        title="Backend Candidate Task Board",
        backend=task_board_backend,
    )

    return BackendCandidateAcceptanceReport(
        minimal=_last_replay(minimal_backend, MinimalBackendCandidateReplay),
        task_board=_last_replay(task_board_backend, TaskBoardBackendCandidateReplay),
    )


def run_headless_candidate_acceptance(
    *,
    renderer_backend: NativeRendererBackend | None = None,
) -> HeadlessCandidateAcceptanceReport:
    minimal_backend = HeadlessCandidateBackend(replay_minimal_candidate)
    run_native(
        backend_candidate_app(),
        stylesheet=BACKEND_CANDIDATE_STYLES,
        title="Headless Candidate Minimal",
        backend=minimal_backend,
        renderer_backend=renderer_backend,
    )

    task_board_backend = HeadlessCandidateBackend(replay_task_board_candidate)
    run_native(
        NativeWindowDemo(renderer_backend=renderer_backend).driver,
        title="Headless Candidate Task Board",
        backend=task_board_backend,
    )

    return HeadlessCandidateAcceptanceReport(
        minimal=_last_report(minimal_backend),
        task_board=_last_report(task_board_backend),
    )


def run_renderer_candidate_acceptance() -> RendererCandidateAcceptanceReport:
    renderer_backend = RecordingRendererCandidate()
    return run_renderer_candidate_acceptance_with(renderer_backend)


def run_raster_only_renderer_candidate_acceptance() -> RendererCandidateAcceptanceReport:
    return run_renderer_candidate_acceptance_with(RasterOnlyRendererCandidate())


def run_paint_only_renderer_candidate_acceptance() -> RendererCandidateAcceptanceReport:
    return run_renderer_candidate_acceptance_with(PaintOnlyRendererCandidate())


def run_layout_only_renderer_candidate_acceptance() -> LayoutOnlyCandidateAcceptanceReport:
    renderer_backend = LayoutOnlyRendererCandidate()
    headless = run_headless_candidate_acceptance(renderer_backend=renderer_backend)
    return LayoutOnlyCandidateAcceptanceReport(
        renderer_backend=renderer_backend.name,
        minimal=headless.minimal,
        task_board=headless.task_board,
        calls=tuple(renderer_backend.calls),
    )


def run_layout_only_task_board_static_acceptance() -> LayoutOnlyTaskBoardStaticAcceptanceReport:
    renderer_backend = LayoutOnlyRendererCandidate()
    demo = NativeWindowDemo(renderer_backend=renderer_backend)
    return LayoutOnlyTaskBoardStaticAcceptanceReport(
        renderer_backend=renderer_backend.name,
        frame=summarize_headless_candidate_frame(
            demo.driver,
            label="task_board_static",
        ),
        calls=tuple(renderer_backend.calls),
    )


def run_composed_renderer_candidate_acceptance(
    output_path: str | Path,
) -> ComposedRendererCandidateAcceptanceReport:
    layout_backend = LayoutOnlyRendererCandidate()
    paint_backend = PaintOnlyRendererCandidate()
    raster_backend = RasterOnlyRendererCandidate()
    renderer_backend = ComposedNativeRendererBackend(
        layout_backend=layout_backend,
        paint_backend=paint_backend,
        raster_backend=raster_backend,
        name="composed-layout-paint-raster-candidate",
    )
    headless = run_headless_candidate_acceptance(renderer_backend=renderer_backend)

    png_driver = NativeWindowDriver.from_target(
        backend_candidate_app(),
        stylesheet=BACKEND_CANDIDATE_STYLES,
        renderer_backend=renderer_backend,
    )
    png_driver.render_png(output_path)

    return ComposedRendererCandidateAcceptanceReport(
        renderer_backend=renderer_backend.name,
        layout_backend=layout_backend.name,
        paint_backend=paint_backend.name,
        raster_backend=raster_backend.name,
        headless=headless,
        png_frame=summarize_headless_candidate_frame(
            png_driver,
            label="png_smoke",
        ),
        png_path=str(output_path),
        layout_calls=tuple(layout_backend.calls),
        paint_calls=tuple(paint_backend.calls),
        raster_calls=tuple(raster_backend.calls),
    )


def run_style_ops_candidate_acceptance(
    style_artifact: dict[str, Any] | None = None,
) -> StyleOpsCandidateAcceptanceReport:
    artifact = (
        backend_candidate_style_artifact()
        if style_artifact is None
        else style_artifact
    )
    if not isinstance(artifact, dict):
        return StyleOpsCandidateAcceptanceReport(
            backend=None,
            style_ops_schema_version=None,
            style_ops_format=None,
            style_support={},
            classes=(),
            errors=("style artifact must be a JSON object",),
        )

    try:
        style_ir = load_style_ir(artifact)
    except StyleIRError as exc:
        style_ops = artifact.get("styleOps") if isinstance(artifact, dict) else None
        style_ops_schema_version = (
            style_ops.get("schemaVersion") if isinstance(style_ops, dict) else None
        )
        style_ops_format = (
            style_ops.get("format") if isinstance(style_ops, dict) else None
        )
        return StyleOpsCandidateAcceptanceReport(
            backend=artifact.get("backend") if isinstance(artifact, dict) else None,
            style_ops_schema_version=style_ops_schema_version,
            style_ops_format=style_ops_format,
            style_support={},
            classes=(),
            errors=(str(exc),),
        )

    application = apply_style_ops(style_ir)
    errors: list[str] = list(application.errors)
    class_reports = tuple(
        _replay_style_ops_class(replay, style_ir.rules_by_class, style_ir.style_support)
        for replay in application.classes
    )
    direct_style_reports = tuple(
        _replay_style_ops_direct_style(
            replay,
            style_ir.direct_styles_by_path,
            style_ir.style_support,
        )
        for replay in application.direct_styles
    )
    classes_with_ops = {
        class_report.class_name
        for class_report in class_reports
        if class_report.class_name != "<invalid>"
    }
    missing_ops = sorted(set(style_ir.rules_by_class) - classes_with_ops)
    if missing_ops:
        errors.append(
            "styleOps missing classes from compiled rules: "
            + ", ".join(missing_ops)
        )
    direct_paths_with_ops = {report.path for report in direct_style_reports}
    missing_direct_ops = sorted(
        set(style_ir.direct_styles_by_path) - direct_paths_with_ops
    )
    if missing_direct_ops:
        errors.append(
            "styleOps missing directStyles from compiled artifact: "
            + ", ".join(str(list(path)) for path in missing_direct_ops)
        )

    return StyleOpsCandidateAcceptanceReport(
        backend=style_ir.backend,
        style_ops_schema_version=style_ir.style_ops_schema_version,
        style_ops_format=style_ir.style_ops_format,
        style_support=dict(style_ir.style_support),
        classes=class_reports,
        errors=tuple(errors),
        direct_styles=direct_style_reports,
    )


def backend_candidate_style_artifact() -> dict[str, Any]:
    mounted = mount(backend_candidate_app())
    try:
        plan = plan_mounted(
            mounted,
            stylesheet=BACKEND_CANDIDATE_STYLES,
        )
        return compiled_styles_to_dict(
            plan,
            target="examples.native.backend_candidate_skeleton:backend_candidate_app",
            stylesheet=BACKEND_CANDIDATE_STYLES,
        )
    finally:
        unmount(mounted)


def run_renderer_candidate_acceptance_with(
    renderer_backend: RecordingRendererCandidate,
) -> RendererCandidateAcceptanceReport:
    headless = run_headless_candidate_acceptance(renderer_backend=renderer_backend)
    return RendererCandidateAcceptanceReport(
        renderer_backend=renderer_backend.name,
        headless=headless,
        calls=tuple(renderer_backend.calls),
    )


def acceptance_report_to_dict(
    report: HeadlessCandidateAcceptanceReport,
) -> dict[str, Any]:
    payload = asdict(report)
    payload["passed"] = report.passed
    payload["minimal"]["passed"] = report.minimal.passed
    payload["task_board"]["passed"] = report.task_board.passed
    payload["minimal"]["replay"]["passed"] = bool(
        getattr(report.minimal.replay, "passed", False)
    )
    payload["task_board"]["replay"]["passed"] = bool(
        getattr(report.task_board.replay, "passed", False)
    )
    return payload


def renderer_contract_snapshot_to_dict(
    report: RendererCandidateAcceptanceReport,
) -> dict[str, Any]:
    return {
        "schemaVersion": 1,
        "rendererBackend": report.renderer_backend,
        "passed": report.passed,
        "capabilityAudit": _renderer_capability_audit_to_dict(report.headless),
        "calls": [_renderer_call_to_dict(call) for call in report.calls],
        "runs": {
            "minimal": _run_contract_snapshot_to_dict(report.headless.minimal),
            "taskBoard": _run_contract_snapshot_to_dict(report.headless.task_board),
        },
    }


def compact_renderer_contract_snapshot_to_dict(
    report: RendererCandidateAcceptanceReport,
) -> dict[str, Any]:
    return {
        "schemaVersion": 1,
        "format": "renderer-contract-compact",
        "rendererBackend": report.renderer_backend,
        "passed": report.passed,
        "capabilityAudit": _renderer_capability_audit_to_dict(report.headless),
        "calls": _compact_call_stream(report.calls),
        "runs": {
            "minimal": _compact_run_contract_snapshot_to_dict(report.headless.minimal),
            "taskBoard": _compact_run_contract_snapshot_to_dict(
                report.headless.task_board
            ),
        },
    }


def composed_renderer_contract_snapshot_to_dict(
    report: ComposedRendererCandidateAcceptanceReport,
) -> dict[str, Any]:
    return {
        "schemaVersion": 1,
        "rendererBackend": report.renderer_backend,
        "passed": report.passed,
        "capabilityAudit": _renderer_capability_audit_to_dict(report.headless),
        "capabilities": {
            "layout": report.layout_backend,
            "paint": report.paint_backend,
            "raster": report.raster_backend,
        },
        "calls": {
            "layout": [_renderer_call_to_dict(call) for call in report.layout_calls],
            "paint": [_renderer_call_to_dict(call) for call in report.paint_calls],
            "raster": [_renderer_call_to_dict(call) for call in report.raster_calls],
        },
        "runs": {
            "minimal": _run_contract_snapshot_to_dict(report.headless.minimal),
            "taskBoard": _run_contract_snapshot_to_dict(report.headless.task_board),
        },
        "pngSmoke": {
            "path": Path(report.png_path).name,
            "frame": _frame_contract_snapshot_to_dict(report.png_frame),
        },
    }


def compact_composed_renderer_contract_snapshot_to_dict(
    report: ComposedRendererCandidateAcceptanceReport,
) -> dict[str, Any]:
    return {
        "schemaVersion": 1,
        "format": "composed-renderer-contract-compact",
        "rendererBackend": report.renderer_backend,
        "passed": report.passed,
        "capabilityAudit": _renderer_capability_audit_to_dict(report.headless),
        "capabilities": {
            "layout": report.layout_backend,
            "paint": report.paint_backend,
            "raster": report.raster_backend,
        },
        "calls": {
            "layout": _compact_call_stream(report.layout_calls),
            "paint": _compact_call_stream(report.paint_calls),
            "raster": _compact_call_stream(report.raster_calls),
        },
        "runs": {
            "minimal": _compact_run_contract_snapshot_to_dict(report.headless.minimal),
            "taskBoard": _compact_run_contract_snapshot_to_dict(
                report.headless.task_board
            ),
        },
        "pngSmoke": {
            "path": Path(report.png_path).name,
            "frame": _compact_frame_contract_snapshot_to_dict(report.png_frame),
        },
    }


def style_ops_candidate_report_to_dict(
    report: StyleOpsCandidateAcceptanceReport,
) -> dict[str, Any]:
    return {
        "schemaVersion": 1,
        "format": "style-ops-contract",
        "passed": report.passed,
        "backend": report.backend,
        "styleOps": {
            "schemaVersion": report.style_ops_schema_version,
            "format": report.style_ops_format,
        },
        "capabilityAudit": _style_ops_capability_audit_to_dict(report),
        "classes": [
            _style_ops_class_report_to_dict(class_report)
            for class_report in report.classes
        ],
        "directStyles": [
            _style_ops_direct_style_report_to_dict(direct_style_report)
            for direct_style_report in report.direct_styles
        ],
        "errors": list(report.errors),
    }


def backend_readiness_report_to_dict(
    *,
    renderer_report: RendererCandidateAcceptanceReport | None = None,
    style_ops_report: StyleOpsCandidateAcceptanceReport | None = None,
) -> dict[str, Any]:
    renderer_report = renderer_report or run_renderer_candidate_acceptance()
    style_ops_report = style_ops_report or run_style_ops_candidate_acceptance()
    renderer_contract = compact_renderer_contract_snapshot_to_dict(renderer_report)
    style_ops_contract = style_ops_candidate_report_to_dict(style_ops_report)
    gates = {
        "rendererReplay": renderer_report.passed,
        "styleOpsReplay": style_ops_report.passed,
        "widgetInputAudit": _audit_has_no_unsupported(
            renderer_contract["capabilityAudit"],
            unsupported_keys=("unsupportedWidgets", "unsupportedInputs"),
        ),
        "styleCapabilityAudit": _audit_has_no_unsupported(
            style_ops_contract["capabilityAudit"],
            unsupported_keys=("unsupportedProperties",),
        ),
    }
    blockers = [
        name
        for name, passed in gates.items()
        if not passed
    ]
    return {
        "schemaVersion": 1,
        "format": "backend-readiness-report",
        "passed": not blockers,
        "readiness": "ready-for-candidate-comparison" if not blockers else "blocked",
        "gates": gates,
        "blockers": blockers,
        "renderer": {
            "backend": renderer_report.renderer_backend,
            "calls": renderer_contract["calls"],
            "capabilityAudit": renderer_contract["capabilityAudit"],
        },
        "styleOps": {
            "backend": style_ops_report.backend,
            "schemaVersion": style_ops_report.style_ops_schema_version,
            "format": style_ops_report.style_ops_format,
            "capabilityAudit": style_ops_contract["capabilityAudit"],
            "classCount": len(style_ops_report.classes),
            "directStyleCount": len(style_ops_report.direct_styles),
            "errors": _style_ops_report_errors(style_ops_report),
        },
        "requirements": _backend_readiness_requirements(
            renderer_contract["capabilityAudit"],
            style_ops_contract["capabilityAudit"],
        ),
    }


def backend_coverage_report_to_dict(
    declaration: dict[str, Any],
    *,
    readiness_report: dict[str, Any] | None = None,
) -> dict[str, Any]:
    readiness_report = readiness_report or backend_readiness_report_to_dict()
    return _backend_coverage_report_to_dict(
        declaration,
        readiness_report=readiness_report,
    )


def format_acceptance_report(report: HeadlessCandidateAcceptanceReport) -> str:
    lines = [
        "backend candidate acceptance",
        f"status: {'passed' if report.passed else 'failed'}",
        _format_run_report("minimal", report.minimal),
        _format_run_report("task_board", report.task_board),
    ]
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m examples.native.backend_candidate_skeleton",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="print the headless candidate acceptance report as JSON",
    )
    parser.add_argument(
        "--renderer-contract-json",
        action="store_true",
        help="print the renderer SPI contract snapshot as JSON",
    )
    parser.add_argument(
        "--composed-renderer-contract-json",
        action="store_true",
        help="print the composed renderer SPI contract snapshot as JSON",
    )
    parser.add_argument(
        "--style-ops-contract-json",
        action="store_true",
        help="print the low-level styleOps replay contract as JSON",
    )
    parser.add_argument(
        "--backend-readiness-json",
        action="store_true",
        help="print a combined renderer and styleOps backend readiness report",
    )
    parser.add_argument(
        "--backend-coverage-declaration-json",
        action="store_true",
        help=(
            "compat: print a coverage declaration; prefer "
            "`python -m otoe backend-profile --coverage-declaration`"
        ),
    )
    parser.add_argument(
        "--backend-coverage-json",
        action="store_true",
        help=(
            "compat: print a backend coverage report; prefer "
            "`python -m otoe backend-coverage`"
        ),
    )
    parser.add_argument(
        "--backend-capability",
        help="backend capability profile used to derive coverage declarations",
    )
    parser.add_argument(
        "--backend-capability-profile",
        help="backend capability profile JSON used to derive coverage declarations",
    )
    parser.add_argument(
        "--coverage-declaration",
        help="backend coverage declaration JSON used by --backend-coverage-json",
    )
    parser.add_argument(
        "--style-artifact",
        help="optional otoe-styles.json path used by styleOps/readiness reports",
    )
    parser.add_argument(
        "--bundle",
        help="optional offline bundle directory used by styleOps/readiness reports",
    )
    parser.add_argument(
        "--compact-contract",
        action="store_true",
        help="print compact contract JSON with signatures and hashes",
    )
    parser.add_argument(
        "--contract-out",
        help="optional path to write contract JSON instead of printing it",
    )
    parser.add_argument(
        "--composed-renderer-png",
        default=str(Path("preview") / "native" / "composed_renderer_candidate.png"),
        help="PNG path used by --composed-renderer-contract-json",
    )
    args = parser.parse_args(argv)
    if args.renderer_contract_json:
        renderer_report = run_renderer_candidate_acceptance()
        payload = (
            compact_renderer_contract_snapshot_to_dict(renderer_report)
            if args.compact_contract
            else renderer_contract_snapshot_to_dict(renderer_report)
        )
        _emit_contract_payload(payload, output_path=args.contract_out)
        return 0 if renderer_report.passed else 1

    if args.composed_renderer_contract_json:
        composed_png = Path(args.composed_renderer_png)
        composed_png.parent.mkdir(parents=True, exist_ok=True)
        composed_report = run_composed_renderer_candidate_acceptance(composed_png)
        payload = (
            compact_composed_renderer_contract_snapshot_to_dict(composed_report)
            if args.compact_contract
            else composed_renderer_contract_snapshot_to_dict(composed_report)
        )
        _emit_contract_payload(payload, output_path=args.contract_out)
        return 0 if composed_report.passed else 1

    if args.style_ops_contract_json:
        if args.style_artifact is not None and args.bundle is not None:
            parser.error("--style-artifact and --bundle are mutually exclusive")
        try:
            style_artifact = _style_artifact_from_args(args)
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            print(f"style-ops-contract: {exc}", file=sys.stderr)
            return 1
        style_ops_report = run_style_ops_candidate_acceptance(style_artifact)
        payload = style_ops_candidate_report_to_dict(style_ops_report)
        _emit_contract_payload(payload, output_path=args.contract_out)
        return 0 if style_ops_report.passed else 1

    if args.backend_readiness_json:
        if args.style_artifact is not None and args.bundle is not None:
            parser.error("--style-artifact and --bundle are mutually exclusive")
        try:
            style_artifact = _style_artifact_from_args(args)
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            print(f"backend-readiness: {exc}", file=sys.stderr)
            return 1
        payload = backend_readiness_report_to_dict(
            style_ops_report=run_style_ops_candidate_acceptance(style_artifact)
        )
        _emit_contract_payload(payload, output_path=args.contract_out)
        return 0 if payload["passed"] else 1

    if args.backend_coverage_declaration_json:
        _warn_backend_coverage_compat("--backend-coverage-declaration-json")
        if args.coverage_declaration is not None:
            parser.error(
                "--coverage-declaration cannot be used with "
                "--backend-coverage-declaration-json"
            )
        if (
            args.backend_capability is not None
            and args.backend_capability_profile is not None
        ):
            parser.error(
                "--backend-capability and --backend-capability-profile are "
                "mutually exclusive"
            )
        try:
            payload = _coverage_declaration_from_backend_args(args)
        except (OSError, CapabilityProfileError) as exc:
            print(f"backend-coverage-declaration: {exc}", file=sys.stderr)
            return 1
        _emit_contract_payload(payload, output_path=args.contract_out)
        return 0

    if args.backend_coverage_json:
        _warn_backend_coverage_compat("--backend-coverage-json")
        if args.coverage_declaration is None and args.backend_capability is None:
            if args.backend_capability_profile is None:
                parser.error(
                    "--coverage-declaration, --backend-capability, or "
                    "--backend-capability-profile is required with "
                    "--backend-coverage-json"
                )
        coverage_sources = sum(
            source is not None
            for source in (
                args.coverage_declaration,
                args.backend_capability,
                args.backend_capability_profile,
            )
        )
        if coverage_sources > 1:
            parser.error(
                "--coverage-declaration, --backend-capability, and "
                "--backend-capability-profile are mutually exclusive with "
                "--backend-coverage-json"
            )
        if args.style_artifact is not None and args.bundle is not None:
            parser.error("--style-artifact and --bundle are mutually exclusive")
        try:
            declaration = _coverage_declaration_from_args(args)
            style_artifact = _style_artifact_from_args(args)
        except (
            OSError,
            json.JSONDecodeError,
            ValueError,
            CapabilityProfileError,
        ) as exc:
            print(f"backend-coverage: {exc}", file=sys.stderr)
            return 1
        readiness_report = backend_readiness_report_to_dict(
            style_ops_report=run_style_ops_candidate_acceptance(style_artifact)
        )
        payload = backend_coverage_report_to_dict(
            declaration,
            readiness_report=readiness_report,
        )
        _emit_contract_payload(payload, output_path=args.contract_out)
        return 0 if payload["passed"] else 1

    report = run_headless_candidate_acceptance()

    if args.json:
        print(json.dumps(acceptance_report_to_dict(report), indent=2, sort_keys=True))
    else:
        print(format_acceptance_report(report))
    return 0 if report.passed else 1


def _warn_backend_coverage_compat(flag: str) -> None:
    print(
        "backend-candidate-skeleton: "
        f"{flag} is compatibility-only; prefer python -m otoe "
        "backend-profile/backend-coverage for coverage workflows.",
        file=sys.stderr,
    )


def _emit_contract_payload(
    payload: dict[str, Any],
    *,
    output_path: str | None,
) -> None:
    encoded = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if output_path is None:
        print(encoded, end="")
        return
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(encoded, encoding="utf-8")
    print(f"contract artifact: {path}")


def _load_style_artifact(path: str) -> dict[str, Any]:
    return _load_json_object(path, label="style artifact")


def _load_json_object(path: str, *, label: str) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected {label} {path!r} to contain a JSON object.")
    return payload


def _style_artifact_from_args(args: argparse.Namespace) -> dict[str, Any] | None:
    if args.bundle is not None:
        return _load_style_artifact_from_bundle(args.bundle)
    if args.style_artifact is not None:
        return _load_style_artifact(args.style_artifact)
    return None


def _coverage_declaration_from_args(args: argparse.Namespace) -> dict[str, Any]:
    if args.coverage_declaration is not None:
        return _load_json_object(
            args.coverage_declaration,
            label="coverage declaration",
        )
    return _coverage_declaration_from_backend_args(args)


def _coverage_declaration_from_backend_args(args: argparse.Namespace) -> dict[str, Any]:
    if args.backend_capability_profile is not None:
        profile = load_backend_capability_profile(args.backend_capability_profile)
    else:
        profile = backend_capability_profile(args.backend_capability)
    return profile.coverage_declaration()


def _load_style_artifact_from_bundle(bundle: str) -> dict[str, Any]:
    bundle_dir = Path(bundle).resolve()
    if not bundle_dir.is_dir():
        raise ValueError(f"Bundle {str(bundle_dir)!r} is not a directory.")
    manifest_path = bundle_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise ValueError(f"Expected {str(manifest_path)!r} to contain a JSON object.")

    _verify_bundle_runner(bundle_dir)
    styles_relative = manifest.get("styles", "otoe-styles.json")
    if not isinstance(styles_relative, str):
        raise ValueError("Bundle manifest field 'styles' must be a string.")
    styles_path = _bundle_relative_path(bundle_dir, styles_relative)
    return _load_style_artifact(str(styles_path))


def _verify_bundle_runner(bundle_dir: Path) -> None:
    runner = bundle_dir / "otoe-run.py"
    if not runner.is_file():
        raise ValueError(f"Bundle is missing {runner.name}.")
    result = subprocess.run(
        [sys.executable, str(runner), "--verify"],
        capture_output=True,
        cwd=bundle_dir,
        env={**os.environ, "PYTHONPATH": ""},
        text=True,
    )
    if result.returncode == 0:
        return
    details = result.stderr.strip() or result.stdout.strip()
    if not details:
        details = f"runner exited with status {result.returncode}"
    raise ValueError(f"Bundle verification failed: {details}")


def _bundle_relative_path(bundle_dir: Path, relative: str) -> Path:
    if relative in {"", "."}:
        raise ValueError(f"Bundle path {relative!r} is not safe.")
    path = Path(relative)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError(f"Bundle path {relative!r} is not safe.")
    return bundle_dir / path


def backend_candidate_app():
    query = signal("seed")
    clicked = signal("none")
    shortcuts = signal(0)
    scroll_y = signal(0)

    @component
    def CandidateApp():
        return ShortcutScope(
            VStack(
                Input(
                    value=query,
                    autoFocus=True,
                    onChange=lambda next_value: query.set(next_value),
                    className="candidate-input",
                ),
                HStack(
                    Button("One", onClick=lambda: clicked.set("one")),
                    Button("Two", onClick=lambda: clicked.set("two")),
                    className="candidate-toolbar",
                ),
                ScrollView(
                    Button("First", onClick=lambda: clicked.set("first")),
                    Button("Second", onClick=lambda: clicked.set("second")),
                    scrollY=scroll_y,
                    onScroll=lambda next_scroll_y: scroll_y.set(next_scroll_y),
                    className="candidate-list",
                ),
                Text(computed(lambda: f"Echo {query.value}")),
                Text(computed(lambda: f"Clicked {clicked.value}")),
                Text(computed(lambda: f"Shortcuts {shortcuts.value}")),
                className="candidate-shell",
            ),
            onKeyDown=lambda _payload: shortcuts.set(shortcuts.value + 1),
        )

    return CandidateApp()


BACKEND_CANDIDATE_STYLES = css(
    """
    .ui-shortcut-scope {
    }
    .candidate-shell {
      width: 220;
      padding: 8;
      gap: 6;
      background: #f8fafc;
      border-style: solid;
    }
    .candidate-input {
      width: 120;
    }
    .candidate-toolbar {
      width: 200;
      height: 44;
      gap: 4;
      align-items: center;
      justify-content: space-between;
    }
    .candidate-list {
      width: 200;
      height: 44;
      padding: 4;
      gap: 4;
      background: #ffffff;
    }
    """
)


def replay_minimal_candidate(
    driver: NativeWindowDriver,
    *,
    title: str = "Otoe",
) -> MinimalBackendCandidateReplay:
    initial_frame = driver.frame
    initial_focus = focused_box_summary(driver)

    driver.dispatch(NativeWindowEvent("input_text", text="alpha"))
    echo_visible = has_layout_text(driver, "Echo alpha")

    driver.dispatch(NativeWindowEvent("key_input", key="k", text="k", ctrl=True))
    shortcut_visible = has_layout_text(driver, "Shortcuts 1")

    button = box_with_text(driver, "Two")
    driver.click(button.x + 2, button.y + 2)
    clicked_visible = has_layout_text(driver, "Clicked two")

    scroll_box = first_box(driver, "ScrollView")
    first_before = box_with_text(driver, "First")
    driver.wheel(scroll_box.x + 2, scroll_box.y + 2, 80)
    scrolled = box_with_text(driver, "First").y < first_before.y

    return MinimalBackendCandidateReplay(
        title=title,
        initial_frame=initial_frame,
        final_frame=driver.frame,
        initial_focus=initial_focus,
        final_focus=focused_box_summary(driver),
        echo_visible=echo_visible,
        clicked_visible=clicked_visible,
        shortcut_visible=shortcut_visible,
        scrolled=scrolled,
    )


def replay_task_board_candidate(
    driver: NativeWindowDriver,
    *,
    title: str = "Otoe",
) -> TaskBoardBackendCandidateReplay:
    initial_frame = driver.frame

    driver.input_text("input")
    filtered_titles = visible_task_titles(driver)

    inspect = box_with_text(driver, "Inspect")
    driver.click(inspect.x + 2, inspect.y + 2)
    modal_visible = has_layout_text(driver, "Inspect Input polish")

    driver.key_down("Escape")
    modal_closed = not has_layout_text(driver, "Inspect Input polish")
    shortcut_text = first_text_starting_with(driver, "Shortcuts ")

    driver.key_down("k", ctrl=True)
    reset_titles = visible_task_titles(driver)

    scroll_box = first_box(driver, "ScrollView")
    first_before = box_with_text(driver, "Runtime bridge")
    driver.wheel(scroll_box.x + 2, scroll_box.y + 2, 48)
    scrolled = box_with_text(driver, "Runtime bridge").y < first_before.y

    return TaskBoardBackendCandidateReplay(
        title=title,
        initial_frame=initial_frame,
        final_frame=driver.frame,
        filtered_titles=filtered_titles,
        modal_visible_after_click=modal_visible,
        modal_closed_after_escape=modal_closed,
        shortcut_text_after_escape=shortcut_text,
        reset_titles=reset_titles,
        scrolled=scrolled,
        final_focus=focused_box_summary(driver),
    )


def visible_task_titles(driver: NativeWindowDriver) -> tuple[str, ...]:
    return tuple(title for title in TASK_BOARD_TITLES if has_layout_text(driver, title))


def has_layout_text(driver: NativeWindowDriver, text: str) -> bool:
    return any(box.text == text for box in driver.surface.layout.boxes)


def first_text_starting_with(driver: NativeWindowDriver, prefix: str) -> str | None:
    for box in driver.surface.layout.boxes:
        if box.text is not None and box.text.startswith(prefix):
            return box.text
    return None


def box_with_text(driver: NativeWindowDriver, text: str):
    for box in driver.surface.layout.boxes:
        if box.text == text:
            return box
    raise KeyError(f"No native box with text {text!r}.")


def first_box(driver: NativeWindowDriver, name: str):
    for box in driver.surface.layout.boxes:
        if box.name == name:
            return box
    raise KeyError(f"No native box named {name!r}.")


def focused_box_summary(driver: NativeWindowDriver) -> tuple[str, str | None] | None:
    box = driver.surface.focused_box
    if box is None:
        return None
    return (box.name, box.text)


def summarize_headless_candidate_frame(
    driver: NativeWindowDriver,
    *,
    label: str,
) -> HeadlessCandidateFrameSummary:
    layout = driver.surface.layout
    paint = driver.paint
    return HeadlessCandidateFrameSummary(
        label=label,
        frame=driver.frame,
        size=driver.size,
        root_name=layout.root.name,
        focused=focused_box_summary(driver),
        layout_boxes=len(layout.boxes),
        paint_commands=len(paint.commands),
        visible_text=tuple(box.text for box in layout.boxes if box.text),
        paint_kinds=tuple(command.kind for command in paint.commands),
        layout_snapshot=tuple(_box_snapshot(box) for box in layout.boxes),
        paint_snapshot=tuple(_paint_snapshot(command) for command in paint.commands),
    )


def _format_run_report(label: str, report: HeadlessCandidateRunReport) -> str:
    return "\n".join(
        [
            f"{label}: {'passed' if report.passed else 'failed'}",
            f"  backend: {report.backend}",
            f"  renderer backend: {report.renderer_backend}",
            f"  title: {report.title}",
            f"  frame: {report.before.frame} -> {report.after.frame}",
            f"  size: {report.after.size[0]}x{report.after.size[1]}",
            f"  root: {report.after.root_name}",
            f"  focused: {_format_focus(report.after.focused)}",
            f"  layout boxes: {report.after.layout_boxes}",
            f"  paint commands: {report.after.paint_commands}",
            f"  visible text: {', '.join(report.after.visible_text)}",
        ]
    )


def _format_focus(focus: tuple[str, str | None] | None) -> str:
    if focus is None:
        return "none"
    name, text = focus
    return name if text is None else f"{name} {text!r}"


def _last_replay(backend: RecordingBackendCandidate, expected_type: type[Any]):
    replay = backend.replays[-1]
    if not isinstance(replay, expected_type):
        raise TypeError(f"Expected {expected_type.__name__}, got {type(replay).__name__}.")
    return replay


def _last_report(backend: HeadlessCandidateBackend) -> HeadlessCandidateRunReport:
    return backend.reports[-1]


def _renderer_call_to_dict(call: RendererCandidateCall) -> dict[str, Any]:
    return {
        "phase": call.phase,
        "subject": call.subject,
        "layoutBoxes": call.layout_boxes,
        "paintCommands": call.paint_commands,
    }


def _run_contract_snapshot_to_dict(
    report: HeadlessCandidateRunReport,
) -> dict[str, Any]:
    return {
        "backend": report.backend,
        "rendererBackend": report.renderer_backend,
        "title": report.title,
        "passed": report.passed,
        "replayPassed": bool(getattr(report.replay, "passed", False)),
        "before": _frame_contract_snapshot_to_dict(report.before),
        "after": _frame_contract_snapshot_to_dict(report.after),
    }


def _compact_run_contract_snapshot_to_dict(
    report: HeadlessCandidateRunReport,
) -> dict[str, Any]:
    return {
        "backend": report.backend,
        "rendererBackend": report.renderer_backend,
        "title": report.title,
        "passed": report.passed,
        "replayPassed": bool(getattr(report.replay, "passed", False)),
        "before": _compact_frame_contract_snapshot_to_dict(report.before),
        "after": _compact_frame_contract_snapshot_to_dict(report.after),
    }


def _frame_contract_snapshot_to_dict(
    frame: HeadlessCandidateFrameSummary,
) -> dict[str, Any]:
    return {
        "label": frame.label,
        "frame": frame.frame,
        "size": list(frame.size),
        "rootName": frame.root_name,
        "focused": list(frame.focused) if frame.focused is not None else None,
        "layoutBoxes": frame.layout_boxes,
        "paintCommands": frame.paint_commands,
        "visibleText": list(frame.visible_text),
        "paintKinds": list(frame.paint_kinds),
        "layout": [_box_snapshot_to_dict(box) for box in frame.layout_snapshot],
        "paint": [
            _paint_snapshot_to_dict(command)
            for command in frame.paint_snapshot
        ],
    }


def _compact_frame_contract_snapshot_to_dict(
    frame: HeadlessCandidateFrameSummary,
) -> dict[str, Any]:
    full = _frame_contract_snapshot_to_dict(frame)
    layout_signature = [
        _compact_box_signature(box)
        for box in frame.layout_snapshot
    ]
    paint_signature = [
        _compact_paint_signature(command)
        for command in frame.paint_snapshot
    ]
    text_paths = [
        {
            "path": list(box.path),
            "text": box.text,
        }
        for box in frame.layout_snapshot
        if box.text is not None
    ]
    clip_rects = sorted(
        {
            command.clip
            for command in frame.paint_snapshot
            if command.clip is not None
        }
    )
    return {
        "label": frame.label,
        "frame": frame.frame,
        "size": list(frame.size),
        "rootName": frame.root_name,
        "focused": list(frame.focused) if frame.focused is not None else None,
        "layoutBoxes": frame.layout_boxes,
        "paintCommands": frame.paint_commands,
        "visibleText": list(frame.visible_text),
        "paintKinds": list(frame.paint_kinds),
        "layoutSignature": _contract_hash(layout_signature),
        "paintSignature": _contract_hash(paint_signature),
        "anchors": {
            "layoutNames": [box.name for box in frame.layout_snapshot],
            "textPaths": text_paths,
            "clipRects": [list(rect) for rect in clip_rects],
        },
        "hashes": {
            "layout": _contract_hash(full["layout"]),
            "paint": _contract_hash(full["paint"]),
            "visibleText": _contract_hash(full["visibleText"]),
            "frame": _contract_hash(full),
        },
    }


def _compact_call_stream(
    calls: Sequence[RendererCandidateCall],
) -> dict[str, Any]:
    signature = [_renderer_call_to_dict(call) for call in calls]
    return {
        "count": len(calls),
        "signature": signature,
        "hash": _contract_hash(signature),
    }


def _audit_has_no_unsupported(
    audit: dict[str, Any],
    *,
    unsupported_keys: tuple[str, ...],
) -> bool:
    return all(not audit.get(key) for key in unsupported_keys)


def _style_ops_report_errors(
    report: StyleOpsCandidateAcceptanceReport,
) -> list[str]:
    return [
        *report.errors,
        *(
            f"class {class_report.class_name!r}: {error}"
            for class_report in report.classes
            for error in class_report.errors
        ),
        *(
            f"directStyles {list(direct_style_report.path)!r}: {error}"
            for direct_style_report in report.direct_styles
            for error in direct_style_report.errors
        ),
    ]


def _backend_readiness_requirements(
    renderer_audit: dict[str, Any],
    style_ops_audit: dict[str, Any],
) -> dict[str, Any]:
    renderer_requirements = renderer_audit.get("requiredForReplay", {})
    if not isinstance(renderer_requirements, dict):
        renderer_requirements = {}
    return {
        "widgets": list(renderer_requirements.get("widgets", [])),
        "inputs": list(renderer_requirements.get("inputs", [])),
        "styles": list(style_ops_audit.get("requiredForReplay", [])),
        "declaredStyleOmissions": list(style_ops_audit.get("declaredOmissions", [])),
    }


def _renderer_capability_audit_to_dict(
    report: HeadlessCandidateAcceptanceReport,
) -> dict[str, Any]:
    frames = (report.minimal.after, report.task_board.after)
    widget_counts: dict[str, dict[str, int]] = {}
    input_counts: dict[str, dict[str, int]] = {}
    unsupported_widgets: dict[str, int] = {}
    unsupported_inputs: dict[str, int] = {}

    for frame in frames:
        for box in frame.layout_snapshot:
            widget_support = native_widget_support(box.name)
            _increment_style_bucket(widget_counts, widget_support, box.name)
            if widget_support == "fallback-container":
                unsupported_widgets[box.name] = (
                    unsupported_widgets.get(box.name, 0) + 1
                )
            for event_name in box.events:
                capability = INPUT_EVENT_CAPABILITIES.get(event_name, event_name)
                input_support = native_input_support(capability) or "unsupported"
                _increment_style_bucket(input_counts, input_support, capability)
                if input_support == "unsupported":
                    unsupported_inputs[capability] = (
                        unsupported_inputs.get(capability, 0) + 1
                    )

    widget_instances = sum(
        count
        for support_counts in widget_counts.values()
        for count in support_counts.values()
    )
    input_bindings = sum(
        count
        for support_counts in input_counts.values()
        for count in support_counts.values()
    )
    return {
        "summary": {
            "widgetInstances": widget_instances,
            "widgetTypes": len(_combined_property_names(widget_counts)),
            "inputBindings": input_bindings,
            "inputCapabilities": len(_combined_property_names(input_counts)),
            "unsupportedWidgets": sum(unsupported_widgets.values()),
            "unsupportedInputs": sum(unsupported_inputs.values()),
        },
        "widgets": _style_support_buckets(
            widget_counts,
            key_name="support",
            items_name="widgets",
            item_key="name",
        ),
        "inputs": _style_support_buckets(
            input_counts,
            key_name="support",
            items_name="capabilities",
            item_key="capability",
        ),
        "unsupportedWidgets": _style_property_counts(
            unsupported_widgets,
            item_key="name",
        ),
        "unsupportedInputs": _style_property_counts(
            unsupported_inputs,
            item_key="capability",
        ),
        "requiredForReplay": {
            "widgets": _renderer_replay_requirements(
                widget_counts,
                kind="widget",
                items_name="widgets",
                item_key="name",
            ),
            "inputs": _renderer_replay_requirements(
                input_counts,
                kind="input",
                items_name="capabilities",
                item_key="capability",
            ),
        },
    }


def _combined_property_names(
    buckets: dict[str, dict[str, int]],
) -> set[str]:
    names: set[str] = set()
    for properties in buckets.values():
        names.update(properties)
    return names


def _renderer_replay_requirements(
    buckets: dict[str, dict[str, int]],
    *,
    kind: str,
    items_name: str,
    item_key: str,
) -> list[dict[str, Any]]:
    return [
        {
            "kind": kind,
            "support": support,
            items_name: _style_property_counts(properties, item_key=item_key),
        }
        for support, properties in sorted(buckets.items())
        if support != "unsupported"
    ]


def _style_ops_capability_audit_to_dict(
    report: StyleOpsCandidateAcceptanceReport,
) -> dict[str, Any]:
    applied: dict[str, dict[str, int]] = {}
    omitted_by_status: dict[str, dict[str, int]] = {}
    omitted_by_support: dict[str, dict[str, int]] = {}
    unsupported: dict[str, int] = {}

    for class_report in report.classes:
        _collect_applied_style_support(
            class_report.applied_declarations,
            report.style_support,
            applied,
            unsupported,
        )
        _collect_omitted_style_support(
            class_report.omitted_ops,
            omitted_by_status,
            omitted_by_support,
            unsupported,
        )
    for direct_style_report in report.direct_styles:
        _collect_applied_style_support(
            direct_style_report.applied_declarations,
            report.style_support,
            applied,
            unsupported,
        )
        _collect_omitted_style_support(
            direct_style_report.omitted_ops,
            omitted_by_status,
            omitted_by_support,
            unsupported,
        )

    applied_total = sum(
        count
        for support_counts in applied.values()
        for count in support_counts.values()
    )
    omitted_total = sum(
        count
        for status_counts in omitted_by_status.values()
        for count in status_counts.values()
    )
    return {
        "backend": report.backend,
        "summary": {
            "applied": applied_total,
            "omitted": omitted_total,
            "unsupported": sum(unsupported.values()),
        },
        "applied": _style_support_buckets(applied, key_name="support"),
        "omittedByStatus": _style_support_buckets(
            omitted_by_status,
            key_name="status",
        ),
        "omittedBySupport": _style_support_buckets(
            omitted_by_support,
            key_name="support",
        ),
        "unsupportedProperties": _style_property_counts(unsupported),
        "requiredForReplay": _style_replay_requirements(applied),
        "declaredOmissions": _style_omission_requirements(omitted_by_status),
    }


def _collect_applied_style_support(
    declarations: dict[str, Any],
    style_support: dict[str, str],
    applied: dict[str, dict[str, int]],
    unsupported: dict[str, int],
) -> None:
    for property_name in declarations:
        support = style_support.get(property_name, "unsupported")
        _increment_style_bucket(applied, support, property_name)
        if support == "unsupported":
            unsupported[property_name] = unsupported.get(property_name, 0) + 1


def _collect_omitted_style_support(
    omitted_ops: tuple[dict[str, Any], ...],
    omitted_by_status: dict[str, dict[str, int]],
    omitted_by_support: dict[str, dict[str, int]],
    unsupported: dict[str, int],
) -> None:
    for op in omitted_ops:
        property_name = op.get("property")
        if not isinstance(property_name, str):
            continue
        status = op.get("status") if isinstance(op.get("status"), str) else "unknown"
        support = (
            op.get("support")
            if isinstance(op.get("support"), str)
            else "unsupported"
        )
        _increment_style_bucket(omitted_by_status, status, property_name)
        _increment_style_bucket(omitted_by_support, support, property_name)
        if support == "unsupported" or status == "invalid":
            unsupported[property_name] = unsupported.get(property_name, 0) + 1


def _increment_style_bucket(
    buckets: dict[str, dict[str, int]],
    bucket: str,
    property_name: str,
) -> None:
    properties = buckets.setdefault(bucket, {})
    properties[property_name] = properties.get(property_name, 0) + 1


def _style_support_buckets(
    buckets: dict[str, dict[str, int]],
    *,
    key_name: str,
    items_name: str = "properties",
    item_key: str = "property",
) -> list[dict[str, Any]]:
    return [
        {
            key_name: bucket,
            "count": sum(properties.values()),
            items_name: _style_property_counts(properties, item_key=item_key),
        }
        for bucket, properties in sorted(buckets.items())
    ]


def _style_property_counts(
    counts: dict[str, int],
    *,
    item_key: str = "property",
) -> list[dict[str, Any]]:
    return [
        {item_key: property_name, "count": count}
        for property_name, count in sorted(counts.items())
    ]


def _style_replay_requirements(
    applied: dict[str, dict[str, int]],
) -> list[dict[str, Any]]:
    return [
        {
            "kind": "apply",
            "support": support,
            "properties": _style_property_counts(properties),
        }
        for support, properties in sorted(applied.items())
        if support != "unsupported"
    ]


def _style_omission_requirements(
    omitted_by_status: dict[str, dict[str, int]],
) -> list[dict[str, Any]]:
    return [
        {
            "kind": "omit",
            "status": status,
            "properties": _style_property_counts(properties),
        }
        for status, properties in sorted(omitted_by_status.items())
    ]


def _style_ops_class_report_to_dict(
    report: StyleOpsCandidateClassReport,
) -> dict[str, Any]:
    return {
        "className": report.class_name,
        "selector": report.selector,
        "missing": report.missing,
        "expectedMissing": report.expected_missing,
        "passed": report.passed,
        "appliedDeclarations": report.applied_declarations,
        "expectedDeclarations": report.expected_declarations,
        "omittedOps": list(report.omitted_ops),
        "expectedOmittedOps": list(report.expected_omitted_ops),
        "errors": list(report.errors),
    }


def _style_ops_direct_style_report_to_dict(
    report: StyleOpsCandidateDirectStyleReport,
) -> dict[str, Any]:
    return {
        "path": list(report.path),
        "widget": report.widget,
        "expectedWidget": report.expected_widget,
        "passed": report.passed,
        "appliedDeclarations": report.applied_declarations,
        "expectedDeclarations": report.expected_declarations,
        "omittedOps": list(report.omitted_ops),
        "expectedOmittedOps": list(report.expected_omitted_ops),
        "errors": list(report.errors),
    }


def _replay_style_ops_class(
    replay: StyleOpsClassReplay,
    rules_by_class: dict[str, dict[str, Any]],
    style_support: dict[str, str],
) -> StyleOpsCandidateClassReport:
    errors = list(replay.errors)

    rule_payload = rules_by_class.get(replay.class_name)
    expected_missing = (
        bool(rule_payload.get("missing")) if isinstance(rule_payload, dict) else True
    )
    expected_declarations = (
        rule_payload.get("declarations", {})
        if isinstance(rule_payload, dict)
        else {}
    )
    if not isinstance(expected_declarations, dict):
        expected_declarations = {}
        errors.append(
            f"compiled rule {replay.class_name!r} declarations must be an object"
        )
    expected_omitted_ops = expected_omitted_style_ops(rule_payload, style_support)

    if replay.missing is not expected_missing:
        errors.append(
            f"styleOps class {replay.class_name!r} missing flag does not match compiled rule"
        )
    if replay.applied_declarations != expected_declarations:
        errors.append(
            f"styleOps class {replay.class_name!r} applied declarations do not match compiled rules"
        )
    if replay.omitted_ops != expected_omitted_ops:
        errors.append(
            f"styleOps class {replay.class_name!r} omitted ops do not match compiled rules"
        )

    return StyleOpsCandidateClassReport(
        class_name=replay.class_name,
        selector=replay.selector,
        missing=replay.missing,
        expected_missing=expected_missing,
        applied_declarations=replay.applied_declarations,
        expected_declarations=expected_declarations,
        omitted_ops=replay.omitted_ops,
        expected_omitted_ops=expected_omitted_ops,
        errors=tuple(errors),
    )


def _replay_style_ops_direct_style(
    replay: StyleOpsDirectReplay,
    direct_styles_by_path: dict[tuple[int, ...], dict[str, Any]],
    style_support: dict[str, str],
) -> StyleOpsCandidateDirectStyleReport:
    errors = list(replay.errors)

    expected_payload = direct_styles_by_path.get(replay.path)
    expected_widget = (
        expected_payload.get("widget")
        if isinstance(expected_payload, dict)
        and isinstance(expected_payload.get("widget"), str)
        else None
    )
    expected_declarations = (
        expected_payload.get("declarations", {})
        if isinstance(expected_payload, dict)
        else {}
    )
    if not isinstance(expected_declarations, dict):
        expected_declarations = {}
        errors.append(
            f"compiled directStyles {list(replay.path)!r} declarations must be an object"
        )
    expected_omitted_ops = expected_omitted_style_ops(expected_payload, style_support)

    if replay.widget != expected_widget:
        errors.append(
            f"styleOps directStyles {list(replay.path)!r} widget does not match compiled artifact"
        )
    if replay.applied_declarations != expected_declarations:
        errors.append(
            f"styleOps directStyles {list(replay.path)!r} applied declarations do not match compiled artifact"
        )
    if replay.omitted_ops != expected_omitted_ops:
        errors.append(
            f"styleOps directStyles {list(replay.path)!r} omitted ops do not match compiled artifact"
        )

    return StyleOpsCandidateDirectStyleReport(
        path=replay.path,
        widget=replay.widget,
        expected_widget=expected_widget,
        applied_declarations=replay.applied_declarations,
        expected_declarations=expected_declarations,
        omitted_ops=replay.omitted_ops,
        expected_omitted_ops=expected_omitted_ops,
        errors=tuple(errors),
    )

def _compact_box_signature(box: RendererContractBoxSnapshot) -> dict[str, Any]:
    return {
        "path": list(box.path),
        "name": box.name,
        "bounds": list(box.bounds),
        "text": box.text,
        "events": list(box.events),
    }


def _compact_paint_signature(
    command: RendererContractPaintSnapshot,
) -> dict[str, Any]:
    return {
        "kind": command.kind,
        "path": list(command.path),
        "bounds": list(command.bounds),
        "text": command.text,
        "clip": list(command.clip) if command.clip is not None else None,
    }


def _contract_hash(payload: Any) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


def _box_snapshot(box: Any) -> RendererContractBoxSnapshot:
    return RendererContractBoxSnapshot(
        path=box.path,
        name=box.name,
        bounds=(box.x, box.y, box.width, box.height),
        text=box.text,
        events=box.events,
        state=box.state,
    )


def _paint_snapshot(command: Any) -> RendererContractPaintSnapshot:
    return RendererContractPaintSnapshot(
        kind=command.kind,
        path=command.path,
        bounds=(command.x, command.y, command.width, command.height),
        fill=command.fill,
        stroke=command.stroke,
        stroke_width=command.stroke_width,
        radius=command.radius,
        text=command.text,
        color=command.color,
        font_size=command.font_size,
        clip=command.clip,
    )


def _box_snapshot_to_dict(box: RendererContractBoxSnapshot) -> dict[str, Any]:
    return {
        "path": list(box.path),
        "name": box.name,
        "bounds": list(box.bounds),
        "text": box.text,
        "events": list(box.events),
        "state": list(box.state),
    }


def _paint_snapshot_to_dict(
    command: RendererContractPaintSnapshot,
) -> dict[str, Any]:
    return {
        "kind": command.kind,
        "path": list(command.path),
        "bounds": list(command.bounds),
        "fill": command.fill,
        "stroke": command.stroke,
        "strokeWidth": command.stroke_width,
        "radius": command.radius,
        "text": command.text,
        "color": command.color,
        "fontSize": command.font_size,
        "clip": list(command.clip) if command.clip is not None else None,
    }


def _layout_candidate_target(
    target: Any,
    *,
    stylesheet: Any,
    strict_styles: bool,
) -> NativeLayout:
    widget = _candidate_root_widget(target)
    root = _layout_candidate_widget(
        widget,
        path=(),
        x=0,
        y=0,
        stylesheet=stylesheet,
        strict_styles=strict_styles,
    )
    return NativeLayout(root=root, boxes=tuple(_candidate_flatten(root)))


def _layout_candidate_widget(
    widget: Any,
    *,
    path: tuple[int, ...],
    x: int,
    y: int,
    stylesheet: Any,
    strict_styles: bool,
) -> LayoutBox:
    style = _layout_candidate_style(
        widget,
        stylesheet=stylesheet,
        strict_styles=strict_styles,
    )
    name = widget.name
    if name in {"Text", "Button", "Input"}:
        return _layout_candidate_leaf(widget, path=path, x=x, y=y, style=style)
    direction = "row" if name == "HStack" else "column"
    return _layout_candidate_container(
        widget,
        path=path,
        x=x,
        y=y,
        style=style,
        direction=direction,
        stylesheet=stylesheet,
        strict_styles=strict_styles,
    )


def _layout_candidate_leaf(
    widget: Any,
    *,
    path: tuple[int, ...],
    x: int,
    y: int,
    style: dict[str, Any],
) -> LayoutBox:
    text = _layout_candidate_text(widget)
    font_size = _candidate_style_dimension(style, "fontSize", default=14)
    default_padding = 8 if widget.name in {"Button", "Input"} else 0
    padding = _candidate_style_dimension(style, "padding", default=default_padding)
    border_width = _candidate_style_dimension(style, "borderWidth", default=0)
    width = max(1, ceil(len(text) * font_size * 0.55))
    height = max(1, ceil(font_size * 1.25))
    width += padding * 2 + border_width * 2
    height += padding * 2 + border_width * 2
    if widget.name == "Input":
        width = max(width, 180)
    width = _candidate_style_dimension(style, "width", default=width)
    height = _candidate_style_dimension(style, "height", default=height)
    return LayoutBox(
        path=path,
        name=widget.name,
        x=x,
        y=y,
        width=width,
        height=height,
        id=_candidate_optional_string(widget.props.get("id")),
        context=_candidate_widget_context(widget),
        text=text,
        events=tuple(sorted(widget.events)),
        state=_candidate_widget_state(widget),
        style=tuple(sorted(style.items())),
    )


def _layout_candidate_container(
    widget: Any,
    *,
    path: tuple[int, ...],
    x: int,
    y: int,
    style: dict[str, Any],
    direction: str,
    stylesheet: Any,
    strict_styles: bool,
) -> LayoutBox:
    padding = _candidate_style_dimension(style, "padding", default=0)
    gap = _candidate_style_dimension(style, "gap", default=0)
    scroll_y = (
        _candidate_style_dimension(style, "scrollY", default=0)
        if widget.name == "ScrollView"
        else 0
    )
    cursor_x = x + padding
    cursor_y = y + padding - scroll_y
    content_width = 0
    content_height = 0
    children = []
    for index, child in enumerate(widget.children):
        if index:
            if direction == "row":
                cursor_x += gap
            else:
                cursor_y += gap
        child_box = _layout_candidate_widget(
            child,
            path=(*path, index),
            x=cursor_x,
            y=cursor_y,
            stylesheet=stylesheet,
            strict_styles=strict_styles,
        )
        children.append(child_box)
        if direction == "row":
            cursor_x += child_box.width
            content_width += child_box.width + (gap if index else 0)
            content_height = max(content_height, child_box.height)
        else:
            cursor_y += child_box.height
            content_width = max(content_width, child_box.width)
            content_height += child_box.height + (gap if index else 0)

    width = _candidate_style_dimension(style, "width", default=content_width + padding * 2)
    height = _candidate_style_dimension(style, "height", default=content_height + padding * 2)
    if widget.name == "HStack":
        children = _layout_candidate_align_row(
            children,
            x=x,
            y=y,
            width=width,
            height=height,
            padding=padding,
            content_width=content_width,
            style=style,
        )
    if widget.name == "ScrollView":
        max_scroll = max(0, content_height + padding * 2 - height)
        clamped_scroll_y = min(max(scroll_y, 0), max_scroll)
        if clamped_scroll_y != scroll_y:
            children = [
                _layout_candidate_offset_y(child, scroll_y - clamped_scroll_y)
                for child in children
            ]
        style = {**style, "scrollY": clamped_scroll_y}

    return LayoutBox(
        path=path,
        name=widget.name,
        x=x,
        y=y,
        width=width,
        height=height,
        id=_candidate_optional_string(widget.props.get("id")),
        context=_candidate_widget_context(widget),
        events=tuple(sorted(widget.events)),
        state=_candidate_widget_state(widget),
        style=tuple(sorted(style.items())),
        children=tuple(children),
    )


def _layout_candidate_align_row(
    children: list[LayoutBox],
    *,
    x: int,
    y: int,
    width: int,
    height: int,
    padding: int,
    content_width: int,
    style: dict[str, Any],
) -> list[LayoutBox]:
    if not children:
        return children
    extra = max(0, width - padding * 2 - content_width)
    justify_content = style.get("justifyContent")
    align_items = style.get("alignItems")
    if justify_content == "space-between" and len(children) > 1:
        main_offsets = [
            (extra * index) // (len(children) - 1)
            for index, _child in enumerate(children)
        ]
    elif justify_content == "center":
        main_offsets = [extra // 2 for _child in children]
    elif justify_content in {"end", "flex-end"}:
        main_offsets = [extra for _child in children]
    else:
        main_offsets = [0 for _child in children]
    return [
        _layout_candidate_offset(
            child,
            dx=main_offsets[index],
            dy=max(0, (height - padding * 2 - child.height) // 2)
            if align_items == "center"
            else 0,
        )
        for index, child in enumerate(children)
    ]


def _layout_candidate_style(
    widget: Any,
    *,
    stylesheet: Any,
    strict_styles: bool,
) -> dict[str, Any]:
    style = {}
    class_name = widget.props.get("className")
    if stylesheet is not None:
        style.update(
            stylesheet.resolve(
                class_name if isinstance(class_name, str) else None,
                strict=strict_styles,
            )
        )
    for prop in ("gap", "padding", "scrollY"):
        if prop in widget.props:
            style[prop] = widget.props[prop]
    if "color" in widget.props:
        style["color"] = widget.props["color"]
    tokens = getattr(stylesheet, "tokens", {}) if stylesheet is not None else {}
    return {
        name: _layout_candidate_resolve_token(value, tokens)
        for name, value in style.items()
    }


def _layout_candidate_resolve_token(value: Any, tokens: dict[str, Any]) -> Any:
    name = getattr(value, "name", None)
    if name is not None and name in tokens:
        return _layout_candidate_resolve_token(tokens[name], tokens)
    return value


def _layout_candidate_text(widget: Any) -> str:
    if widget.name == "Button":
        return str(widget.props.get("label", ""))
    if widget.name == "Input":
        return str(widget.props.get("value") or widget.props.get("placeholder") or "")
    return str(widget.props.get("content", ""))


def _layout_candidate_offset(box: LayoutBox, *, dx: int = 0, dy: int = 0) -> LayoutBox:
    return LayoutBox(
        path=box.path,
        name=box.name,
        x=box.x + dx,
        y=box.y + dy,
        width=box.width,
        height=box.height,
        id=box.id,
        context=box.context,
        text=box.text,
        events=box.events,
        state=box.state,
        style=box.style,
        children=tuple(_layout_candidate_offset(child, dx=dx, dy=dy) for child in box.children),
    )


def _layout_candidate_offset_y(box: LayoutBox, delta: int) -> LayoutBox:
    return _layout_candidate_offset(box, dy=delta)


def _candidate_root_widget(target: Any) -> Any:
    if hasattr(target, "root_widget"):
        return target.root_widget()
    return target


def _candidate_flatten(box: LayoutBox) -> list[LayoutBox]:
    boxes = [box]
    for child in box.children:
        boxes.extend(_candidate_flatten(child))
    return boxes


def _candidate_widget_context(widget: Any) -> str:
    stack = getattr(widget, "component_stack", ())
    if not stack:
        return widget.name
    return " > ".join((*stack, widget.name))


def _candidate_widget_state(widget: Any) -> tuple[str, ...]:
    return ("disabled",) if widget.props.get("disabled") else ()


def _candidate_optional_string(value: Any) -> str | None:
    return value if isinstance(value, str) else None


def _paint_candidate_layout(
    layout: NativeLayout,
    *,
    background: str,
    focused_path: tuple[int, ...] | None,
) -> NativePaint:
    commands = [
        PaintCommand(
            kind="rect",
            path=(),
            x=0,
            y=0,
            width=max(layout.root.width, 1),
            height=max(layout.root.height, 1),
            fill=_candidate_style_color(background, default="#ffffff"),
            context="PaintOnlyRendererCandidate surface",
        )
    ]
    commands.extend(
        _paint_candidate_box(
            layout.root,
            focused_path=focused_path,
            clip=None,
        )
    )
    return NativePaint(
        width=max(layout.root.width, 1),
        height=max(layout.root.height, 1),
        commands=tuple(commands),
    )


def _paint_candidate_box(
    box: Any,
    *,
    focused_path: tuple[int, ...] | None,
    clip: tuple[int, int, int, int] | None,
) -> list[PaintCommand]:
    style = dict(box.style)
    commands: list[PaintCommand] = []
    rect = _paint_candidate_rect(box, style, clip=clip)
    if rect is not None:
        commands.append(rect)
    focus_ring = _paint_candidate_focus_ring(box, style, focused_path=focused_path, clip=clip)
    if focus_ring is not None:
        commands.append(focus_ring)
    if box.text:
        commands.append(_paint_candidate_text(box, style, clip=clip))

    child_clip = (
        _candidate_intersect_rects(clip, (box.x, box.y, box.width, box.height))
        if box.name == "ScrollView"
        else clip
    )
    for child in box.children:
        commands.extend(
            _paint_candidate_box(
                child,
                focused_path=focused_path,
                clip=child_clip,
            )
        )
    return commands


def _paint_candidate_rect(
    box: Any,
    style: dict[str, Any],
    *,
    clip: tuple[int, int, int, int] | None,
) -> PaintCommand | None:
    fill = _paint_candidate_fill(box, style)
    stroke = _paint_candidate_stroke(box, style)
    stroke_width = _candidate_style_dimension(
        style,
        "borderWidth",
        default=1 if box.name in {"Button", "Input"} else 0,
    )
    radius = _candidate_style_dimension(
        style,
        "borderRadius",
        default=8 if box.name in {"Button", "Input"} else 0,
    )
    if fill is None and (stroke is None or stroke_width <= 0):
        return None
    return PaintCommand(
        kind="rect",
        path=box.path,
        x=box.x,
        y=box.y,
        width=box.width,
        height=box.height,
        fill=fill,
        stroke=stroke,
        stroke_width=stroke_width,
        radius=radius,
        clip=clip,
        context=f"PaintOnlyRendererCandidate {box.name}",
    )


def _paint_candidate_focus_ring(
    box: Any,
    style: dict[str, Any],
    *,
    focused_path: tuple[int, ...] | None,
    clip: tuple[int, int, int, int] | None,
) -> PaintCommand | None:
    if box.path != focused_path or box.name not in {"Button", "Input"}:
        return None
    if "disabled" in box.state:
        return None
    return PaintCommand(
        kind="rect",
        path=box.path,
        x=box.x - 2,
        y=box.y - 2,
        width=box.width + 4,
        height=box.height + 4,
        stroke="#38bdf8",
        stroke_width=2,
        radius=_candidate_style_dimension(
            style,
            "borderRadius",
            default=8 if box.name in {"Button", "Input"} else 0,
        )
        + 2,
        clip=clip,
        context=f"PaintOnlyRendererCandidate {box.name}",
    )


def _paint_candidate_text(
    box: Any,
    style: dict[str, Any],
    *,
    clip: tuple[int, int, int, int] | None,
) -> PaintCommand:
    font_size = _candidate_style_dimension(style, "fontSize", default=14)
    padding = _candidate_text_padding(box, style)
    height = max(8, int(font_size * 0.85))
    return PaintCommand(
        kind="text",
        path=box.path,
        x=box.x + padding,
        y=box.y + max(0, (box.height - height) // 2),
        width=max(1, box.width - (padding * 2)),
        height=height,
        text=box.text or "",
        color=_paint_candidate_text_color(box, style),
        font_size=font_size,
        clip=clip,
        context=f"PaintOnlyRendererCandidate {box.name}",
    )


def _paint_candidate_fill(box: Any, style: dict[str, Any]) -> str | None:
    if "background" in style:
        return _candidate_style_color(style["background"], default="#ffffff")
    if "disabled" in box.state:
        if box.name == "Button":
            return "#d1d5db"
        if box.name == "Input":
            return "#f3f4f6"
    if box.name == "Button":
        return "#1f2937"
    if box.name == "Input":
        return "#ffffff"
    return None


def _paint_candidate_stroke(box: Any, style: dict[str, Any]) -> str | None:
    if "borderColor" in style:
        return _candidate_style_color(style["borderColor"], default="#d1d5db")
    if box.name == "Button":
        return "#111827"
    if box.name == "Input":
        return "#94a3b8"
    return None


def _paint_candidate_text_color(box: Any, style: dict[str, Any]) -> str:
    if "color" in style:
        return _candidate_style_color(style["color"], default="#111827")
    if "disabled" in box.state:
        return "#64748b"
    if box.name == "Button":
        return "#ffffff"
    return "#111827"


def _candidate_text_padding(box: Any, style: dict[str, Any]) -> int:
    if box.name in {"Button", "Input"}:
        return min(8, max(0, box.width // 4))
    return 0


def _candidate_style_dimension(
    style: dict[str, Any],
    name: str,
    *,
    default: int,
) -> int:
    value = style.get(name)
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return max(0, int(value))
    raw_value = getattr(value, "value", None)
    if isinstance(raw_value, (int, float)):
        return max(0, int(raw_value))
    return default


def _candidate_style_color(value: Any, *, default: str) -> str:
    return value if isinstance(value, str) and value.startswith("#") else default


def _candidate_intersect_rects(
    first: tuple[int, int, int, int] | None,
    second: tuple[int, int, int, int],
) -> tuple[int, int, int, int]:
    if first is None:
        return second
    ax, ay, aw, ah = first
    bx, by, bw, bh = second
    x1 = max(ax, bx)
    y1 = max(ay, by)
    x2 = min(ax + aw, bx + bw)
    y2 = min(ay + ah, by + bh)
    return (x1, y1, max(0, x2 - x1), max(0, y2 - y1))


def _write_candidate_png(paint: NativePaint, path: str | Path) -> None:
    image = bytearray([0, 0, 0, 0] * paint.width * paint.height)
    for command in paint.commands:
        if command.kind == "rect":
            _candidate_draw_rect(image, paint.width, paint.height, command)
        elif command.kind == "text":
            _candidate_draw_text(image, paint.width, paint.height, command)
        else:
            raise ValueError(f"Unsupported candidate paint command {command.kind!r}.")
    Path(path).write_bytes(_candidate_encode_png(image, paint.width, paint.height))


def _candidate_draw_rect(
    image: bytearray,
    image_width: int,
    image_height: int,
    command: Any,
) -> None:
    clip_x, clip_y, clip_width, clip_height = _candidate_clip(
        command.clip,
        image_width,
        image_height,
    )
    x1 = max(command.x, 0, clip_x)
    y1 = max(command.y, 0, clip_y)
    x2 = min(command.x + command.width, image_width, clip_x + clip_width)
    y2 = min(command.y + command.height, image_height, clip_y + clip_height)

    if command.fill is not None:
        fill = _candidate_color(command.fill)
        for y in range(y1, y2):
            for x in range(x1, x2):
                _candidate_set_pixel(image, image_width, x, y, fill)

    if command.stroke is None or command.stroke_width <= 0:
        return
    stroke = _candidate_color(command.stroke)
    stroke_width = max(command.stroke_width, 1)
    for y in range(y1, y2):
        for x in range(x1, x2):
            if (
                x < command.x + stroke_width
                or x >= command.x + command.width - stroke_width
                or y < command.y + stroke_width
                or y >= command.y + command.height - stroke_width
            ):
                _candidate_set_pixel(image, image_width, x, y, stroke)


def _candidate_draw_text(
    image: bytearray,
    image_width: int,
    image_height: int,
    command: Any,
) -> None:
    if not command.text:
        return
    color = _candidate_color(command.color or "#111827")
    clip_x, clip_y, clip_width, clip_height = _candidate_clip(
        command.clip,
        image_width,
        image_height,
    )
    glyph_width = max(2, command.font_size // 4)
    glyph_height = max(6, int(command.font_size * 0.75))
    step = glyph_width + 2
    for index, character in enumerate(command.text):
        if character == " ":
            continue
        x = command.x + index * step
        y = command.y + max(0, (command.height - glyph_height) // 2)
        for px in range(max(x, 0, clip_x), min(x + glyph_width, image_width, clip_x + clip_width)):
            for py in range(max(y, 0, clip_y), min(y + glyph_height, image_height, clip_y + clip_height)):
                if px in {x, x + glyph_width - 1} or py in {y, y + glyph_height - 1}:
                    _candidate_set_pixel(image, image_width, px, py, color)
                elif (ord(character) + px + py) % 13 == 0:
                    _candidate_set_pixel(image, image_width, px, py, color)


def _candidate_clip(
    clip: tuple[int, int, int, int] | None,
    image_width: int,
    image_height: int,
) -> tuple[int, int, int, int]:
    if clip is None:
        return (0, 0, image_width, image_height)
    x, y, width, height = clip
    x1 = max(x, 0)
    y1 = max(y, 0)
    x2 = min(x + width, image_width)
    y2 = min(y + height, image_height)
    return (x1, y1, max(0, x2 - x1), max(0, y2 - y1))


def _candidate_color(value: str) -> tuple[int, int, int, int]:
    if not isinstance(value, str) or not value.startswith("#"):
        raise ValueError(f"Candidate raster only supports hex colors, got {value!r}.")
    raw = value[1:]
    if len(raw) == 6:
        raw = f"{raw}ff"
    if len(raw) != 8:
        raise ValueError(f"Candidate raster only supports #rrggbb colors, got {value!r}.")
    return tuple(int(raw[index : index + 2], 16) for index in range(0, 8, 2))  # type: ignore[return-value]


def _candidate_set_pixel(
    image: bytearray,
    image_width: int,
    x: int,
    y: int,
    color: tuple[int, int, int, int],
) -> None:
    offset = (y * image_width + x) * 4
    image[offset : offset + 4] = bytes(color)


def _candidate_encode_png(image: bytearray, width: int, height: int) -> bytes:
    rows = []
    stride = width * 4
    for y in range(height):
        start = y * stride
        rows.append(b"\x00" + bytes(image[start : start + stride]))
    raw = b"".join(rows)
    return b"".join(
        [
            b"\x89PNG\r\n\x1a\n",
            _candidate_png_chunk(
                b"IHDR",
                struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0),
            ),
            _candidate_png_chunk(b"IDAT", zlib.compress(raw)),
            _candidate_png_chunk(b"IEND", b""),
        ]
    )


def _candidate_png_chunk(kind: bytes, data: bytes) -> bytes:
    checksum = zlib.crc32(kind)
    checksum = zlib.crc32(data, checksum)
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", checksum)


def _target_name(target: Any) -> str:
    widget = getattr(target, "widget", None)
    if widget is not None:
        return str(getattr(widget, "name", type(widget).__name__))
    return str(getattr(target, "name", type(target).__name__))


if __name__ == "__main__":
    raise SystemExit(main())
