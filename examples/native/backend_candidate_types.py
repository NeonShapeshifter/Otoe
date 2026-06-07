from __future__ import annotations

from .backend_candidate_render_tree_types import (
    Path0RenderTreeEvidenceReport,
    RenderTreeCandidateAcceptanceReport,
)
from .backend_candidate_renderer_types import (
    ComposedRendererCandidateAcceptanceReport,
    HeadlessCandidateAcceptanceReport,
    HeadlessCandidateFrameSummary,
    HeadlessCandidateRunReport,
    LayoutOnlyCandidateAcceptanceReport,
    LayoutOnlyTaskBoardStaticAcceptanceReport,
    RendererCandidateAcceptanceReport,
    RendererCandidateCall,
    RendererContractBoxSnapshot,
    RendererContractPaintSnapshot,
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
