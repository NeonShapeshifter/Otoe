from __future__ import annotations

from typing import Any

from .backend_candidate_capability_audit_utils import (
    increment_bucket,
    property_counts,
    support_buckets,
)
from .backend_candidate_style_ops_types import StyleOpsCandidateAcceptanceReport


def style_ops_capability_audit_to_dict(
    report: StyleOpsCandidateAcceptanceReport,
) -> dict[str, Any]:
    applied: dict[str, dict[str, int]] = {}
    omitted_by_status: dict[str, dict[str, int]] = {}
    omitted_by_support: dict[str, dict[str, int]] = {}
    unsupported: dict[str, int] = {}

    for class_report in report.classes:
        _collect_applied_style_support(
            class_report.applied_declarations,
            report.style_support,
            applied,
            unsupported,
        )
        _collect_omitted_style_support(
            class_report.omitted_ops,
            omitted_by_status,
            omitted_by_support,
            unsupported,
        )
    for direct_style_report in report.direct_styles:
        _collect_applied_style_support(
            direct_style_report.applied_declarations,
            report.style_support,
            applied,
            unsupported,
        )
        _collect_omitted_style_support(
            direct_style_report.omitted_ops,
            omitted_by_status,
            omitted_by_support,
            unsupported,
        )

    applied_total = sum(
        count
        for support_counts in applied.values()
        for count in support_counts.values()
    )
    omitted_total = sum(
        count
        for status_counts in omitted_by_status.values()
        for count in status_counts.values()
    )
    return {
        "backend": report.backend,
        "summary": {
            "applied": applied_total,
            "omitted": omitted_total,
            "unsupported": sum(unsupported.values()),
        },
        "applied": support_buckets(applied, key_name="support"),
        "omittedByStatus": support_buckets(
            omitted_by_status,
            key_name="status",
        ),
        "omittedBySupport": support_buckets(
            omitted_by_support,
            key_name="support",
        ),
        "unsupportedProperties": property_counts(unsupported),
        "requiredForReplay": _style_replay_requirements(applied),
        "declaredOmissions": _style_omission_requirements(omitted_by_status),
    }


def _collect_applied_style_support(
    declarations: dict[str, Any],
    style_support: dict[str, str],
    applied: dict[str, dict[str, int]],
    unsupported: dict[str, int],
) -> None:
    for property_name in declarations:
        support = style_support.get(property_name, "unsupported")
        increment_bucket(applied, support, property_name)
        if support == "unsupported":
            unsupported[property_name] = unsupported.get(property_name, 0) + 1


def _collect_omitted_style_support(
    omitted_ops: tuple[dict[str, Any], ...],
    omitted_by_status: dict[str, dict[str, int]],
    omitted_by_support: dict[str, dict[str, int]],
    unsupported: dict[str, int],
) -> None:
    for op in omitted_ops:
        property_name = op.get("property")
        if not isinstance(property_name, str):
            continue
        status = op.get("status") if isinstance(op.get("status"), str) else "unknown"
        support = (
            op.get("support")
            if isinstance(op.get("support"), str)
            else "unsupported"
        )
        increment_bucket(omitted_by_status, status, property_name)
        increment_bucket(omitted_by_support, support, property_name)
        if support == "unsupported" or status == "invalid":
            unsupported[property_name] = unsupported.get(property_name, 0) + 1


def _style_replay_requirements(
    applied: dict[str, dict[str, int]],
) -> list[dict[str, Any]]:
    return [
        {
            "kind": "apply",
            "support": support,
            "properties": property_counts(properties),
        }
        for support, properties in sorted(applied.items())
        if support != "unsupported"
    ]


def _style_omission_requirements(
    omitted_by_status: dict[str, dict[str, int]],
) -> list[dict[str, Any]]:
    return [
        {
            "kind": "omit",
            "status": status,
            "properties": property_counts(properties),
        }
        for status, properties in sorted(omitted_by_status.items())
    ]
