from __future__ import annotations

import argparse
import compileall
import importlib
import json
import os
import subprocess
import sys
from collections.abc import Callable, Mapping, Sequence
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from typing import Any

from .capabilities import (
    BackendCapabilityProfile,
    CapabilityProfileError,
    backend_capability_profile,
    load_backend_capability_profile,
    supported_backend_capability_names,
)
from .backend_coverage import (
    backend_coverage_report_to_dict,
    requirements_from_backend_coverage_payload,
)
from .build import (
    BACKEND_COVERAGE_ARTIFACT_FILENAME,
    BUILD_MANIFEST_FILENAME,
    DEPS_ARTIFACT_FILENAME,
    PLAN_ARTIFACT_FILENAME,
    RUNNER_FILENAME,
    STYLE_ARTIFACT_FILENAME,
    BuildError,
    build_manifest,
    bundle_artifact,
    copy_assets,
    copy_framework_files,
    copy_runtime_files,
    write_runner,
)
from .contract_compare import (
    ContractCompareError,
    compare_json_contracts,
    delete_json_pointer,
    format_contract_difference,
)
from .deps import audit_deps, deps_to_dict, format_deps
from .html import render_html
from .live_server import LivePreviewApp, LivePreviewConfig, run_live_preview
from .mount import MountedNode, mount
from .native import render_native_png
from .node import Node
from .pack import PackError, pack_bundle
from .plan import (
    OtoePlan,
    PlanError,
    plan_mounted,
)
from .plan_artifacts import (
    compiled_styles_to_dict,
    format_plan,
    plan_to_dict,
)
from .profile import (
    DEFAULT_PROFILE_FILENAME,
    ProfileError,
    load_plan_profile,
)
from .profile_types import PlanProfileConfig
from .runtime_files import RuntimeFileError, build_runtime_files
from .static_classes import static_class_scan_for_target
from .style import StyleError, StyleSheet, css
from .style_ops import StyleIRError, apply_style_ops, load_style_ir, validate_style_ops
from .utilities import utility_stylesheet

DEFAULT_CHECK_PATHS = ("src", "examples", "tests")


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
    check.set_defaults(func=_check)

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
    render.set_defaults(func=_render)

    plan = subcommands.add_parser(
        "plan",
        help="diagnose an Otoe target for an offline deployment profile",
    )
    plan.add_argument("target", help="import target in MODULE:OBJECT form")
    plan.add_argument(
        "--profile",
        default=None,
        choices=["cage"],
        help="offline target profile to diagnose",
    )
    plan.add_argument(
        "--profile-file",
        help="optional TOML profile file; defaults to otoe.profile.toml when present",
    )
    plan.add_argument(
        "--backend",
        default=None,
        help="backend capability profile used for plan diagnostics",
    )
    plan.add_argument(
        "--backend-capability-profile",
        help="backend capability profile JSON used for plan diagnostics",
    )
    plan.add_argument(
        "--backend-coverage-requirements",
        help="backend readiness/requirements JSON used as a plan gate",
    )
    plan.add_argument(
        "--css",
        action="append",
        help="optional Otoe CSS file to include in the style plan",
    )
    utilities = plan.add_mutually_exclusive_group()
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
    plan.add_argument(
        "--no-strict-styles",
        action="store_false",
        default=True,
        dest="strict_styles",
        help="treat missing class rules as html-only warnings",
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
    plan.set_defaults(func=_plan)

    build = subcommands.add_parser(
        "build",
        help="write a minimal offline bundle manifest for an Otoe target",
    )
    build.add_argument("target", help="import target in MODULE:OBJECT form")
    build.add_argument(
        "--out",
        required=True,
        help="output bundle directory",
    )
    build.add_argument(
        "--profile",
        default=None,
        choices=["cage"],
        help="offline target profile to build",
    )
    build.add_argument(
        "--profile-file",
        help="optional TOML profile file; defaults to otoe.profile.toml when present",
    )
    build.add_argument(
        "--backend",
        default=None,
        help="backend capability profile used for build-time plan diagnostics",
    )
    build.add_argument(
        "--backend-capability-profile",
        help="backend capability profile JSON used for build-time plan diagnostics",
    )
    build.add_argument(
        "--backend-coverage-requirements",
        help="backend readiness/requirements JSON used as a build gate",
    )
    build.add_argument(
        "--css",
        action="append",
        help="optional Otoe CSS file to include in the style plan",
    )
    build_utilities = build.add_mutually_exclusive_group()
    build_utilities.add_argument(
        "--utilities",
        action="store_true",
        default=None,
        help="include Otoe's built-in utility stylesheet",
    )
    build_utilities.add_argument(
        "--no-utilities",
        action="store_false",
        dest="utilities",
        help="disable built-in utilities even when a profile file enables them",
    )
    build.add_argument(
        "--no-strict-styles",
        action="store_false",
        default=True,
        dest="strict_styles",
        help="treat missing class rules as html-only warnings",
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
    backend_profile.set_defaults(func=_backend_profile)

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
        "--out",
        help="optional path to write the JSON coverage report",
    )
    backend_coverage.set_defaults(func=_backend_coverage)

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
    pack.set_defaults(func=_pack)

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
    compare_contract.set_defaults(func=_compare_contract)

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
    style_ir.set_defaults(func=_style_ir)

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
    deps.set_defaults(func=_deps)

    dev = subcommands.add_parser("dev", help="run a local live preview app")
    dev.add_argument("target", help="app target in MODULE:APP form")
    dev.add_argument("--host", default="127.0.0.1")
    dev.add_argument("--port", default=8767, type=int)
    dev.add_argument("--title", default="Otoe Dev")
    dev.add_argument("--css", help="optional CSS file to serve")
    dev.add_argument("--css-route", default="/otoe.css")
    dev.add_argument("--root-class", default="", help="class added to the live root")
    dev.set_defaults(func=_dev)

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
    new.set_defaults(func=_new)

    return parser


def _check(args: argparse.Namespace) -> int:
    paths = tuple(args.paths or DEFAULT_CHECK_PATHS)
    ok = True
    for path in paths:
        ok = _compile_path(path) and ok
    if not ok:
        return 1
    if args.tests:
        command = [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            *args.pytest_arg,
            *_pytest_args(args.pytest_args),
        ]
        print(f"pytest: {' '.join(command)}")
        return subprocess.run(command).returncode
    return 0


def _compile_path(path: str) -> bool:
    target = Path(path)
    if not target.exists():
        print(f"compile {path}: missing", file=sys.stderr)
        return False
    if target.is_dir():
        ok = compileall.compile_dir(str(target), quiet=1)
    else:
        ok = compileall.compile_file(str(target), quiet=1)
    print(f"compile {path}: {'ok' if ok else 'failed'}")
    return bool(ok)


def _pytest_args(args: list[str]) -> list[str]:
    if args and args[0] == "--":
        return args[1:]
    return args


def _render(args: argparse.Namespace) -> int:
    try:
        target = _load_target(args.target)
        mounted = _coerce_render_target(target)
        stylesheet = _load_stylesheet(args.css)
    except CliError as exc:
        print(f"render: {exc}", file=sys.stderr)
        return 1

    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        if args.native:
            render_native_png(
                mounted,
                output,
                stylesheet=stylesheet,
                strict_styles=args.strict_styles,
                background=args.background,
            )
            print(f"render native {args.target}: {output}")
            return 0

        output.write_text(
            render_html(
                mounted,
                pretty=args.pretty,
                indent=args.indent,
                stylesheet=stylesheet,
                strict_styles=args.strict_styles,
            ),
            encoding="utf-8",
        )
    except (StyleError, ValueError) as exc:
        print(f"render: {exc}", file=sys.stderr)
        return 1
    print(f"render {args.target}: {output}")
    return 0


def _plan(args: argparse.Namespace) -> int:
    try:
        _, plan, plan_dict, _, backend_coverage = _resolve_plan_request(args)
        if args.out:
            _write_json_artifact(Path(args.out), plan_dict)
    except (CliError, PlanError, RuntimeFileError) as exc:
        print(f"plan: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(plan_dict, indent=2, sort_keys=True))
    else:
        print(format_plan(plan, target=args.target))
        if backend_coverage is not None:
            print(_format_plan_backend_coverage(backend_coverage))
        if args.out:
            print(f"plan artifact: {Path(args.out)}")
    return 1 if plan.has_errors or _backend_coverage_failed(plan_dict) else 0


def _build(args: argparse.Namespace) -> int:
    try:
        (
            profile_config,
            plan,
            plan_dict,
            stylesheet,
            backend_coverage,
        ) = _resolve_plan_request(args)
        output = Path(args.out)
        output.mkdir(parents=True, exist_ok=True)
        plan_path = output / PLAN_ARTIFACT_FILENAME
        _write_json_artifact(plan_path, plan_dict)
        if plan.has_errors:
            raise BuildError("plan invalid; refusing to write build manifest")
        backend_coverage_path = None
        if backend_coverage is not None:
            backend_coverage_path = output / BACKEND_COVERAGE_ARTIFACT_FILENAME
            _write_json_artifact(backend_coverage_path, backend_coverage)
            if backend_coverage.get("passed") is not True:
                raise BuildError(
                    "backend coverage invalid; refusing to write build manifest"
                )
        deps_audit = audit_deps(target=args.target, profile_config=profile_config)
        deps_dict = deps_to_dict(deps_audit)
        deps_path = output / DEPS_ARTIFACT_FILENAME
        _write_json_artifact(deps_path, deps_dict)
        if deps_audit.has_errors:
            raise BuildError(
                "dependency audit invalid; refusing to write build manifest"
            )
        style_path = output / STYLE_ARTIFACT_FILENAME
        _write_json_artifact(
            style_path,
            compiled_styles_to_dict(
                plan,
                target=args.target,
                stylesheet=stylesheet,
            ),
        )
        artifact_manifest = [
            bundle_artifact(plan_path, output_dir=output),
            bundle_artifact(deps_path, output_dir=output),
            bundle_artifact(style_path, output_dir=output),
        ]
        if backend_coverage_path is not None:
            artifact_manifest.append(
                bundle_artifact(backend_coverage_path, output_dir=output)
            )
        framework_file_manifest = copy_framework_files(
            profile_config,
            output_dir=output,
        )
        asset_manifest = copy_assets(profile_config.assets, output_dir=output)
        runtime_file_manifest = copy_runtime_files(
            build_runtime_files(args.target, profile_config.runtime_files),
            output_dir=output,
        )
        runner_manifest = write_runner(output_dir=output)
        manifest = build_manifest(
            target=args.target,
            plan=plan_dict,
            deps=deps_dict,
            profile_config=profile_config,
            assets=asset_manifest,
            artifacts=artifact_manifest,
            backend_coverage=backend_coverage,
            framework_files=framework_file_manifest,
            runner=runner_manifest,
            runtime_files=runtime_file_manifest,
        )
        manifest_path = output / BUILD_MANIFEST_FILENAME
        _write_json_artifact(manifest_path, manifest)
        if args.validate:
            _validate_build_runner(output)
    except (BuildError, CliError, PlanError, RuntimeFileError) as exc:
        print(f"build: {exc}", file=sys.stderr)
        return 1

    print(f"build {args.target}: {output}")
    print(f"plan artifact: {plan_path}")
    if backend_coverage_path is not None:
        print(f"backend coverage artifact: {backend_coverage_path}")
    print(f"deps artifact: {deps_path}")
    print(f"styles artifact: {style_path}")
    print(f"manifest: {manifest_path}")
    if args.validate:
        print("validation: ok")
    return 0


def _backend_profile(args: argparse.Namespace) -> int:
    try:
        profile = _backend_profile_from_args(args)
    except (CliError, OSError, CapabilityProfileError) as exc:
        print(f"backend-profile: {exc}", file=sys.stderr)
        return 1

    if args.coverage_declaration:
        _emit_json_payload(
            profile.coverage_declaration(),
            print_json=args.json or args.out is None,
            output_path=args.out,
            artifact_label="backend profile artifact",
        )
        return 0

    report = _backend_profile_report(profile)
    if args.json or args.out:
        _emit_json_payload(
            report,
            print_json=args.json,
            output_path=args.out,
            artifact_label="backend profile artifact",
        )
    else:
        print(_format_backend_profile_report(report))
    return 0


def _backend_coverage(args: argparse.Namespace) -> int:
    try:
        declaration = _backend_coverage_declaration_from_args(args)
        requirements_payload = _load_json_artifact(
            Path(args.requirements),
            label="requirements",
        )
        if not isinstance(requirements_payload, dict):
            raise CliError("requirements JSON must be an object")
        requirements, readiness_report = requirements_from_backend_coverage_payload(
            requirements_payload
        )
    except (CliError, OSError, CapabilityProfileError) as exc:
        print(f"backend-coverage: {exc}", file=sys.stderr)
        return 1

    report = backend_coverage_report_to_dict(
        declaration,
        requirements=requirements,
        readiness_report=readiness_report,
    )
    if args.json:
        _emit_json_payload(
            report,
            print_json=True,
            output_path=args.out,
            artifact_label="backend coverage artifact",
        )
    elif args.out:
        _emit_json_payload(
            report,
            print_json=False,
            output_path=args.out,
            artifact_label="backend coverage artifact",
        )
    else:
        print(_format_backend_coverage_report(report))
    return 0 if report["passed"] else 1


def _pack(args: argparse.Namespace) -> int:
    try:
        result = pack_bundle(Path(args.bundle), Path(args.out))
    except PackError as exc:
        print(f"pack: {exc}", file=sys.stderr)
        return 1

    print(f"pack {Path(args.bundle)}: {Path(args.out)}")
    print(f"files: {result.files}")
    print(f"size: {result.size}")
    print(f"sha256: {result.sha256}")
    return 0


def _compare_contract(args: argparse.Namespace) -> int:
    try:
        expected = _load_json_artifact(Path(args.expected), label="expected")
        actual = _load_json_artifact(Path(args.actual), label="actual")
        ignored_paths = tuple(args.ignore_path or ())
        if ignored_paths:
            expected = deepcopy(expected)
            actual = deepcopy(actual)
            for pointer in ignored_paths:
                delete_json_pointer(expected, pointer)
                delete_json_pointer(actual, pointer)
    except (CliError, ContractCompareError) as exc:
        print(f"compare-contract: {exc}", file=sys.stderr)
        return 1

    differences = compare_json_contracts(expected, actual)
    max_diffs = max(args.max_diffs, 0)
    shown_differences = differences[:max_diffs]
    report = {
        "schemaVersion": 1,
        "expected": str(Path(args.expected)),
        "actual": str(Path(args.actual)),
        "matched": not differences,
        "differenceCount": len(differences),
        "differences": shown_differences,
        "ignoredPaths": list(ignored_paths),
        "truncated": len(shown_differences) < len(differences),
    }

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    elif not differences:
        print(f"contracts match: {Path(args.expected)} == {Path(args.actual)}")
    else:
        print(
            f"contracts differ: {len(differences)} difference(s) between "
            f"{Path(args.expected)} and {Path(args.actual)}"
        )
        for difference in shown_differences:
            print(format_contract_difference(difference))
        if report["truncated"]:
            print(f"... {len(differences) - len(shown_differences)} more difference(s)")

    return 0 if not differences else 1


def _style_ir(args: argparse.Namespace) -> int:
    artifact_path = Path(args.artifact)
    try:
        payload = _load_json_artifact(artifact_path, label="style artifact")
        artifact = load_style_ir(payload)
        applied = apply_style_ops(artifact)
        validation = validate_style_ops(artifact) if args.strict else None
    except (CliError, StyleIRError) as exc:
        print(f"style-ir: {exc}", file=sys.stderr)
        return 1

    report = _style_ir_report(
        artifact_path,
        artifact,
        applied,
        strict=args.strict,
        validation=validation,
    )
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(_format_style_ir_report(report))
    return 0 if report["passed"] else 1


def _style_ir_report(
    artifact_path: Path,
    artifact,
    applied,
    *,
    strict: bool,
    validation,
) -> dict[str, Any]:
    class_reports = [
        {
            "className": replay.class_name,
            "selector": replay.selector,
            "missing": replay.missing,
            "appliedDeclarations": replay.applied_declarations,
            "omittedOps": list(replay.omitted_ops),
            "errors": list(replay.errors),
        }
        for replay in applied.classes
    ]
    direct_style_reports = [
        {
            "path": list(replay.path),
            "widget": replay.widget,
            "appliedDeclarations": replay.applied_declarations,
            "omittedOps": list(replay.omitted_ops),
            "errors": list(replay.errors),
        }
        for replay in applied.direct_styles
    ]
    style_ops_errors = [
        *applied.errors,
        *(
            error
            for replay in applied.classes
            for error in replay.errors
        ),
        *(
            error
            for replay in applied.direct_styles
            for error in replay.errors
        ),
    ]
    strict_errors = list(validation.errors) if validation is not None else []
    errors = strict_errors if strict else style_ops_errors
    return {
        "schemaVersion": 1,
        "artifact": str(artifact_path),
        "target": artifact.payload.get("target"),
        "profile": artifact.payload.get("profile"),
        "backend": artifact.backend,
        "status": artifact.payload.get("status"),
        "styleIr": {
            "schemaVersion": artifact.schema_version,
        },
        "styleOps": {
            "schemaVersion": artifact.style_ops_schema_version,
            "format": artifact.style_ops_format,
            "passed": applied.passed,
        },
        "strict": {
            "enabled": strict,
            "passed": not strict_errors,
            "errors": strict_errors,
        },
        "counts": {
            "rules": len(artifact.rules),
            "classOps": len(applied.classes),
            "directStyles": len(artifact.direct_styles),
            "directStyleOps": len(applied.direct_styles),
            "errors": len(errors),
        },
        "classes": class_reports,
        "directStyles": direct_style_reports,
        "errors": errors,
        "passed": not errors,
    }


def _format_style_ir_report(report: dict[str, Any]) -> str:
    counts = report["counts"]
    style_ops = report["styleOps"]
    status = "passed" if report["passed"] else "failed"
    lines = [
        f"style-ir {report['artifact']}",
        f"target: {report.get('target') or '<unknown>'}",
        f"profile: {report.get('profile') or '<unknown>'}",
        f"backend: {report.get('backend') or '<unknown>'}",
        f"status: {report.get('status') or '<unknown>'}",
        (
            "styleOps: "
            f"schema={style_ops['schemaVersion']} "
            f"format={style_ops['format']} "
            f"{status}"
        ),
        f"classes: {counts['rules']} rules, {counts['classOps']} primitive entries",
        (
            "direct styles: "
            f"{counts['directStyles']} entries, "
            f"{counts['directStyleOps']} primitive entries"
        ),
    ]
    if report["errors"]:
        lines.append(f"errors: {len(report['errors'])}")
        lines.extend(f"error: {error}" for error in report["errors"])
    else:
        lines.append("errors: none")
    if report["strict"]["enabled"]:
        strict_status = "passed" if report["strict"]["passed"] else "failed"
        lines.append(f"strict: {strict_status}")
    return "\n".join(lines)


def _emit_json_payload(
    payload: dict[str, Any],
    *,
    print_json: bool,
    output_path: str | None,
    artifact_label: str,
) -> None:
    encoded = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if output_path is not None:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(encoded, encoding="utf-8")
        if not print_json:
            print(f"{artifact_label}: {path}")
    if print_json:
        print(encoded, end="")


def _backend_profile_from_args(args: argparse.Namespace) -> BackendCapabilityProfile:
    if args.profile is not None and args.backend_capability_profile is not None:
        raise CliError(
            "profile name and --backend-capability-profile are mutually exclusive"
        )
    if args.backend_capability_profile is not None:
        return load_backend_capability_profile(args.backend_capability_profile)
    return backend_capability_profile(args.profile)


def _backend_coverage_declaration_from_args(args: argparse.Namespace) -> dict[str, Any]:
    coverage_sources = sum(
        source is not None
        for source in (
            args.coverage_declaration,
            args.backend,
            args.backend_capability_profile,
        )
    )
    if coverage_sources > 1:
        raise CliError(
            "--coverage-declaration, --backend, and "
            "--backend-capability-profile are mutually exclusive"
        )
    if args.coverage_declaration is not None:
        payload = _load_json_artifact(
            Path(args.coverage_declaration),
            label="coverage declaration",
        )
        if not isinstance(payload, dict):
            raise CliError("coverage declaration JSON must be an object")
        return payload
    profile = _backend_profile_from_name_or_path(
        profile_name=args.backend,
        profile_path=args.backend_capability_profile,
    )
    return profile.coverage_declaration()


def _backend_profile_from_name_or_path(
    *,
    profile_name: str | None,
    profile_path: str | None,
) -> BackendCapabilityProfile:
    if profile_name is not None and profile_path is not None:
        raise CliError(
            "profile name and --backend-capability-profile are mutually exclusive"
        )
    if profile_path is not None:
        return load_backend_capability_profile(profile_path)
    return backend_capability_profile(profile_name)


def _backend_profile_report(profile: BackendCapabilityProfile) -> dict[str, Any]:
    coverage_declaration = profile.coverage_declaration()
    covers = coverage_declaration["covers"]
    return {
        "schemaVersion": 1,
        "format": "backend-profile-report",
        "profile": profile.to_dict(),
        "summary": {
            "styles": _support_counts(profile.style_support),
            "widgets": _support_counts(profile.widget_support),
            "inputs": _support_counts(profile.input_support),
            "coverage": {
                "widgets": len(covers["widgets"]),
                "inputs": len(covers["inputs"]),
                "styles": len(covers["styles"]),
                "declaredStyleOmissions": len(covers["declaredStyleOmissions"]),
            },
        },
        "coverageDeclaration": coverage_declaration,
    }


def _format_backend_profile_report(report: dict[str, Any]) -> str:
    profile = report["profile"]
    summary = report["summary"]
    coverage = summary["coverage"]
    return "\n".join(
        [
            f"backend-profile {profile['name']}",
            f"label: {profile['label']}",
            f"styles: {_format_support_counts(summary['styles'])}",
            f"widgets: {_format_support_counts(summary['widgets'])}",
            f"inputs: {_format_support_counts(summary['inputs'])}",
            (
                "coverage: "
                f"widgets={coverage['widgets']}, "
                f"inputs={coverage['inputs']}, "
                f"styles={coverage['styles']}, "
                f"declaredStyleOmissions={coverage['declaredStyleOmissions']}"
            ),
        ]
    )


def _format_backend_coverage_report(report: dict[str, Any]) -> str:
    status = "passed" if report["passed"] else "failed"
    readiness_status = "passed" if report["readiness"]["passed"] else "failed"
    lines = [
        f"backend-coverage {report.get('backend') or '<unknown>'}",
        f"status: {status}",
        f"readiness: {readiness_status}",
    ]
    for section in ("widgets", "inputs", "styles", "declaredStyleOmissions"):
        summary = report["coverage"][section]["summary"]
        lines.append(
            f"{section}: "
            f"covered={summary['covered']}/{summary['required']}, "
            f"missing={summary['missing']}, "
            f"extra={summary['extra']}"
        )
        missing = report["coverage"][section]["missing"]
        if missing:
            lines.append(f"{section} missing: {', '.join(missing)}")
    if report["declarationErrors"]:
        lines.append(f"declaration errors: {len(report['declarationErrors'])}")
        lines.extend(f"error: {error}" for error in report["declarationErrors"])
    if report["blockers"]:
        lines.append(f"blockers: {', '.join(report['blockers'])}")
    else:
        lines.append("blockers: none")
    return "\n".join(lines)


def _format_plan_backend_coverage(report: dict[str, Any]) -> str:
    status = "passed" if report.get("passed") is True else "failed"
    lines = [f"backend coverage: {status}"]
    blockers = report.get("blockers", [])
    if isinstance(blockers, list) and blockers:
        lines.extend(f"backend coverage blocker: {blocker}" for blocker in blockers)
    return "\n".join(lines)


def _backend_coverage_failed(plan_dict: dict[str, Any]) -> bool:
    report = plan_dict.get("backendCoverage")
    return isinstance(report, dict) and report.get("passed") is not True


def _support_counts(values: Mapping[str, str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for support in values.values():
        counts[support] = counts.get(support, 0) + 1
    return dict(sorted(counts.items()))


def _format_support_counts(counts: Mapping[str, int]) -> str:
    if not counts:
        return "none"
    return ", ".join(f"{name}={count}" for name, count in sorted(counts.items()))


def _validate_build_runner(output: Path) -> None:
    _run_build_runner(output, "--verify", label="verification")
    _run_build_runner(output, "--check", label="validation")
    _run_build_runner(output, "--layout-check", label="layout validation")


def _run_build_runner(output: Path, mode: str, *, label: str) -> None:
    command = [sys.executable, str(output / RUNNER_FILENAME), mode]
    result = subprocess.run(
        command,
        capture_output=True,
        cwd=output,
        env={**os.environ, "PYTHONPATH": ""},
        text=True,
    )
    if result.returncode == 0:
        return
    details = result.stderr.strip() or result.stdout.strip()
    if not details:
        details = f"runner exited with status {result.returncode}"
    raise BuildError(f"runner {label} failed: {details}")


def _deps(args: argparse.Namespace) -> int:
    try:
        _parse_target_spec(args.target)
        profile_config = _load_plan_profile_config(args.profile_file)
        if args.profile is not None:
            profile_config = replace(profile_config, profile=args.profile)
        audit = audit_deps(target=args.target, profile_config=profile_config)
    except CliError as exc:
        print(f"deps: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(deps_to_dict(audit), indent=2, sort_keys=True))
    else:
        print(format_deps(audit))
    return 1 if audit.has_errors else 0


def _dev(args: argparse.Namespace) -> int:
    try:
        target = _load_target(args.target)
        app_factory = _coerce_dev_app_factory(target)
        css_path = _dev_css_path(args.css)
    except CliError as exc:
        print(f"dev: {exc}", file=sys.stderr)
        return 1

    config = LivePreviewConfig(
        title=args.title,
        css_route=args.css_route,
        css_path=css_path,
        root_class=args.root_class,
    )
    try:
        run_live_preview(
            app_factory=app_factory,
            config=config,
            host=args.host,
            port=args.port,
            label="Otoe dev",
        )
    except CliError as exc:
        print(f"dev: {exc}", file=sys.stderr)
        return 1
    return 0


def _new(args: argparse.Namespace) -> int:
    target = Path(args.path)
    app_name = args.name or _display_name_from_path(target)
    try:
        target.mkdir(parents=True, exist_ok=True)
        _write_scaffold_file(
            target / "app.py",
            _app_template(app_name),
            force=args.force,
        )
        _write_scaffold_file(
            target / "README.md",
            _readme_template(app_name, include_css=not args.no_css),
            force=args.force,
        )
        if not args.no_css:
            _write_scaffold_file(
                target / "styles.css",
                _css_template(),
                force=args.force,
            )
    except CliError as exc:
        print(f"new: {exc}", file=sys.stderr)
        return 1
    print(f"new {app_name}: {target}")
    return 0


def _load_target(spec: str) -> Any:
    module_name, object_path = _parse_target_spec(spec)
    _ensure_cwd_on_syspath()
    try:
        value = importlib.import_module(module_name)
    except Exception as exc:
        raise CliError(f"could not import module {module_name!r}") from exc
    for part in object_path.split("."):
        try:
            value = getattr(value, part)
        except AttributeError as exc:
            raise CliError(f"{spec!r} could not resolve attribute {part!r}") from exc
    return value


def _ensure_cwd_on_syspath() -> None:
    cwd = str(Path.cwd())
    if "" in sys.path or cwd in sys.path:
        return
    sys.path.insert(0, cwd)


def _parse_target_spec(spec: str) -> tuple[str, str]:
    module_name, separator, object_path = spec.partition(":")
    if not separator or not module_name or not object_path:
        raise CliError("target must use MODULE:OBJECT syntax")
    return module_name, object_path


def _load_stylesheet(path: str | Path | None) -> StyleSheet | None:
    if path is None:
        return None
    source = Path(path)
    if not source.exists():
        raise CliError(f"css file {path!r} does not exist")
    try:
        return css(source.read_text(encoding="utf-8"))
    except StyleError as exc:
        raise CliError(f"css file {path!r}: {exc}") from exc


def _load_plan_profile_config(path: str | None) -> PlanProfileConfig:
    profile_path = Path(path) if path is not None else Path(DEFAULT_PROFILE_FILENAME)
    if not profile_path.exists():
        if path is not None:
            raise CliError(f"profile file {path!r} does not exist")
        return PlanProfileConfig()
    try:
        return load_plan_profile(profile_path)
    except ProfileError as exc:
        raise CliError(str(exc)) from exc


def _resolve_plan_request(
    args: argparse.Namespace,
) -> tuple[
    PlanProfileConfig,
    Any,
    dict[str, Any],
    StyleSheet | None,
    dict[str, Any] | None,
]:
    target = _load_target(args.target)
    mounted = _coerce_render_target(target)
    profile_config = _load_plan_profile_config(args.profile_file)
    if args.profile is not None:
        profile_config = replace(profile_config, profile=args.profile)
    if (
        getattr(args, "backend", None) is not None
        and getattr(args, "backend_capability_profile", None) is not None
    ):
        raise CliError(
            "--backend and --backend-capability-profile are mutually exclusive"
        )
    if getattr(args, "backend", None) is not None:
        profile_config = replace(
            profile_config,
            backend_capability=args.backend,
            backend_capability_profile=None,
        )
    if getattr(args, "backend_capability_profile", None) is not None:
        profile_config = replace(
            profile_config,
            backend_capability=None,
            backend_capability_profile=Path(args.backend_capability_profile),
        )
    if getattr(args, "backend_coverage_requirements", None) is not None:
        profile_config = replace(
            profile_config,
            backend_coverage_requirements=Path(args.backend_coverage_requirements),
        )
    include_utilities = profile_config.utilities if args.utilities is None else args.utilities
    css_paths = tuple(args.css or profile_config.css_paths)
    stylesheet = _load_plan_stylesheet(
        css_paths,
        include_utilities=include_utilities,
    )
    static_class_scan = static_class_scan_for_target(args.target)
    plan = plan_mounted(
        mounted,
        profile=profile_config.profile,
        backend=_plan_backend_capability(profile_config),
        stylesheet=stylesheet,
        static_classes=static_class_scan.class_names,
        safelist=profile_config.style_safelist,
        diagnostics=static_class_scan.diagnostics,
        strict_styles=args.strict_styles,
    )
    plan_dict = plan_to_dict(plan, target=args.target)
    backend_coverage = _plan_backend_coverage_report(profile_config, plan)
    if backend_coverage is not None:
        plan_dict["backendCoverage"] = backend_coverage
    return profile_config, plan, plan_dict, stylesheet, backend_coverage


def _plan_backend_capability(
    profile_config: PlanProfileConfig,
) -> str | BackendCapabilityProfile | None:
    if profile_config.backend_capability_profile is not None:
        try:
            return load_backend_capability_profile(
                profile_config.backend_capability_profile
            )
        except (OSError, CapabilityProfileError) as exc:
            raise CliError(str(exc)) from exc
    if profile_config.backend_capability is not None:
        return profile_config.backend_capability
    if profile_config.backend_name in supported_backend_capability_names():
        return profile_config.backend_name
    return None


def _plan_backend_coverage_report(
    profile_config: PlanProfileConfig,
    plan: OtoePlan,
) -> dict[str, Any] | None:
    requirements_path = profile_config.backend_coverage_requirements
    if requirements_path is None:
        return None
    payload = _load_json_artifact(
        requirements_path,
        label="backend coverage requirements",
    )
    if not isinstance(payload, dict):
        raise CliError("backend coverage requirements JSON must be an object")
    requirements, readiness_report = requirements_from_backend_coverage_payload(payload)
    return backend_coverage_report_to_dict(
        plan.backend_capabilities.coverage_declaration(),
        requirements=requirements,
        readiness_report=readiness_report,
    )


def _load_plan_stylesheet(
    paths: Sequence[str | Path],
    *,
    include_utilities: bool,
) -> StyleSheet | None:
    stylesheets: list[StyleSheet] = []
    if include_utilities:
        stylesheets.append(utility_stylesheet())
    for path in paths:
        stylesheet = _load_stylesheet(path)
        if stylesheet is not None:
            stylesheets.append(stylesheet)
    if not stylesheets:
        return None
    return _merge_stylesheets(stylesheets)


def _merge_stylesheets(stylesheets: list[StyleSheet]) -> StyleSheet:
    rules = {}
    tokens = {}
    for stylesheet in stylesheets:
        rules.update(stylesheet.rules)
        tokens.update(stylesheet.tokens)
    return StyleSheet(rules=rules, tokens=tokens)


def _write_json_artifact(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _load_json_artifact(path: Path, *, label: str) -> Any:
    if not path.exists():
        raise CliError(f"{label} file {str(path)!r} does not exist")
    if not path.is_file():
        raise CliError(f"{label} path {str(path)!r} is not a file")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise CliError(f"{label} file {str(path)!r} is not valid JSON: {exc}") from exc


def _coerce_render_target(target: Any) -> MountedNode:
    if isinstance(target, MountedNode):
        return target
    if isinstance(target, Node):
        return mount(target)
    if callable(target):
        return _coerce_render_target(target())
    raise CliError(
        "render target must be a Node, MountedNode, or zero-argument callable "
        f"returning one; got {type(target).__name__}"
    )


def _coerce_dev_app_factory(target: Any) -> Callable[[], LivePreviewApp]:
    if _is_live_preview_app(target):
        return lambda: target
    if callable(target):
        return lambda: _coerce_dev_app(target())
    return _coerce_dev_app(target)


def _coerce_dev_app(target: Any) -> LivePreviewApp:
    if _is_live_preview_app(target):
        return target
    raise CliError(
        "dev target must expose render_fragment() and dispatch_event(event_id, *args)"
    )


def _is_live_preview_app(target: Any) -> bool:
    if callable(getattr(target, "render_fragment", None)) and callable(
        getattr(target, "dispatch_event", None)
    ):
        return True
    return False


def _dev_css_path(path: str | None) -> Path | None:
    if path is None:
        return None
    css_path = Path(path)
    if not css_path.exists():
        raise CliError(f"css file {path!r} does not exist")
    return css_path


def _write_scaffold_file(path: Path, content: str, *, force: bool) -> None:
    if path.exists() and not force:
        raise CliError(f"{path} already exists; pass --force to overwrite")
    path.write_text(content, encoding="utf-8")


def _display_name_from_path(path: Path) -> str:
    name = path.name.strip().replace("_", " ").replace("-", " ")
    return name.title() if name else "Otoe App"


def _app_template(app_name: str) -> str:
    return (
        "from otoe import Button, Text, VStack, computed, signal\n"
        "\n"
        "\n"
        "count = signal(0)\n"
        "\n"
        "\n"
        "def app():\n"
        f"    title = {app_name!r}\n"
        "    label = computed(lambda: f\"Count: {count.value}\")\n"
        "    return VStack(\n"
        "        Text(title, className=\"title\"),\n"
        "        Text(label),\n"
        "        Button(\"Increment\", onClick=lambda: count.set(count.value + 1)),\n"
        "        className=\"app\",\n"
        "        gap=8,\n"
        "        padding=12,\n"
        "    )\n"
    )


def _readme_template(app_name: str, *, include_css: bool) -> str:
    css_arg = " --css styles.css" if include_css else ""
    return (
        f"# {app_name}\n"
        "\n"
        "Render the app from this directory:\n"
        "\n"
        "```bash\n"
        f"otoe render app:app --out preview.html{css_arg} --pretty\n"
        f"otoe render app:app --out preview.png --native{css_arg}\n"
        "```\n"
    )


def _css_template() -> str:
    return (
        ".app {\n"
        "  padding: 16;\n"
        "  gap: 8;\n"
        "  background: #f8fafc;\n"
        "}\n"
        "\n"
        ".title {\n"
        "  color: #111827;\n"
        "  font-size: 20;\n"
        "}\n"
    )


class CliError(ValueError):
    pass
