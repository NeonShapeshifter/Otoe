from pathlib import Path
import re

import otoe
from otoe import ui as otoe_ui
from otoe import (
    API_STATUSES,
    API_TIERS,
    API_METADATA_APIS,
    CORE_PREVIEW_APIS,
    EXPERIMENTAL_BACKEND_APIS,
    EXPERIMENTAL_NATIVE_APIS,
    PREVIEW_APIS,
    PREVIEW_SUPPORT_APIS,
    PRODUCT_PREVIEW_UI_APIS,
    api_status,
    is_experimental_api,
)
from otoe._widget_contracts import known_widget_names
from otoe.experimental import backend as experimental_backend
from otoe.experimental import native as experimental_native


DOCS_API_TIERS = Path(__file__).resolve().parents[1] / "docs" / "api-tiers.md"
ALLOWLISTED_UNKNOWN_PUBLIC_EXPORTS = frozenset()
PRODUCT_PREVIEW_REGISTRY_WIDGETS = frozenset({"FocusScope", "ShortcutScope"})
PREFERRED_IMPORT_MODULES = {
    "otoe": otoe,
    "otoe.ui": otoe_ui,
    "otoe.experimental.native": experimental_native,
    "otoe.experimental.backend": experimental_backend,
}
PUBLIC_API_REPORT_TIERS = (
    "core-preview",
    "product-preview-ui",
    "preview-support",
    "experimental-native",
    "experimental-backend",
)


def test_native_top_level_exports_are_marked_experimental():
    assert EXPERIMENTAL_NATIVE_APIS <= set(otoe.__all__)

    for name in EXPERIMENTAL_NATIVE_APIS:
        status = api_status(name)
        assert status.category == "experimental-native"
        assert status.tier == "experimental-native"
        assert status.preferred_import == "otoe.experimental.native"
        assert "not be treated as a stable" in status.detail
        assert is_experimental_api(name)
        assert getattr(experimental_native, name) is getattr(otoe, name)


def test_backend_evidence_exports_are_marked_experimental():
    assert EXPERIMENTAL_BACKEND_APIS <= set(otoe.__all__)

    for name in EXPERIMENTAL_BACKEND_APIS:
        status = api_status(name)
        assert status.category == "experimental-backend"
        assert status.tier == "experimental-backend"
        assert status.preferred_import == "otoe.experimental.backend"
        assert "renderer candidates" in status.detail
        assert is_experimental_api(name)
        assert getattr(experimental_backend, name) is getattr(otoe, name)


def test_core_preview_exports_are_declared_but_not_stable():
    assert {"component", "signal", "computed", "Text", "Button"} <= CORE_PREVIEW_APIS
    assert PREVIEW_APIS <= set(otoe.__all__)

    for name in CORE_PREVIEW_APIS:
        status = api_status(name)
        assert status.category == "preview"
        assert status.tier == "core-preview"
        assert status.preferred_import == "otoe"
        assert "does not carry a stable compatibility promise" in status.detail
        assert not is_experimental_api(name)


def test_core_widget_registry_names_have_api_status():
    registry_names = frozenset(known_widget_names())
    expected_core_widgets = registry_names - PRODUCT_PREVIEW_REGISTRY_WIDGETS

    assert expected_core_widgets <= CORE_PREVIEW_APIS
    assert PRODUCT_PREVIEW_REGISTRY_WIDGETS <= PRODUCT_PREVIEW_UI_APIS

    for name in registry_names:
        assert name in otoe.__all__
        assert api_status(name).tier != "unknown"


def test_product_preview_ui_exports_prefer_otoe_ui_imports():
    assert {"Card", "Badge", "ActionButton", "DataTable"} <= PRODUCT_PREVIEW_UI_APIS

    for name in PRODUCT_PREVIEW_UI_APIS:
        status = api_status(name)
        assert status.category == "preview"
        assert status.tier == "product-preview-ui"
        assert status.preferred_import == "otoe.ui"
        assert "Prefer importing it from otoe.ui" in status.detail
        assert not is_experimental_api(name)


def test_product_preview_ui_exports_exist_in_otoe_ui_facade():
    assert PRODUCT_PREVIEW_UI_APIS <= set(otoe_ui.__all__)

    for name in PRODUCT_PREVIEW_UI_APIS:
        assert getattr(otoe_ui, name) is getattr(otoe, name)


def test_preview_support_exports_are_separate_from_core():
    assert {"LiveHtmlRenderer", "MountedNode", "utility_css"} <= PREVIEW_SUPPORT_APIS

    for name in PREVIEW_SUPPORT_APIS:
        status = api_status(name)
        assert status.category == "preview"
        assert status.tier == "preview-support"
        assert status.preferred_import == "otoe"
        assert not is_experimental_api(name)


def test_api_metadata_exports_describe_the_registry():
    assert {"API_TIERS", "api_status", "ApiStatus"} <= API_METADATA_APIS

    for name in API_METADATA_APIS:
        status = api_status(name)
        assert status.category == "preview"
        assert status.tier == "api-metadata"
        assert status.preferred_import == "otoe"
        assert not is_experimental_api(name)


def test_unknown_api_status_defaults_to_internal_guidance():
    status = api_status("_native_internal_helper")

    assert status.category == "unknown"
    assert "Treat it as internal" in status.detail


def test_api_status_registry_matches_declared_sets():
    declared = PREVIEW_APIS | EXPERIMENTAL_NATIVE_APIS | EXPERIMENTAL_BACKEND_APIS

    assert set(API_STATUSES) == declared
    assert set().union(*API_TIERS.values()) == declared
    assert set(API_TIERS) == {
        "api-metadata",
        "core-preview",
        "product-preview-ui",
        "preview-support",
        "experimental-native",
        "experimental-backend",
    }


def test_pre_alpha_exports_do_not_claim_stable_status():
    for status in API_STATUSES.values():
        assert status.category != "stable"
        assert status.tier != "stable"


def test_api_tier_sets_are_disjoint():
    tier_items = list(API_TIERS.items())
    for index, (tier, names) in enumerate(tier_items):
        for other_tier, other_names in tier_items[index + 1 :]:
            assert not names & other_names, f"{tier} overlaps {other_tier}"


def test_public_exports_are_declared_or_experimental():
    assert set(otoe.__all__) == (
        PREVIEW_APIS | EXPERIMENTAL_NATIVE_APIS | EXPERIMENTAL_BACKEND_APIS
    )


def test_public_exports_have_declared_status_or_are_allowlisted():
    unknown = [
        name
        for name in otoe.__all__
        if api_status(name).tier == "unknown"
        and name not in ALLOWLISTED_UNKNOWN_PUBLIC_EXPORTS
    ]

    assert unknown == []


def test_experimental_facade_exports_match_declared_tiers():
    assert set(experimental_native.__all__) == EXPERIMENTAL_NATIVE_APIS
    assert set(experimental_backend.__all__) == EXPERIMENTAL_BACKEND_APIS


def test_api_status_entries_exist_at_declared_preferred_imports():
    for name, status in API_STATUSES.items():
        assert name in otoe.__all__
        assert status.preferred_import is not None
        module = PREFERRED_IMPORT_MODULES[status.preferred_import]
        assert getattr(module, name) is getattr(otoe, name)


def test_experimental_top_level_exports_exist_in_matching_facades():
    for name in EXPERIMENTAL_NATIVE_APIS:
        assert getattr(experimental_native, name) is getattr(otoe, name)
    for name in EXPERIMENTAL_BACKEND_APIS:
        assert getattr(experimental_backend, name) is getattr(otoe, name)


def test_api_status_report_has_expected_public_tiers():
    report = _api_status_report()

    assert tuple(report) == (
        "api-metadata",
        *PUBLIC_API_REPORT_TIERS,
    )
    for tier in PUBLIC_API_REPORT_TIERS:
        assert report[tier] == tuple(sorted(API_TIERS[tier]))


def test_documented_top_level_export_map_matches_api_status_report():
    documented = _documented_top_level_export_map()
    expected = _api_status_report()

    assert set(documented) == set(expected)
    for tier, names in expected.items():
        assert documented[tier] == names


def _api_status_report() -> dict[str, tuple[str, ...]]:
    return {tier: tuple(sorted(names)) for tier, names in API_TIERS.items()}


def _documented_top_level_export_map() -> dict[str, tuple[str, ...]]:
    markdown = DOCS_API_TIERS.read_text(encoding="utf-8")
    section = markdown.split("## Current Top-Level Export Map", maxsplit=1)[1]
    documented: dict[str, tuple[str, ...]] = {}
    for line in section.splitlines():
        match = re.match(r"^\| `([^`]+)` \| (.*) \|$", line)
        if match is None:
            continue
        tier = match.group(1)
        names = tuple(sorted(re.findall(r"`([^`]+)`", match.group(2))))
        documented[tier] = names
    return documented
