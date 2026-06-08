from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from .backend_coverage import (
    backend_coverage_report_to_dict,
    requirements_from_backend_coverage_payload,
)
from .capabilities import (
    BackendCapabilityProfile,
    CapabilityProfileError,
    load_backend_capability_profile,
    supported_backend_capability_names,
)
from .cli_common import (
    CliError,
    load_json_artifact,
    load_plan_profile_config,
    load_target,
    write_json_artifact,
)
from .cli_styles import load_plan_stylesheet
from .cli_targets import coerce_render_target
from .mount import MountedNode
from .plan import OtoePlan, PlanError, plan_mounted
from .plan_artifacts import format_plan, plan_to_dict
from .profile_types import PlanProfileConfig
from .runtime_files import RuntimeFileError
from .static_classes import static_class_scan_for_target
from .style import StyleSheet


@dataclass(frozen=True)
class ResolvedPlanRequest:
    profile_config: PlanProfileConfig
    mounted: MountedNode
    plan: OtoePlan
    plan_dict: dict[str, Any]
    stylesheet: StyleSheet | None
    backend_coverage: dict[str, Any] | None


def run_plan(args: argparse.Namespace) -> int:
    try:
        _, plan, plan_dict, _, backend_coverage = resolve_plan_request(args)
        if args.out:
            write_json_artifact(Path(args.out), plan_dict)
    except (CliError, PlanError, RuntimeFileError) as exc:
        print(f"plan: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(plan_dict, indent=2, sort_keys=True))
    else:
        print(format_plan(plan, target=args.target))
        if backend_coverage is not None:
            print(format_plan_backend_coverage(backend_coverage))
        if args.out:
            print(f"plan artifact: {Path(args.out)}")
    return 1 if plan.has_errors or backend_coverage_failed(plan_dict) else 0


def resolve_plan_request(
    args: argparse.Namespace,
) -> tuple[
    PlanProfileConfig,
    OtoePlan,
    dict[str, Any],
    StyleSheet | None,
    dict[str, Any] | None,
]:
    resolved = resolve_plan_request_details(args)
    return (
        resolved.profile_config,
        resolved.plan,
        resolved.plan_dict,
        resolved.stylesheet,
        resolved.backend_coverage,
    )


def resolve_plan_request_details(args: argparse.Namespace) -> ResolvedPlanRequest:
    target = load_target(args.target)
    mounted = coerce_render_target(target)
    profile_config = load_plan_profile_config(args.profile_file)
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
    stylesheet = load_plan_stylesheet(
        css_paths,
        include_utilities=include_utilities,
    )
    static_class_scan = static_class_scan_for_target(args.target)
    framework_static_classes = framework_classes_with_rules(
        static_class_scan.framework_class_candidates,
        stylesheet,
    )
    plan = plan_mounted(
        mounted,
        profile=profile_config.profile,
        backend=plan_backend_capability(profile_config),
        stylesheet=stylesheet,
        static_classes=(
            *static_class_scan.class_names,
            *framework_static_classes,
        ),
        safelist=profile_config.style_safelist,
        diagnostics=static_class_scan.diagnostics,
        strict_styles=args.strict_styles,
    )
    plan_dict = plan_to_dict(plan, target=args.target)
    backend_coverage = plan_backend_coverage_report(profile_config, plan)
    if backend_coverage is not None:
        plan_dict["backendCoverage"] = backend_coverage
    return ResolvedPlanRequest(
        profile_config=profile_config,
        mounted=mounted,
        plan=plan,
        plan_dict=plan_dict,
        stylesheet=stylesheet,
        backend_coverage=backend_coverage,
    )


def framework_classes_with_rules(
    class_names: tuple[str, ...],
    stylesheet: StyleSheet | None,
) -> tuple[str, ...]:
    if stylesheet is None:
        return ()
    return tuple(
        class_name
        for class_name in class_names
        if stylesheet.rules.get(f".{class_name}") is not None
    )


def plan_backend_capability(
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


def plan_backend_coverage_report(
    profile_config: PlanProfileConfig,
    plan: OtoePlan,
) -> dict[str, Any] | None:
    requirements_path = profile_config.backend_coverage_requirements
    if requirements_path is None:
        return None
    payload = load_json_artifact(
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


def format_plan_backend_coverage(report: dict[str, Any]) -> str:
    status = "passed" if report.get("passed") is True else "failed"
    lines = [f"backend coverage: {status}"]
    blockers = report.get("blockers", [])
    if isinstance(blockers, list) and blockers:
        lines.extend(f"backend coverage blocker: {blocker}" for blocker in blockers)
    return "\n".join(lines)


def backend_coverage_failed(plan_dict: dict[str, Any]) -> bool:
    report = plan_dict.get("backendCoverage")
    return isinstance(report, dict) and report.get("passed") is not True
