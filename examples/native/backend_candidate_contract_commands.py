from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .backend_candidate_acceptance import (
    run_composed_renderer_candidate_acceptance,
    run_headless_candidate_acceptance,
    run_renderer_candidate_acceptance,
)
from .backend_candidate_acceptance_reports import (
    acceptance_report_to_dict,
    format_acceptance_report,
)
from .backend_candidate_artifacts import (
    emit_contract_payload,
    render_tree_source_from_args,
    style_artifact_from_args,
)
from .backend_candidate_command_helpers import (
    reject_ambiguous_style_sources,
    run_render_tree_source_acceptance,
    style_artifact_or_default,
)
from .backend_candidate_path0_evidence import run_path0_render_tree_evidence
from .backend_candidate_readiness_reports import (
    path0_render_tree_evidence_report_to_dict,
)
from .backend_candidate_renderer_reports import (
    compact_composed_renderer_contract_snapshot_to_dict,
    compact_renderer_contract_snapshot_to_dict,
    composed_renderer_contract_snapshot_to_dict,
    renderer_contract_snapshot_to_dict,
)
from .backend_candidate_render_tree_reports import render_tree_contract_report_to_dict
from .backend_candidate_style_ops_contracts import run_style_ops_candidate_acceptance
from .backend_candidate_style_ops_reports import style_ops_candidate_report_to_dict


def handle_renderer_contract(args: argparse.Namespace) -> int:
    renderer_report = run_renderer_candidate_acceptance()
    payload = (
        compact_renderer_contract_snapshot_to_dict(renderer_report)
        if args.compact_contract
        else renderer_contract_snapshot_to_dict(renderer_report)
    )
    emit_contract_payload(payload, output_path=args.contract_out)
    return 0 if renderer_report.passed else 1


def handle_composed_renderer_contract(args: argparse.Namespace) -> int:
    composed_png = Path(args.composed_renderer_png)
    composed_png.parent.mkdir(parents=True, exist_ok=True)
    composed_report = run_composed_renderer_candidate_acceptance(composed_png)
    payload = (
        compact_composed_renderer_contract_snapshot_to_dict(composed_report)
        if args.compact_contract
        else composed_renderer_contract_snapshot_to_dict(composed_report)
    )
    emit_contract_payload(payload, output_path=args.contract_out)
    return 0 if composed_report.passed else 1


def handle_style_ops_contract(
    parser: argparse.ArgumentParser,
    args: argparse.Namespace,
) -> int:
    reject_ambiguous_style_sources(parser, args)
    try:
        style_artifact = style_artifact_from_args(args)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"style-ops-contract: {exc}", file=sys.stderr)
        return 1
    style_ops_report = run_style_ops_candidate_acceptance(style_artifact)
    payload = style_ops_candidate_report_to_dict(style_ops_report)
    emit_contract_payload(payload, output_path=args.contract_out)
    return 0 if style_ops_report.passed else 1


def handle_render_tree_contract(
    parser: argparse.ArgumentParser,
    args: argparse.Namespace,
) -> int:
    reject_ambiguous_style_sources(parser, args)
    try:
        render_tree_source = render_tree_source_from_args(args)
        render_tree_report = run_render_tree_source_acceptance(render_tree_source)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"render-tree-contract: {exc}", file=sys.stderr)
        return 1
    payload = render_tree_contract_report_to_dict(render_tree_report)
    emit_contract_payload(payload, output_path=args.contract_out)
    return 0 if render_tree_report.passed else 1


def handle_path0_render_tree_evidence(
    parser: argparse.ArgumentParser,
    args: argparse.Namespace,
) -> int:
    reject_ambiguous_style_sources(parser, args)
    try:
        render_tree_source = render_tree_source_from_args(args)
        style_artifact = style_artifact_or_default(None, render_tree_source)
        render_tree_report = run_render_tree_source_acceptance(
            render_tree_source,
            style_artifact,
        )
        source = render_tree_report.artifact_source or "contract:minimal"
        render_tree = render_tree_report.artifact_target or render_tree_report.minimal
        path0_png = Path(args.path0_render_tree_png)
        path0_png.parent.mkdir(parents=True, exist_ok=True)
        path0_report = run_path0_render_tree_evidence(
            render_tree,
            style_artifact=style_artifact,
            source=source,
            output_path=path0_png,
        )
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"path0-render-tree-evidence: {exc}", file=sys.stderr)
        return 1
    payload = path0_render_tree_evidence_report_to_dict(path0_report)
    emit_contract_payload(payload, output_path=args.contract_out)
    return 0 if render_tree_report.passed and path0_report.passed else 1


def handle_headless_report(args: argparse.Namespace) -> int:
    report = run_headless_candidate_acceptance()
    if args.json:
        print(json.dumps(acceptance_report_to_dict(report), indent=2, sort_keys=True))
    else:
        print(format_acceptance_report(report))
    return 0 if report.passed else 1
