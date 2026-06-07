from __future__ import annotations

import argparse
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .backend_coverage import (
    backend_coverage_report_to_dict,
    requirements_from_backend_coverage_payload,
)
from .capabilities import (
    BackendCapabilityProfile,
    CapabilityProfileError,
    backend_capability_profile,
    load_backend_capability_profile,
)
from .cli_common import CliError, emit_json_payload, load_json_artifact


def run_backend_profile(args: argparse.Namespace) -> int:
    try:
        profile = backend_profile_from_args(args)
    except (CliError, OSError, CapabilityProfileError) as exc:
        print(f"backend-profile: {exc}", file=sys.stderr)
        return 1

    if args.coverage_declaration:
        emit_json_payload(
            profile.coverage_declaration(),
            print_json=args.json or args.out is None,
            output_path=args.out,
            artifact_label="backend profile artifact",
        )
        return 0

    report = backend_profile_report(profile)
    if args.json or args.out:
        emit_json_payload(
            report,
            print_json=args.json,
            output_path=args.out,
            artifact_label="backend profile artifact",
        )
    else:
        print(format_backend_profile_report(report))
    return 0


def run_backend_coverage(args: argparse.Namespace) -> int:
    try:
        if args.audit and (args.json or args.out):
            raise CliError("--audit cannot be combined with --json or --out")
        declaration = backend_coverage_declaration_from_args(args)
        requirements_payload = load_json_artifact(
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
        emit_json_payload(
            report,
            print_json=True,
            output_path=args.out,
            artifact_label="backend coverage artifact",
        )
    elif args.out:
        emit_json_payload(
            report,
            print_json=False,
            output_path=args.out,
            artifact_label="backend coverage artifact",
        )
    else:
        if args.audit:
            print(format_backend_coverage_audit(report))
        else:
            print(format_backend_coverage_report(report))
    return 0 if report["passed"] else 1


def backend_profile_from_args(args: argparse.Namespace) -> BackendCapabilityProfile:
    if args.profile is not None and args.backend_capability_profile is not None:
        raise CliError(
            "profile name and --backend-capability-profile are mutually exclusive"
        )
    if args.backend_capability_profile is not None:
        return load_backend_capability_profile(args.backend_capability_profile)
    return backend_capability_profile(args.profile)


def backend_coverage_declaration_from_args(args: argparse.Namespace) -> dict[str, Any]:
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
        payload = load_json_artifact(
            Path(args.coverage_declaration),
            label="coverage declaration",
        )
        if not isinstance(payload, dict):
            raise CliError("coverage declaration JSON must be an object")
        return payload
    profile = backend_profile_from_name_or_path(
        profile_name=args.backend,
        profile_path=args.backend_capability_profile,
    )
    return profile.coverage_declaration()


def backend_profile_from_name_or_path(
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


def backend_profile_report(profile: BackendCapabilityProfile) -> dict[str, Any]:
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
            "rendererBoundaries": _support_counts(
                profile.renderer_boundary_support
            ),
            "coverage": {
                "rendererBoundaries": len(covers["rendererBoundaries"]),
                "widgets": len(covers["widgets"]),
                "inputs": len(covers["inputs"]),
                "styles": len(covers["styles"]),
                "declaredStyleOmissions": len(covers["declaredStyleOmissions"]),
            },
        },
        "coverageDeclaration": coverage_declaration,
    }


def format_backend_profile_report(report: dict[str, Any]) -> str:
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
                "renderer boundaries: "
                f"{_format_support_counts(summary['rendererBoundaries'])}"
            ),
            (
                "coverage: "
                f"rendererBoundaries={coverage['rendererBoundaries']}, "
                f"widgets={coverage['widgets']}, "
                f"inputs={coverage['inputs']}, "
                f"styles={coverage['styles']}, "
                f"declaredStyleOmissions={coverage['declaredStyleOmissions']}"
            ),
        ]
    )


def format_backend_coverage_report(report: dict[str, Any]) -> str:
    status = "passed" if report["passed"] else "failed"
    readiness_status = "passed" if report["readiness"]["passed"] else "failed"
    lines = [
        f"backend-coverage {report.get('backend') or '<unknown>'}",
        f"status: {status}",
        f"readiness: {readiness_status}",
    ]
    for section in (
        "rendererBoundaries",
        "widgets",
        "inputs",
        "styles",
        "declaredStyleOmissions",
    ):
        summary = report["coverage"][section]["summary"]
        lines.append(
            f"{section}: "
            f"covered={summary['covered']}/{summary['required']}, "
            f"missing={summary['missing']}, "
            f"unproven={summary['unproven']}"
        )
        missing = report["coverage"][section]["missing"]
        if missing:
            lines.append(f"{section} missing: {', '.join(missing)}")
        unproven = report["coverage"][section]["evidence"]["unproven"]
        if unproven:
            lines.append(f"{section} unproven: {', '.join(unproven)}")
    if report["declarationErrors"]:
        lines.append(f"declaration errors: {len(report['declarationErrors'])}")
        lines.extend(f"error: {error}" for error in report["declarationErrors"])
    evidence_errors = report["readiness"].get("evidenceErrors", [])
    if evidence_errors:
        lines.append(f"evidence errors: {len(evidence_errors)}")
        lines.extend(_format_backend_coverage_evidence_summary(report))
        lines.extend(
            f"evidence error: {error['message']}"
            for error in evidence_errors
            if isinstance(error, dict) and isinstance(error.get("message"), str)
        )
    if report["blockers"]:
        lines.append(f"blockers: {', '.join(report['blockers'])}")
    else:
        lines.append("blockers: none")
    return "\n".join(lines)


def format_backend_coverage_audit(report: dict[str, Any]) -> str:
    status = "passed" if report["passed"] else "failed"
    readiness_status = "passed" if report["readiness"]["passed"] else "failed"
    lines = [
        f"backend-coverage audit {report.get('backend') or '<unknown>'}",
        f"status: {status}",
        f"readiness: {readiness_status}",
    ]
    for section in (
        "rendererBoundaries",
        "widgets",
        "inputs",
        "styles",
        "declaredStyleOmissions",
    ):
        section_payload = report["coverage"][section]
        summary = section_payload["summary"]
        lines.append(
            f"{section}: "
            f"covered={summary['covered']}/{summary['required']}, "
            f"missing={summary['missing']}, "
            f"unproven={summary['unproven']}"
        )
        evidence_map = section_payload.get("evidenceMap", {})
        if not isinstance(evidence_map, dict) or not evidence_map:
            lines.append(f"{section} proof: none")
            continue
        for name, entry in sorted(evidence_map.items()):
            if not isinstance(entry, dict):
                continue
            lines.extend(_format_backend_coverage_audit_entry(section, name, entry))
    if report["declarationErrors"]:
        lines.append(f"declaration errors: {len(report['declarationErrors'])}")
        lines.extend(f"error: {error}" for error in report["declarationErrors"])
    evidence_errors = report["readiness"].get("evidenceErrors", [])
    if evidence_errors:
        lines.append(f"evidence errors: {len(evidence_errors)}")
        lines.extend(_format_backend_coverage_evidence_summary(report))
        lines.extend(
            f"evidence error: {error['message']}"
            for error in evidence_errors
            if isinstance(error, dict) and isinstance(error.get("message"), str)
        )
    if report["blockers"]:
        lines.append(f"blockers: {', '.join(report['blockers'])}")
    else:
        lines.append("blockers: none")
    return "\n".join(lines)


def _format_backend_coverage_audit_entry(
    section: str,
    name: str,
    entry: dict[str, Any],
) -> list[str]:
    status = _coverage_audit_status(entry)
    lines = [
        (
            f"{section} {name}: {status} "
            f"required={_yes_no(entry.get('required'))} "
            f"declared={_yes_no(entry.get('declared'))} "
            f"exercised={_yes_no(entry.get('exercised'))}"
        )
    ]
    sources = entry.get("sources")
    if not isinstance(sources, list) or not sources:
        lines.append(f"{section} {name} proof: none")
        return lines
    for index, source in enumerate(sources):
        if not isinstance(source, dict):
            continue
        lines.append(
            f"{section} {name} proof[{index}]: "
            f"{_format_backend_coverage_source(source)}"
        )
    return lines


def _format_backend_coverage_evidence_summary(report: Mapping[str, Any]) -> list[str]:
    readiness = report.get("readiness")
    if not isinstance(readiness, dict):
        return []
    summary = readiness.get("evidenceSummary")
    if not isinstance(summary, dict):
        return []
    malformed = summary.get("malformed")
    by_blocker = summary.get("malformedByBlocker")
    if not isinstance(malformed, int) or malformed <= 0:
        return []
    lines = [f"evidence malformed: {malformed}"]
    if isinstance(by_blocker, dict):
        counts = [
            f"{blocker}={count}"
            for blocker, count in sorted(by_blocker.items())
            if isinstance(blocker, str) and blocker and isinstance(count, int)
        ]
        if counts:
            lines.append(f"evidence malformed by blocker: {', '.join(counts)}")
    return lines


def _coverage_audit_status(entry: Mapping[str, Any]) -> str:
    if entry.get("missing") is True:
        return "missing"
    if entry.get("unproven") is True:
        return "unproven"
    if entry.get("unevidenced") is True:
        return "unevidenced"
    if entry.get("covered") is True:
        return "covered"
    if entry.get("exercised") is True:
        return "exercised"
    if entry.get("declared") is True and entry.get("required") is not True:
        return "extra"
    return "unknown"


def _format_backend_coverage_source(source: Mapping[str, Any]) -> str:
    parts: list[str] = []
    for key in ("source", "gate", "kind", "support", "status"):
        value = source.get(key)
        if isinstance(value, str) and value:
            parts.append(f"{key}={value}")
    group_index = source.get("groupIndex")
    if isinstance(group_index, int):
        parts.append(f"group={group_index}")
    count = source.get("count")
    if type(count) in {int, float}:
        parts.append(f"count={count:g}")
    runtime = source.get("runtimeProof")
    if isinstance(runtime, dict):
        parts.extend(_format_backend_coverage_runtime(runtime))
    boundary = source.get("boundaryProof")
    if isinstance(boundary, dict):
        parts.extend(_format_backend_coverage_boundary(boundary))
    return " ".join(parts) if parts else "unknown"


def _format_backend_coverage_boundary(boundary: Mapping[str, Any]) -> list[str]:
    parts: list[str] = []
    phase = boundary.get("phase")
    if isinstance(phase, str) and phase:
        parts.append(f"phase={phase}")
    boundary_kind = boundary.get("boundary")
    if isinstance(boundary_kind, str) and boundary_kind:
        parts.append(f"boundary={boundary_kind}")
    for key in ("layoutBoxes", "paintCommands"):
        value = boundary.get(key)
        if type(value) in {int, float}:
            parts.append(f"{key}={value:g}")
    output_hash = boundary.get("outputHash")
    if isinstance(output_hash, str) and output_hash:
        parts.append(f"outputHash={output_hash}")
    return parts


def _format_backend_coverage_runtime(runtime: Mapping[str, Any]) -> list[str]:
    parts: list[str] = []
    backend = runtime.get("rendererBackend")
    if isinstance(backend, str) and backend:
        parts.append(f"runtime={backend}")
    phases = runtime.get("phases")
    if isinstance(phases, list):
        phase_names = [phase for phase in phases if isinstance(phase, str) and phase]
        if phase_names:
            parts.append(f"phases={'+'.join(phase_names)}")
        for phase in phase_names:
            observation_hash = runtime.get(f"{phase}ObservationHash")
            if isinstance(observation_hash, str) and observation_hash:
                parts.append(f"{phase}Hash={observation_hash}")
    return parts


def _yes_no(value: Any) -> str:
    return "yes" if value is True else "no"


def _support_counts(values: Mapping[str, str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for support in values.values():
        counts[support] = counts.get(support, 0) + 1
    return dict(sorted(counts.items()))


def _format_support_counts(counts: Mapping[str, int]) -> str:
    if not counts:
        return "none"
    return ", ".join(f"{name}={count}" for name, count in sorted(counts.items()))
