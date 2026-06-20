from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from ._style_schema import (
    native_ignored_style_properties,
    native_layout_style_properties,
    native_paint_style_properties,
    native_style_support,
)
from ._widget_contracts import known_widget_names


class CapabilityProfileError(ValueError):
    pass


@dataclass(frozen=True)
class BackendCapabilityProfile:
    name: str
    label: str
    style_support: Mapping[str, str]
    widget_support: Mapping[str, str]
    input_support: Mapping[str, str]
    renderer_boundary_support: Mapping[str, str]

    def style(self, name: str) -> str | None:
        return self.style_support.get(name)

    def widget(self, name: str) -> str:
        return self.widget_support.get(name, "fallback-container")

    def input(self, name: str) -> str | None:
        return self.input_support.get(name)

    def renderer_boundary(self, name: str) -> str | None:
        return self.renderer_boundary_support.get(name)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "label": self.label,
            "styles": dict(sorted(self.style_support.items())),
            "widgets": dict(sorted(self.widget_support.items())),
            "inputs": dict(sorted(self.input_support.items())),
            "rendererBoundaries": dict(
                sorted(self.renderer_boundary_support.items())
            ),
        }

    def coverage_declaration(self) -> dict[str, Any]:
        return {
            "schemaVersion": 1,
            "format": "backend-coverage-declaration",
            "backend": self.name,
            "source": {
                "kind": "backendCapabilityProfile",
                "name": self.name,
            },
            "covers": {
                "widgets": sorted(self.widget_support),
                "inputs": sorted(
                    name
                    for name, support in self.input_support.items()
                    if support == "supported"
                ),
                "styles": sorted(
                    name
                    for name, support in self.style_support.items()
                    if support != "ignored"
                ),
                "declaredStyleOmissions": sorted(
                    name
                    for name, support in self.style_support.items()
                    if support == "ignored"
                ),
                "rendererBoundaries": sorted(
                    name
                    for name, support in self.renderer_boundary_support.items()
                    if support == "supported"
                ),
            },
        }


STYLE_SUPPORT_VALUES = frozenset({"layout", "paint", "layout+paint", "ignored"})
WIDGET_SUPPORT_VALUES = frozenset({"container", "control", "text"})
INPUT_SUPPORT_VALUES = frozenset({"supported", "deferred"})
RENDERER_BOUNDARY_SUPPORT_VALUES = frozenset({"supported", "deferred"})

NATIVE_LAYOUT_STYLE_PROPERTIES = native_layout_style_properties()
NATIVE_PAINT_STYLE_PROPERTIES = native_paint_style_properties()
NATIVE_IGNORED_STYLE_PROPERTIES = native_ignored_style_properties()
NATIVE_STYLE_SUPPORT = native_style_support()

_CORE_WIDGET_NAMES = frozenset(known_widget_names())
NATIVE_TEXT_WIDGETS = _CORE_WIDGET_NAMES & {"Text"}
NATIVE_CONTROL_WIDGETS = _CORE_WIDGET_NAMES & {"Button", "Input"}
# Show and For are control nodes, not registry widgets, but native layout treats
# them as transparent containers after mount resolves their current branch.
NATIVE_CONTAINER_WIDGETS = (
    _CORE_WIDGET_NAMES - NATIVE_TEXT_WIDGETS - NATIVE_CONTROL_WIDGETS
) | frozenset({"For", "Show"})
NATIVE_WIDGET_SUPPORT = {
    **{name: "text" for name in NATIVE_TEXT_WIDGETS},
    **{name: "control" for name in NATIVE_CONTROL_WIDGETS},
    **{name: "container" for name in NATIVE_CONTAINER_WIDGETS},
}
NATIVE_INPUT_SUPPORT = {
    "click": "supported",
    "focus": "supported",
    "input_text": "supported",
    "key_down": "supported",
    "key_input": "supported",
    "shortcut": "supported",
    "tab_focus": "supported",
    "wheel": "supported",
    "caret_movement": "deferred",
    "drag": "deferred",
    "gesture": "deferred",
    "ime": "deferred",
    "inertial_scroll": "deferred",
    "pointer_move": "deferred",
    "text_selection": "deferred",
    "uncontrolled_input": "deferred",
}
NATIVE_RENDERER_BOUNDARY_SUPPORT = {
    "paint": "supported",
    "renderTreeLayout": "supported",
}


NATIVE_PYTHON_CAPABILITY_PROFILE = BackendCapabilityProfile(
    name="native-python",
    label="Python native renderer",
    style_support=NATIVE_STYLE_SUPPORT,
    widget_support=NATIVE_WIDGET_SUPPORT,
    input_support=NATIVE_INPUT_SUPPORT,
    renderer_boundary_support=NATIVE_RENDERER_BOUNDARY_SUPPORT,
)

BACKEND_CAPABILITY_PROFILES = {
    NATIVE_PYTHON_CAPABILITY_PROFILE.name: NATIVE_PYTHON_CAPABILITY_PROFILE,
}
BACKEND_CAPABILITY_ALIASES = {
    "native": "native-python",
    "python-native": "native-python",
}


def backend_capability_profile(
    name: str | None = None,
) -> BackendCapabilityProfile:
    profile_name = name or "native-python"
    canonical = BACKEND_CAPABILITY_ALIASES.get(profile_name, profile_name)
    try:
        return BACKEND_CAPABILITY_PROFILES[canonical]
    except KeyError as exc:
        supported = ", ".join(supported_backend_capability_names())
        raise CapabilityProfileError(
            f"unsupported backend capability profile {profile_name!r}; "
            f"supported: {supported}"
        ) from exc


def load_backend_capability_profile(path: str | Path) -> BackendCapabilityProfile:
    profile_path = Path(path)
    try:
        payload = json.loads(profile_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise CapabilityProfileError(
            f"backend capability profile {str(profile_path)!r} is not valid JSON: {exc}"
        ) from exc
    if not isinstance(payload, dict):
        raise CapabilityProfileError(
            f"backend capability profile {str(profile_path)!r} must be a JSON object"
        )
    return backend_capability_profile_from_dict(
        payload,
        source=str(profile_path),
    )


def backend_capability_profile_from_dict(
    payload: Mapping[str, Any],
    *,
    source: str = "backend capability profile",
) -> BackendCapabilityProfile:
    if payload.get("schemaVersion") != 1:
        raise CapabilityProfileError(f"{source}: schemaVersion must be 1")
    if payload.get("format") != "backend-capability-profile":
        raise CapabilityProfileError(
            f"{source}: format must be 'backend-capability-profile'"
        )
    name = _required_profile_string(payload, "name", source=source)
    label = _required_profile_string(payload, "label", source=source)
    return BackendCapabilityProfile(
        name=name,
        label=label,
        style_support=_profile_support_map(
            payload,
            key="styles",
            values=STYLE_SUPPORT_VALUES,
            source=source,
        ),
        widget_support=_profile_support_map(
            payload,
            key="widgets",
            values=WIDGET_SUPPORT_VALUES,
            source=source,
        ),
        input_support=_profile_support_map(
            payload,
            key="inputs",
            values=INPUT_SUPPORT_VALUES,
            source=source,
        ),
        renderer_boundary_support=_profile_support_map(
            payload,
            key="rendererBoundaries",
            values=RENDERER_BOUNDARY_SUPPORT_VALUES,
            source=source,
            required=False,
        ),
    )


def supported_backend_capability_names() -> tuple[str, ...]:
    names = set(BACKEND_CAPABILITY_PROFILES) | set(BACKEND_CAPABILITY_ALIASES)
    return tuple(sorted(names))


def _required_profile_string(
    payload: Mapping[str, Any],
    key: str,
    *,
    source: str,
) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise CapabilityProfileError(f"{source}: {key} must be a non-empty string")
    return value


def _profile_support_map(
    payload: Mapping[str, Any],
    *,
    key: str,
    values: frozenset[str],
    source: str,
    required: bool = True,
) -> dict[str, str]:
    if key not in payload and not required:
        return {}
    section = payload.get(key)
    if not isinstance(section, dict):
        raise CapabilityProfileError(f"{source}: {key} must be an object")
    support: dict[str, str] = {}
    for name, value in section.items():
        if not isinstance(name, str) or not name:
            raise CapabilityProfileError(
                f"{source}: {key} keys must be non-empty strings"
            )
        if not isinstance(value, str) or value not in values:
            expected = ", ".join(sorted(values))
            raise CapabilityProfileError(
                f"{source}: {key}.{name} must be one of: {expected}"
            )
        support[name] = value
    return support
