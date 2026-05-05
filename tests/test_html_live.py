import re

from otoe import Button, HStack, Input, LiveHtmlRenderer, Text, mount, signal


def _event_id(html, attr):
    match = re.search(rf'{attr}="([^"]+)"', html)
    assert match is not None
    return match.group(1)


def test_live_html_renderer_registers_and_dispatches_click_events():
    active = signal(False)
    mounted = mount(
        HStack(
            Text("OFF", className="state"),
            Button("Toggle", onClick=lambda: active.set(not active.value)),
        )
    )
    renderer = LiveHtmlRenderer()
    html = renderer.render(mounted)
    click_id = _event_id(html, "data-otoe-click")

    renderer.dispatch(click_id)

    assert active.value is True


def test_live_html_renderer_dispatches_input_change_payloads():
    query = signal("")
    mounted = mount(
        Input(
            value=query,
            placeholder="Search",
            onChange=lambda value: query.set(value),
        )
    )
    renderer = LiveHtmlRenderer()
    html = renderer.render(mounted)
    change_id = _event_id(html, "data-otoe-change")

    renderer.dispatch(change_id, "rf")
    html = renderer.render(mounted)

    assert query.value == "rf"
    assert 'value="rf"' in html
