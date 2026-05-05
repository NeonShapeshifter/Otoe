from pathlib import Path

from examples.live_server import LivePreviewConfig, render_live_page


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


def test_render_live_page_includes_click_and_input_dispatchers():
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
    assert 'fetch("/event"' in html
