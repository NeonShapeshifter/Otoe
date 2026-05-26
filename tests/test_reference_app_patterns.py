from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_reference_app_patterns_tracks_current_phase5_apps():
    text = (ROOT / "REFERENCE_APP_PATTERNS.md").read_text(encoding="utf-8")

    assert "examples.hardware.control_panel" in text
    assert "examples.admin.settings_console" in text
    assert "examples.data_workflow.workbench" in text
    assert "Provider Contract" in text
    assert "Feedback Pattern" in text
    assert "Table Pattern" in text
    assert "SectionHeader" in text
    assert "EmptyState" in text
    assert "FeedbackToast" in text
    assert "Full-suite baseline after the first UI-kit extraction pass: `334 passed`." in text


def test_readme_links_reference_app_patterns():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "REFERENCE_APP_PATTERNS.md" in readme
    assert "Phase 5 professional reference apps" in readme
