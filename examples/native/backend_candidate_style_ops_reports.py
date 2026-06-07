from __future__ import annotations

from typing import Any

from otoe.style_ops import (
    StyleOpsClassReplay,
    StyleOpsDirectReplay,
    expected_omitted_style_ops,
)

from .backend_candidate_style_ops_capability_audits import (
    style_ops_capability_audit_to_dict,
)
from .backend_candidate_style_ops_types import (
    StyleOpsCandidateAcceptanceReport,
    StyleOpsCandidateClassReport,
    StyleOpsCandidateDirectStyleReport,
)


def replay_style_ops_class(
    replay: StyleOpsClassReplay,
    rules_by_class: dict[str, dict[str, Any]],
    style_support: dict[str, str],
) -> StyleOpsCandidateClassReport:
    errors = list(replay.errors)

    rule_payload = rules_by_class.get(replay.class_name)
    expected_missing = (
        bool(rule_payload.get("missing")) if isinstance(rule_payload, dict) else True
    )
    expected_declarations = (
        rule_payload.get("declarations", {})
        if isinstance(rule_payload, dict)
        else {}
    )
    if not isinstance(expected_declarations, dict):
        expected_declarations = {}
        errors.append(
            f"compiled rule {replay.class_name!r} declarations must be an object"
        )
    expected_omitted_ops = expected_omitted_style_ops(rule_payload, style_support)

    if replay.missing is not expected_missing:
        errors.append(
            f"styleOps class {replay.class_name!r} missing flag does not match compiled rule"
        )
    if replay.applied_declarations != expected_declarations:
        errors.append(
            f"styleOps class {replay.class_name!r} applied declarations do not match compiled rules"
        )
    if replay.omitted_ops != expected_omitted_ops:
        errors.append(
            f"styleOps class {replay.class_name!r} omitted ops do not match compiled rules"
        )

    return StyleOpsCandidateClassReport(
        class_name=replay.class_name,
        selector=replay.selector,
        missing=replay.missing,
        expected_missing=expected_missing,
        applied_declarations=replay.applied_declarations,
        expected_declarations=expected_declarations,
        omitted_ops=replay.omitted_ops,
        expected_omitted_ops=expected_omitted_ops,
        errors=tuple(errors),
    )


def replay_style_ops_direct_style(
    replay: StyleOpsDirectReplay,
    direct_styles_by_path: dict[tuple[int, ...], dict[str, Any]],
    style_support: dict[str, str],
    direct_styles_by_node_id: dict[str, dict[str, Any]] | None = None,
) -> StyleOpsCandidateDirectStyleReport:
    errors = list(replay.errors)

    expected_payload = (
        direct_styles_by_node_id.get(replay.node_id)
        if direct_styles_by_node_id is not None and replay.node_id is not None
        else direct_styles_by_path.get(replay.path)
    )
    expected_node_id = (
        expected_payload.get("nodeId")
        if isinstance(expected_payload, dict)
        and isinstance(expected_payload.get("nodeId"), str)
        else None
    )
    expected_widget = (
        expected_payload.get("widget")
        if isinstance(expected_payload, dict)
        and isinstance(expected_payload.get("widget"), str)
        else None
    )
    expected_declarations = (
        expected_payload.get("declarations", {})
        if isinstance(expected_payload, dict)
        else {}
    )
    if not isinstance(expected_declarations, dict):
        expected_declarations = {}
        errors.append(
            f"compiled directStyles {list(replay.path)!r} declarations must be an object"
        )
    expected_omitted_ops = expected_omitted_style_ops(expected_payload, style_support)

    if replay.widget != expected_widget:
        errors.append(
            f"styleOps directStyles {list(replay.path)!r} widget does not match compiled artifact"
        )
    if replay.node_id != expected_node_id:
        errors.append(
            f"styleOps directStyles {list(replay.path)!r} nodeId does not match compiled artifact"
        )
    if replay.applied_declarations != expected_declarations:
        errors.append(
            f"styleOps directStyles {list(replay.path)!r} applied declarations do not match compiled artifact"
        )
    if replay.omitted_ops != expected_omitted_ops:
        errors.append(
            f"styleOps directStyles {list(replay.path)!r} omitted ops do not match compiled artifact"
        )

    return StyleOpsCandidateDirectStyleReport(
        path=replay.path,
        node_id=replay.node_id,
        widget=replay.widget,
        expected_widget=expected_widget,
        expected_node_id=expected_node_id,
        applied_declarations=replay.applied_declarations,
        expected_declarations=expected_declarations,
        omitted_ops=replay.omitted_ops,
        expected_omitted_ops=expected_omitted_ops,
        errors=tuple(errors),
    )


def style_ops_candidate_report_to_dict(
    report: StyleOpsCandidateAcceptanceReport,
) -> dict[str, Any]:
    return {
        "schemaVersion": 1,
        "format": "style-ops-contract",
        "passed": report.passed,
        "backend": report.backend,
        "styleOps": {
            "schemaVersion": report.style_ops_schema_version,
            "format": report.style_ops_format,
        },
        "capabilityAudit": style_ops_capability_audit_to_dict(report),
        "classes": [
            _style_ops_class_report_to_dict(class_report)
            for class_report in report.classes
        ],
        "directStyles": [
            _style_ops_direct_style_report_to_dict(direct_style_report)
            for direct_style_report in report.direct_styles
        ],
        "errors": list(report.errors),
    }


def style_ops_report_errors(
    report: StyleOpsCandidateAcceptanceReport,
) -> list[str]:
    return [
        *report.errors,
        *(
            f"class {class_report.class_name!r}: {error}"
            for class_report in report.classes
            for error in class_report.errors
        ),
        *(
            f"directStyles {list(direct_style_report.path)!r}: {error}"
            for direct_style_report in report.direct_styles
            for error in direct_style_report.errors
        ),
    ]


def _style_ops_class_report_to_dict(
    report: StyleOpsCandidateClassReport,
) -> dict[str, Any]:
    return {
        "className": report.class_name,
        "selector": report.selector,
        "missing": report.missing,
        "expectedMissing": report.expected_missing,
        "passed": report.passed,
        "appliedDeclarations": report.applied_declarations,
        "expectedDeclarations": report.expected_declarations,
        "omittedOps": list(report.omitted_ops),
        "expectedOmittedOps": list(report.expected_omitted_ops),
        "errors": list(report.errors),
    }


def _style_ops_direct_style_report_to_dict(
    report: StyleOpsCandidateDirectStyleReport,
) -> dict[str, Any]:
    return {
        "path": list(report.path),
        "nodeId": report.node_id,
        "widget": report.widget,
        "expectedNodeId": report.expected_node_id,
        "expectedWidget": report.expected_widget,
        "passed": report.passed,
        "appliedDeclarations": report.applied_declarations,
        "expectedDeclarations": report.expected_declarations,
        "omittedOps": list(report.omitted_ops),
        "expectedOmittedOps": list(report.expected_omitted_ops),
        "errors": list(report.errors),
    }
