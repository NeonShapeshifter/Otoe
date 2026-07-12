from __future__ import annotations

from collections import Counter

from hypothesis import given, strategies as st

from otoe import (
    FakeWidget,
    For,
    LiveHtmlRenderer,
    NativeSurface,
    Show,
    Text,
    VStack,
    component,
    mount,
    on_cleanup,
    render_html,
    render_tree_from_target,
    render_tree_to_dict,
    root_widget,
    signal,
    unmount,
)


@given(st.lists(st.booleans(), min_size=1, max_size=40))
def test_show_activates_and_disposes_every_branch_exactly_once(sequence: list[bool]):
    visible = signal(False)
    mounted_ids: list[int] = []
    cleaned_ids: list[int] = []
    next_id = 0

    @component
    def Branch():
        nonlocal next_id
        branch_id = next_id
        next_id += 1
        mounted_ids.append(branch_id)
        on_cleanup(lambda: cleaned_ids.append(branch_id))
        return Text("active")

    mounted = mount(Show(Branch(), when=visible, fallback=Text("inactive")))
    try:
        for next_visible in sequence:
            visible.set(next_visible)
            assert len(mounted_ids) - len(cleaned_ids) == int(next_visible)
    finally:
        unmount(mounted)

    assert Counter(mounted_ids) == Counter(cleaned_ids)
    assert all(count == 1 for count in Counter(cleaned_ids).values())


key_lists = st.lists(
    st.lists(st.integers(min_value=0, max_value=8), unique=True, max_size=8),
    min_size=1,
    max_size=30,
)


@given(key_lists)
def test_for_retains_current_keys_and_cleans_every_instance_once(
    sequence: list[list[int]],
):
    items = signal([])
    mounted_ids: list[int] = []
    cleaned_ids: list[int] = []
    next_id = 0

    @component
    def Row(*, item: int):
        nonlocal next_id
        row_id = next_id
        next_id += 1
        mounted_ids.append(row_id)
        on_cleanup(lambda: cleaned_ids.append(row_id))
        return Text(str(item))

    mounted = mount(
        For(
            each=items,
            key=lambda item: item,
            children=lambda item: Row(item=item),
        )
    )
    previous_widgets: dict[int, FakeWidget] = {}
    try:
        for next_items in sequence:
            items.set(next_items)
            children = root_widget(mounted).children
            current_widgets = {
                int(child.props["content"]): child for child in children
            }
            assert list(current_widgets) == next_items
            for retained_key in previous_widgets.keys() & current_widgets.keys():
                assert current_widgets[retained_key] is previous_widgets[retained_key]
            previous_widgets = current_widgets
    finally:
        unmount(mounted)

    assert Counter(mounted_ids) == Counter(cleaned_ids)
    assert all(count == 1 for count in Counter(cleaned_ids).values())


labels = st.lists(
    st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=1, max_size=8),
    unique=True,
    max_size=6,
)


@given(labels, st.booleans())
def test_mounted_html_live_native_and_render_tree_agree_on_visible_text(
    item_labels: list[str],
    is_visible: bool,
):
    visible = signal(is_visible)
    items = signal(item_labels)
    mounted = mount(
        VStack(
            Show(Text("visible"), when=visible, fallback=Text("hidden")),
            For(
                each=items,
                key=lambda item: item,
                children=lambda item: Text(item),
            ),
        )
    )
    surface = NativeSurface(mounted)
    try:
        expected = ["visible" if is_visible else "hidden", *item_labels]
        mounted_text = _widget_text(root_widget(mounted))
        static_html = render_html(mounted)
        live_html = LiveHtmlRenderer().render(mounted)
        native_text = [box.text for box in surface.layout.boxes if box.text is not None]
        render_tree_payload = str(render_tree_to_dict(render_tree_from_target(mounted)))

        assert mounted_text == expected
        for text in expected:
            assert text in static_html
            assert text in live_html
            assert text in native_text
            assert text in render_tree_payload
    finally:
        surface.dispose()
        unmount(mounted)


def _widget_text(widget: FakeWidget) -> list[str]:
    values = []
    if widget.name == "Text":
        values.append(str(widget.props["content"]))
    for child in widget.children:
        values.extend(_widget_text(child))
    return values
