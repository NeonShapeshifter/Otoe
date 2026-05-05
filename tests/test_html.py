from examples.wraith.preview import build_preview_html
from otoe import Button, HStack, Input, Text, css, mount, render_html


def test_render_html_escapes_text_and_attrs():
    mounted = mount(
        HStack(
            Text("<Wraith>", className="brand"),
            Button("Run", className='x"y', onClick=lambda: None),
            className="topbar",
            gap=8,
        )
    )

    html = render_html(mounted)

    assert "&lt;Wraith&gt;" in html
    assert 'class="otoe-button x&quot;y"' in html
    assert 'style="--otoe-gap:8px"' in html
    assert "<button" in html


def test_render_html_pretty_indents_nested_widgets():
    mounted = mount(
        HStack(
            Text("Signal", className="brand"),
            Button("Run", onClick=lambda: None),
            className="topbar",
            gap=8,
        )
    )

    html = render_html(mounted, pretty=True, indent=2)

    assert html.splitlines() == [
        '  <div class="otoe-stack otoe-hstack topbar" style="--otoe-gap:8px">',
        '    <span class="otoe-text brand">Signal</span>',
        '    <button class="otoe-button" type="button">Run</button>',
        "  </div>",
    ]


def test_render_html_marks_autofocus_input():
    mounted = mount(Input(value="", placeholder="Search", autoFocus=True))

    html = render_html(mounted)

    assert 'autofocus="autofocus"' in html
    assert 'data-otoe-autofocus="true"' in html


def test_render_html_can_apply_otoe_stylesheet_inline():
    mounted = mount(
        HStack(
            Text("Signal", className="brand"),
            className="topbar",
            gap=8,
        )
    )
    styles = css(
        """
        .topbar {
          padding: 16;
          background: panel;
        }
        .brand {
          color: accent;
          font-weight: 800;
        }
        """,
        tokens={"panel": "#101216", "accent": "#f0c866"},
    )

    html = render_html(mounted, stylesheet=styles)

    assert (
        'style="--otoe-gap:8px;padding:16px;background:#101216"'
        in html
    )
    assert 'style="color:#f0c866;font-weight:800"' in html


def test_wraith_preview_builder_contains_core_surfaces():
    html = build_preview_html()

    assert "<!doctype html>" in html
    assert "WRAITH OS" in html
    assert "Runtime" in html
    assert "Arsenal" in html
    assert "WiFi Scan" in html
    assert "RuntimeStatusCluster" not in html
