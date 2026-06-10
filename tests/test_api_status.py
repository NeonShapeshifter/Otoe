import otoe
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
from otoe.experimental import backend as experimental_backend
from otoe.experimental import native as experimental_native


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


def test_product_preview_ui_exports_prefer_otoe_ui_imports():
    assert {"Card", "Badge", "ActionButton", "DataTable"} <= PRODUCT_PREVIEW_UI_APIS

    for name in PRODUCT_PREVIEW_UI_APIS:
        status = api_status(name)
        assert status.category == "preview"
        assert status.tier == "product-preview-ui"
        assert status.preferred_import == "otoe.ui"
        assert "Prefer importing it from otoe.ui" in status.detail
        assert not is_experimental_api(name)


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


def test_api_tier_sets_are_disjoint():
    tier_items = list(API_TIERS.items())
    for index, (tier, names) in enumerate(tier_items):
        for other_tier, other_names in tier_items[index + 1 :]:
            assert not names & other_names, f"{tier} overlaps {other_tier}"


def test_public_exports_are_declared_or_experimental():
    assert set(otoe.__all__) == (
        PREVIEW_APIS | EXPERIMENTAL_NATIVE_APIS | EXPERIMENTAL_BACKEND_APIS
    )


def test_experimental_facade_exports_match_declared_tiers():
    assert set(experimental_native.__all__) == EXPERIMENTAL_NATIVE_APIS
    assert set(experimental_backend.__all__) == EXPERIMENTAL_BACKEND_APIS
