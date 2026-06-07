from __future__ import annotations

from .backend_candidate_acceptance import (
    backend_coverage_report_to_dict,
    backend_readiness_report_to_dict,
    run_backend_candidate_acceptance,
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
from .backend_candidate_acceptance_reports import (
    acceptance_report_to_dict,
    format_acceptance_report,
)
from .backend_candidate_apps import (
    BACKEND_CANDIDATE_STYLES,
    TASK_BOARD_TITLES,
    backend_candidate_app,
)
from .backend_candidate_cli import main
from .backend_candidate_render_tree_contracts import (
    run_render_tree_candidate_acceptance,
)
from .backend_candidate_style_ops_contracts import (
    backend_candidate_style_artifact,
    run_style_ops_candidate_acceptance,
)
from .backend_candidate_renderer_reports import (
    compact_composed_renderer_contract_snapshot_to_dict,
    compact_renderer_contract_snapshot_to_dict,
    composed_renderer_contract_snapshot_to_dict,
    renderer_contract_snapshot_to_dict,
)
from .backend_candidate_render_tree_reports import render_tree_contract_report_to_dict
from .backend_candidate_readiness_reports import (
    backend_readiness_report_payload_to_dict,
    path0_render_tree_evidence_report_to_dict,
)
from .backend_candidate_path0_evidence import (
    RenderTreeRendererCandidate,
    run_path0_render_tree_artifact_evidence,
    run_path0_render_tree_evidence,
)
from .backend_candidate_path0_renderer import Path0RendererCandidate
from .backend_candidate_phase_renderer_candidates import (
    LayoutOnlyRendererCandidate,
    PaintOnlyRendererCandidate,
    RasterOnlyRendererCandidate,
)
from .backend_candidate_recording_renderer import RecordingRendererCandidate
from .backend_candidate_replays import (
    HeadlessCandidateBackend,
    RecordingBackendCandidate,
    box_with_text,
    first_box,
    first_text_starting_with,
    focused_box_summary,
    has_layout_text,
    last_report as _last_report,
    last_replay as _last_replay,
    replay_minimal_candidate,
    replay_task_board_candidate,
    summarize_headless_candidate_frame,
    visible_task_titles,
)
from .backend_candidate_style_ops_reports import style_ops_candidate_report_to_dict
from .backend_candidate_render_tree_types import (
    Path0RenderTreeEvidenceReport,
    RenderTreeCandidateAcceptanceReport,
)
from .backend_candidate_renderer_types import (
    ComposedRendererCandidateAcceptanceReport,
    HeadlessCandidateAcceptanceReport,
    HeadlessCandidateRunReport,
    LayoutOnlyCandidateAcceptanceReport,
    LayoutOnlyTaskBoardStaticAcceptanceReport,
    RendererCandidateAcceptanceReport,
    RendererCandidateCall,
)
from .backend_candidate_replay_types import (
    BackendCandidateAcceptanceReport,
    MinimalBackendCandidateReplay,
    TaskBoardBackendCandidateReplay,
)
from .backend_candidate_style_ops_types import (
    StyleOpsCandidateAcceptanceReport,
    StyleOpsCandidateClassReport,
    StyleOpsCandidateDirectStyleReport,
)


if __name__ == "__main__":
    raise SystemExit(main())
