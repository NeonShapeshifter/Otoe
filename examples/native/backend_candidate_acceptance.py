from __future__ import annotations

from typing import Any

from otoe import (
    NativeRendererBackend,
    run_native,
)
from otoe.backend_coverage import (
    backend_coverage_report_to_dict as _backend_coverage_report_to_dict,
)

from .backend_candidate_apps import (
    BACKEND_CANDIDATE_STYLES,
    backend_candidate_app,
)
from .backend_candidate_render_tree_contracts import run_render_tree_candidate_acceptance
from .backend_candidate_style_ops_contracts import (
    backend_candidate_style_artifact,
    run_style_ops_candidate_acceptance,
)
from .backend_candidate_path0_evidence import (
    run_path0_render_tree_evidence,
)
from .backend_candidate_path0_external_evidence import (
    run_external_path0_backend_evidence,
)
from .backend_candidate_renderer_acceptance import (
    run_composed_renderer_candidate_acceptance,
    run_headless_candidate_acceptance,
    run_layout_only_renderer_candidate_acceptance,
    run_layout_only_task_board_static_acceptance,
    run_paint_only_renderer_candidate_acceptance,
    run_path0_renderer_candidate_acceptance,
    run_raster_only_renderer_candidate_acceptance,
    run_renderer_candidate_acceptance,
    run_renderer_candidate_acceptance_with,
)
from .backend_candidate_replays import (
    RecordingBackendCandidate,
    last_replay as _last_replay,
    replay_minimal_candidate,
    replay_task_board_candidate,
)
from .backend_candidate_readiness_reports import (
    backend_readiness_report_payload_to_dict,
)
from .backend_candidate_render_tree_types import (
    Path0RenderTreeEvidenceReport,
    RenderTreeCandidateAcceptanceReport,
)
from .backend_candidate_renderer_types import (
    RendererCandidateAcceptanceReport,
)
from .backend_candidate_replay_types import (
    BackendCandidateAcceptanceReport,
    MinimalBackendCandidateReplay,
    TaskBoardBackendCandidateReplay,
)
from .backend_candidate_style_ops_types import (
    StyleOpsCandidateAcceptanceReport,
)
from .window_demo import NativeWindowDemo


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


def backend_readiness_report_to_dict(
    *,
    renderer_report: RendererCandidateAcceptanceReport | None = None,
    style_ops_report: StyleOpsCandidateAcceptanceReport | None = None,
    render_tree_report: RenderTreeCandidateAcceptanceReport | None = None,
    path0_report: Path0RenderTreeEvidenceReport | None = None,
    style_artifact: dict[str, Any] | None = None,
    include_external_path0_backend: bool = False,
) -> dict[str, Any]:
    if style_artifact is None and (
        style_ops_report is None
        or render_tree_report is None
    ):
        style_artifact = backend_candidate_style_artifact()
    renderer_report = renderer_report or run_renderer_candidate_acceptance()
    style_ops_report = style_ops_report or run_style_ops_candidate_acceptance(
        style_artifact
    )
    render_tree_report = render_tree_report or run_render_tree_candidate_acceptance(
        style_artifact
    )
    path0_report = path0_report or _path0_report_from_render_tree_report(
        render_tree_report,
        style_artifact=style_artifact,
    )
    external_path0_report = (
        _external_path0_report_from_render_tree_report(
            render_tree_report,
            style_artifact=style_artifact,
        )
        if include_external_path0_backend
        else None
    )
    return backend_readiness_report_payload_to_dict(
        renderer_report=renderer_report,
        style_ops_report=style_ops_report,
        render_tree_report=render_tree_report,
        path0_report=path0_report,
        external_path0_report=external_path0_report,
    )


def _path0_report_from_render_tree_report(
    render_tree_report: RenderTreeCandidateAcceptanceReport,
    *,
    style_artifact: dict[str, Any] | None,
) -> Path0RenderTreeEvidenceReport:
    source = render_tree_report.artifact_source or "contract:minimal"
    render_tree = render_tree_report.artifact_target or render_tree_report.minimal
    return run_path0_render_tree_evidence(
        render_tree,
        style_artifact=style_artifact,
        source=source,
    )


def _external_path0_report_from_render_tree_report(
    render_tree_report: RenderTreeCandidateAcceptanceReport,
    *,
    style_artifact: dict[str, Any] | None,
) -> dict[str, Any]:
    source = render_tree_report.artifact_source or "contract:minimal"
    render_tree = render_tree_report.artifact_target or render_tree_report.minimal
    return run_external_path0_backend_evidence(
        render_tree,
        style_artifact=style_artifact,
        source=source,
    )


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
