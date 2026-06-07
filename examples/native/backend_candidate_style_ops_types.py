from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class StyleOpsCandidateClassReport:
    class_name: str
    selector: str
    missing: bool
    expected_missing: bool
    applied_declarations: dict[str, Any]
    expected_declarations: dict[str, Any]
    omitted_ops: tuple[dict[str, Any], ...]
    expected_omitted_ops: tuple[dict[str, Any], ...]
    errors: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return (
            not self.errors
            and self.missing is self.expected_missing
            and self.applied_declarations == self.expected_declarations
            and self.omitted_ops == self.expected_omitted_ops
        )


@dataclass(frozen=True)
class StyleOpsCandidateDirectStyleReport:
    path: tuple[int, ...]
    node_id: str | None
    widget: str
    expected_widget: str | None
    expected_node_id: str | None
    applied_declarations: dict[str, Any]
    expected_declarations: dict[str, Any]
    omitted_ops: tuple[dict[str, Any], ...]
    expected_omitted_ops: tuple[dict[str, Any], ...]
    errors: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return (
            not self.errors
            and self.expected_widget == self.widget
            and self.expected_node_id == self.node_id
            and self.applied_declarations == self.expected_declarations
            and self.omitted_ops == self.expected_omitted_ops
        )


@dataclass(frozen=True)
class StyleOpsCandidateAcceptanceReport:
    backend: Any
    style_ops_schema_version: Any
    style_ops_format: Any
    style_support: dict[str, str]
    classes: tuple[StyleOpsCandidateClassReport, ...]
    errors: tuple[str, ...]
    direct_styles: tuple[StyleOpsCandidateDirectStyleReport, ...] = ()

    @property
    def passed(self) -> bool:
        return (
            not self.errors
            and self.style_ops_schema_version == 1
            and self.style_ops_format == "otoe-style-ops"
            and bool(self.classes)
            and all(class_report.passed for class_report in self.classes)
            and all(
                direct_style_report.passed
                for direct_style_report in self.direct_styles
            )
        )
