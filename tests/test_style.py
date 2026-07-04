import pytest

from otoe import (
    Size,
    StyleRule,
    StyleSheet,
    StyleSyntaxError,
    Token,
    UnknownStyleClassError,
    css,
)


def test_css_parses_class_rules_and_tokens():
    sheet = css(
        """
        .card {
          padding: 16px;
          border-radius: 8px;
          background: panel;
        }
        .primary {
          background: accent;
          color: white;
          font-weight: 800;
        }
        """
    )

    assert sheet.resolve("card primary") == {
        "padding": Size(16),
        "borderRadius": Size(8),
        "background": Token("accent"),
        "color": "white",
        "fontWeight": 800,
    }


def test_css_generates_html_inline_styles_with_tokens():
    sheet = css(
        """
        .card {
          padding: 12;
          border-radius: 8;
          background: panel;
        }
        """,
        tokens={"panel": "#ffffff"},
    )

    assert sheet.inline_style("card") == (
        "padding:12px;border-radius:8px;background:#ffffff"
    )


def test_inline_style_rejects_non_html_style_properties_without_keyerror():
    sheet = StyleSheet(
        rules={".scroll": StyleRule(".scroll", {"scrollY": Size(12)})},
        tokens={},
    )

    with pytest.raises(
        StyleSyntaxError,
        match="Style property 'scrollY' cannot be rendered as HTML",
    ):
        sheet.inline_style("scroll")


def test_css_resolves_direct_token_to_html_value():
    sheet = css(
        ".button { background: accent; }",
        tokens={"accent": "#2563eb"},
    )

    assert sheet.resolve("button") == {"background": Token("accent")}
    assert sheet.inline_style("button") == "background:#2563eb"


def test_css_unknown_token_falls_back_to_css_custom_property():
    sheet = css(".button { background: missing; }")

    assert sheet.inline_style("button") == "background:var(--missing)"


def test_css_rejects_cyclic_tokens_with_clear_error():
    sheet = css(
        ".button { background: first; }",
        tokens={"first": Token("second"), "second": Token("first")},
    )

    with pytest.raises(
        StyleSyntaxError,
        match="Cyclic style token reference: first -> second -> first",
    ):
        sheet.inline_style("button")


def test_css_parses_portable_text_overflow_styles():
    sheet = css(
        """
        .truncate {
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }
        """
    )

    assert sheet.resolve("truncate") == {
        "overflow": "hidden",
        "textOverflow": "ellipsis",
        "whiteSpace": "nowrap",
    }
    assert sheet.inline_style("truncate") == (
        "overflow:hidden;text-overflow:ellipsis;white-space:nowrap"
    )


def test_css_validates_opacity_values():
    with pytest.raises(
        StyleSyntaxError,
        match="Invalid value 'banana' for style property 'opacity'",
    ):
        css(".fade { opacity: banana; }")

    sheet = css(".fade { opacity: 0.5; }")

    assert sheet.resolve("fade") == {"opacity": 0.5}


def test_css_validates_alignment_keywords():
    with pytest.raises(
        StyleSyntaxError,
        match="Invalid value 'diagonal' for style property 'align-items'",
    ):
        css(".row { align-items: diagonal; }")

    sheet = css(".row { align-items: center; justify-content: space-between; }")

    assert sheet.resolve("row") == {
        "alignItems": "center",
        "justifyContent": "space-between",
    }


def test_css_validates_overflow_keywords():
    with pytest.raises(
        StyleSyntaxError,
        match="Invalid value 'scrollplease' for style property 'overflow'",
    ):
        css(".scroll { overflow: scrollplease; }")

    for value in ("hidden", "auto", "scroll", "visible"):
        sheet = css(f".scroll {{ overflow: {value}; }}")
        assert sheet.resolve("scroll") == {"overflow": value}


def test_css_validates_simple_width_height_dimensions():
    with pytest.raises(
        StyleSyntaxError,
        match="Invalid value 'wide' for style property 'width'",
    ):
        css(".box { width: wide; }")

    sheet = css(".box { width: 320px; height: 50%; }")

    assert sheet.resolve("box") == {"width": Size(320), "height": Size(50, "%")}


def test_css_validates_remaining_dimension_values():
    invalid_sources = {
        "padding": ".box { padding: chunky; }",
        "gap": ".box { gap: loose; }",
        "border-radius": ".box { border-radius: round; }",
        "border-width": ".box { border-width: thickish; }",
        "font-size": ".box { font-size: huge; }",
        "margin": ".box { margin: outside; }",
        "min-width": ".box { min-width: narrow; }",
        "max-height": ".box { max-height: tall; }",
    }
    for css_name, source in invalid_sources.items():
        with pytest.raises(
            StyleSyntaxError,
            match=rf"Invalid value .* for style property '{css_name}'",
        ):
            css(source)

    sheet = css(
        """
        .box {
          padding: 8;
          gap: 4px;
          border-radius: 6px;
          border-width: 1;
          font-size: 13px;
          margin: auto;
          min-width: 0;
          max-height: 50%;
        }
        """
    )

    assert sheet.resolve("box") == {
        "padding": Size(8),
        "gap": Size(4),
        "borderRadius": Size(6),
        "borderWidth": Size(1),
        "fontSize": Size(13),
        "margin": "auto",
        "minWidth": Size(0),
        "maxHeight": Size(50, "%"),
    }


def test_css_validates_color_tokens_and_literals():
    with pytest.raises(
        StyleSyntaxError,
        match="Invalid value 'url\\(bad\\)' for style property 'color'",
    ):
        css(".text { color: url(bad); }")

    sheet = css(
        ".text { color: red; background: panel; border-color: white; }"
    )

    assert sheet.resolve("text") == {
        "color": "red",
        "background": Token("panel"),
        "borderColor": "white",
    }


def test_css_validates_border_color_tokens_and_literals():
    with pytest.raises(
        StyleSyntaxError,
        match="Invalid value 'url\\(bad\\)' for style property 'border-color'",
    ):
        css(".box { border-color: url(bad); }")

    sheet = css(".box { border-color: line; }", tokens={"line": "#dfe5ee"})

    assert sheet.resolve("box") == {"borderColor": Token("line")}
    assert sheet.inline_style("box") == "border-color:#dfe5ee"


def test_css_validates_font_weight_numbers_and_keywords():
    for source in (
        ".text { font-weight: banana; }",
        ".text { font-weight: 1001; }",
        ".text { font-weight: 12.5; }",
    ):
        with pytest.raises(
            StyleSyntaxError,
            match="Invalid value .* for style property 'font-weight'",
        ):
            css(source)

    sheet = css(
        ".text { font-weight: 760; }\n"
        ".strong { font-weight: bold; }\n"
        ".plain { font-weight: normal; }"
    )

    assert sheet.resolve("text") == {"fontWeight": 760}
    assert sheet.resolve("strong") == {"fontWeight": "bold"}
    assert sheet.resolve("plain") == {"fontWeight": "normal"}


def test_css_validates_text_and_border_keywords():
    invalid_sources = {
        "border-style": ".box { border-style: sparkly; }",
        "text-overflow": ".box { text-overflow: fade; }",
        "white-space": ".box { white-space: sideways; }",
    }
    for css_name, source in invalid_sources.items():
        with pytest.raises(
            StyleSyntaxError,
            match=rf"Invalid value .* for style property '{css_name}'",
        ):
            css(source)

    sheet = css(
        """
        .box {
          border-style: dashed;
          text-overflow: clip;
          white-space: pre-wrap;
        }
        """
    )

    assert sheet.resolve("box") == {
        "borderStyle": "dashed",
        "textOverflow": "clip",
        "whiteSpace": "pre-wrap",
    }


def test_css_rejects_unknown_properties_and_selectors():
    with pytest.raises(StyleSyntaxError) as excinfo:
        css(".card { unknown-prop: 1; }")
    message = str(excinfo.value)
    assert "Unknown style property 'unknown-prop'." in message
    assert "Known portable properties:" in message
    assert "background" in message
    assert "padding" in message

    with pytest.raises(StyleSyntaxError, match="Only single class selectors"):
        css("Button { padding: 8; }")


def test_css_rejects_compound_selectors():
    with pytest.raises(StyleSyntaxError, match="Only single class selectors"):
        css(".card.primary { padding: 8; }")

    with pytest.raises(StyleSyntaxError, match="Only single class selectors"):
        css(".card, .panel { padding: 8; }")


def test_css_rejects_unexpected_content_outside_rules():
    with pytest.raises(StyleSyntaxError, match="Unexpected style content"):
        css(".card { padding: 8; } trailing")


def test_css_resolve_rejects_unknown_classes_in_strict_mode():
    sheet = css(".card { padding: 8; }\n.panel { gap: 4; }")

    with pytest.raises(UnknownStyleClassError) as excinfo:
        sheet.resolve("card missing")
    message = str(excinfo.value)
    assert "Unknown style class 'missing'." in message
    assert "Known classes: card, panel." in message

    assert sheet.resolve("card missing", strict=False) == {"padding": Size(8)}
