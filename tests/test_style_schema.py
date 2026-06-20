from __future__ import annotations

from pathlib import Path
import re

from otoe._style_schema import (
    STYLE_PROPERTY_SPECS,
    STYLE_PROPERTY_SPECS_BY_CSS_NAME,
    STYLE_PROPERTY_SPECS_BY_INTERNAL_NAME,
    native_ignored_style_properties,
    native_layout_style_properties,
    native_paint_style_properties,
    native_style_support,
    portable_dimension_properties,
)
from otoe.capabilities import (
    NATIVE_IGNORED_STYLE_PROPERTIES,
    NATIVE_LAYOUT_STYLE_PROPERTIES,
    NATIVE_PAINT_STYLE_PROPERTIES,
    NATIVE_STYLE_SUPPORT,
)
from otoe.style import (
    DIMENSION_PROPERTIES,
    HTML_PROPERTIES,
    SUPPORTED_PROPERTIES,
    TOKEN_PROPERTIES,
)


ROOT = Path(__file__).resolve().parents[1]
STYLE_GUIDE = ROOT / "STYLE_GUIDE.md"


EXPECTED_SUPPORTED_PROPERTIES = {
    "align-items": "alignItems",
    "background": "background",
    "border-color": "borderColor",
    "border-radius": "borderRadius",
    "border-style": "borderStyle",
    "border-width": "borderWidth",
    "color": "color",
    "display": "display",
    "font-size": "fontSize",
    "font-weight": "fontWeight",
    "gap": "gap",
    "height": "height",
    "justify-content": "justifyContent",
    "margin": "margin",
    "max-height": "maxHeight",
    "max-width": "maxWidth",
    "min-height": "minHeight",
    "min-width": "minWidth",
    "opacity": "opacity",
    "overflow": "overflow",
    "padding": "padding",
    "text-overflow": "textOverflow",
    "white-space": "whiteSpace",
    "width": "width",
}
EXPECTED_DIMENSION_PROPERTIES = frozenset(
    {
        "borderRadius",
        "borderWidth",
        "fontSize",
        "gap",
        "height",
        "margin",
        "maxHeight",
        "maxWidth",
        "minHeight",
        "minWidth",
        "padding",
        "width",
    }
)
EXPECTED_TOKEN_PROPERTIES = frozenset({"background", "borderColor", "color"})


def test_style_schema_preserves_css_subset() -> None:
    assert SUPPORTED_PROPERTIES == EXPECTED_SUPPORTED_PROPERTIES
    assert DIMENSION_PROPERTIES == EXPECTED_DIMENSION_PROPERTIES
    assert TOKEN_PROPERTIES == EXPECTED_TOKEN_PROPERTIES
    assert "scrollY" not in SUPPORTED_PROPERTIES.values()
    assert "scrollY" in portable_dimension_properties()


def test_html_properties_are_supported_properties_inverse() -> None:
    assert HTML_PROPERTIES == {
        internal_name: css_name
        for css_name, internal_name in SUPPORTED_PROPERTIES.items()
    }


def test_style_schema_indexes_are_complete_and_unique() -> None:
    css_names = [spec.css_name for spec in STYLE_PROPERTY_SPECS if spec.css_name]
    internal_names = [spec.internal_name for spec in STYLE_PROPERTY_SPECS]

    assert len(css_names) == len(set(css_names))
    assert len(internal_names) == len(set(internal_names))
    assert set(STYLE_PROPERTY_SPECS_BY_CSS_NAME) == set(SUPPORTED_PROPERTIES)
    assert set(STYLE_PROPERTY_SPECS_BY_INTERNAL_NAME) == set(internal_names)


def test_native_style_capabilities_are_derived_from_schema() -> None:
    assert NATIVE_LAYOUT_STYLE_PROPERTIES == native_layout_style_properties()
    assert NATIVE_PAINT_STYLE_PROPERTIES == native_paint_style_properties()
    assert NATIVE_IGNORED_STYLE_PROPERTIES == native_ignored_style_properties()
    assert NATIVE_STYLE_SUPPORT == native_style_support()

    known_internal_names = set(STYLE_PROPERTY_SPECS_BY_INTERNAL_NAME)
    assert set(NATIVE_STYLE_SUPPORT) <= known_internal_names
    assert set(NATIVE_STYLE_SUPPORT) == set(SUPPORTED_PROPERTIES.values()) | {"scrollY"}


def test_style_guide_property_table_matches_schema() -> None:
    documented = _style_guide_supported_properties()

    assert documented == {
        spec.css_name: {
            "internal_name": spec.internal_name,
            "value_role": _style_guide_value_role(spec),
        }
        for spec in STYLE_PROPERTY_SPECS
        if spec.css_name is not None
    }


def test_style_guide_native_matrix_matches_schema() -> None:
    assert _style_guide_native_list("Native layout-only properties") == tuple(
        sorted(NATIVE_LAYOUT_STYLE_PROPERTIES - NATIVE_PAINT_STYLE_PROPERTIES)
    )
    assert _style_guide_native_list("Native paint-only properties") == tuple(
        sorted(NATIVE_PAINT_STYLE_PROPERTIES - NATIVE_LAYOUT_STYLE_PROPERTIES)
    )
    assert _style_guide_native_list("Native layout-and-paint properties") == tuple(
        sorted(NATIVE_LAYOUT_STYLE_PROPERTIES & NATIVE_PAINT_STYLE_PROPERTIES)
    )
    assert _style_guide_native_list(
        "Accepted but intentionally ignored in native rendering"
    ) == tuple(sorted(NATIVE_IGNORED_STYLE_PROPERTIES))


def _style_guide_supported_properties() -> dict[str, dict[str, str]]:
    markdown = STYLE_GUIDE.read_text(encoding="utf-8")
    section = markdown.split("## Supported Parsed Properties", maxsplit=1)[1]
    section = section.split("## Values", maxsplit=1)[0]
    documented: dict[str, dict[str, str]] = {}
    for line in section.splitlines():
        match = re.match(r"^\| `([^`]+)` \| `([^`]+)` \| .* \|$", line)
        if match is None:
            continue
        documented[match.group(1)] = {
            "internal_name": match.group(2),
            "value_role": line.strip("|").split("|")[2].strip(),
        }
    return documented


def _style_guide_value_role(spec) -> str:
    if spec.native_ignored:
        return "accepted, native no-op"
    if spec.token_allowed:
        return "color/token"
    if spec.is_dimension:
        return "dimension"
    if spec.internal_name == "alignItems":
        return "native stack alignment"
    if spec.internal_name == "justifyContent":
        return "native stack distribution"
    if spec.internal_name in {"overflow", "textOverflow", "whiteSpace"}:
        return "text clipping keyword"
    return spec.value_kind


def _style_guide_native_list(heading: str) -> tuple[str, ...]:
    markdown = STYLE_GUIDE.read_text(encoding="utf-8")
    section = markdown.split(f"{heading}:", maxsplit=1)[1].lstrip()
    section = section.split("\n\n", maxsplit=1)[0]
    return tuple(sorted(re.findall(r"^- `([^`]+)`$", section, flags=re.MULTILINE)))
