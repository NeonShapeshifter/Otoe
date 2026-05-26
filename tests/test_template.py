import pytest

from otoe import (
    Button,
    HStack,
    TemplateError,
    Text,
    VStack,
    mount,
    root_widget,
    signal,
    template,
)


def test_template_builds_same_node_tree_as_python_components():
    on_click = lambda: None

    from_template = template(
        """
        <VStack className="screen" gap="12">
          <Text className="title">Dashboard</Text>
          <Button className="primary" onClick="{on_click}">Save</Button>
        </VStack>
        """,
        scope={"on_click": on_click},
    )
    from_python = VStack(
        Text("Dashboard", className="title"),
        Button("Save", className="primary", onClick=on_click),
        className="screen",
        gap=12,
    )

    assert from_template == from_python


def test_template_supports_scope_values_as_props_and_text():
    title = signal("Pipeline")
    mounted = mount(
        template(
            """
            <HStack className="header">
              <Text className="title">{title}</Text>
            </HStack>
            """,
            scope={"title": title},
        )
    )
    root = root_widget(mounted)

    assert root.children[0].props["content"] == "Pipeline"

    title.set("Revenue")

    assert root.children[0].props["content"] == "Revenue"


def test_template_supports_custom_tags():
    node = template(
        "<Hero className=\"hero\">Launch</Hero>",
        tags={"Hero": Text},
    )

    assert node == Text("Launch", className="hero")


def test_template_rejects_unknown_tags_and_expressions():
    with pytest.raises(TemplateError, match="Unknown template tag"):
        template("<Unknown />")

    with pytest.raises(TemplateError, match="Unknown template expression"):
        template("<Text>{missing}</Text>")


def test_template_rejects_implicit_primary_content_mixed_with_child_nodes():
    with pytest.raises(TemplateError, match="cannot mix primary content"):
        template("<Button>Save <Text>now</Text></Button>")


def test_template_allows_explicit_primary_prop_with_child_nodes():
    node = template('<Button label="Save"><Text>now</Text></Button>')

    assert node == Button("Save", Text("now"))
