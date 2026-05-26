from pathlib import Path

from otoe.live_server import LivePreviewConfig, LivePreviewStylesheet, render_live_page


class DummyPreview:
    def render_fragment(self) -> str:
        return '    <button data-otoe-click="x:onClick">Ping</button>'

    def dispatch_event(self, event_id, *args):
        return f"{event_id}:{len(args)}"


def test_render_live_page_wraps_fragment_with_shared_shell():
    html = render_live_page(
        DummyPreview(),
        LivePreviewConfig(
            title="Dummy",
            css_route="/dummy.css",
            css_path=Path("dummy.css"),
            root_class="dummy-root",
        ),
    )

    assert "<!doctype html>" in html
    assert "<title>Dummy</title>" in html
    assert '<link rel="stylesheet" href="/dummy.css">' in html
    assert '<div id="otoe-root" class="dummy-root">' in html
    assert 'data-otoe-click="x:onClick"' in html


def test_render_live_page_links_extra_stylesheets_before_primary_css():
    config = LivePreviewConfig(
        title="Dummy",
        css_route="/dummy.css",
        css_path=Path("dummy.css"),
        extra_css=(
            LivePreviewStylesheet("/theme.css", Path("theme.css")),
            LivePreviewStylesheet("/helpers.css", Path("helpers.css")),
        ),
    )

    html = render_live_page(DummyPreview(), config)

    assert [
        stylesheet.route
        for stylesheet in config.stylesheets()
    ] == ["/theme.css", "/helpers.css", "/dummy.css"]
    assert html.index('href="/theme.css"') < html.index('href="/dummy.css"')
    assert config.stylesheet_for("/helpers.css").path == Path("helpers.css")
    assert config.stylesheet_for("/missing.css") is None


def test_render_live_page_includes_click_input_and_keydown_dispatchers():
    html = render_live_page(
        DummyPreview(),
        LivePreviewConfig(
            title="Dummy",
            css_route="/dummy.css",
            css_path=Path("dummy.css"),
        ),
    )

    assert 'closest("[data-otoe-click]")' in html
    assert 'closest("[data-otoe-change]")' in html
    assert 'closest("[data-otoe-keydown]")' in html
    assert 'querySelector("[data-otoe-global-keydown]")' in html
    assert 'querySelector("[data-otoe-autofocus]")' in html
    assert "[data-otoe-focus-scope='trap']" in html
    assert "trapFocus(event)" in html
    assert "lastFocusOutsideScope" in html
    assert "restoreFocusTarget(restoreSelector)" in html
    assert "focusSelectorFor(activeTarget)" in html
    assert "focusAutoTarget()" in html
    assert "event.key" in html
    assert "ctrlKey" in html
    assert "metaKey" in html
    assert 'fetch("/event"' in html
