from __future__ import annotations

from dataclasses import asdict
from typing import Any

from .backend_candidate_renderer_types import (
    HeadlessCandidateAcceptanceReport,
    HeadlessCandidateRunReport,
)


def acceptance_report_to_dict(
    report: HeadlessCandidateAcceptanceReport,
) -> dict[str, Any]:
    payload = asdict(report)
    payload["passed"] = report.passed
    payload["minimal"]["passed"] = report.minimal.passed
    payload["task_board"]["passed"] = report.task_board.passed
    payload["minimal"]["replay"]["passed"] = bool(
        getattr(report.minimal.replay, "passed", False)
    )
    payload["task_board"]["replay"]["passed"] = bool(
        getattr(report.task_board.replay, "passed", False)
    )
    return payload


def format_acceptance_report(report: HeadlessCandidateAcceptanceReport) -> str:
    lines = [
        "backend candidate acceptance",
        f"status: {'passed' if report.passed else 'failed'}",
        _format_run_report("minimal", report.minimal),
        _format_run_report("task_board", report.task_board),
    ]
    return "\n".join(lines)


def _format_run_report(label: str, report: HeadlessCandidateRunReport) -> str:
    return "\n".join(
        [
            f"{label}: {'passed' if report.passed else 'failed'}",
            f"  backend: {report.backend}",
            f"  renderer backend: {report.renderer_backend}",
            f"  title: {report.title}",
            f"  frame: {report.before.frame} -> {report.after.frame}",
            f"  size: {report.after.size[0]}x{report.after.size[1]}",
            f"  root: {report.after.root_name}",
            f"  focused: {_format_focus(report.after.focused)}",
            f"  layout boxes: {report.after.layout_boxes}",
            f"  paint commands: {report.after.paint_commands}",
            f"  visible text: {', '.join(report.after.visible_text)}",
        ]
    )


def _format_focus(focus: tuple[str, str | None] | None) -> str:
    if focus is None:
        return "none"
    name, text = focus
    return name if text is None else f"{name} {text!r}"
