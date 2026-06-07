from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from .backend_candidate_commands import (
    handle_backend_coverage,
    handle_backend_coverage_declaration,
    handle_backend_readiness,
    handle_composed_renderer_contract,
    handle_headless_report,
    handle_path0_render_tree_evidence,
    handle_render_tree_contract,
    handle_renderer_contract,
    handle_style_ops_contract,
)


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
        "--render-tree-contract-json",
        action="store_true",
        help="print the low-level RenderTree replay contract as JSON",
    )
    parser.add_argument(
        "--path0-render-tree-evidence-json",
        action="store_true",
        help="print low-level Path0 RenderTree render evidence as JSON",
    )
    parser.add_argument(
        "--backend-readiness-json",
        action="store_true",
        help="print a combined renderer, styleOps, and RenderTree readiness report",
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
        "--render-tree-artifact",
        help=(
            "optional serialized RenderTree JSON artifact used by "
            "render-tree/path0/readiness reports"
        ),
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
    parser.add_argument(
        "--path0-render-tree-png",
        default=str(Path("preview") / "native" / "path0_render_tree_evidence.png"),
        help="PNG path used by --path0-render-tree-evidence-json",
    )
    args = parser.parse_args(argv)
    if args.renderer_contract_json:
        return handle_renderer_contract(args)

    if args.composed_renderer_contract_json:
        return handle_composed_renderer_contract(args)

    if args.style_ops_contract_json:
        return handle_style_ops_contract(parser, args)

    if args.render_tree_contract_json:
        return handle_render_tree_contract(parser, args)

    if args.path0_render_tree_evidence_json:
        return handle_path0_render_tree_evidence(parser, args)

    if args.backend_readiness_json:
        return handle_backend_readiness(parser, args)

    if args.backend_coverage_declaration_json:
        return handle_backend_coverage_declaration(parser, args)

    if args.backend_coverage_json:
        return handle_backend_coverage(parser, args)

    return handle_headless_report(args)
