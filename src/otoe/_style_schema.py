from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType


@dataclass(frozen=True)
class StylePropertySpec:
    css_name: str | None
    internal_name: str
    value_kind: str
    is_dimension: bool
    token_allowed: bool
    native_layout_support: bool
    native_paint_support: bool
    html_support: bool
    portable_support: bool
    native_ignored: bool = False


STYLE_PROPERTY_SPECS = (
    StylePropertySpec(
        "align-items",
        "alignItems",
        "keyword",
        is_dimension=False,
        token_allowed=False,
        native_layout_support=True,
        native_paint_support=False,
        html_support=True,
        portable_support=True,
    ),
    StylePropertySpec(
        "background",
        "background",
        "color-token",
        is_dimension=False,
        token_allowed=True,
        native_layout_support=False,
        native_paint_support=True,
        html_support=True,
        portable_support=True,
    ),
    StylePropertySpec(
        "border-color",
        "borderColor",
        "color-token",
        is_dimension=False,
        token_allowed=True,
        native_layout_support=False,
        native_paint_support=True,
        html_support=True,
        portable_support=True,
    ),
    StylePropertySpec(
        "border-radius",
        "borderRadius",
        "dimension",
        is_dimension=True,
        token_allowed=False,
        native_layout_support=False,
        native_paint_support=True,
        html_support=True,
        portable_support=True,
    ),
    StylePropertySpec(
        "border-style",
        "borderStyle",
        "keyword",
        is_dimension=False,
        token_allowed=False,
        native_layout_support=False,
        native_paint_support=False,
        html_support=True,
        portable_support=True,
        native_ignored=True,
    ),
    StylePropertySpec(
        "border-width",
        "borderWidth",
        "dimension",
        is_dimension=True,
        token_allowed=False,
        native_layout_support=True,
        native_paint_support=True,
        html_support=True,
        portable_support=True,
    ),
    StylePropertySpec(
        "color",
        "color",
        "color-token",
        is_dimension=False,
        token_allowed=True,
        native_layout_support=False,
        native_paint_support=True,
        html_support=True,
        portable_support=True,
    ),
    StylePropertySpec(
        "display",
        "display",
        "keyword",
        is_dimension=False,
        token_allowed=False,
        native_layout_support=False,
        native_paint_support=False,
        html_support=True,
        portable_support=True,
        native_ignored=True,
    ),
    StylePropertySpec(
        "font-size",
        "fontSize",
        "dimension",
        is_dimension=True,
        token_allowed=False,
        native_layout_support=True,
        native_paint_support=True,
        html_support=True,
        portable_support=True,
    ),
    StylePropertySpec(
        "font-weight",
        "fontWeight",
        "number-keyword",
        is_dimension=False,
        token_allowed=False,
        native_layout_support=False,
        native_paint_support=False,
        html_support=True,
        portable_support=True,
        native_ignored=True,
    ),
    StylePropertySpec(
        "gap",
        "gap",
        "dimension",
        is_dimension=True,
        token_allowed=False,
        native_layout_support=True,
        native_paint_support=False,
        html_support=True,
        portable_support=True,
    ),
    StylePropertySpec(
        "height",
        "height",
        "dimension",
        is_dimension=True,
        token_allowed=False,
        native_layout_support=True,
        native_paint_support=False,
        html_support=True,
        portable_support=True,
    ),
    StylePropertySpec(
        "justify-content",
        "justifyContent",
        "keyword",
        is_dimension=False,
        token_allowed=False,
        native_layout_support=True,
        native_paint_support=False,
        html_support=True,
        portable_support=True,
    ),
    StylePropertySpec(
        "margin",
        "margin",
        "dimension",
        is_dimension=True,
        token_allowed=False,
        native_layout_support=False,
        native_paint_support=False,
        html_support=True,
        portable_support=True,
        native_ignored=True,
    ),
    StylePropertySpec(
        "max-height",
        "maxHeight",
        "dimension",
        is_dimension=True,
        token_allowed=False,
        native_layout_support=True,
        native_paint_support=False,
        html_support=True,
        portable_support=True,
    ),
    StylePropertySpec(
        "max-width",
        "maxWidth",
        "dimension",
        is_dimension=True,
        token_allowed=False,
        native_layout_support=True,
        native_paint_support=False,
        html_support=True,
        portable_support=True,
    ),
    StylePropertySpec(
        "min-height",
        "minHeight",
        "dimension",
        is_dimension=True,
        token_allowed=False,
        native_layout_support=True,
        native_paint_support=False,
        html_support=True,
        portable_support=True,
    ),
    StylePropertySpec(
        "min-width",
        "minWidth",
        "dimension",
        is_dimension=True,
        token_allowed=False,
        native_layout_support=True,
        native_paint_support=False,
        html_support=True,
        portable_support=True,
    ),
    StylePropertySpec(
        "opacity",
        "opacity",
        "number-keyword",
        is_dimension=False,
        token_allowed=False,
        native_layout_support=False,
        native_paint_support=False,
        html_support=True,
        portable_support=True,
        native_ignored=True,
    ),
    StylePropertySpec(
        "overflow",
        "overflow",
        "keyword",
        is_dimension=False,
        token_allowed=False,
        native_layout_support=False,
        native_paint_support=True,
        html_support=True,
        portable_support=True,
    ),
    StylePropertySpec(
        "padding",
        "padding",
        "dimension",
        is_dimension=True,
        token_allowed=False,
        native_layout_support=True,
        native_paint_support=False,
        html_support=True,
        portable_support=True,
    ),
    StylePropertySpec(
        "text-overflow",
        "textOverflow",
        "keyword",
        is_dimension=False,
        token_allowed=False,
        native_layout_support=False,
        native_paint_support=True,
        html_support=True,
        portable_support=True,
    ),
    StylePropertySpec(
        "white-space",
        "whiteSpace",
        "keyword",
        is_dimension=False,
        token_allowed=False,
        native_layout_support=False,
        native_paint_support=True,
        html_support=True,
        portable_support=True,
    ),
    StylePropertySpec(
        "width",
        "width",
        "dimension",
        is_dimension=True,
        token_allowed=False,
        native_layout_support=True,
        native_paint_support=False,
        html_support=True,
        portable_support=True,
    ),
    StylePropertySpec(
        None,
        "scrollY",
        "dimension",
        is_dimension=True,
        token_allowed=False,
        native_layout_support=True,
        native_paint_support=False,
        html_support=False,
        portable_support=True,
    ),
)


STYLE_PROPERTY_SPECS_BY_INTERNAL_NAME = MappingProxyType(
    {spec.internal_name: spec for spec in STYLE_PROPERTY_SPECS}
)
STYLE_PROPERTY_SPECS_BY_CSS_NAME = MappingProxyType(
    {
        spec.css_name: spec
        for spec in STYLE_PROPERTY_SPECS
        if spec.css_name is not None
    }
)


def supported_properties() -> dict[str, str]:
    return {
        spec.css_name: spec.internal_name
        for spec in STYLE_PROPERTY_SPECS
        if spec.css_name is not None and spec.html_support
    }


def html_properties() -> dict[str, str]:
    return {internal: css for css, internal in supported_properties().items()}


def dimension_properties() -> frozenset[str]:
    return frozenset(
        spec.internal_name
        for spec in STYLE_PROPERTY_SPECS
        if spec.css_name is not None and spec.is_dimension
    )


def portable_dimension_properties() -> frozenset[str]:
    return frozenset(
        spec.internal_name
        for spec in STYLE_PROPERTY_SPECS
        if spec.portable_support and spec.is_dimension
    )


def token_properties() -> frozenset[str]:
    return frozenset(
        spec.internal_name
        for spec in STYLE_PROPERTY_SPECS
        if spec.css_name is not None and spec.token_allowed
    )


def native_layout_style_properties() -> frozenset[str]:
    return frozenset(
        spec.internal_name for spec in STYLE_PROPERTY_SPECS if spec.native_layout_support
    )


def native_paint_style_properties() -> frozenset[str]:
    return frozenset(
        spec.internal_name for spec in STYLE_PROPERTY_SPECS if spec.native_paint_support
    )


def native_ignored_style_properties() -> frozenset[str]:
    return frozenset(
        spec.internal_name for spec in STYLE_PROPERTY_SPECS if spec.native_ignored
    )


def native_style_support() -> dict[str, str]:
    support: dict[str, str] = {}
    for spec in STYLE_PROPERTY_SPECS:
        if spec.native_layout_support and spec.native_paint_support:
            support[spec.internal_name] = "layout+paint"
        elif spec.native_layout_support:
            support[spec.internal_name] = "layout"
        elif spec.native_paint_support:
            support[spec.internal_name] = "paint"
        elif spec.native_ignored:
            support[spec.internal_name] = "ignored"
    return support
