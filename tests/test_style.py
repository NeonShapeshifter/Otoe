import pytest

from otoe import (
    Size,
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
        "color": Token("white"),
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


def test_css_rejects_unknown_properties_and_selectors():
    with pytest.raises(StyleSyntaxError, match="Unknown style property"):
        css(".card { unknown-prop: 1; }")

    with pytest.raises(StyleSyntaxError, match="Only single class selectors"):
        css("Button { padding: 8; }")


def test_css_resolve_rejects_unknown_classes_in_strict_mode():
    sheet = css(".card { padding: 8; }")

    with pytest.raises(UnknownStyleClassError, match="missing"):
        sheet.resolve("card missing")

    assert sheet.resolve("card missing", strict=False) == {"padding": Size(8)}
