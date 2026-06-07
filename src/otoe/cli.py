from __future__ import annotations

import argparse
from collections.abc import Sequence

from . import cli_build as _cli_build
from .cli_backend import run_backend_coverage, run_backend_profile
from .cli_check import DEFAULT_CHECK_PATHS, run_check
from .cli_contract import run_compare_contract
from .cli_deps import run_deps
from .cli_dev import run_dev
from .cli_new import run_new
from .cli_pack import run_pack
from .cli_plan import run_plan
from .cli_style_ir import run_style_ir
from .cli_render import run_render
from .plan_artifacts import compiled_styles_to_dict


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="otoe")
    subcommands = parser.add_subparsers(dest="command", required=True)

    check = subcommands.add_parser("check", help="run local Otoe health checks")
    check.add_argument(
        "--path",
        action="append",
        dest="paths",
        help="path to compile; may be passed more than once",
    )
    check.add_argument(
        "--tests",
        action="store_true",
        help="also run pytest after compile checks",
    )
    check.add_argument(
        "--pytest-arg",
        action="append",
        default=[],
        help="extra argument passed to pytest; may be passed more than once",
    )
    check.add_argument(
        "pytest_args",
        nargs=argparse.REMAINDER,
        help="pytest arguments after --",
    )
    check.set_defaults(func=run_check)

    render = subcommands.add_parser("render", help="render an Otoe target")
    render.add_argument("target", help="import target in MODULE:OBJECT form")
    render.add_argument("--out", required=True, help="output HTML path")
    render.add_argument("--pretty", action="store_true", help="pretty-print HTML")
    render.add_argument("--indent", type=int, default=0, help="base HTML indent")
    render.add_argument(
        "--css",
        help="optional Otoe CSS file to apply inline during render",
    )
    render.add_argument(
        "--no-strict-styles",
        action="store_false",
        default=True,
        dest="strict_styles",
        help="ignore class names missing from --css",
    )
    render.add_argument(
        "--native",
        action="store_true",
        help="render a native PNG frame",
    )
    render.add_argument(
        "--background",
        default="#ffffff",
        help="native PNG background",
    )
    render.set_defaults(func=run_render)

    plan = subcommands.add_parser(
        "plan",
        help="diagnose an Otoe target for an offline deployment profile",
    )
    _add_offline_profile_args(
        plan,
        action="diagnose",
        backend_context="plan diagnostics",
        gate="plan",
    )
    plan.add_argument(
        "--json",
        action="store_true",
        help="write the plan report as JSON to stdout",
    )
    plan.add_argument(
        "--out",
        help="optional path to write the JSON plan artifact",
    )
    plan.set_defaults(func=run_plan)

    build = subcommands.add_parser(
        "build",
        help="write a minimal offline bundle manifest for an Otoe target",
    )
    _add_offline_profile_args(
        build,
        action="build",
        backend_context="build-time plan diagnostics",
        gate="build",
    )
    build.add_argument(
        "--out",
        required=True,
        help="output bundle directory",
    )
    build.add_argument(
        "--validate",
        action="store_true",
        help="run the generated bundle runner after writing artifacts",
    )
    build.set_defaults(func=_build)

    backend_profile = subcommands.add_parser(
        "backend-profile",
        help="inspect a backend capability profile",
    )
    backend_profile.add_argument(
        "profile",
        nargs="?",
        help="built-in backend capability profile; defaults to native-python",
    )
    backend_profile.add_argument(
        "--backend-capability-profile",
        help="backend capability profile JSON to inspect",
    )
    backend_profile.add_argument(
        "--coverage-declaration",
        action="store_true",
        help="write the profile's backend coverage declaration as JSON",
    )
    backend_profile.add_argument(
        "--json",
        action="store_true",
        help="write the backend profile report as JSON",
    )
    backend_profile.add_argument(
        "--out",
        help="optional path to write the JSON output",
    )
    backend_profile.set_defaults(func=run_backend_profile)

    backend_coverage = subcommands.add_parser(
        "backend-coverage",
        help="compare backend coverage against readiness requirements",
    )
    backend_coverage.add_argument(
        "--requirements",
        required=True,
        help="backend readiness report or requirements JSON to compare against",
    )
    backend_coverage.add_argument(
        "--backend",
        default=None,
        help="built-in backend capability profile; defaults to native-python",
    )
    backend_coverage.add_argument(
        "--backend-capability-profile",
        help="backend capability profile JSON used to derive coverage",
    )
    backend_coverage.add_argument(
        "--coverage-declaration",
        help="explicit backend coverage declaration JSON to compare",
    )
    backend_coverage.add_argument(
        "--json",
        action="store_true",
        help="write the backend coverage report as JSON",
    )
    backend_coverage.add_argument(
        "--audit",
        action="store_true",
        help="write a text audit of per-capability coverage evidence",
    )
    backend_coverage.add_argument(
        "--out",
        help="optional path to write the JSON coverage report",
    )
    backend_coverage.set_defaults(func=run_backend_coverage)

    pack = subcommands.add_parser(
        "pack",
        help="verify and package an offline Otoe bundle",
    )
    pack.add_argument("bundle", help="bundle directory written by otoe build")
    pack.add_argument(
        "--out",
        required=True,
        help="output .tar.gz path",
    )
    pack.set_defaults(func=run_pack)

    compare_contract = subcommands.add_parser(
        "compare-contract",
        help="compare two JSON contract artifacts",
    )
    compare_contract.add_argument("expected", help="expected JSON contract path")
    compare_contract.add_argument("actual", help="actual JSON contract path")
    compare_contract.add_argument(
        "--json",
        action="store_true",
        help="write the comparison report as JSON to stdout",
    )
    compare_contract.add_argument(
        "--max-diffs",
        type=int,
        default=20,
        help="maximum differences to print or include in the report",
    )
    compare_contract.add_argument(
        "--ignore-path",
        action="append",
        default=[],
        help="JSON pointer path to ignore; may be passed more than once",
    )
    compare_contract.set_defaults(func=run_compare_contract)

    style_ir = subcommands.add_parser(
        "style-ir",
        help="inspect a compiled otoe-styles.json Style IR artifact",
    )
    style_ir.add_argument("artifact", help="compiled otoe-styles.json path")
    style_ir.add_argument(
        "--strict",
        action="store_true",
        help="fail if styleOps drift from compiled rules or directStyles",
    )
    style_ir_output = style_ir.add_mutually_exclusive_group()
    style_ir_output.add_argument(
        "--summary",
        action="store_true",
        help="write a human summary; this is the default",
    )
    style_ir_output.add_argument(
        "--json",
        action="store_true",
        help="write the Style IR inspection report as JSON",
    )
    style_ir.set_defaults(func=run_style_ir)

    deps = subcommands.add_parser(
        "deps",
        help="audit profile dependencies without installing anything",
    )
    deps.add_argument("target", help="import target label in MODULE:OBJECT form")
    deps.add_argument(
        "--profile",
        default=None,
        choices=["cage"],
        help="offline target profile to audit",
    )
    deps.add_argument(
        "--profile-file",
        help="optional TOML profile file; defaults to otoe.profile.toml when present",
    )
    deps.add_argument(
        "--json",
        action="store_true",
        help="write the dependency audit as JSON to stdout",
    )
    deps.set_defaults(func=run_deps)

    dev = subcommands.add_parser("dev", help="run a local live preview app")
    dev.add_argument("target", help="app target in MODULE:APP form")
    dev.add_argument("--host", default="127.0.0.1")
    dev.add_argument("--port", default=8767, type=int)
    dev.add_argument("--title", default="Otoe Dev")
    dev.add_argument("--css", help="optional CSS file to serve")
    dev.add_argument("--css-route", default="/otoe.css")
    dev.add_argument("--root-class", default="", help="class added to the live root")
    dev.set_defaults(func=run_dev)

    new = subcommands.add_parser("new", help="scaffold a small Otoe app")
    new.add_argument("path", help="directory to create or populate")
    new.add_argument(
        "--name",
        help="display name for the generated app; defaults to the directory name",
    )
    new.add_argument(
        "--force",
        action="store_true",
        help="overwrite existing scaffold files",
    )
    new.add_argument(
        "--no-css",
        action="store_true",
        help="skip writing styles.css",
    )
    new.set_defaults(func=run_new)

    return parser


def _add_offline_profile_args(
    parser: argparse.ArgumentParser,
    *,
    action: str,
    backend_context: str,
    gate: str,
) -> None:
    parser.add_argument("target", help="import target in MODULE:OBJECT form")
    parser.add_argument(
        "--profile",
        default=None,
        choices=["cage"],
        help=f"offline target profile to {action}",
    )
    parser.add_argument(
        "--profile-file",
        help="optional TOML profile file; defaults to otoe.profile.toml when present",
    )
    parser.add_argument(
        "--backend",
        default=None,
        help=f"backend capability profile used for {backend_context}",
    )
    parser.add_argument(
        "--backend-capability-profile",
        help=f"backend capability profile JSON used for {backend_context}",
    )
    parser.add_argument(
        "--backend-coverage-requirements",
        help=f"backend readiness/requirements JSON used as a {gate} gate",
    )
    parser.add_argument(
        "--css",
        action="append",
        help="optional Otoe CSS file to include in the style plan",
    )
    _add_utility_args(parser)
    parser.add_argument(
        "--no-strict-styles",
        action="store_false",
        default=True,
        dest="strict_styles",
        help="treat missing class rules as html-only warnings",
    )


def _add_utility_args(parser: argparse.ArgumentParser) -> None:
    utilities = parser.add_mutually_exclusive_group()
    utilities.add_argument(
        "--utilities",
        action="store_true",
        default=None,
        help="include Otoe's built-in utility stylesheet",
    )
    utilities.add_argument(
        "--no-utilities",
        action="store_false",
        dest="utilities",
        help="disable built-in utilities even when a profile file enables them",
    )


def _build(args: argparse.Namespace) -> int:
    _cli_build.compiled_styles_to_dict = compiled_styles_to_dict
    return _cli_build.run_build(args)
