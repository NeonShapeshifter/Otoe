import json
from dataclasses import replace

from otoe import Button, For, HStack, Show, Text, VStack, css, mount, signal, unmount
from otoe.render_ir import (
    RENDER_TREE_SCHEMA_VERSION,
    RenderIRError,
    RenderNode,
    RenderTree,
    assert_render_tree_valid,
    load_render_tree_artifact,
    render_tree_from_dict,
    render_tree_from_target,
    render_tree_to_dict,
    validate_render_tree,
    walk_render_nodes,
)
from otoe.plan import plan_mounted
from otoe.style import resolved_style_map_from_style_ops_artifact
from otoe.style_ir import compiled_styles_to_dict


def test_render_tree_from_mounted_emits_serializable_resolved_nodes():
    stylesheet = css(
        """
        .shell {
          padding: 12;
          gap: 4;
        }
        .title {
          color: ink;
          font-size: 18;
        }
        """,
        tokens={"ink": "#111827"},
    )
    mounted = mount(
        VStack(
            Text("Hello", className="title", id="headline"),
            Button("Run", onClick=lambda: None, disabled=True),
            className="shell",
            id="root",
        )
    )

    try:
        tree = render_tree_from_target(mounted, stylesheet=stylesheet)
        payload = render_tree_to_dict(tree)
    finally:
        unmount(mounted)

    assert isinstance(tree, RenderTree)
    assert tree.schema_version == RENDER_TREE_SCHEMA_VERSION
    assert validate_render_tree(tree) == []
    assert tree.node_count == 3
    assert payload["format"] == "otoe-render-tree"
    assert payload["root"]["id"] == "root:root"
    assert payload["root"]["style"]["padding"] == {
        "type": "size",
        "value": 12,
        "unit": "px",
    }
    assert payload["root"]["children"][0]["id"] == "root:root/id:headline:Text"
    assert payload["root"]["children"][0]["style"]["color"] == {
        "type": "literal",
        "value": "#111827",
    }
    assert payload["root"]["children"][1]["events"] == ["onClick"]
    assert payload["root"]["children"][1]["state"] == ["disabled"]
    json.dumps(payload, sort_keys=True)


def test_render_tree_from_dict_roundtrips_serialized_tree():
    tree = _minimal_render_tree()
    payload = render_tree_to_dict(tree)

    parsed = render_tree_from_dict(payload)

    assert render_tree_to_dict(parsed) == payload
    assert validate_render_tree(parsed) == []


def test_load_render_tree_artifact_reads_serialized_json(tmp_path):
    payload = render_tree_to_dict(_minimal_render_tree())
    artifact = tmp_path / "render-tree.json"
    artifact.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    parsed = load_render_tree_artifact(artifact)

    assert render_tree_to_dict(parsed) == payload
    assert parsed.node_count == 2


def test_render_tree_from_dict_rejects_invalid_schema_type():
    payload = render_tree_to_dict(_minimal_render_tree())
    payload["schemaVersion"] = "1"

    try:
        render_tree_from_dict(payload)
    except RenderIRError as exc:
        assert str(exc) == "RenderTree schemaVersion must be an integer"
    else:
        raise AssertionError("Expected RenderIRError")


def test_render_tree_from_dict_rejects_boolean_schema_version():
    payload = render_tree_to_dict(_minimal_render_tree())
    payload["schemaVersion"] = True

    try:
        render_tree_from_dict(payload)
    except RenderIRError as exc:
        assert str(exc) == "RenderTree schemaVersion must be an integer"
    else:
        raise AssertionError("Expected RenderIRError")


def test_render_tree_from_dict_rejects_boolean_node_count():
    payload = render_tree_to_dict(_minimal_render_tree())
    payload["nodeCount"] = True

    try:
        render_tree_from_dict(payload)
    except RenderIRError as exc:
        assert str(exc) == "RenderTree nodeCount must be a non-negative integer"
    else:
        raise AssertionError("Expected RenderIRError")


def test_render_tree_from_dict_rejects_boolean_path_item():
    payload = render_tree_to_dict(_minimal_render_tree())
    payload["root"]["children"][0]["path"] = [True]

    try:
        render_tree_from_dict(payload)
    except RenderIRError as exc:
        assert (
            str(exc)
            == "RenderTree root.children[0].path must be a list of non-negative integers"
        )
    else:
        raise AssertionError("Expected RenderIRError")


def test_render_tree_from_dict_rejects_extra_fields():
    payload = render_tree_to_dict(_minimal_render_tree())
    payload["root"]["extra"] = True

    try:
        render_tree_from_dict(payload)
    except RenderIRError as exc:
        assert str(exc) == "RenderTree root has unexpected fields: 'extra'"
    else:
        raise AssertionError("Expected RenderIRError")


def test_render_tree_from_dict_rejects_invalid_child_payload():
    payload = render_tree_to_dict(_minimal_render_tree())
    payload["root"]["children"][0] = "bad-child"

    try:
        render_tree_from_dict(payload)
    except RenderIRError as exc:
        assert str(exc) == "RenderTree root.children[0] must be a JSON object; got str"
    else:
        raise AssertionError("Expected RenderIRError")


def test_render_tree_from_dict_rejects_invalid_style_value():
    payload = render_tree_to_dict(_minimal_render_tree())
    payload["root"]["style"]["width"] = {"type": "mystery"}

    try:
        render_tree_from_dict(payload)
    except RenderIRError as exc:
        assert str(exc) == "RenderTree root.style.width: Unknown serialized style value type 'mystery'."
    else:
        raise AssertionError("Expected RenderIRError")


def test_render_tree_from_dict_rejects_empty_optional_string():
    payload = render_tree_to_dict(_minimal_render_tree())
    payload["root"]["widgetId"] = ""

    try:
        render_tree_from_dict(payload)
    except RenderIRError as exc:
        assert str(exc) == (
            "RenderTree root.widgetId must be a non-empty string or null"
        )
    else:
        raise AssertionError("Expected RenderIRError")


def test_render_tree_from_dict_rejects_empty_event_name():
    payload = render_tree_to_dict(_minimal_render_tree())
    payload["root"]["events"] = [""]

    try:
        render_tree_from_dict(payload)
    except RenderIRError as exc:
        assert str(exc) == "RenderTree root.events must be a list of non-empty strings"
    else:
        raise AssertionError("Expected RenderIRError")


def test_render_tree_from_dict_rejects_duplicate_ids_after_parse():
    payload = render_tree_to_dict(_minimal_render_tree())
    payload["root"]["children"][0]["id"] = "root"

    try:
        render_tree_from_dict(payload)
    except RenderIRError as exc:
        assert str(exc) == "RenderTree node id 'root' is duplicated"
    else:
        raise AssertionError("Expected RenderIRError")


def test_render_tree_validator_rejects_duplicate_node_ids():
    tree = _minimal_render_tree()
    duplicate = replace(
        tree,
        root=replace(
            tree.root,
            children=(replace(tree.root.children[0], node_id=tree.root.node_id),),
        ),
    )

    assert validate_render_tree(duplicate) == [
        "RenderTree node id 'root' is duplicated"
    ]


def test_render_tree_validator_rejects_inconsistent_child_path():
    tree = _minimal_render_tree()
    broken = replace(
        tree,
        root=replace(
            tree.root,
            children=(replace(tree.root.children[0], path=(2,)),),
        ),
    )

    assert validate_render_tree(broken) == [
        "RenderTree node 'child' path must be [0]; got [2]"
    ]


def test_render_tree_validator_rejects_boolean_path_item():
    tree = _minimal_render_tree()
    broken = replace(
        tree,
        root=replace(tree.root, path=(True,)),
    )

    assert validate_render_tree(broken) == [
        "RenderTree node 'root' path must be a tuple of non-negative integers"
    ]


def test_render_tree_validator_rejects_empty_event_name():
    tree = _minimal_render_tree()
    broken = replace(
        tree,
        root=replace(tree.root, events=("",)),
    )

    assert validate_render_tree(broken) == [
        "RenderTree node 'root' events must be a tuple of non-empty strings"
    ]


def test_render_tree_validator_rejects_invalid_child_type():
    tree = _minimal_render_tree()
    broken = replace(tree, root=replace(tree.root, children=("bad-child",)))

    assert validate_render_tree(broken) == [
        "RenderTree node at [0] must be a RenderNode; got str"
    ]


def test_render_tree_validator_rejects_unserializable_style_value():
    tree = _minimal_render_tree()
    broken = replace(
        tree,
        root=replace(tree.root, style=(("width", object()),)),
    )

    errors = validate_render_tree(broken)

    assert len(errors) == 1
    assert errors[0].startswith(
        "RenderTree node 'root' style style 'width' must be JSON serializable"
    )


def test_assert_render_tree_valid_raises_render_ir_error():
    tree = _minimal_render_tree()
    broken = replace(tree, schema_version=0)

    try:
        assert_render_tree_valid(broken)
    except RenderIRError as exc:
        assert "RenderTree schemaVersion must be 1; got 0" in str(exc)
    else:
        raise AssertionError("Expected RenderIRError")


def test_render_tree_validator_rejects_boolean_schema_version():
    tree = _minimal_render_tree()
    broken = replace(tree, schema_version=True)

    assert validate_render_tree(broken) == [
        "RenderTree schemaVersion must be 1; got True"
    ]


def test_render_tree_from_target_normalizes_empty_optional_strings():
    mounted = mount(Button("Run", id="", className=""))

    try:
        tree = render_tree_from_target(mounted)
    finally:
        unmount(mounted)

    assert tree.root.widget_id is None
    assert tree.root.class_name is None
    assert tree.root.node_id == "root:Button"


def test_render_tree_can_resolve_class_styles_from_style_ops_map():
    stylesheet = css(".shell { padding: 12; color: #111827; }\n")
    mounted = mount(VStack(Text("Mapped", className="shell")))
    plan = plan_mounted(mounted, stylesheet=stylesheet)
    payload = compiled_styles_to_dict(
        plan,
        target="app:app",
        stylesheet=stylesheet,
    )
    payload["rules"][0]["declarations"]["color"] = {
        "type": "literal",
        "value": "#dc2626",
    }
    style_map = resolved_style_map_from_style_ops_artifact(payload, strict=False)

    try:
        tree = render_tree_from_target(mounted, style_map=style_map)
        text_node = tree.root.children[0]
    finally:
        unmount(mounted)

    assert text_node.style_dict()["color"] == "#111827"
    assert text_node.style_dict()["padding"] == stylesheet.resolve("shell")["padding"]


def test_render_tree_preserves_for_keys_across_reorder():
    items = signal(
        [
            {"id": "alpha", "label": "Alpha"},
            {"id": "beta", "label": "Beta"},
        ]
    )
    mounted = mount(
        VStack(
            For(
                each=items,
                key=lambda item: item["id"],
                children=lambda item: HStack(Text(item["label"])),
            )
        )
    )

    try:
        before = _ids_by_text(render_tree_from_target(mounted))
        items.set(
            [
                {"id": "beta", "label": "Beta"},
                {"id": "alpha", "label": "Alpha"},
            ]
        )
        after = _ids_by_text(render_tree_from_target(mounted))
    finally:
        unmount(mounted)

    assert before["Alpha"] == after["Alpha"]
    assert before["Beta"] == after["Beta"]
    assert '/key:"alpha":HStack/' in before["Alpha"]
    assert '/key:"beta":HStack/' in before["Beta"]


def test_render_tree_reflects_show_branch_changes():
    visible = signal(False)
    mounted = mount(
        VStack(
            Show(
                Text("Visible"),
                when=visible,
                fallback=Text("Fallback"),
            )
        )
    )

    try:
        before_text = _visible_text(render_tree_from_target(mounted))
        visible.set(True)
        after_text = _visible_text(render_tree_from_target(mounted))
    finally:
        unmount(mounted)

    assert before_text == ["Fallback"]
    assert after_text == ["Visible"]


def _ids_by_text(tree: RenderTree) -> dict[str, str]:
    result = {}
    for node in walk_render_nodes(tree.root):
        props = node.prop_dict()
        content = props.get("content")
        if isinstance(content, str):
            result[content] = node.node_id
    return result


def _visible_text(tree: RenderTree) -> list[str]:
    return [
        props["content"]
        for node in walk_render_nodes(tree.root)
        if isinstance((props := node.prop_dict()).get("content"), str)
    ]


def _minimal_render_tree() -> RenderTree:
    child = RenderNode(
        node_id="child",
        path=(0,),
        name="Text",
        widget_id=None,
        key=None,
        class_name=None,
        props=(("content", "Hello"),),
        events=(),
        state=(),
        context="Text",
        style=(),
        children=(),
    )
    root = RenderNode(
        node_id="root",
        path=(),
        name="VStack",
        widget_id=None,
        key=None,
        class_name=None,
        props=(),
        events=(),
        state=(),
        context="VStack",
        style=(("width", 120),),
        children=(child,),
    )
    return RenderTree(root=root)
