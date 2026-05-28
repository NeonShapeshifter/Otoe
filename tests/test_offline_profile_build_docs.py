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
    assert "audit-only" in text
    assert "--json" in text
    assert "--out" in text
    assert "otoe.profile.toml" in text
    assert "manifest.json" in text
    assert "otoe-deps.json" in text
    assert "otoe-run.py" in text
    assert "frameworkFiles" in text
    assert "runtimeFiles" in text
    assert 'assets = ["static/logo.png"]' in text
    assert 'files = ["app.py"]' in text
    assert 'packages = ["pytest"]' in text
    assert 'extras = ["dev"]' in text
    assert "SHA-256" in text
    assert "built-in `native`" in text
    assert "--check" in text
    assert "--png" in text
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
    assert "manifest.json" in text
    assert "otoe-deps.json" in text
    assert "otoe-run.py" in text
    assert "frameworkFiles" in text
    assert "otoe.profile.toml" in text
    assert 'assets = ["static/logo.png"]' in text
    assert 'files = ["app.py"]' in text
    assert 'packages = ["pytest"]' in text
    assert 'extras = ["dev"]' in text
    assert "asset, and runtime file paths" in text
    assert "allow_runtime_installs = true" in text
    assert "without installing packages" in single_spaced
    assert "--profile cage" in text


def test_roadmap_keeps_low_level_build_work_in_scope():
    text = (ROOT / "ROADMAP.md").read_text(encoding="utf-8")
    single_spaced = _single_spaced(text)

    assert "Low-Level Build Direction" in text
    assert "offline profile planner" in text
    assert "otoe plan" in text
    assert "otoe deps" in text
    assert "otoe plan --json/--out" in text
    assert "otoe.profile.toml" in text
    assert "manifest-first" in text
    assert "audit-only" in text
    assert "Asset and explicit app runtime file copying" in single_spaced
    assert "explicit app runtime file copying" in text
    assert "otoe build --profile cage" in text
    assert "no runtime dependency installs" in text
