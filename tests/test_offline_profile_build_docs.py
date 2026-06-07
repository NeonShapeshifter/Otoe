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
    assert "--backend native-python" in text
    assert "otoe.profile.toml" in text
    assert "manifest.json" in text
    assert "otoe-deps.json" in text
    assert 'resolution.mode = "audit-only"' in text
    assert "no lockfile or wheel closure" in single_spaced
    assert "otoe-styles.json" in text
    assert "styleOps" in text
    assert "otoe-run.py" in text
    assert "frameworkFiles" in text
    assert "runtimeFiles" in text
    assert 'assets = ["static/logo.png"]' in text
    assert 'files = ["app.py"]' in text
    assert "local target module or package" in text
    assert "static local imports" in text
    assert "[styles]" in text
    assert 'safelist = ["is-danger", "bg-alert"]' in text
    assert "safelisted classes" in text
    assert "Statically extract literal class tokens" in text
    assert "local `className` expressions" in single_spaced
    assert "emits a warning with the source file and line" in single_spaced
    assert "Dynamic class" in text
    assert 'packages = ["pytest"]' in text
    assert 'extras = ["dev"]' in text
    assert "static external imports" in text
    assert "undeclared static external imports" in text
    assert "`Pillow` for\n`import PIL`" in text
    assert "no installed package metadata" in text
    assert "SHA-256" in text
    assert "manifest/hash metadata" in text
    assert "built-in `native`" in text
    assert 'capability = "native-python"' in text
    assert "backend capability profile" in single_spaced
    assert "strict evidence source/gate" in single_spaced
    assert "Path 0 runtime style proof" in single_spaced
    assert "declared support phase" in text
    assert "--verify" in text
    assert "--check" in text
    assert "--layout-check" in text
    assert "--png" in text
    assert "bundled compiled styles" in text
    assert "schemaVersion = 1" in text
    assert "backend framework policy" in text
    assert "expected `frameworkFiles` set" in text
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
    assert "--backend native-python" in text
    assert 'assets = ["static/logo.png"]' in text
    assert 'files = ["app.py"]' in text
    assert 'packages = ["pytest"]' in text
    assert 'extras = ["dev"]' in text
    assert "static external imports" in text
    assert "undeclared external imports" in text
    assert "`Pillow` for `import PIL`" in text
    assert "no package metadata" in text
    assert 'capability = "native-python"' in text
    assert "asset, and runtime file paths" in text
    assert "local targets such as `app:app` or `workspace_pkg.app:app`" in text
    assert "static local imports" in text
    assert "package-relative imports" in text
    assert "[styles]" in text
    assert 'safelist = ["is-danger", "bg-alert"]' in text
    assert "safelisted classes" in text
    assert "statically extract literal class tokens" in text
    assert "conditional literal branches" in text
    assert "Dynamic Class Extraction Examples" in text
    assert "build-time enumerable" in text
    assert '"is-ready" if ready.value else "is-idle"' in text
    assert "classes.static" in text
    assert 'className=computed(lambda: f"status is-{tone.value}")' in text
    assert 'safelist = ["is-idle", "is-ready", "is-danger"]' in text
    assert "F-strings or string interpolation" in single_spaced
    assert "source file and line" in single_spaced
    assert "missing safelist edge" in text
    assert "dynamic class" in text
    assert "allow_runtime_installs = true" in text
    assert "without installing packages" in single_spaced
    assert ".tar.gz" in text
    assert "bundled compiled styles" in text
    assert "schemaVersion = 1" in text
    assert "backend framework policy" in text
    assert "backend capability profile" in single_spaced
    assert "source/gate evidence" in text
    assert "runtime Path 0 proof" in text
    assert "declared support phase" in text
    assert "declared style omissions" in text
    assert "low-level `styleOps`" in text
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
    assert "styleOps" in text
    assert "backend capability profile" in single_spaced
    assert "validate_render_tree(...)" in text
    assert "render_tree_from_dict(...)" in text
    assert "load_render_tree_artifact(...)" in text
    assert "--render-tree-artifact" in text
    assert "malformed `RenderTree` IR" in text
    assert "boolean schema/path values" in text
    assert "empty identity/event strings" in single_spaced
    assert "Strict backend-readiness evidence" in text
    assert "layout/paint observation hashes" in text
    assert "declared support phase" in text
    assert "runtime-applied layout/paint evidence" in single_spaced
    assert "native-python" in text
    assert "[styles].safelist" in text
    assert "statically extract literal class tokens" in text
    assert "class_names(...)" in text
    assert "Dynamic `className` f-strings" in text
    assert "schema versions" in text
    assert "required `frameworkFiles` policy" in text
    assert "safe relative paths" in text
    assert "lowercase SHA-256 hashes" in text
    assert "unique bundle paths" in single_spaced
    assert "audit-only" in text
    assert "Asset, local target module/package, namespace package target, static local import, and explicit app runtime file copying" in single_spaced
    assert "explicit app runtime file copying" in single_spaced
    assert "otoe build --profile cage" in text
    assert "--validate" in text
    assert "layout/paint" in text
    assert ".tar.gz" in text
    assert "no runtime dependency installs" in text
