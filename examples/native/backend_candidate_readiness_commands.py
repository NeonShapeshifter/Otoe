from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from otoe.capabilities import CapabilityProfileError

from .backend_candidate_acceptance import (
    backend_coverage_report_to_dict,
    backend_readiness_report_to_dict,
)
from .backend_candidate_artifacts import (
    RenderTreeSource,
    coverage_declaration_from_args,
    coverage_declaration_from_backend_args,
    emit_contract_payload,
    render_tree_source_from_args,
    style_artifact_from_args,
    warn_backend_coverage_compat,
)
from .backend_candidate_command_helpers import (
    reject_ambiguous_style_sources,
    run_render_tree_source_acceptance,
    style_artifact_or_default,
)
from .backend_candidate_style_ops_contracts import run_style_ops_candidate_acceptance


def handle_backend_readiness(
    parser: argparse.ArgumentParser,
    args: argparse.Namespace,
) -> int:
    reject_ambiguous_style_sources(parser, args)
    try:
        style_artifact = style_artifact_from_args(args)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"backend-readiness: {exc}", file=sys.stderr)
        return 1
    try:
        render_tree_source = render_tree_source_from_args(
            args,
            loaded_style_artifact=style_artifact,
        )
        payload = backend_readiness_payload(
            style_artifact,
            render_tree_source,
            include_external_path0_backend=args.external_path0_backend,
        )
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"backend-readiness: {exc}", file=sys.stderr)
        return 1
    emit_contract_payload(payload, output_path=args.contract_out)
    return 0 if payload["passed"] else 1


def handle_backend_coverage_declaration(
    parser: argparse.ArgumentParser,
    args: argparse.Namespace,
) -> int:
    warn_backend_coverage_compat("--backend-coverage-declaration-json")
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
            "--backend-capability and --backend-capability-profile are mutually exclusive"
        )
    try:
        payload = coverage_declaration_from_backend_args(args)
    except (OSError, CapabilityProfileError) as exc:
        print(f"backend-coverage-declaration: {exc}", file=sys.stderr)
        return 1
    emit_contract_payload(payload, output_path=args.contract_out)
    return 0


def handle_backend_coverage(
    parser: argparse.ArgumentParser,
    args: argparse.Namespace,
) -> int:
    warn_backend_coverage_compat("--backend-coverage-json")
    if args.coverage_declaration is None and args.backend_capability is None:
        if args.backend_capability_profile is None:
            parser.error(
                "--coverage-declaration, --backend-capability, or "
                "--backend-capability-profile is required with --backend-coverage-json"
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
    reject_ambiguous_style_sources(parser, args)
    try:
        declaration = coverage_declaration_from_args(args)
        style_artifact = style_artifact_from_args(args)
        render_tree_source = render_tree_source_from_args(
            args,
            loaded_style_artifact=style_artifact,
        )
        readiness_report = backend_readiness_payload(
            style_artifact,
            render_tree_source,
            include_external_path0_backend=args.external_path0_backend,
        )
    except (
        OSError,
        json.JSONDecodeError,
        ValueError,
        CapabilityProfileError,
    ) as exc:
        print(f"backend-coverage: {exc}", file=sys.stderr)
        return 1
    payload = backend_coverage_report_to_dict(
        declaration,
        readiness_report=readiness_report,
    )
    emit_contract_payload(payload, output_path=args.contract_out)
    return 0 if payload["passed"] else 1


def backend_readiness_payload(
    style_artifact: dict[str, Any] | None,
    render_tree_source: RenderTreeSource,
    *,
    include_external_path0_backend: bool = False,
) -> dict[str, Any]:
    readiness_style_artifact = style_artifact_or_default(
        style_artifact,
        render_tree_source,
    )
    return backend_readiness_report_to_dict(
        style_ops_report=run_style_ops_candidate_acceptance(readiness_style_artifact),
        render_tree_report=run_render_tree_source_acceptance(
            render_tree_source,
            readiness_style_artifact,
        ),
        style_artifact=readiness_style_artifact,
        include_external_path0_backend=include_external_path0_backend,
    )
