from __future__ import annotations

from otoe.render_ir import render_tree_from_target

from .backend_candidate_layout_styles import candidate_resolved_style_map
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
