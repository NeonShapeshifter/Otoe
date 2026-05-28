from otoe import (
    Size,
    Text,
    Token,
    VStack,
    layout_native,
    mount,
    render_html,
    utility_css,
    utility_stylesheet,
)


def test_utility_css_exports_tokens_and_low_level_classes():
    stylesheet = utility_css()

    assert "--otoe-panel: #ffffff;" in stylesheet
    assert ".p-4 {\n  padding: 16px;\n}" in stylesheet
    assert ".bg-panel {\n  background: var(--otoe-panel);\n}" in stylesheet
    assert ".flex-1 {\n  flex: 1 1 0%;\n}" in stylesheet
    assert ".min-h-screen {\n  min-height: 100vh;\n}" in stylesheet
    assert ".max-w-7xl {\n  max-width: 1280px;\n}" in stylesheet
    assert ".rounded-md {\n  border-radius: 8px;\n}" in stylesheet
    assert ".shadow-sm {\n  box-shadow: 0 8px 20px rgba(23, 32, 51, 0.08);\n}" in stylesheet


def test_utility_stylesheet_resolves_portable_subset_for_html_and_native():
    styles = utility_stylesheet()
    mounted = mount(
        VStack(
            Text("Queue", className="text-muted text-sm font-bold"),
            className="p-4 gap-2 bg-panel rounded-md border",
        )
    )

    html = render_html(mounted, stylesheet=styles)

    assert (
        'style="padding:16px;gap:8px;background:#ffffff;'
        'border-radius:8px;border-width:1px;'
        'border-style:solid;border-color:#dfe5ee"'
    ) in html
    assert 'style="color:#607086;font-size:13px;font-weight:760"' in html

    layout = layout_native(mounted, stylesheet=styles)
    root_style = dict(layout.root.style)

    assert root_style["padding"] == Size(16)
    assert root_style["gap"] == Size(8)
    assert root_style["background"] == "#ffffff"
    assert root_style["borderRadius"] == Size(8)
    assert root_style["borderWidth"] == Size(1)
    assert root_style["borderColor"] == "#dfe5ee"
    assert dict(layout.by_path((0,)).style)["color"] == "#607086"


def test_utility_stylesheet_keeps_html_only_utilities_strict_checkable():
    styles = utility_stylesheet(tokens={"panel": "#fafafa"})

    assert styles.resolve("flex flex-col flex-1 mx-auto px-4 shadow-sm truncate", strict=True) == {
        "display": "flex"
    }
    assert styles.resolve("w-80 max-w-7xl", strict=True) == {
        "width": Size(320),
        "maxWidth": Size(1280),
    }
    assert styles.resolve("bg-panel", strict=True) == {
        "background": Token("otoe-panel")
    }
    assert styles.inline_style("bg-panel") == "background:#fafafa"


def test_utility_layer_generates_classes_for_custom_tokens():
    assert ".bg-brand" in utility_css(tokens={"brand": "#123456"})

    styles = utility_stylesheet(tokens={"brand": "#123456"})

    assert styles.inline_style("bg-brand text-brand") == (
        "background:#123456;color:#123456"
    )
