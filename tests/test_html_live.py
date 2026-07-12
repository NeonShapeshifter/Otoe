import gc
import re
import weakref

import pytest
from otoe import (
    Button,
    EventHandlerArityError,
    HStack,
    Input,
    LiveHtmlRenderer,
    ShortcutScope,
    Text,
    mount,
    signal,
)


def _event_id(html, attr):
    match = re.search(rf'{attr}="([^"]+)"', html)
    assert match is not None
    return match.group(1)


class _Recorder:
    def __init__(self, calls, value):
        self.calls = calls
        self.value = value

    def __call__(self):
        self.calls.append(self.value)


def _render_old_button(renderer, calls):
    handler = _Recorder(calls, "old")
    handler_ref = weakref.ref(handler)
    html = renderer.render(mount(Button("Old", onClick=handler)))
    return _event_id(html, "data-otoe-click"), handler_ref


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


def test_live_html_renderer_arity_errors_include_event_context():
    def handle_change():
        return None

    renderer = LiveHtmlRenderer()
    html = renderer.render(mount(Input(value="", onChange=handle_change)))
    change_id = _event_id(html, "data-otoe-change")

    with pytest.raises(
        EventHandlerArityError,
        match=r"Input\.onChange\(value\) handler handle_change expected",
    ):
        renderer.dispatch(change_id, "updated")


def test_live_html_renderer_drops_stale_handlers_between_frames():
    calls = []
    renderer = LiveHtmlRenderer()
    old_click_id, old_handler_ref = _render_old_button(renderer, calls)

    assert old_handler_ref() is not None

    html = renderer.render(mount(Text("No button")))
    gc.collect()

    assert "Old" not in html
    assert renderer.events == {}
    assert old_handler_ref() is None
    with pytest.raises(KeyError, match="Unknown live event id"):
        renderer.dispatch(old_click_id)

    new_handler = _Recorder(calls, "new")
    new_html = renderer.render(mount(Button("New", onClick=new_handler)))
    new_click_id = _event_id(new_html, "data-otoe-click")
    renderer.dispatch(new_click_id)

    assert calls == ["new"]


def test_live_html_renderer_clear_allows_multi_root_frame():
    calls = []
    renderer = LiveHtmlRenderer()
    first = mount(Button("One", onClick=_Recorder(calls, "one")))
    second = mount(Button("Two", onClick=_Recorder(calls, "two")))

    renderer.clear()
    first_html = renderer.render(first)
    second_html = renderer.render(second)

    renderer.dispatch(_event_id(first_html, "data-otoe-click"))
    renderer.dispatch(_event_id(second_html, "data-otoe-click"))

    assert calls == ["one", "two"]


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
