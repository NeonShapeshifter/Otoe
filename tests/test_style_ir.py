import pytest

from otoe import Text, VStack, css, layout_native, mount, render_html
from otoe.plan import plan_mounted, plan_to_dict
from otoe.style import StyleSyntaxError, stylesheet_from_artifact
from otoe.style_ir import compiled_styles_to_dict
from otoe.style_ops import (
    STYLE_IR_SCHEMA_VERSION,
    STYLE_OPS_FORMAT,
    STYLE_OPS_SCHEMA_VERSION,
    StyleIRError,
    apply_style_ops,
    expected_omitted_style_ops,
    load_style_ir,
    replay_style_ops_direct,
    replay_style_ops_class,
    style_ops_support_map,
    validate_style_ops,
)


def test_style_ir_resolves_portable_tokens_before_bundle_runtime():
    stylesheet = css(
        ".shell { padding: 8; background: panel; width: 50%; border-style: solid; }\n",
        tokens={"panel": "#f8fafc"},
    )
    mounted = mount(VStack(Text("Ready"), className="shell"))
    plan = plan_mounted(mounted, stylesheet=stylesheet)

    payload = compiled_styles_to_dict(
        plan,
        target="app:app",
        stylesheet=stylesheet,
    )
    shell_rule = payload["rules"][0]
    shell_ops = payload["styleOps"]["classes"][0]

    assert payload["schemaVersion"] == STYLE_IR_SCHEMA_VERSION
    assert payload["styleOps"]["schemaVersion"] == STYLE_OPS_SCHEMA_VERSION
    assert payload["styleOps"]["format"] == STYLE_OPS_FORMAT
    assert payload["backendCapabilities"]["name"] == "native-python"
    assert shell_rule["declarations"]["background"] == {
        "type": "literal",
        "value": "#f8fafc",
    }
    assert {
        "op": "setStyle",
        "property": "background",
        "support": "paint",
        "value": {"type": "literal", "value": "#f8fafc"},
    } in shell_ops["ops"]
    assert {
        "property": "width",
        "status": "deferred",
        "value": {"type": "size", "value": 50, "unit": "%"},
        "message": "property 'width' uses non-px dimension '%'",
    } in shell_rule["omittedDeclarations"]
    assert {
        "op": "omitStyle",
        "property": "borderStyle",
        "support": "ignored",
        "status": "html-only",
        "value": {"type": "literal", "value": "solid"},
        "message": "property 'borderStyle' is accepted but ignored by native",
    } in shell_ops["omittedOps"]


def test_style_ir_keeps_static_and_safelisted_classes_in_deterministic_order():
    stylesheet = css(
        ".used { color: #111827; }\n"
        ".static { color: #123456; }\n"
        ".safe { color: #654321; }\n"
    )
    mounted = mount(Text("State", className="used"))
    plan = plan_mounted(
        mounted,
        stylesheet=stylesheet,
        static_classes=("static",),
        safelist=("safe",),
    )

    payload = compiled_styles_to_dict(
        plan,
        target="app:app",
        stylesheet=stylesheet,
    )

    assert payload["classes"] == {
        "used": ["used"],
        "static": ["static"],
        "safelisted": ["safe"],
        "planned": ["used", "static", "safe"],
        "htmlOnly": [],
        "invalid": [],
    }
    assert [
        rule["className"]
        for rule in payload["rules"]
    ] == ["used", "static", "safe"]
    assert [
        entry["className"]
        for entry in payload["styleOps"]["classes"]
    ] == ["used", "static", "safe"]


def test_style_ir_rehydrates_native_runtime_stylesheet_from_resolved_rules():
    stylesheet = css(
        ".title { color: ink; font-size: 18px; }\n",
        tokens={"ink": "#111827"},
    )
    mounted = mount(Text("Title", className="title"))
    plan = plan_mounted(mounted, stylesheet=stylesheet)
    payload = compiled_styles_to_dict(
        plan,
        target="app:app",
        stylesheet=stylesheet,
    )

    runtime_stylesheet = stylesheet_from_artifact(payload)

    assert runtime_stylesheet.tokens == {"ink": "#111827"}
    assert runtime_stylesheet.resolve("title") == {
        "color": "#111827",
        "fontSize": stylesheet.resolve("title")["fontSize"],
    }


def test_style_ir_keeps_html_source_styles_and_native_resolved_ir_separate():
    stylesheet = css(
        ".shell { padding: 8; background: panel; border-style: solid; color: #111827; }\n",
        tokens={"panel": "#f8fafc"},
    )
    mounted = mount(VStack(Text("Boundary"), className="shell"))
    plan = plan_mounted(mounted, stylesheet=stylesheet)
    payload = compiled_styles_to_dict(
        plan,
        target="app:app",
        stylesheet=stylesheet,
    )

    html = render_html(mounted, stylesheet=stylesheet)
    runtime_stylesheet = stylesheet_from_artifact(payload)
    source_layout = layout_native(mounted, stylesheet=stylesheet)
    runtime_layout = layout_native(mounted, stylesheet=runtime_stylesheet)
    source_style = dict(source_layout.root.style)
    runtime_style = dict(runtime_layout.root.style)

    assert "border-style:solid" in html
    assert runtime_stylesheet.inline_style("shell") == (
        "padding:8px;background:#f8fafc;color:#111827"
    )
    assert source_style["borderStyle"] == "solid"
    assert "borderStyle" not in runtime_style
    assert {
        property_name: source_style[property_name]
        for property_name in runtime_style
    } == runtime_style
    assert runtime_style["background"] == "#f8fafc"


def test_style_ir_replays_low_level_style_ops_without_source_css():
    stylesheet = css(
        ".shell { padding: 8; width: 50%; border-style: solid; color: #111827; }\n"
    )
    mounted = mount(VStack(Text("Ops"), className="shell"))
    plan = plan_mounted(mounted, stylesheet=stylesheet)
    payload = compiled_styles_to_dict(
        plan,
        target="app:app",
        stylesheet=stylesheet,
    )
    style_ops = payload["styleOps"]
    shell_rule = payload["rules"][0]
    shell_ops = style_ops["classes"][0]

    replay = replay_style_ops_class(
        shell_ops,
        style_support=style_ops_support_map(style_ops),
    )

    assert replay.errors == ()
    assert replay.class_name == "shell"
    assert replay.missing is False
    assert replay.applied_declarations == shell_rule["declarations"]
    assert replay.applied_declarations == {
        "padding": {"type": "size", "value": 8, "unit": "px"},
        "color": {"type": "literal", "value": "#111827"},
    }
    assert replay.omitted_ops == expected_omitted_style_ops(
        shell_rule,
        style_ops_support_map(style_ops),
    )


def test_style_ir_compiles_direct_styles_by_widget_path():
    mounted = mount(
        VStack(
            Text("Direct", color="#dc2626"),
            gap=4,
            padding=8,
        )
    )
    plan = plan_mounted(mounted, stylesheet=None)
    payload = compiled_styles_to_dict(
        plan,
        target="app:app",
        stylesheet=None,
    )
    plan_payload = plan_to_dict(plan, target="app:app")
    direct_styles = payload["directStyles"]
    direct_ops = payload["styleOps"]["directStyles"]

    assert payload["directStyleCounts"]["portable"] == 3
    assert [entry["path"] for entry in plan_payload["directStyles"]] == [[], [0]]
    assert plan_payload["directStyles"][0]["declarations"]["gap"] == {
        "type": "literal",
        "value": 4,
    }
    assert direct_styles == [
        {
            "path": [],
            "widget": "VStack",
            "declarations": {
                "gap": {"type": "size", "value": 4, "unit": "px"},
                "padding": {"type": "size", "value": 8, "unit": "px"},
            },
            "omittedDeclarations": [],
        },
        {
            "path": [0],
            "widget": "Text",
            "declarations": {
                "color": {"type": "literal", "value": "#dc2626"},
            },
            "omittedDeclarations": [],
        },
    ]
    assert direct_ops == [
        {
            "path": [],
            "widget": "VStack",
            "ops": [
                {
                    "op": "setStyle",
                    "property": "gap",
                    "support": "layout",
                    "value": {"type": "size", "value": 4, "unit": "px"},
                },
                {
                    "op": "setStyle",
                    "property": "padding",
                    "support": "layout",
                    "value": {"type": "size", "value": 8, "unit": "px"},
                },
            ],
            "omittedOps": [],
        },
        {
            "path": [0],
            "widget": "Text",
            "ops": [
                {
                    "op": "setStyle",
                    "property": "color",
                    "support": "paint",
                    "value": {"type": "literal", "value": "#dc2626"},
                }
            ],
            "omittedOps": [],
        },
    ]

    replay = replay_style_ops_direct(
        direct_ops[0],
        style_support=style_ops_support_map(payload["styleOps"]),
    )

    assert replay.errors == ()
    assert replay.path == ()
    assert replay.widget == "VStack"
    assert replay.applied_declarations == direct_styles[0]["declarations"]


def test_style_ir_loads_and_applies_artifact_primitives():
    stylesheet = css(".shell { padding: 8; color: #111827; }\n")
    mounted = mount(
        VStack(
            Text("Artifact"),
            className="shell",
            gap=4,
        )
    )
    plan = plan_mounted(mounted, stylesheet=stylesheet)
    payload = compiled_styles_to_dict(
        plan,
        target="app:app",
        stylesheet=stylesheet,
    )

    artifact = load_style_ir(payload)
    applied = apply_style_ops(artifact)

    assert artifact.schema_version == STYLE_IR_SCHEMA_VERSION
    assert artifact.style_ops_schema_version == STYLE_OPS_SCHEMA_VERSION
    assert artifact.style_ops_format == STYLE_OPS_FORMAT
    assert artifact.backend == "native-python"
    assert artifact.rules_by_class["shell"]["declarations"] == {
        "padding": {"type": "size", "value": 8, "unit": "px"},
        "color": {"type": "literal", "value": "#111827"},
    }
    assert artifact.direct_styles_by_path[()]["declarations"] == {
        "gap": {"type": "size", "value": 4, "unit": "px"}
    }
    assert applied.passed is True
    assert applied.classes_by_name["shell"].applied_declarations == (
        artifact.rules_by_class["shell"]["declarations"]
    )
    assert applied.direct_styles_by_path[()].applied_declarations == (
        artifact.direct_styles_by_path[()]["declarations"]
    )


def test_style_ir_validation_detects_drift_from_compiled_rules():
    stylesheet = css(".shell { padding: 8; color: #111827; }\n")
    mounted = mount(VStack(Text("Drift"), className="shell"))
    plan = plan_mounted(mounted, stylesheet=stylesheet)
    payload = compiled_styles_to_dict(
        plan,
        target="app:app",
        stylesheet=stylesheet,
    )
    shell_ops = payload["styleOps"]["classes"][0]
    color_op = next(op for op in shell_ops["ops"] if op["property"] == "color")
    color_op["value"] = {"type": "literal", "value": "#dc2626"}

    applied = apply_style_ops(payload)
    validation = validate_style_ops(payload)

    assert applied.passed is True
    assert validation.passed is False
    assert (
        "styleOps class 'shell' applied declarations do not match compiled rules"
        in validation.errors
    )


def test_style_ir_validation_rejects_invalid_class_value_payloads():
    stylesheet = css(".shell { padding: 8; color: #111827; }\n")
    mounted = mount(VStack(Text("Bad class payload"), className="shell"))
    plan = plan_mounted(mounted, stylesheet=stylesheet)
    payload = compiled_styles_to_dict(
        plan,
        target="app:app",
        stylesheet=stylesheet,
    )
    shell_rule = payload["rules"][0]
    shell_ops = payload["styleOps"]["classes"][0]
    bad_value = {"type": "size", "value": "8", "unit": "px"}
    shell_rule["declarations"]["padding"] = bad_value
    padding_op = next(op for op in shell_ops["ops"] if op["property"] == "padding")
    padding_op["value"] = bad_value

    validation = validate_style_ops(payload)

    assert validation.passed is False
    assert (
        "styleOps class 'shell' op 0 value size value must be int or float"
        in validation.errors
    )
    assert (
        "compiled rule 'shell' declaration 'padding' value size value must be int or float"
        in validation.errors
    )


def test_style_ir_validation_rejects_unresolved_runtime_style_ops():
    stylesheet = css(".shell { color: ink; }\n", tokens={"ink": "#111827"})
    mounted = mount(VStack(Text("Bad runtime payload"), className="shell"))
    plan = plan_mounted(mounted, stylesheet=stylesheet)
    payload = compiled_styles_to_dict(
        plan,
        target="app:app",
        stylesheet=stylesheet,
    )
    shell_rule = payload["rules"][0]
    shell_ops = payload["styleOps"]["classes"][0]
    bad_value = {"type": "token", "name": "ink"}
    shell_rule["declarations"]["color"] = bad_value
    color_op = next(op for op in shell_ops["ops"] if op["property"] == "color")
    color_op["value"] = bad_value

    validation = validate_style_ops(payload)

    assert validation.passed is False
    assert (
        "styleOps class 'shell' op 0 value must be resolved before styleOps runtime"
        in validation.errors
    )
    assert (
        "compiled rule 'shell' declaration 'color' value must be resolved before styleOps runtime"
        in validation.errors
    )


def test_style_ir_validation_rejects_invalid_direct_and_omitted_value_payloads():
    mounted = mount(VStack(Text("Bad direct payload"), padding=8))
    plan = plan_mounted(mounted, stylesheet=None)
    payload = compiled_styles_to_dict(
        plan,
        target="app:app",
        stylesheet=None,
    )
    direct_style = payload["directStyles"][0]
    direct_ops = payload["styleOps"]["directStyles"][0]
    bad_direct_value = {"type": "literal", "value": []}
    direct_style["declarations"]["padding"] = bad_direct_value
    direct_ops["ops"][0]["value"] = bad_direct_value

    validation = validate_style_ops(payload)

    assert validation.passed is False
    assert (
        "styleOps class 'direct style []' op 0 value literal value must be JSON scalar"
        in validation.errors
    )
    assert (
        "compiled directStyles [] declaration 'padding' value literal value must be JSON scalar"
        in validation.errors
    )

    stylesheet = css(".shell { width: 50%; }\n")
    mounted = mount(VStack(Text("Bad omitted payload"), className="shell"))
    plan = plan_mounted(mounted, stylesheet=stylesheet)
    omitted_payload = compiled_styles_to_dict(
        plan,
        target="app:app",
        stylesheet=stylesheet,
    )
    shell_rule = omitted_payload["rules"][0]
    shell_ops = omitted_payload["styleOps"]["classes"][0]
    bad_omitted_value = {"type": "runtime", "valueType": "", "repr": 1}
    shell_rule["omittedDeclarations"][0]["value"] = bad_omitted_value
    shell_ops["omittedOps"][0]["value"] = bad_omitted_value

    omitted_validation = validate_style_ops(omitted_payload)

    assert omitted_validation.passed is False
    assert (
        "styleOps class 'shell' omitted op 0 value runtime valueType must be a non-empty string"
        in omitted_validation.errors
    )
    assert (
        "compiled rule 'shell' omitted declaration 0 value runtime repr must be a string"
        in omitted_validation.errors
    )


def test_stylesheet_from_artifact_rejects_style_ops_drift_by_default():
    stylesheet = css(".shell { padding: 8; color: #111827; }\n")
    mounted = mount(VStack(Text("Drift"), className="shell"))
    plan = plan_mounted(mounted, stylesheet=stylesheet)
    payload = compiled_styles_to_dict(
        plan,
        target="app:app",
        stylesheet=stylesheet,
    )
    shell_ops = payload["styleOps"]["classes"][0]
    color_op = next(op for op in shell_ops["ops"] if op["property"] == "color")
    color_op["value"] = {"type": "literal", "value": "#dc2626"}

    with pytest.raises(
        StyleSyntaxError,
        match="Invalid style artifact: styleOps class 'shell' applied declarations",
    ):
        stylesheet_from_artifact(payload)

    loose_stylesheet = stylesheet_from_artifact(payload, strict=False)

    assert loose_stylesheet.resolve("shell")["color"] == "#111827"


def test_style_ir_loader_rejects_bad_schema_and_shape():
    with pytest.raises(
        StyleIRError,
        match="style artifact: unsupported schemaVersion 2; expected 1",
    ):
        load_style_ir({"schemaVersion": 2})

    with pytest.raises(StyleIRError, match="styleOps classes must be a list"):
        load_style_ir(
            {
                "schemaVersion": 1,
                "styleOps": {
                    "schemaVersion": 1,
                    "format": "otoe-style-ops",
                    "classes": {},
                },
            }
        )


def test_style_ir_keeps_invalid_direct_styles_as_omitted_primitives():
    mounted = mount(VStack(Text("Invalid direct"), padding=-1))
    plan = plan_mounted(mounted, stylesheet=None)
    payload = compiled_styles_to_dict(
        plan,
        target="app:app",
        stylesheet=None,
    )
    direct_style = payload["directStyles"][0]
    direct_ops = payload["styleOps"]["directStyles"][0]

    assert payload["status"] == "invalid"
    assert payload["directStyleCounts"]["invalid"] == 1
    assert direct_style["declarations"] == {}
    assert direct_style["omittedDeclarations"] == [
        {
            "property": "padding",
            "status": "invalid",
            "value": {"type": "literal", "value": -1},
            "message": "property 'padding' uses negative dimension -1",
        }
    ]
    assert direct_ops["ops"] == []
    assert direct_ops["omittedOps"] == [
        {
            "op": "omitStyle",
            "property": "padding",
            "support": "layout",
            "status": "invalid",
            "value": {"type": "literal", "value": -1},
            "message": "property 'padding' uses negative dimension -1",
        }
    ]


def test_style_ir_replay_reports_invalid_primitive_ops():
    replay = replay_style_ops_class(
        {
            "className": "bad",
            "selector": ".bad",
            "missing": False,
            "ops": [
                {
                    "op": "setStyle",
                    "property": "color",
                    "support": "layout",
                    "value": {"type": "literal", "value": "#111827"},
                }
            ],
            "omittedOps": [{"op": "skipStyle", "property": "width"}],
        },
        style_support={"color": "paint", "width": "layout"},
    )

    assert replay.applied_declarations == {
        "color": {"type": "literal", "value": "#111827"}
    }
    assert (
        "styleOps class 'bad' op 0 support 'layout' does not match 'paint'"
        in replay.errors
    )
    assert (
        "styleOps class 'bad' omitted op 0 must use op='omitStyle'"
        in replay.errors
    )
