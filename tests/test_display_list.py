import json

import pytest

import otoe
from examples.wraith.mission_exec_showcase import MissionExecShowcaseDemo
from otoe import Button, NativePaint, PaintCommand, Text, VStack, css, mount, render_native_png
from otoe._display_list import (
    DISPLAY_LIST_FORMAT,
    DISPLAY_LIST_SCHEMA_VERSION,
    DisplayList,
    DisplayListCommand,
    DisplayListError,
    display_list_from_paint,
    display_list_to_dict,
    display_list_to_json,
    export_native_display_list,
)


def test_display_list_is_not_top_level_public_api():
    assert "DisplayList" not in otoe.__all__
    assert not hasattr(otoe, "DisplayList")


def test_display_list_manual_creation_and_stable_json():
    display_list = DisplayList(
        width=64,
        height=32,
        commands=(
            DisplayListCommand(
                op="rect",
                path=(),
                x=0,
                y=0,
                width=64,
                height=32,
                fill="#ffffff",
                stroke="#111827",
                stroke_width=1,
                radius=4,
                clip=(0, 0, 64, 32),
                context="manual root",
            ),
            DisplayListCommand(
                op="text",
                path=(0,),
                x=8,
                y=9,
                width=48,
                height=14,
                text="OK",
                color="#111827",
                font_size=14,
            ),
        ),
    )

    assert display_list_to_dict(display_list) == {
        "schemaVersion": DISPLAY_LIST_SCHEMA_VERSION,
        "format": DISPLAY_LIST_FORMAT,
        "width": 64,
        "height": 32,
        "commands": [
            {
                "op": "rect",
                "path": [],
                "box": [0, 0, 64, 32],
                "clip": [0, 0, 64, 32],
                "fill": "#ffffff",
                "stroke": "#111827",
                "strokeWidth": 1,
                "radius": 4,
                "context": "manual root",
            },
            {
                "op": "text",
                "path": [0],
                "box": [8, 9, 48, 14],
                "text": "OK",
                "color": "#111827",
                "fontSize": 14,
            },
        ],
    }
    assert display_list_to_json(display_list) == (
        '{"schemaVersion":0,"format":"otoe-display-list","width":64,"height":32,'
        '"commands":[{"op":"rect","path":[],"box":[0,0,64,32],'
        '"clip":[0,0,64,32],"fill":"#ffffff","stroke":"#111827",'
        '"strokeWidth":1,"radius":4,"context":"manual root"},'
        '{"op":"text","path":[0],"box":[8,9,48,14],"text":"OK",'
        '"color":"#111827","fontSize":14}]}'
    )
    assert json.loads(display_list.to_json()) == display_list.to_dict()


def test_display_list_exports_simple_native_app():
    sheet = css(
        """
        .panel {
          padding: 8;
          gap: 4;
          background: #f8fafc;
          border-color: #d0d7de;
          border-width: 1;
          border-radius: 6;
        }
        """
    )
    mounted = mount(
        VStack(
            Text("Hello"),
            Button("Run", onClick=lambda: None),
            className="panel",
        )
    )

    display_list = export_native_display_list(mounted, stylesheet=sheet)
    payload = display_list_to_dict(display_list)

    assert payload["format"] == "otoe-display-list"
    assert display_list.width == 56
    assert display_list.height == 72
    assert [command.op for command in display_list.commands[:3]] == ["rect", "rect", "text"]
    assert display_list.commands[0].fill == "#ffffff"
    assert display_list.commands[1].fill == "#f8fafc"
    assert display_list.commands[1].stroke == "#d0d7de"
    assert display_list.commands[1].radius == 6
    assert [
        command.text
        for command in display_list.commands
        if command.op == "text"
    ] == ["Hello", "Run"]
    json.dumps(payload, sort_keys=True)


def test_display_list_exports_mission_exec_showcase_surface():
    demo = MissionExecShowcaseDemo()

    display_list = export_native_display_list(demo.surface.paint)

    assert display_list.width > 0
    assert display_list.height > 0
    assert len(display_list.commands) > 100
    assert {command.op for command in display_list.commands} == {"rect", "text"}
    assert any(command.text == "Mission Exec" for command in display_list.commands)
    assert any(command.clip is not None for command in display_list.commands)
    assert json.loads(display_list_to_json(display_list))["format"] == DISPLAY_LIST_FORMAT


def test_display_list_export_does_not_change_native_png_output(tmp_path):
    mounted = mount(
        VStack(
            Text("Stable"),
            Button("Run", onClick=lambda: None),
            padding=8,
            gap=4,
        )
    )
    first = tmp_path / "first.png"
    second = tmp_path / "second.png"

    paint = render_native_png(mounted, first)
    display_list = display_list_from_paint(paint)
    render_native_png(mounted, second)

    assert display_list.commands
    assert first.read_bytes() == second.read_bytes()


def test_display_list_rejects_unknown_native_paint_command_kind():
    paint = NativePaint(
        width=8,
        height=8,
        commands=(
            PaintCommand(
                kind="oval",
                path=(2,),
                x=0,
                y=0,
                width=8,
                height=8,
            ),
        ),
    )

    with pytest.raises(DisplayListError, match=r"kind 'oval' at path \(2,\)"):
        display_list_from_paint(paint)
