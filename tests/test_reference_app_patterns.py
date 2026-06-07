from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_reference_app_patterns_tracks_current_phase5_apps():
    text = (ROOT / "REFERENCE_APP_PATTERNS.md").read_text(encoding="utf-8")

    assert "examples.hardware.control_panel" in text
    assert "examples.admin.settings_console" in text
    assert "examples.data_workflow.workbench" in text
    assert "examples.utility.ops_console" in text
    assert "Provider Contract" in text
    assert "Feedback Pattern" in text
    assert "Table Pattern" in text
    assert "SectionHeader" in text
    assert "EmptyState" in text
    assert "FeedbackToast" in text
    assert "AppFrame" in text
    assert "MetricTile" in text
    assert "ListRow" in text
    assert (
        "Full-suite baseline after the live preview, static class hardening, "
        "Style IR\npack gate, bundle replay, backend readiness fixture, "
        "backend readiness report,\nbackend coverage declaration, renderer "
        "capability audit, StyleOps capability\naudit, primitive value "
        "validation, bundle manifest hardening, namespace runtime\n"
        "discovery, dependency audit contract metadata, RenderTree validation, "
        "and\nbackend coverage trace plus Path0 output semantic contract and "
        "external Path0\nJSON runner/readiness evidence plus backend package "
        "manifest pass:"
        in text
    )
    assert "`705 passed, 1 skipped`." in text


def test_reference_theme_covers_extracted_ui_helpers():
    theme = (ROOT / "preview" / "reference_theme.css").read_text(encoding="utf-8")

    for selector in (
        ".otoe-stack",
        ".otoe-panel",
        ".otoe-button",
        ".otoe-input",
        ".is-success",
        ".ui-section-header",
        ".ui-empty-state",
        ".ui-toast",
        ".ui-button-content",
        ".ui-card-body",
    ):
        assert selector in theme

    app_css = [
        (ROOT / "preview" / "admin.css").read_text(encoding="utf-8"),
        (ROOT / "preview" / "hardware.css").read_text(encoding="utf-8"),
        (ROOT / "preview" / "data_workflow.css").read_text(encoding="utf-8"),
    ]
    for css in app_css:
        assert ".otoe-button {" not in css
        assert ".otoe-panel {" not in css
        assert ".otoe-input {" not in css


def test_readme_links_reference_app_patterns():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "REFERENCE_APP_PATTERNS.md" in readme
    assert "Phase 5 professional reference apps" in readme
