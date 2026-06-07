from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .cli_common import CliError, load_json_artifact
from .style_ops import StyleIRError, apply_style_ops, load_style_ir, validate_style_ops


def run_style_ir(args: argparse.Namespace) -> int:
    artifact_path = Path(args.artifact)
    try:
        payload = load_json_artifact(artifact_path, label="style artifact")
        artifact = load_style_ir(payload)
        applied = apply_style_ops(artifact)
        validation = validate_style_ops(artifact) if args.strict else None
    except (CliError, StyleIRError) as exc:
        print(f"style-ir: {exc}", file=sys.stderr)
        return 1

    report = style_ir_report(
        artifact_path,
        artifact,
        applied,
        strict=args.strict,
        validation=validation,
    )
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(format_style_ir_report(report))
    return 0 if report["passed"] else 1


def style_ir_report(
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
            "nodeId": replay.node_id,
            "widget": replay.widget,
            "appliedDeclarations": replay.applied_declarations,
            "omittedOps": list(replay.omitted_ops),
            "errors": list(replay.errors),
        }
        for replay in applied.direct_styles
    ]
    style_ops_errors = [
        *applied.errors,
        *(error for replay in applied.classes for error in replay.errors),
        *(error for replay in applied.direct_styles for error in replay.errors),
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


def format_style_ir_report(report: dict[str, Any]) -> str:
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
