from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _single_spaced(text: str) -> str:
    return " ".join(text.split())


def test_offline_profile_build_adr_captures_hardware_direction():
    text = (ROOT / "ADR-018-offline-profile-build-planner.md").read_text(
        encoding="utf-8"
    )
    single_spaced = _single_spaced(text)

    assert "CSS-facing, not browser-CSS-powered" in text
    assert "otoe plan" in text
    assert "otoe build" in text
    assert "otoe deps" in text
    assert "otoe pack" in text
    assert "dist/cage.tar.gz" in text
    assert "audit-only" in text
    assert "--json" in text
    assert "--out" in text
    assert "otoe.profile.toml" in text
    assert "manifest.json" in text
    assert "otoe-deps.json" in text
    assert "otoe-styles.json" in text
    assert "otoe-run.py" in text
    assert "frameworkFiles" in text
    assert "runtimeFiles" in text
    assert 'assets = ["static/logo.png"]' in text
    assert 'files = ["app.py"]' in text
    assert "simple local target module" in text
    assert "same-directory imports" in text
    assert "[styles]" in text
    assert 'safelist = ["is-danger", "bg-alert"]' in text
    assert "safelisted classes" in text
    assert "Dynamic class" in text
    assert 'packages = ["pytest"]' in text
    assert 'extras = ["dev"]' in text
    assert "SHA-256" in text
    assert "built-in `native`" in text
    assert "--verify" in text
    assert "--check" in text
    assert "--layout-check" in text
    assert "--png" in text
    assert "bundled compiled styles" in text
    assert "schemaVersion = 1" in text
    assert "--validate" in text
    assert "__pycache__" in text
    assert "allow_runtime_installs = false" in text
    assert "--profile cage" in text
    assert "No runtime dependency installs" in text
    assert "does not install packages" in single_spaced
    for classification in ("portable", "html-only", "deferred", "invalid"):
        assert classification in text


def test_style_guide_points_css_at_offline_profiles():
    text = (ROOT / "STYLE_GUIDE.md").read_text(encoding="utf-8")
    single_spaced = _single_spaced(text)

    assert "Offline Profile Direction" in text
    assert "ADR-018-offline-profile-build-planner.md" in text
    assert "CSS-facing without being browser-CSS-powered" in text
    assert "dist/otoe-plan.json" in text
    assert "dist/cage" in text
    assert "otoe deps" in text
    assert "otoe pack" in text
    assert "dist/cage.tar.gz" in text
    assert "manifest.json" in text
    assert "otoe-deps.json" in text
    assert "otoe-styles.json" in text
    assert "otoe-run.py" in text
    assert "frameworkFiles" in text
    assert "otoe.profile.toml" in text
    assert 'assets = ["static/logo.png"]' in text
    assert 'files = ["app.py"]' in text
    assert 'packages = ["pytest"]' in text
    assert 'extras = ["dev"]' in text
    assert "asset, and runtime file paths" in text
    assert "simple local target module" in text
    assert "same-directory imports" in text
    assert "package modules" in text
    assert "[styles]" in text
    assert 'safelist = ["is-danger", "bg-alert"]' in text
    assert "safelisted classes" in text
    assert "dynamic class" in text
    assert "allow_runtime_installs = true" in text
    assert "without installing packages" in single_spaced
    assert ".tar.gz" in text
    assert "bundled compiled styles" in text
    assert "schemaVersion = 1" in text
    assert "--layout-check" in text
    assert "--profile cage" in text


def test_roadmap_keeps_low_level_build_work_in_scope():
    text = (ROOT / "ROADMAP.md").read_text(encoding="utf-8")
    single_spaced = _single_spaced(text)

    assert "Low-Level Build Direction" in text
    assert "offline profile planner" in text
    assert "otoe plan" in text
    assert "otoe deps" in text
    assert "otoe pack" in text
    assert "otoe plan --json/--out" in text
    assert "otoe.profile.toml" in text
    assert "manifest-first" in text
    assert "otoe-styles.json" in text
    assert "[styles].safelist" in text
    assert "schema versions" in text
    assert "audit-only" in text
    assert "Asset, simple local target module, same-directory import, and explicit app runtime file copying" in single_spaced
    assert "explicit app runtime file copying" in single_spaced
    assert "otoe build --profile cage" in text
    assert "--validate" in text
    assert "layout/paint" in text
    assert ".tar.gz" in text
    assert "no runtime dependency installs" in text
