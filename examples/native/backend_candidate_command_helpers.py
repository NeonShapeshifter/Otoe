from __future__ import annotations

import argparse
from typing import Any

from .backend_candidate_artifacts import RenderTreeSource
from .backend_candidate_render_tree_contracts import run_render_tree_candidate_acceptance
from .backend_candidate_style_ops_contracts import backend_candidate_style_artifact


def reject_ambiguous_style_sources(
    parser: argparse.ArgumentParser,
    args: argparse.Namespace,
) -> None:
    if args.style_artifact is not None and args.bundle is not None:
        parser.error("--style-artifact and --bundle are mutually exclusive")


def style_artifact_or_default(
    style_artifact: dict[str, Any] | None,
    render_tree_source: RenderTreeSource,
) -> dict[str, Any]:
    if style_artifact is not None:
        return style_artifact
    if render_tree_source.style_artifact is not None:
        return render_tree_source.style_artifact
    return backend_candidate_style_artifact()


def run_render_tree_source_acceptance(
    render_tree_source: RenderTreeSource,
    style_artifact: dict[str, Any] | None = None,
) -> Any:
    resolved_style_artifact = (
        style_artifact
        if style_artifact is not None
        else render_tree_source.style_artifact
    )
    return run_render_tree_candidate_acceptance(
        resolved_style_artifact,
        artifact_target=render_tree_source.target,
        artifact_render_tree=render_tree_source.render_tree,
        artifact_source=render_tree_source.source,
    )
