from pathlib import Path

from otoe import build
from otoe.build import CORE_RUNTIME_FILES, FRAMEWORK_OUTPUT_DIR, OTOE_PACKAGE_DIR


def test_core_runtime_files_exist():
    missing = [
        path
        for path in CORE_RUNTIME_FILES
        if not (OTOE_PACKAGE_DIR / path).is_file()
    ]

    assert missing == []


def test_core_runtime_files_are_unique():
    assert len(CORE_RUNTIME_FILES) == len(set(CORE_RUNTIME_FILES))


def test_core_runtime_files_include_typing_artifacts():
    assert "py.typed" in CORE_RUNTIME_FILES
    assert "widgets.pyi" in CORE_RUNTIME_FILES
    assert "ui.pyi" in CORE_RUNTIME_FILES
    assert "control.pyi" in CORE_RUNTIME_FILES


def test_core_runtime_files_include_critical_bundle_helpers():
    assert {
        "bundle_deps.py",
        "bundle_backend_package.py",
        "bundle_backend_coverage.py",
        "render_ir_serialize.py",
        "_style_schema.py",
        "style_ops.py",
        "style_ops_replay.py",
        "style_ops_validation.py",
        "_widget_contracts.py",
    } <= set(CORE_RUNTIME_FILES)


def test_core_runtime_files_include_ui_facade_modules():
    assert {
        "_ui_commands.py",
        "_ui_data.py",
        "_ui_helpers.py",
        "_ui_keyboard.py",
        "_ui_layout.py",
        "_ui_models.py",
        "_ui_navigation.py",
        "_ui_overlays.py",
        "_ui_surfaces.py",
        "_ui_theme.py",
        "ui.py",
        "ui.pyi",
    } <= set(CORE_RUNTIME_FILES)


def test_native_runtime_files_include_native_surface_helpers():
    assert {
        "_native_surface.py",
        "_native_surface_focus.py",
        "_native_surface_input.py",
        "_native_surface_scroll.py",
    } <= set(build.BACKEND_RUNTIME_FILES["native"])


def test_runner_expected_framework_files_include_core_runtime_files():
    expected = build._runner_expected_framework_files()["native"]
    expected_paths = set(expected)

    for path in CORE_RUNTIME_FILES:
        bundle_path = (Path(FRAMEWORK_OUTPUT_DIR) / "otoe" / path).as_posix()
        assert bundle_path in expected_paths


def test_framework_runtime_files_cover_local_import_dependencies():
    assert build._framework_import_dependency_errors("native") == ()


def test_framework_runtime_import_check_detects_missing_private_dependency():
    included = tuple(
        path
        for path in build._framework_runtime_paths("native")
        if path != "_widget_contracts.py"
    )

    errors = build._framework_import_dependency_errors(
        "native",
        included_paths=included,
    )

    assert any("imports _widget_contracts.py" in error for error in errors)


def test_framework_runtime_import_graph_covers_recent_private_helpers():
    expected_edges = {
        "capabilities.py": {"_style_schema.py", "_widget_contracts.py"},
        "mount.py": {"_widget_contracts.py"},
        "plan.py": {"_style_planning.py"},
        "style.py": {"_style_schema.py"},
        "style_ir.py": {"_style_planning.py", "_style_schema.py"},
        "_native_surface.py": {
            "_native_surface_focus.py",
            "_native_surface_input.py",
            "_native_surface_scroll.py",
        },
    }

    for source, expected_dependencies in expected_edges.items():
        assert expected_dependencies <= set(build._local_runtime_imports(source))
