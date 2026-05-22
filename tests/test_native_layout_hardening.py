import pytest

from otoe import (
    Button,
    HStack,
    NativeLayoutError,
    ScrollView,
    Text,
    VStack,
    css,
    component,
    layout_native,
    mount,
)


def test_native_layout_empty_container_uses_explicit_dimensions():
    sheet = css(".empty { width: 160; height: 90; padding: 12; }")

    layout = layout_native(mount(VStack(className="empty")), stylesheet=sheet)

    assert layout.root.width == 160
    assert layout.root.height == 90
    assert layout.root.children == ()


def test_native_layout_fixed_container_can_be_larger_than_content():
    sheet = css(".shell { width: 180; height: 96; padding: 10; gap: 8; }")

    layout = layout_native(
        mount(VStack(Text("A"), Button("Go", onClick=lambda: None), className="shell")),
        stylesheet=sheet,
    )

    assert layout.root.width == 180
    assert layout.root.height == 96
    assert (layout.by_path((0,)).x, layout.by_path((0,)).y) == (10, 10)
    assert (layout.by_path((1,)).x, layout.by_path((1,)).y) == (10, 36)


def test_native_layout_min_constraints_win_over_conflicting_max_constraints():
    sheet = css(
        """
        .shell {
          width: 80;
          min-width: 120;
          max-width: 100;
          height: 40;
          min-height: 70;
          max-height: 60;
        }
        """
    )

    layout = layout_native(mount(VStack(Text("Bounds"), className="shell")), stylesheet=sheet)

    assert layout.root.width == 120
    assert layout.root.height == 70


def test_native_layout_nested_stacks_keep_stable_child_paths_and_offsets():
    layout = layout_native(
        mount(
            VStack(
                HStack(Text("A"), Text("BB"), gap=3, padding=2),
                VStack(Text("CCC"), Text("D"), gap=5, padding=4),
                gap=7,
                padding=6,
            )
        )
    )

    assert layout.root.width == 44
    assert layout.root.height == 90
    assert (layout.by_path((0,)).x, layout.by_path((0,)).y) == (6, 6)
    assert (layout.by_path((0, 1)).x, layout.by_path((0, 1)).y) == (19, 8)
    assert (layout.by_path((1,)).x, layout.by_path((1,)).y) == (6, 35)
    assert (layout.by_path((1, 1)).x, layout.by_path((1, 1)).y) == (10, 62)


def test_native_layout_scrollview_clamps_to_nested_content_bounds():
    sheet = css(".scroll { width: 150; height: 52; padding: 4; gap: 6; }")
    mounted = mount(
        ScrollView(
            VStack(
                Button("One", onClick=lambda: None),
                Button("Two", onClick=lambda: None),
                Button("Three", onClick=lambda: None),
                gap=4,
            ),
            scrollY=999,
            className="scroll",
        )
    )

    layout = layout_native(mounted, stylesheet=sheet)

    assert dict(layout.root.style)["scrollY"] == 66
    assert layout.root.height == 52
    assert layout.by_path((0, 0)).y == -62
    assert layout.by_path((0, 2)).y == 14


def test_native_layout_auto_and_percent_dimensions_remain_unsupported():
    for source, pattern in [
        (".box { width: auto; }", "expected numeric width"),
        (".box { width: 50%; }", "only supports px dimensions"),
    ]:
        with pytest.raises(NativeLayoutError, match=pattern):
            layout_native(
                mount(VStack(Text("Unsupported"), className="box")),
                stylesheet=css(source),
            )


@pytest.mark.parametrize(
    ("source", "pattern"),
    [
        (".box { width: -10; }", "expected non-negative width"),
        (".box { height: -10; }", "expected non-negative height"),
        (".box { padding: -4; }", "expected non-negative padding"),
        (".box { gap: -2; }", "expected non-negative gap"),
    ],
)
def test_native_layout_rejects_negative_dimensions(source, pattern):
    with pytest.raises(NativeLayoutError, match=pattern):
        layout_native(
            mount(VStack(Text("Negative"), className="box")),
            stylesheet=css(source),
        )


def test_native_layout_rejects_negative_font_size():
    with pytest.raises(NativeLayoutError, match="expected non-negative fontSize"):
        layout_native(
            mount(Text("Negative", className="box")),
            stylesheet=css(".box { font-size: -12; }"),
        )


def test_native_layout_negative_dimension_errors_include_component_context():
    sheet = css(".box { width: -10; }")

    @component
    def BadBox():
        return VStack(Text("Negative"), className="box")

    with pytest.raises(
        NativeLayoutError,
        match=r"BadBox > VStack: Native layout expected non-negative width",
    ):
        layout_native(mount(BadBox()), stylesheet=sheet)


def test_native_layout_negative_scroll_y_clamps_to_zero():
    sheet = css(".scroll { width: 120; height: 40; padding: 4; gap: 4; }")
    mounted = mount(
        ScrollView(
            Button("First", onClick=lambda: None),
            Button("Second", onClick=lambda: None),
            scrollY=-30,
            className="scroll",
        )
    )

    layout = layout_native(mounted, stylesheet=sheet)

    assert dict(layout.root.style)["scrollY"] == 0
    assert layout.by_path((0,)).y == 4
    assert layout.by_path((1,)).y == 42


def test_native_layout_alignment_center_offsets_hstack_children():
    sheet = css(
        """
        .row {
          align-items: center;
          justify-content: center;
          width: 160;
          height: 80;
          padding: 10;
          gap: 4;
        }
        """
    )

    layout = layout_native(mount(HStack(Text("A"), Text("B"), className="row")), stylesheet=sheet)

    assert layout.root.width == 160
    assert layout.root.height == 80
    assert dict(layout.root.style)["alignItems"] == "center"
    assert dict(layout.root.style)["justifyContent"] == "center"
    assert (layout.by_path((0,)).x, layout.by_path((0,)).y) == (70, 31)
    assert (layout.by_path((1,)).x, layout.by_path((1,)).y) == (82, 31)


def test_native_layout_alignment_center_offsets_vstack_children():
    sheet = css(
        """
        .column {
          align-items: center;
          justify-content: center;
          width: 120;
          height: 100;
          padding: 10;
          gap: 4;
        }
        """
    )

    layout = layout_native(
        mount(VStack(Text("AA"), Text("B"), className="column")),
        stylesheet=sheet,
    )

    assert (layout.by_path((0,)).x, layout.by_path((0,)).y) == (52, 30)
    assert (layout.by_path((1,)).x, layout.by_path((1,)).y) == (56, 52)


def test_native_layout_alignment_end_offsets_hstack_children():
    sheet = css(
        """
        .row {
          align-items: flex-end;
          justify-content: flex-end;
          width: 100;
          height: 60;
          padding: 10;
          gap: 4;
        }
        """
    )

    layout = layout_native(mount(HStack(Text("A"), Text("B"), className="row")), stylesheet=sheet)

    assert (layout.by_path((0,)).x, layout.by_path((0,)).y) == (70, 32)
    assert (layout.by_path((1,)).x, layout.by_path((1,)).y) == (82, 32)


def test_native_layout_justify_space_between_distributes_hstack_children():
    sheet = css(
        """
        .row {
          justify-content: space-between;
          width: 100;
          padding: 10;
        }
        """
    )

    layout = layout_native(
        mount(HStack(Text("A"), Text("B"), Text("C"), className="row")),
        stylesheet=sheet,
    )

    assert layout.root.width == 100
    assert [layout.by_path((index,)).x for index in range(3)] == [10, 46, 82]


def test_native_layout_align_stretch_resizes_vstack_children_cross_axis():
    sheet = css(
        """
        .column {
          align-items: stretch;
          width: 100;
          padding: 10;
          gap: 4;
        }
        """
    )

    layout = layout_native(
        mount(VStack(Text("A"), Text("BB"), className="column")),
        stylesheet=sheet,
    )

    first = layout.by_path((0,))
    second = layout.by_path((1,))

    assert (first.x, first.width) == (10, 80)
    assert (second.x, second.width) == (10, 80)


def test_native_layout_alignment_rejects_unknown_values():
    sheet = css(".row { align-items: baseline; }")

    with pytest.raises(NativeLayoutError, match="does not support alignItems='baseline'"):
        layout_native(mount(HStack(Text("A"), className="row")), stylesheet=sheet)


def test_native_layout_alignment_rejects_non_stack_widgets():
    sheet = css(".title { align-items: center; }")

    with pytest.raises(NativeLayoutError, match="only on HStack and VStack"):
        layout_native(mount(Text("Title", className="title")), stylesheet=sheet)
