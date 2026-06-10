from examples.native.portable_core_ui_demo import (
    MARKER_FRAME,
    load_portable_styles,
    main,
    render_demo_frames,
)
from examples.portable_core_ui import app
from otoe import NativeSurface


def test_native_portable_core_ui_demo_writes_marker_frame(tmp_path):
    (marker,) = render_demo_frames(tmp_path, include_pillow=False)

    assert marker.name == MARKER_FRAME
    assert marker.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")


def test_native_portable_core_ui_demo_cli_marker_only(tmp_path, capsys):
    result = main(["--out", str(tmp_path), "--marker-only"])

    captured = capsys.readouterr()
    frame = tmp_path / MARKER_FRAME
    assert result == 0
    assert f"Wrote {frame}" in captured.out
    assert frame.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")


def test_native_portable_core_ui_demo_uses_gallery_styles():
    surface = NativeSurface(app(), stylesheet=load_portable_styles())

    root_style = dict(surface.layout.root.style)
    title = surface.box((0,))

    assert root_style["padding"] == 12
    assert title.text == "Portable Core UI v0"
    assert dict(title.style)["fontSize"].value == 22
