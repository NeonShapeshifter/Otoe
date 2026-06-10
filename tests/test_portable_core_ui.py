import json
import os
import subprocess
import sys
from importlib import import_module
from pathlib import Path

import otoe
from otoe import (
    Button,
    Input,
    PRODUCT_PREVIEW_UI_APIS,
    ScrollView,
    Text,
    VStack,
    api_status,
    css,
    mount,
    render_html,
    root_widget,
)
from otoe._native_shared import native_widget_support
from otoe.cli import main
from otoe.portable_core import (
    format_portable_core_ui_v0,
    portable_core_ui_v0_matrix,
)
from otoe.ui import ActionButton, ListRow, TabButton, Tabs
from otoe.experimental.native import NativeSurface, layout_native, paint_native
from examples.portable_core_ui import PORTABLE_CORE_EXAMPLES


ROOT = Path(__file__).resolve().parents[1]
MATRIX_PATH = ROOT / "docs" / "portable-core-ui-v0.json"
DOC_PATH = ROOT / "docs" / "portable-core-ui-v0.md"
PORTABLE_STYLES_PATH = ROOT / "preview" / "portable_core_ui.css"


def _matrix():
    return json.loads(MATRIX_PATH.read_text(encoding="utf-8"))


def _entries():
    return _matrix()["entries"]


def _outside_portable_core():
    return _matrix()["outsidePortableCore"]


def _load_target(target: str):
    module_name, _, object_name = target.partition(":")
    assert module_name and object_name
    return getattr(import_module(module_name), object_name)


def _sample(entry_id: str):
    entry = next(item for item in _entries() if item["id"] == entry_id)
    return _load_target(entry["exampleTarget"])()


def _sample_text(entry_id: str) -> str:
    return {
        "text": "Portable text",
        "button": "Run",
        "input": "A",
        "vstack": "One",
        "hstack": "Left",
        "panel": "Panel body",
        "scrollview": "First",
        "card": "Card body",
        "badge": "Ready",
        "action-button": "Execute",
        "tabs": "Overview",
        "dialog": "Dialog body",
        "list-row": "Job",
        "metric-tile": "Latency",
        "app-frame": "Workspace",
    }[entry_id]


def _markdown_matrix_rows():
    rows = []
    in_table = False
    for line in DOC_PATH.read_text(encoding="utf-8").splitlines():
        if line.startswith("| Primitive |"):
            in_table = True
            continue
        if not in_table:
            continue
        if not line.startswith("|"):
            break
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if cells[0].startswith("---"):
            continue
        rows.append(cells)
    return rows


def test_portable_core_ui_matrix_contract_is_machine_readable():
    payload = _matrix()
    entries = payload["entries"]
    ids = [entry["id"] for entry in entries]

    assert payload["schemaVersion"] == 1
    assert payload["format"] == "otoe-portable-core-ui-v0"
    assert ids == [
        "text",
        "button",
        "input",
        "vstack",
        "hstack",
        "panel",
        "scrollview",
        "card",
        "badge",
        "action-button",
        "tabs",
        "dialog",
        "list-row",
        "metric-tile",
        "app-frame",
    ]
    assert len(ids) == len(set(ids))
    assert [entry["id"] for entry in entries if not entry["portableCore"]] == [
        "dialog"
    ]
    for entry in entries:
        assert entry["exampleTarget"].startswith("examples.portable_core_ui:")


def test_portable_core_ui_packaged_matrix_matches_docs_json():
    assert portable_core_ui_v0_matrix() == _matrix()


def test_portable_core_ui_formatter_exposes_matrix_sections():
    report = format_portable_core_ui_v0(include_outside=True, include_examples=True)

    assert "Portable Core UI v0" in report
    assert "14 portable primitives" in report
    assert "`Button`" in report
    assert "Native Window" in report
    assert "Example Targets" in report
    assert "examples.portable_core_ui:button_example" in report
    assert "Outside Portable Core v0" in report
    assert "app-shell-navigation" in report


def test_portable_core_examples_cover_core_entries():
    assert set(PORTABLE_CORE_EXAMPLES) == {
        entry["id"] for entry in _entries() if entry["portableCore"]
    }

    for entry_id, example in PORTABLE_CORE_EXAMPLES.items():
        assert example is _load_target(
            next(entry["exampleTarget"] for entry in _entries() if entry["id"] == entry_id)
        )


def test_portable_core_ui_markdown_table_matches_json_matrix():
    expected = [
        [
            entry["label"],
            entry["html"],
            entry["liveHtml"],
            entry["nativeHeadless"],
            entry["nativeWindowDriver"],
            entry["status"],
        ]
        for entry in _entries()
    ]

    assert _markdown_matrix_rows() == expected


def test_portable_core_examples_and_non_core_groups_are_documented():
    doc = DOC_PATH.read_text(encoding="utf-8")

    for entry in _entries():
        assert entry["exampleTarget"] in doc
    for item in _outside_portable_core():
        assert item["id"] in doc
        assert item["classification"] in doc
        for symbol in item["symbols"]:
            assert f"`{symbol}`" in doc


def test_portable_core_ui_symbols_are_exported_and_statused():
    for entry in _entries():
        for symbol in entry["symbols"]:
            assert hasattr(otoe, symbol)
            assert api_status(symbol).category == "preview"


def test_product_preview_ui_surface_is_fully_classified():
    matrix_symbols = {
        symbol for entry in _entries() for symbol in entry["symbols"]
    }
    outside_symbols = {
        symbol for item in _outside_portable_core() for symbol in item["symbols"]
    }
    classifications = {item["classification"] for item in _outside_portable_core()}

    assert PRODUCT_PREVIEW_UI_APIS <= matrix_symbols | outside_symbols
    assert not matrix_symbols & outside_symbols
    assert classifications == {
        "interactive-preview",
        "product-preview-app-shell",
        "product-preview-composite",
        "support-model",
    }
    for item in _outside_portable_core():
        assert item["id"]
        assert item["reason"].endswith(".")
        assert item["symbols"]


def test_portable_core_ui_native_widgets_are_declared_supported():
    for entry in _entries():
        for widget in entry["nativeWidgets"]:
            assert native_widget_support(widget) in {"container", "control", "text"}


def test_portable_core_ui_samples_render_html():
    for entry in _entries():
        mounted = mount(_sample(entry["id"]))

        html = render_html(mounted)

        assert _sample_text(entry["id"]) in html


def test_portable_core_ui_samples_layout_and_paint_native():
    for entry in _entries():
        mounted = mount(_sample(entry["id"]))

        layout = layout_native(mounted)
        paint = paint_native(layout)
        widgets = {box.name for box in layout.boxes}

        assert set(entry["nativeWidgets"]) <= widgets
        assert paint.width >= 1
        assert paint.height >= 1
        assert paint.commands


def test_portable_core_ui_gallery_cli_renders_html_and_native_png(tmp_path):
    html_output = tmp_path / "portable-core-ui.html"
    png_output = tmp_path / "portable-core-ui.png"

    html_result = main(
        [
            "render",
            "examples.portable_core_ui:app",
            "--out",
            str(html_output),
            "--css",
            str(PORTABLE_STYLES_PATH),
            "--pretty",
        ]
    )
    native_result = main(
        [
            "render",
            "examples.portable_core_ui:app",
            "--out",
            str(png_output),
            "--native",
            "--css",
            str(PORTABLE_STYLES_PATH),
        ]
    )

    html = html_output.read_text(encoding="utf-8")
    assert html_result == 0
    assert native_result == 0
    assert "Portable Core UI v0" in html
    assert "Latency" in html
    assert 'style="' in html
    assert png_output.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")


def test_portable_core_ui_gallery_build_validates_offline_bundle(
    tmp_path,
    capsys,
):
    output = tmp_path / "portable-core-ui-cage"
    frame = tmp_path / "portable-core-ui-frame.png"
    scaled_frame = tmp_path / "portable-core-ui-frame@2x.png"

    result = main(
        [
            "build",
            "examples.portable_core_ui:app",
            "--out",
            str(output),
            "--css",
            str(PORTABLE_STYLES_PATH),
            "--validate",
        ]
    )

    captured = capsys.readouterr()
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    plan = json.loads((output / "otoe-plan.json").read_text(encoding="utf-8"))
    styles = json.loads((output / "otoe-styles.json").read_text(encoding="utf-8"))
    runtime_paths = sorted(entry["bundlePath"] for entry in manifest["runtimeFiles"])
    planned_classes = {entry["className"] for entry in styles["styleOps"]["classes"]}
    png = subprocess.run(
        [sys.executable, str(output / "otoe-run.py"), "--png", str(frame)],
        capture_output=True,
        cwd=output,
        env={**os.environ, "PYTHONPATH": ""},
        text=True,
    )
    scaled_png = subprocess.run(
        [
            sys.executable,
            str(output / "otoe-run.py"),
            "--png",
            str(scaled_frame),
            "--scale",
            "2",
        ],
        capture_output=True,
        cwd=output,
        env={**os.environ, "PYTHONPATH": ""},
        text=True,
    )

    assert result == 0
    assert "validation: ok" in captured.out
    assert manifest["target"] == "examples.portable_core_ui:app"
    assert manifest["status"] == "warnings"
    assert plan["status"] == "warnings"
    assert plan["hasErrors"] is False
    assert runtime_paths == ["app/examples/portable_core_ui.py"]
    assert {"portable-title", "ui-card", "ui-frame"} <= planned_classes
    assert png.returncode == 0, png.stderr
    assert scaled_png.returncode == 0, scaled_png.stderr
    assert frame.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    width, height = _png_size(frame.read_bytes())
    scaled_width, scaled_height = _png_size(scaled_frame.read_bytes())
    assert (scaled_width, scaled_height) == (width * 2, height * 2)


def test_portable_core_native_input_controls_dispatch_events():
    clicked = []
    changed = []
    scrolled = []
    stylesheet = css(".scroll { width: 120; height: 40; padding: 4; gap: 4; }")
    surface = NativeSurface(
        VStack(
            Button("Run", onClick=lambda: clicked.append("button")),
            Input(value="", onChange=changed.append),
            ScrollView(
                Button("First", onClick=lambda: None),
                Button("Second", onClick=lambda: None),
                className="scroll",
                onScroll=scrolled.append,
            ),
            gap=4,
        ),
        stylesheet=stylesheet,
    )

    button = surface.box((0,))
    surface.click(button.x + 1, button.y + 1)
    surface.key_down("Enter")
    field = surface.box((1,))
    surface.click(field.x + 1, field.y + 1)
    surface.input_text("hello")
    scroll = surface.box((2,))
    surface.scroll(scroll.x + 1, scroll.y + 1, 40)

    assert clicked == ["button", "button"]
    assert changed == ["hello"]
    assert scrolled == [40]


def test_portable_product_controls_keep_click_contracts():
    clicked = []
    root = root_widget(
        mount(
            VStack(
                ActionButton("Execute", onClick=lambda: clicked.append("action")),
                Tabs(
                    TabButton(
                        "Overview",
                        active=True,
                        onClick=lambda: clicked.append("tab"),
                    )
                ),
                ListRow(
                    title="Job",
                    action_label="Open",
                    on_action=lambda: clicked.append("row"),
                ),
            )
        )
    )

    root.children[0].trigger("onClick")
    root.children[1].children[0].trigger("onClick")
    root.children[2].children[-1].trigger("onClick")

    assert clicked == ["action", "tab", "row"]


def _png_size(data: bytes) -> tuple[int, int]:
    assert data.startswith(b"\x89PNG\r\n\x1a\n")
    return (
        int.from_bytes(data[16:20], "big"),
        int.from_bytes(data[20:24], "big"),
    )
