from __future__ import annotations

from typing import Any

from otoe._native_shared import native_input_support, native_widget_support

from .backend_candidate_capability_audit_utils import (
    increment_bucket,
    property_counts,
    support_buckets,
)
from .backend_candidate_renderer_types import HeadlessCandidateAcceptanceReport


INPUT_EVENT_CAPABILITIES = {
    "onBlur": "focus",
    "onChange": "input_text",
    "onClick": "click",
    "onFocus": "focus",
    "onGlobalKeyDown": "shortcut",
    "onKeyDown": "key_down",
    "onScroll": "wheel",
}


def renderer_capability_audit_to_dict(
    report: HeadlessCandidateAcceptanceReport,
) -> dict[str, Any]:
    frames = (report.minimal.after, report.task_board.after)
    widget_counts: dict[str, dict[str, int]] = {}
    input_counts: dict[str, dict[str, int]] = {}
    unsupported_widgets: dict[str, int] = {}
    unsupported_inputs: dict[str, int] = {}

    for frame in frames:
        for box in frame.layout_snapshot:
            widget_support = native_widget_support(box.name)
            increment_bucket(widget_counts, widget_support, box.name)
            if widget_support == "fallback-container":
                unsupported_widgets[box.name] = (
                    unsupported_widgets.get(box.name, 0) + 1
                )
            for event_name in box.events:
                capability = INPUT_EVENT_CAPABILITIES.get(event_name, event_name)
                input_support = native_input_support(capability) or "unsupported"
                increment_bucket(input_counts, input_support, capability)
                if input_support == "unsupported":
                    unsupported_inputs[capability] = (
                        unsupported_inputs.get(capability, 0) + 1
                    )
    required_input_counts = {
        support: dict(capability_counts)
        for support, capability_counts in input_counts.items()
    }
    for capability in _run_input_capabilities(report):
        input_support = native_input_support(capability) or "unsupported"
        increment_bucket(required_input_counts, input_support, capability)
        if input_support == "unsupported":
            unsupported_inputs[capability] = (
                unsupported_inputs.get(capability, 0) + 1
            )

    widget_instances = sum(
        count
        for support_counts in widget_counts.values()
        for count in support_counts.values()
    )
    input_bindings = sum(
        count
        for support_counts in input_counts.values()
        for count in support_counts.values()
    )
    return {
        "summary": {
            "widgetInstances": widget_instances,
            "widgetTypes": len(_combined_names(widget_counts)),
            "inputBindings": input_bindings,
            "inputCapabilities": len(_combined_names(required_input_counts)),
            "unsupportedWidgets": sum(unsupported_widgets.values()),
            "unsupportedInputs": sum(unsupported_inputs.values()),
        },
        "widgets": support_buckets(
            widget_counts,
            key_name="support",
            items_name="widgets",
            item_key="name",
        ),
        "inputs": support_buckets(
            input_counts,
            key_name="support",
            items_name="capabilities",
            item_key="capability",
        ),
        "unsupportedWidgets": property_counts(
            unsupported_widgets,
            item_key="name",
        ),
        "unsupportedInputs": property_counts(
            unsupported_inputs,
            item_key="capability",
        ),
        "requiredForReplay": {
            "widgets": _renderer_replay_requirements(
                widget_counts,
                kind="widget",
                items_name="widgets",
                item_key="name",
            ),
            "inputs": _renderer_replay_requirements(
                required_input_counts,
                kind="input",
                items_name="capabilities",
                item_key="capability",
            ),
        },
    }


def _run_input_capabilities(
    report: HeadlessCandidateAcceptanceReport,
) -> tuple[str, ...]:
    capabilities: set[str] = set()
    for run in (report.minimal, report.task_board):
        value = run.input_capabilities
        if isinstance(value, tuple):
            capabilities.update(item for item in value if isinstance(item, str))
    return tuple(sorted(capabilities))


def _combined_names(
    buckets: dict[str, dict[str, int]],
) -> set[str]:
    names: set[str] = set()
    for properties in buckets.values():
        names.update(properties)
    return names


def _renderer_replay_requirements(
    buckets: dict[str, dict[str, int]],
    *,
    kind: str,
    items_name: str,
    item_key: str,
) -> list[dict[str, Any]]:
    return [
        {
            "kind": kind,
            "support": support,
            items_name: property_counts(properties, item_key=item_key),
        }
        for support, properties in sorted(buckets.items())
        if support != "unsupported"
    ]
