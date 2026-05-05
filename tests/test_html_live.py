import re

from otoe import Button, HStack, Input, LiveHtmlRenderer, ShortcutScope, Text, mount, signal


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


def test_live_html_renderer_dispatches_keydown_payloads():
    key = signal(None)
    mounted = mount(
        Input(
            value="",
            placeholder="Search",
            onKeyDown=lambda value: key.set(value),
        )
    )
    renderer = LiveHtmlRenderer()
    html = renderer.render(mounted)
    keydown_id = _event_id(html, "data-otoe-keydown")

    renderer.dispatch(keydown_id, "Enter")

    assert key.value == "Enter"


def test_live_html_renderer_dispatches_button_keydown_payloads():
    key = signal(None)
    mounted = mount(Button("Open", onKeyDown=lambda value: key.set(value)))
    renderer = LiveHtmlRenderer()
    html = renderer.render(mounted)
    keydown_id = _event_id(html, "data-otoe-keydown")

    renderer.dispatch(keydown_id, "ArrowDown")

    assert key.value == "ArrowDown"


def test_live_html_renderer_dispatches_global_keydown_payloads():
    payload = signal(None)
    mounted = mount(
        ShortcutScope(
            Text("App"),
            onKeyDown=lambda value: payload.set(value),
        )
    )
    renderer = LiveHtmlRenderer()
    html = renderer.render(mounted)
    global_keydown_id = _event_id(html, "data-otoe-global-keydown")

    renderer.dispatch(global_keydown_id, {"key": "k", "ctrlKey": True})

    assert payload.value == {"key": "k", "ctrlKey": True}
