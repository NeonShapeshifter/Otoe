from __future__ import annotations

from typing import Any

from otoe import MountedNode
from otoe.plan import plan_mounted
from otoe.style import (
    ResolvedStyleMap,
    resolved_style_map_from_style_ops_artifact,
)
from otoe.style_ir import compiled_styles_to_dict

from .backend_candidate_renderer_utils import _target_name


def candidate_resolved_style_map(
    target: Any,
    *,
    stylesheet: Any,
    strict_styles: bool,
) -> ResolvedStyleMap | None:
    if stylesheet is None or not isinstance(target, MountedNode):
        return None
    plan = plan_mounted(
        target,
        stylesheet=stylesheet,
        strict_styles=strict_styles,
    )
    artifact = compiled_styles_to_dict(
        plan,
        target=f"candidate:{_target_name(target)}",
        stylesheet=stylesheet,
    )
    return resolved_style_map_from_style_ops_artifact(artifact)


def _layout_candidate_style(
    widget: Any,
    *,
    stylesheet: Any,
    strict_styles: bool,
) -> dict[str, Any]:
    style = {}
    class_name = widget.props.get("className")
    if stylesheet is not None:
        style.update(
            stylesheet.resolve(
                class_name if isinstance(class_name, str) else None,
                strict=strict_styles,
            )
        )
    for prop in ("gap", "padding", "scrollY"):
        if prop in widget.props:
            style[prop] = widget.props[prop]
    if "color" in widget.props:
        style["color"] = widget.props["color"]
    tokens = getattr(stylesheet, "tokens", {}) if stylesheet is not None else {}
    return {
        name: _layout_candidate_resolve_token(value, tokens)
        for name, value in style.items()
    }


def _layout_candidate_resolve_token(value: Any, tokens: dict[str, Any]) -> Any:
    name = getattr(value, "name", None)
    if name is not None and name in tokens:
        return _layout_candidate_resolve_token(tokens[name], tokens)
    return value
