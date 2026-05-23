import tomllib
from pathlib import Path

import otoe.ui as ui
import otoe.widgets as widgets
from otoe.component import Component


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_pyproject_includes_pep_561_typing_files():
    metadata = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    package_data = metadata["tool"]["setuptools"]["package-data"]["otoe"]

    assert "py.typed" in package_data
    assert "*.pyi" in package_data


def test_core_typing_artifacts_exist():
    package_root = PROJECT_ROOT / "src" / "otoe"

    assert (package_root / "py.typed").is_file()
    assert (package_root / "widgets.pyi").is_file()
    assert (package_root / "control.pyi").is_file()
    assert (package_root / "ui.pyi").is_file()


def test_widget_stub_covers_runtime_widgets():
    widget_stub = (PROJECT_ROOT / "src" / "otoe" / "widgets.pyi").read_text(encoding="utf-8")
    widget_names = sorted(
        name
        for name, value in vars(widgets).items()
        if isinstance(value, type)
        and value.__module__ == "otoe.widgets"
        and hasattr(value, "props")
    )

    assert widget_names
    for name in widget_names:
        assert f"def {name}(" in widget_stub


def test_control_stub_declares_public_helpers():
    control_stub = (PROJECT_ROOT / "src" / "otoe" / "control.pyi").read_text(encoding="utf-8")

    for signature in ("def Show(", "def For(", "def is_control_tag(", "def list_from_value("):
        assert signature in control_stub


def test_ui_stub_covers_runtime_components_and_models():
    ui_stub = (PROJECT_ROOT / "src" / "otoe" / "ui.pyi").read_text(encoding="utf-8")
    component_names = sorted(
        name
        for name, value in vars(ui).items()
        if isinstance(value, Component)
        and getattr(value, "__module__", None) == "otoe.ui"
    )

    assert component_names
    for name in component_names:
        assert f"def {name}(" in ui_stub

    for name in (
        "Command",
        "CommandRegistry",
        "MenuItem",
        "NavRoute",
        "SelectOption",
        "TableColumn",
    ):
        assert f"class {name}:" in ui_stub

    assert "UI_EVENT_SIGNATURES: dict[str, EventSignature]" in ui_stub
    assert "def class_names(" in ui_stub
