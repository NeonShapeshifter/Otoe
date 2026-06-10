from pathlib import Path

import pytest

from otoe import (
    Button,
    HStack,
    Input,
    NativeLayoutError,
    StyleRule,
    StyleSheet,
    Text,
    VStack,
    Widget,
    css,
    layout_native,
    mount,
)
from otoe.capabilities import (
    CapabilityProfileError,
    backend_capability_profile_from_dict,
    backend_capability_profile,
    load_backend_capability_profile,
    supported_backend_capability_names,
)
from otoe._native_shared import (
    NATIVE_CONTAINER_WIDGETS,
    NATIVE_CONTROL_WIDGETS,
    NATIVE_IGNORED_STYLE_PROPERTIES,
    NATIVE_INPUT_SUPPORT,
    NATIVE_LAYOUT_STYLE_PROPERTIES,
    NATIVE_PAINT_STYLE_PROPERTIES,
    NATIVE_RENDERER_BOUNDARY_SUPPORT,
    NATIVE_STYLE_SUPPORT,
    NATIVE_TEXT_WIDGETS,
    NATIVE_WIDGET_SUPPORT,
    native_input_support,
    native_style_support,
    native_widget_support,
)
from otoe.style import SUPPORTED_PROPERTIES


EXPECTED_LAYOUT_ONLY_STYLES = frozenset(
    {
        "alignItems",
        "gap",
        "height",
        "justifyContent",
        "maxHeight",
        "maxWidth",
        "minHeight",
        "minWidth",
        "padding",
        "scrollY",
        "width",
    }
)
EXPECTED_PAINT_ONLY_STYLES = frozenset(
    {
        "background",
        "borderColor",
        "borderRadius",
        "color",
        "overflow",
        "textOverflow",
        "whiteSpace",
    }
)
EXPECTED_LAYOUT_AND_PAINT_STYLES = frozenset({"borderWidth", "fontSize"})
EXPECTED_IGNORED_STYLES = frozenset(
    {
        "borderStyle",
        "display",
        "fontWeight",
        "margin",
        "opacity",
    }
)
EXPECTED_TEXT_WIDGETS = frozenset({"Text"})
EXPECTED_CONTROL_WIDGETS = frozenset({"Button", "Input"})
EXPECTED_CONTAINER_WIDGETS = frozenset(
    {
        "FocusScope",
        "For",
        "HStack",
        "Panel",
        "ScrollView",
        "ShortcutScope",
        "Show",
        "VStack",
    }
)
EXPECTED_SUPPORTED_INPUT = frozenset(
    {
        "click",
        "focus",
        "input_text",
        "key_down",
        "key_input",
        "shortcut",
        "tab_focus",
        "wheel",
    }
)
EXPECTED_DEFERRED_INPUT = frozenset(
    {
        "caret_movement",
        "drag",
        "gesture",
        "ime",
        "inertial_scroll",
        "pointer_move",
        "text_selection",
        "uncontrolled_input",
    }
)
EXPECTED_RENDERER_BOUNDARIES = {
    "paint": "supported",
    "renderTreeLayout": "supported",
}


def test_native_style_support_matrix_is_complete_and_categorized():
    assert NATIVE_LAYOUT_STYLE_PROPERTIES == (
        EXPECTED_LAYOUT_ONLY_STYLES | EXPECTED_LAYOUT_AND_PAINT_STYLES
    )
    assert NATIVE_PAINT_STYLE_PROPERTIES == (
        EXPECTED_PAINT_ONLY_STYLES | EXPECTED_LAYOUT_AND_PAINT_STYLES
    )
    assert NATIVE_IGNORED_STYLE_PROPERTIES == EXPECTED_IGNORED_STYLES
    assert set(NATIVE_STYLE_SUPPORT) == set(SUPPORTED_PROPERTIES.values()) | {"scrollY"}

    for name in EXPECTED_LAYOUT_ONLY_STYLES:
        assert native_style_support(name) == "layout"
    for name in EXPECTED_PAINT_ONLY_STYLES:
        assert native_style_support(name) == "paint"
    for name in EXPECTED_LAYOUT_AND_PAINT_STYLES:
        assert native_style_support(name) == "layout+paint"
    for name in EXPECTED_IGNORED_STYLES:
        assert native_style_support(name) == "ignored"
    assert native_style_support("lineHeight") is None


def test_native_python_capability_profile_matches_support_matrices():
    profile = backend_capability_profile("native")

    assert profile.name == "native-python"
    assert profile.style_support == NATIVE_STYLE_SUPPORT
    assert profile.widget_support == NATIVE_WIDGET_SUPPORT
    assert profile.input_support == NATIVE_INPUT_SUPPORT
    assert NATIVE_RENDERER_BOUNDARY_SUPPORT == EXPECTED_RENDERER_BOUNDARIES
    assert profile.renderer_boundary_support == EXPECTED_RENDERER_BOUNDARIES
    assert profile.style("padding") == "layout"
    assert profile.widget("Hero") == "fallback-container"
    assert profile.input("wheel") == "supported"
    assert profile.renderer_boundary("renderTreeLayout") == "supported"
    assert "native-python" in supported_backend_capability_names()


def test_backend_capability_profile_rejects_unknown_name():
    with pytest.raises(CapabilityProfileError, match="unsupported backend capability"):
        backend_capability_profile("gpu-magic")


def test_backend_capability_profile_from_dict_derives_coverage_declaration():
    profile = backend_capability_profile_from_dict(
        {
            "schemaVersion": 1,
            "format": "backend-capability-profile",
            "name": "candidate-mini",
            "label": "Candidate Mini",
            "styles": {
                "background": "paint",
                "borderStyle": "ignored",
                "padding": "layout",
            },
            "widgets": {
                "Button": "control",
                "Text": "text",
                "VStack": "container",
            },
            "inputs": {
                "click": "supported",
                "gesture": "deferred",
            },
            "rendererBoundaries": {
                "paint": "supported",
                "raster": "deferred",
                "renderTreeLayout": "supported",
            },
        }
    )

    assert profile.name == "candidate-mini"
    assert profile.style("padding") == "layout"
    assert profile.widget("Hero") == "fallback-container"
    assert profile.input("gesture") == "deferred"
    assert profile.renderer_boundary("raster") == "deferred"
    assert profile.coverage_declaration() == {
        "schemaVersion": 1,
        "format": "backend-coverage-declaration",
        "backend": "candidate-mini",
        "source": {
            "kind": "backendCapabilityProfile",
            "name": "candidate-mini",
        },
        "covers": {
            "widgets": ["Button", "Text", "VStack"],
            "inputs": ["click"],
            "rendererBoundaries": ["paint", "renderTreeLayout"],
            "styles": ["background", "padding"],
            "declaredStyleOmissions": ["borderStyle"],
        },
    }


def test_load_backend_capability_profile_rejects_invalid_support_value(tmp_path):
    profile_path = tmp_path / "backend-profile.json"
    profile_path.write_text(
        '{'
        '"schemaVersion": 1,'
        '"format": "backend-capability-profile",'
        '"name": "bad",'
        '"label": "Bad",'
        '"styles": {"padding": "magic"},'
        '"widgets": {},'
        '"inputs": {}'
        '}',
        encoding="utf-8",
    )

    with pytest.raises(
        CapabilityProfileError,
        match="styles.padding must be one of",
    ):
        load_backend_capability_profile(profile_path)


def test_backend_capability_profile_rejects_null_renderer_boundaries():
    with pytest.raises(
        CapabilityProfileError,
        match="rendererBoundaries must be an object",
    ):
        backend_capability_profile_from_dict(
            {
                "schemaVersion": 1,
                "format": "backend-capability-profile",
                "name": "bad-boundary",
                "label": "Bad Boundary",
                "styles": {},
                "widgets": {},
                "inputs": {},
                "rendererBoundaries": None,
            }
        )


def test_native_style_matrix_matches_layout_acceptance_behavior():
    sheet = css(
        """
        .box {
          align-items: center;
          background: #ffffff;
          border-color: #d0d7de;
          border-radius: 4;
          border-style: solid;
          border-width: 1;
          color: #111827;
          display: flex;
          font-size: 16;
          font-weight: 700;
          gap: 4;
          height: 80;
          justify-content: center;
          margin: 10;
          max-height: 100;
          max-width: 220;
          min-height: 40;
          min-width: 120;
          opacity: 0.9;
          padding: 8;
          width: 180;
        }
        """
    )

    layout = layout_native(
        mount(HStack(Text("Matrix"), className="box")),
        stylesheet=sheet,
    )
    style = dict(layout.root.style)

    assert style["alignItems"] == "center"
    assert style["justifyContent"] == "center"
    assert style["borderStyle"] == "solid"
    assert style["margin"].value == 10
    assert layout.root.width == 180
    assert layout.root.height == 80
    assert layout.by_path((0,)).x > 8
    assert layout.by_path((0,)).y > 8

    unsupported_sheet = StyleSheet(
        rules={".box": StyleRule(".box", {"lineHeight": 20})},
        tokens={},
    )
    with pytest.raises(NativeLayoutError, match="Unsupported native style properties"):
        layout_native(mount(VStack(Text("Nope"), className="box")), stylesheet=unsupported_sheet)


def test_native_widget_support_matrix_is_complete_and_categorized():
    assert NATIVE_TEXT_WIDGETS == EXPECTED_TEXT_WIDGETS
    assert NATIVE_CONTROL_WIDGETS == EXPECTED_CONTROL_WIDGETS
    assert NATIVE_CONTAINER_WIDGETS == EXPECTED_CONTAINER_WIDGETS
    assert set(NATIVE_WIDGET_SUPPORT) == (
        EXPECTED_TEXT_WIDGETS | EXPECTED_CONTROL_WIDGETS | EXPECTED_CONTAINER_WIDGETS
    )

    for name in EXPECTED_TEXT_WIDGETS:
        assert native_widget_support(name) == "text"
    for name in EXPECTED_CONTROL_WIDGETS:
        assert native_widget_support(name) == "control"
    for name in EXPECTED_CONTAINER_WIDGETS:
        assert native_widget_support(name) == "container"
    assert native_widget_support("Hero") == "fallback-container"


def test_native_widget_matrix_matches_layout_fallback_behavior():
    class Hero(Widget):
        props = {"className"}

    layout = layout_native(mount(Hero(HStack(Text("Launch")), className="hero")))

    assert layout.root.name == "Hero"
    assert layout.root.children[0].name == "HStack"
    assert layout.root.children[0].children[0].text == "Launch"

    controls = layout_native(mount(HStack(Button("Run", onClick=lambda: None), Input(value=""))))
    assert controls.by_path((0,)).events == ("onClick",)
    assert controls.by_path((1,)).name == "Input"


def test_native_input_support_matrix_is_complete_and_categorized():
    assert set(NATIVE_INPUT_SUPPORT) == EXPECTED_SUPPORTED_INPUT | EXPECTED_DEFERRED_INPUT

    for name in EXPECTED_SUPPORTED_INPUT:
        assert native_input_support(name) == "supported"
    for name in EXPECTED_DEFERRED_INPUT:
        assert native_input_support(name) == "deferred"
    assert native_input_support("pinch") is None


def test_native_support_matrix_is_reflected_in_renderer_spike_doc():
    doc = Path("NATIVE_RENDERER_SPIKE.md").read_text(encoding="utf-8")

    for name in EXPECTED_LAYOUT_ONLY_STYLES | EXPECTED_LAYOUT_AND_PAINT_STYLES:
        assert f"`{name}`" in doc
    for name in EXPECTED_PAINT_ONLY_STYLES | EXPECTED_LAYOUT_AND_PAINT_STYLES:
        assert f"`{name}`" in doc
    for name in EXPECTED_IGNORED_STYLES:
        assert f"`{name}`" in doc
    for name in EXPECTED_SUPPORTED_INPUT | EXPECTED_DEFERRED_INPUT:
        assert f"`{name}`" in doc
    for name in EXPECTED_TEXT_WIDGETS | EXPECTED_CONTROL_WIDGETS | EXPECTED_CONTAINER_WIDGETS:
        assert f"`{name}`" in doc
    assert "`Hero`" in doc
    assert "`lineHeight`" in doc
    assert "`native-python`" in doc
    assert "`otoe plan --backend native-python`" in doc


def test_native_renderer_spike_documents_executable_acceptance_surfaces():
    doc = Path("NATIVE_RENDERER_SPIKE.md").read_text(encoding="utf-8")
    single_spaced = " ".join(doc.split())

    assert "## Executable Acceptance Surfaces" in doc
    assert "`tests/test_native_support_matrix.py`" in doc
    assert "`tests/test_native_layout.py`" in doc
    assert "`tests/test_native_backend_contract.py`" in doc
    assert "`tests/test_native_renderer_backend.py`" in doc
    assert "`examples/native/backend_candidate_skeleton.py`" in doc
    assert "`HeadlessCandidateBackend`" in doc
    assert "`RecordingRendererCandidate`" in doc
    assert "`RasterOnlyRendererCandidate`" in doc
    assert "`PaintOnlyRendererCandidate`" in doc
    assert "`LayoutOnlyRendererCandidate`" in doc
    assert "`ComposedNativeRendererBackend`" in doc
    assert "`NativeLayoutBackend`" in doc
    assert "`NativePaintBackend`" in doc
    assert "`NativeRasterBackend`" in doc
    assert "static task-board layout acceptance" in single_spaced
    assert "interactive task-board replay" in single_spaced
    assert "`run_composed_renderer_candidate_acceptance(...)`" in doc
    assert "`--composed-renderer-contract-json`" in doc
    assert "`--compact-contract`" in doc
    assert "stable `sha256:` hashes" in doc
    assert "`run_style_ops_candidate_acceptance(...)`" in doc
    assert "`--style-ops-contract-json`" in doc
    assert "`--style-artifact`" in doc
    assert "`styleOps` artifact" in doc
    assert "support categories" in doc
    assert "examples/native/contracts/style_ops_expected.json" in doc
    assert "not in hardware runtime" in single_spaced
    assert "`tests/test_native_window.py`" in doc
    assert "`tests/test_native_phase3_closeout.py`" in doc
    assert "minimal backend harness" in doc
    assert "app-shaped native task board replay" in single_spaced
    assert "fake adapter replay through `run_native(...)`" in doc
    assert "records `layout`, `paint`, and `write_png` calls" in single_spaced
    assert "schema-versioned JSON contract snapshot" in doc
    assert "A backend candidate must reproduce" in doc
    assert "Tk is optional, local, and non-production" in single_spaced


def test_native_workflows_documents_backend_candidate_replay_bar():
    doc = Path("NATIVE_WORKFLOWS.md").read_text(encoding="utf-8")
    single_spaced = " ".join(doc.split())

    assert "The current backend-candidate acceptance bar has three replay surfaces" in doc
    assert "BACKEND_CANDIDATE_GUIDE.md" in doc
    assert "the minimal harness in `tests/test_native_backend_contract.py`" in doc
    assert "the app-shaped native task board replay" in doc
    assert "the fake adapter replay through `run_native(...)`" in doc
    assert "`examples/native/backend_candidate_skeleton.py`" in doc
    assert "`HeadlessCandidateBackend`" in doc
    assert "`RecordingRendererCandidate`" in doc
    assert "`RasterOnlyRendererCandidate`" in doc
    assert "`PaintOnlyRendererCandidate`" in doc
    assert "`LayoutOnlyRendererCandidate`" in doc
    assert "`ComposedNativeRendererBackend`" in doc
    assert "`run_renderer_candidate_acceptance()`" in doc
    assert "`renderer_contract_snapshot_to_dict(...)`" in doc
    assert "`--renderer-contract-json`" in doc
    assert "static task-board layout acceptance" in doc
    assert "interactive task-board replay" in single_spaced
    assert "`run_composed_renderer_candidate_acceptance(...)`" in doc
    assert "`--composed-renderer-contract-json`" in doc
    assert "`--composed-renderer-png`" in doc
    assert "`--compact-contract`" in doc
    assert "`run_style_ops_candidate_acceptance(...)`" in doc
    assert "`--style-ops-contract-json`" in doc
    assert "`--style-artifact`" in doc
    assert "`styleOps` artifact" in doc
    assert "omitted operations" in doc
    assert "support categories" in doc
    assert "examples/native/contracts/style_ops_expected.json" in doc
    assert "`--contract-out`" in doc
    assert "otoe compare-contract" in doc
    assert "`--ignore-path`" in doc
    assert "examples/native/contracts/composed_renderer_compact_expected.json" in doc
    assert "JSON-pointer paths" in doc
    assert "signature-and-hash contract" in doc
    assert "PNG smoke" in doc
    assert "small acceptance report" in doc
    assert (
        "layout, paint, focus, frame, renderer-backend, and visible-text summaries"
        in single_spaced
    )


def test_backend_candidate_guide_documents_graduation_path():
    doc = Path("BACKEND_CANDIDATE_GUIDE.md").read_text(encoding="utf-8")
    readme = Path("README.md").read_text(encoding="utf-8")
    single_spaced = " ".join(doc.split())

    assert "## Ground Rules" in doc
    assert "## Acceptance Path" in doc
    assert "## Core Commands" in doc
    assert "## Capability Profile Contract" in doc
    assert "## Graduation Criteria" in doc
    assert "Hardware runtimes must not install dependencies" in doc
    assert "Raw CSS is an authoring/build input" in doc
    assert "Tk is a local manual smoke adapter only" in doc
    assert "`backend-profile.json`" in doc
    assert "`backend-readiness.json`" in doc
    assert "`otoe-styles.json`" in doc
    assert "`otoe-backend-coverage.json`" in doc
    assert "`tests/test_native_backend_contract.py`" in doc
    assert "app-shaped native task board replay" in doc
    assert "fake adapter replay through `run_native(...)`" in doc
    assert "`NativeBackendAdapter`" in doc
    assert "`NativeWindowDriver`" in doc
    assert "`tests/test_native_renderer_backend.py`" in doc
    assert "`--backend-readiness-json`" in doc
    assert "`--style-ops-contract-json`" in doc
    assert "`--composed-renderer-contract-json`" in doc
    assert "python -m otoe backend-profile --backend-capability-profile" in doc
    assert "python -m otoe backend-coverage --requirements" in doc
    assert "python -m otoe build app:app --profile cage" in doc
    assert "python -m otoe style-ir dist/cage/otoe-styles.json --strict" in doc
    assert "python -m otoe pack dist/cage --out dist/cage.tar.gz" in doc
    assert '"format": "backend-capability-profile"' in doc
    assert "`declaredStyleOmissions`" in doc
    assert "not as a built-in backend profile" in single_spaced
    assert "BACKEND_CANDIDATE_GUIDE.md" in readme
    assert "python -m examples.native.backend_candidate_skeleton" in doc
    assert "python -m examples.native.backend_candidate_skeleton --json" in doc
    assert (
        "python -m examples.native.backend_candidate_skeleton --renderer-contract-json"
        in doc
    )
    assert (
        "python -m examples.native.backend_candidate_skeleton --style-ops-contract-json"
        in doc
    )
    assert (
        "python -m otoe compare-contract examples/native/contracts/style_ops_expected.json"
        in doc
    )
    assert "renderer-candidate replay" in doc
    assert "`tests/test_native_support_matrix.py` keeps `NATIVE_RENDERER_SPIKE.md`" in doc
    assert "supported style, widget, input, fallback, ignored, and deferred" in doc
