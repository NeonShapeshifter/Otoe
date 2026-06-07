from __future__ import annotations

from pathlib import Path
from typing import Any

from otoe import (
    ComposedNativeRendererBackend,
    NativeRendererBackend,
    NativeWindowDriver,
    run_native,
)

from .backend_candidate_apps import (
    BACKEND_CANDIDATE_STYLES,
    backend_candidate_app,
)
from .backend_candidate_path0_renderer import Path0RendererCandidate
from .backend_candidate_phase_renderer_candidates import (
    LayoutOnlyRendererCandidate,
    PaintOnlyRendererCandidate,
    RasterOnlyRendererCandidate,
)
from .backend_candidate_recording_renderer import RecordingRendererCandidate
from .backend_candidate_renderer_types import (
    ComposedRendererCandidateAcceptanceReport,
    HeadlessCandidateAcceptanceReport,
    LayoutOnlyCandidateAcceptanceReport,
    LayoutOnlyTaskBoardStaticAcceptanceReport,
    RendererCandidateAcceptanceReport,
)
from .backend_candidate_replays import (
    HeadlessCandidateBackend,
    last_report as _last_report,
    replay_minimal_candidate,
    replay_task_board_candidate,
    summarize_headless_candidate_frame,
)
from .window_demo import NativeWindowDemo


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


def run_path0_renderer_candidate_acceptance() -> RendererCandidateAcceptanceReport:
    return run_renderer_candidate_acceptance_with(Path0RendererCandidate())


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


def run_renderer_candidate_acceptance_with(
    renderer_backend: Any,
) -> RendererCandidateAcceptanceReport:
    headless = run_headless_candidate_acceptance(renderer_backend=renderer_backend)
    return RendererCandidateAcceptanceReport(
        renderer_backend=renderer_backend.name,
        headless=headless,
        calls=tuple(renderer_backend.calls),
    )
