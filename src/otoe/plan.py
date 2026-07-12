from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from typing import Any

from .capabilities import (
    BackendCapabilityProfile,
    CapabilityProfileError,
    backend_capability_profile,
)
from ._render_identity import (
    mounted_child_key,
    optional_string,
    render_key_label,
    render_node_id,
)
from ._style_planning import (
    classify_style_value,
    dedupe_names,
    planned_class_names,
)
from .mount import FakeWidget, MountedNode
from .style import StyleSheet


PLAN_STATUSES = ("portable", "html-only", "deferred", "invalid")
SUPPORTED_PLAN_PROFILES = frozenset({"cage"})
DIRECT_STYLE_PROPS = ("gap", "padding", "scrollY", "color")


class PlanError(ValueError):
    pass


@dataclass(frozen=True)
class PlanDiagnostic:
    level: str
    message: str


@dataclass(frozen=True)
class DirectStyleDeclaration:
    property: str
    value: Any


@dataclass(frozen=True)
class DirectStyleOmission:
    property: str
    status: str
    value: Any
    message: str | None


@dataclass(frozen=True)
class DirectStyleEntry:
    path: tuple[int, ...]
    node_id: str
    widget: str
    declarations: tuple[DirectStyleDeclaration, ...]
    omitted_declarations: tuple[DirectStyleOmission, ...]


@dataclass(frozen=True)
class OtoePlan:
    profile: str
    backend: str
    backend_capabilities: BackendCapabilityProfile
    widget_count: int
    widget_support_counts: dict[str, int]
    used_classes: tuple[str, ...]
    static_classes: tuple[str, ...]
    safelisted_classes: tuple[str, ...]
    planned_classes: tuple[str, ...]
    html_only_classes: tuple[str, ...]
    invalid_classes: tuple[str, ...]
    style_counts: dict[str, int]
    direct_style_counts: dict[str, int]
    direct_styles: tuple[DirectStyleEntry, ...]
    diagnostics: tuple[PlanDiagnostic, ...]

    @property
    def has_errors(self) -> bool:
        return any(diagnostic.level == "error" for diagnostic in self.diagnostics)

    @property
    def has_warnings(self) -> bool:
        if any(diagnostic.level == "warning" for diagnostic in self.diagnostics):
            return True
        return self.style_counts["html-only"] > 0 or self.style_counts["deferred"] > 0

    @property
    def status(self) -> str:
        if self.has_errors:
            return "invalid"
        if self.has_warnings:
            return "warnings"
        return "ok"


def plan_mounted(
    target: MountedNode,
    *,
    profile: str = "cage",
    backend: str | BackendCapabilityProfile | None = None,
    stylesheet: StyleSheet | None = None,
    static_classes: tuple[str, ...] = (),
    safelist: tuple[str, ...] = (),
    diagnostics: tuple[PlanDiagnostic, ...] = (),
    strict_styles: bool = True,
) -> OtoePlan:
    if profile not in SUPPORTED_PLAN_PROFILES:
        raise PlanError(f"unsupported plan profile {profile!r}; supported: cage")
    if isinstance(backend, BackendCapabilityProfile):
        capabilities = backend
    else:
        try:
            capabilities = backend_capability_profile(backend)
        except CapabilityProfileError as exc:
            raise PlanError(str(exc)) from exc

    widgets_with_paths = tuple(_walk_widgets_with_paths(target))
    widgets = [entry.widget for entry in widgets_with_paths]
    widget_support_counts = _widget_support_counts(widgets, capabilities)
    used_classes = _used_classes(widgets)
    safelisted_classes = tuple(dedupe_names(safelist))
    static_classes = tuple(
        dedupe_names(
            class_name
            for class_name in static_classes
            if class_name not in used_classes and class_name not in safelisted_classes
        )
    )
    classes_to_plan = planned_class_names(
        used_classes=used_classes,
        static_classes=static_classes,
        safelisted_classes=safelisted_classes,
    )
    planned_classes: list[str] = []
    html_only_classes: list[str] = []
    invalid_classes: list[str] = []
    diagnostic_entries: list[PlanDiagnostic] = list(diagnostics)
    style_counts = _empty_counts()
    direct_style_counts = _empty_counts()
    direct_styles: list[DirectStyleEntry] = []

    for class_name in classes_to_plan:
        rule = stylesheet.rules.get(f".{class_name}") if stylesheet is not None else None
        if rule is None:
            missing_message = (
                f"class {class_name!r} has no portable rule for profile {profile!r}"
            )
            if strict_styles:
                invalid_classes.append(class_name)
                style_counts["invalid"] += 1
                diagnostic_entries.append(PlanDiagnostic("error", missing_message))
            else:
                html_only_classes.append(class_name)
                diagnostic_entries.append(
                    PlanDiagnostic("warning", f"{missing_message}; treating it as html-only")
                )
            continue

        planned_classes.append(class_name)
        if not rule.declarations:
            html_only_classes.append(class_name)
            diagnostic_entries.append(
                PlanDiagnostic(
                    "warning",
                    f"class {class_name!r} has no portable declarations for profile {profile!r}",
                )
            )
            continue

        for prop, value in rule.declarations.items():
            status, message = classify_style_value(prop, value, stylesheet, capabilities)
            style_counts[status] += 1
            if message is not None:
                diagnostic_entries.append(
                    PlanDiagnostic(
                        "error" if status == "invalid" else "warning",
                        f"class {class_name!r}: {message}",
                    )
                )

    for entry in widgets_with_paths:
        path = entry.path
        node_id = entry.node_id
        widget = entry.widget
        direct_declarations: list[DirectStyleDeclaration] = []
        omitted_direct_declarations: list[DirectStyleOmission] = []
        for prop in DIRECT_STYLE_PROPS:
            if prop not in widget.props:
                continue
            status, message = classify_style_value(
                prop,
                widget.props[prop],
                stylesheet,
                capabilities,
            )
            direct_style_counts[status] += 1
            if status == "portable":
                direct_declarations.append(
                    DirectStyleDeclaration(prop, widget.props[prop])
                )
            else:
                omitted_direct_declarations.append(
                    DirectStyleOmission(
                        property=prop,
                        status=status,
                        value=widget.props[prop],
                        message=message,
                    )
                )
            if message is not None:
                diagnostic_entries.append(
                    PlanDiagnostic(
                        "error" if status == "invalid" else "warning",
                        f"{widget.name} direct style {prop!r}: {message}",
                    )
                )
        if direct_declarations or omitted_direct_declarations:
            direct_styles.append(
                DirectStyleEntry(
                    path=path,
                    node_id=node_id,
                    widget=widget.name,
                    declarations=tuple(direct_declarations),
                    omitted_declarations=tuple(omitted_direct_declarations),
                )
            )

    return OtoePlan(
        profile=profile,
        backend=capabilities.name,
        backend_capabilities=capabilities,
        widget_count=len(widgets),
        widget_support_counts=widget_support_counts,
        used_classes=used_classes,
        static_classes=static_classes,
        safelisted_classes=safelisted_classes,
        planned_classes=tuple(planned_classes),
        html_only_classes=tuple(dedupe_names(html_only_classes)),
        invalid_classes=tuple(dedupe_names(invalid_classes)),
        style_counts=style_counts,
        direct_style_counts=direct_style_counts,
        direct_styles=tuple(direct_styles),
        diagnostics=tuple(diagnostic_entries),
    )


def format_plan(plan: OtoePlan, *, target: str) -> str:
    from .plan_artifacts import format_plan as _format_plan

    return _format_plan(plan, target=target)


def plan_to_dict(plan: OtoePlan, *, target: str) -> dict[str, Any]:
    from .plan_artifacts import plan_to_dict as _plan_to_dict

    return _plan_to_dict(plan, target=target)


def compiled_styles_to_dict(
    plan: OtoePlan,
    *,
    target: str,
    stylesheet: StyleSheet | None,
) -> dict[str, Any]:
    from .plan_artifacts import compiled_styles_to_dict as _compiled_styles_to_dict

    return _compiled_styles_to_dict(plan, target=target, stylesheet=stylesheet)


def _widget_support_counts(
    widgets: Iterable[FakeWidget],
    capabilities: BackendCapabilityProfile,
) -> dict[str, int]:
    counts: dict[str, int] = {}
    for widget in widgets:
        support = capabilities.widget(widget.name)
        counts[support] = counts.get(support, 0) + 1
    return dict(sorted(counts.items()))


@dataclass(frozen=True)
class _PlannedWidget:
    path: tuple[int, ...]
    node_id: str
    widget: FakeWidget


def _walk_widgets_with_paths(
    mounted: MountedNode,
    *,
    path: tuple[int, ...] = (),
    parent_id: str | None = None,
    key: Any = None,
) -> Iterator[_PlannedWidget]:
    if mounted.widget is None:
        if len(mounted.children) != 1:
            return
        yield from _walk_widgets_with_paths(
            mounted.children[0],
            path=path,
            parent_id=parent_id,
            key=key,
        )
        return

    widget = mounted.widget
    node_id = render_node_id(
        parent_id=parent_id,
        name=widget.name,
        path=path,
        widget_id=optional_string(widget.props.get("id")),
        key_label=render_key_label(key),
    )
    yield _PlannedWidget(path=path, node_id=node_id, widget=widget)
    for index, child in enumerate(mounted.children):
        yield from _walk_widgets_with_paths(
            child,
            path=(*path, index),
            parent_id=node_id,
            key=mounted_child_key(mounted, child),
        )


def _used_classes(widgets: Iterable[FakeWidget]) -> tuple[str, ...]:
    class_names: list[str] = []
    for widget in widgets:
        raw = widget.props.get("className")
        if raw is None:
            continue
        class_names.extend(name for name in str(raw).split() if name)
    return tuple(dedupe_names(class_names))


def _empty_counts() -> dict[str, int]:
    return {status: 0 for status in PLAN_STATUSES}
