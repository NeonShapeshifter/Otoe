from __future__ import annotations

from dataclasses import dataclass
from typing import Any

STYLE_IR_SCHEMA_VERSION = 1
STYLE_OPS_SCHEMA_VERSION = 1
STYLE_OPS_FORMAT = "otoe-style-ops"


class StyleIRError(ValueError):
    pass


@dataclass(frozen=True)
class StyleOpsClassReplay:
    class_name: str
    selector: str
    missing: bool
    applied_declarations: dict[str, Any]
    omitted_ops: tuple[dict[str, Any], ...]
    errors: tuple[str, ...]


@dataclass(frozen=True)
class StyleOpsDirectReplay:
    path: tuple[int, ...]
    node_id: str | None
    widget: str
    applied_declarations: dict[str, Any]
    omitted_ops: tuple[dict[str, Any], ...]
    errors: tuple[str, ...]


@dataclass(frozen=True)
class StyleIRArtifact:
    payload: dict[str, Any]
    style_ops: dict[str, Any]
    rules: tuple[dict[str, Any], ...]
    direct_styles: tuple[dict[str, Any], ...]
    rules_by_class: dict[str, dict[str, Any]]
    direct_styles_by_path: dict[tuple[int, ...], dict[str, Any]]
    direct_styles_by_node_id: dict[str, dict[str, Any]]
    style_support: dict[str, str]

    @property
    def schema_version(self) -> Any:
        return self.payload.get("schemaVersion")

    @property
    def style_ops_schema_version(self) -> Any:
        return self.style_ops.get("schemaVersion")

    @property
    def style_ops_format(self) -> Any:
        return self.style_ops.get("format")

    @property
    def backend(self) -> Any:
        return self.payload.get("backend")


@dataclass(frozen=True)
class AppliedStyleOps:
    classes: tuple[StyleOpsClassReplay, ...]
    direct_styles: tuple[StyleOpsDirectReplay, ...]
    errors: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return (
            not self.errors
            and all(class_replay.errors == () for class_replay in self.classes)
            and all(
                direct_style_replay.errors == ()
                for direct_style_replay in self.direct_styles
            )
        )

    @property
    def classes_by_name(self) -> dict[str, StyleOpsClassReplay]:
        return {
            class_replay.class_name: class_replay
            for class_replay in self.classes
            if class_replay.class_name != "<invalid>"
        }

    @property
    def direct_styles_by_path(self) -> dict[tuple[int, ...], StyleOpsDirectReplay]:
        return {
            direct_style_replay.path: direct_style_replay
            for direct_style_replay in self.direct_styles
        }

    @property
    def direct_styles_by_node_id(self) -> dict[str, StyleOpsDirectReplay]:
        return {
            direct_style_replay.node_id: direct_style_replay
            for direct_style_replay in self.direct_styles
            if direct_style_replay.node_id is not None
        }


@dataclass(frozen=True)
class StyleOpsValidation:
    applied: AppliedStyleOps
    errors: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return not self.errors
