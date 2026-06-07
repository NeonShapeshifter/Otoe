from __future__ import annotations

from typing import Any

from otoe import mount, unmount
from otoe.plan import plan_mounted
from otoe.style_ir import compiled_styles_to_dict
from otoe.style_ops import StyleIRError, apply_style_ops, load_style_ir

from .backend_candidate_apps import (
    BACKEND_CANDIDATE_STYLES,
    backend_candidate_app,
)
from .backend_candidate_style_ops_reports import (
    replay_style_ops_class,
    replay_style_ops_direct_style,
)
from .backend_candidate_style_ops_types import StyleOpsCandidateAcceptanceReport


def run_style_ops_candidate_acceptance(
    style_artifact: dict[str, Any] | None = None,
) -> StyleOpsCandidateAcceptanceReport:
    artifact = (
        backend_candidate_style_artifact()
        if style_artifact is None
        else style_artifact
    )
    if not isinstance(artifact, dict):
        return StyleOpsCandidateAcceptanceReport(
            backend=None,
            style_ops_schema_version=None,
            style_ops_format=None,
            style_support={},
            classes=(),
            errors=("style artifact must be a JSON object",),
        )

    try:
        style_ir = load_style_ir(artifact)
    except StyleIRError as exc:
        style_ops = artifact.get("styleOps") if isinstance(artifact, dict) else None
        style_ops_schema_version = (
            style_ops.get("schemaVersion") if isinstance(style_ops, dict) else None
        )
        style_ops_format = (
            style_ops.get("format") if isinstance(style_ops, dict) else None
        )
        return StyleOpsCandidateAcceptanceReport(
            backend=artifact.get("backend") if isinstance(artifact, dict) else None,
            style_ops_schema_version=style_ops_schema_version,
            style_ops_format=style_ops_format,
            style_support={},
            classes=(),
            errors=(str(exc),),
        )

    application = apply_style_ops(style_ir)
    errors: list[str] = list(application.errors)
    class_reports = tuple(
        replay_style_ops_class(replay, style_ir.rules_by_class, style_ir.style_support)
        for replay in application.classes
    )
    direct_style_reports = tuple(
        replay_style_ops_direct_style(
            replay,
            style_ir.direct_styles_by_path,
            style_ir.style_support,
            style_ir.direct_styles_by_node_id,
        )
        for replay in application.direct_styles
    )
    classes_with_ops = {
        class_report.class_name
        for class_report in class_reports
        if class_report.class_name != "<invalid>"
    }
    missing_ops = sorted(set(style_ir.rules_by_class) - classes_with_ops)
    if missing_ops:
        errors.append(
            "styleOps missing classes from compiled rules: "
            + ", ".join(missing_ops)
        )
    direct_node_ids_with_ops = {
        report.node_id
        for report in direct_style_reports
        if report.node_id is not None
    }
    missing_direct_ops = sorted(
        set(style_ir.direct_styles_by_node_id) - direct_node_ids_with_ops
    )
    if missing_direct_ops:
        errors.append(
            "styleOps missing directStyles from compiled artifact: "
            + ", ".join(repr(node_id) for node_id in missing_direct_ops)
        )

    return StyleOpsCandidateAcceptanceReport(
        backend=style_ir.backend,
        style_ops_schema_version=style_ir.style_ops_schema_version,
        style_ops_format=style_ir.style_ops_format,
        style_support=dict(style_ir.style_support),
        classes=class_reports,
        errors=tuple(errors),
        direct_styles=direct_style_reports,
    )


def backend_candidate_style_artifact() -> dict[str, Any]:
    mounted = mount(backend_candidate_app())
    try:
        plan = plan_mounted(
            mounted,
            stylesheet=BACKEND_CANDIDATE_STYLES,
        )
        return compiled_styles_to_dict(
            plan,
            target="examples.native.backend_candidate_skeleton:backend_candidate_app",
            stylesheet=BACKEND_CANDIDATE_STYLES,
        )
    finally:
        unmount(mounted)
