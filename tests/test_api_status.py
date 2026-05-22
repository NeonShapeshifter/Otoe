import otoe
from otoe import (
    API_STATUSES,
    CORE_PREVIEW_APIS,
    EXPERIMENTAL_NATIVE_APIS,
    PREVIEW_APIS,
    api_status,
    is_experimental_api,
)


def test_native_top_level_exports_are_marked_experimental():
    assert EXPERIMENTAL_NATIVE_APIS <= set(otoe.__all__)

    for name in EXPERIMENTAL_NATIVE_APIS:
        status = api_status(name)
        assert status.category == "experimental-native"
        assert "not be treated as a stable" in status.detail
        assert is_experimental_api(name)


def test_core_preview_exports_are_declared_but_not_stable():
    assert CORE_PREVIEW_APIS == PREVIEW_APIS
    assert PREVIEW_APIS <= set(otoe.__all__)

    for name in PREVIEW_APIS:
        status = api_status(name)
        assert status.category == "preview"
        assert "does not carry a stable compatibility promise" in status.detail
        assert not is_experimental_api(name)


def test_unknown_api_status_defaults_to_internal_guidance():
    status = api_status("_native_internal_helper")

    assert status.category == "unknown"
    assert "Treat it as internal" in status.detail


def test_api_status_registry_matches_declared_sets():
    declared = PREVIEW_APIS | EXPERIMENTAL_NATIVE_APIS

    assert set(API_STATUSES) == declared


def test_public_exports_are_declared_or_experimental():
    assert set(otoe.__all__) == PREVIEW_APIS | EXPERIMENTAL_NATIVE_APIS
