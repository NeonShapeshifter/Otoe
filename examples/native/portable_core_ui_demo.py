from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path

from examples.portable_core_ui import app
from otoe import (
    NativePaintError,
    NativeRendererBackend,
    NativeSurface,
    PillowNativeRendererBackend,
    css,
)


ROOT = Path(__file__).resolve().parents[2]
PORTABLE_STYLES_PATH = ROOT / "preview" / "portable_core_ui.css"
MARKER_FRAME = "portable_core_ui_marker.png"
PILLOW_FRAME = "portable_core_ui_pillow.png"


def load_portable_styles(path: str | Path = PORTABLE_STYLES_PATH):
    return css(Path(path).read_text(encoding="utf-8"))


def render_demo_frames(
    directory: str | Path,
    *,
    include_pillow: bool | None = None,
    styles_path: str | Path = PORTABLE_STYLES_PATH,
) -> tuple[Path, ...]:
    output_dir = Path(directory)
    output_dir.mkdir(parents=True, exist_ok=True)
    stylesheet = load_portable_styles(styles_path)

    frames = [
        _render_frame(
            output_dir / MARKER_FRAME,
            stylesheet=stylesheet,
            renderer_backend=None,
        )
    ]
    if include_pillow is None:
        include_pillow = _pillow_available()
    if include_pillow:
        frames.append(
            _render_frame(
                output_dir / PILLOW_FRAME,
                stylesheet=stylesheet,
                renderer_backend=PillowNativeRendererBackend(),
            )
        )
    return tuple(frames)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m examples.native.portable_core_ui_demo"
    )
    parser.add_argument(
        "--out",
        default=str(Path("preview") / "native"),
        help="directory to write native demo PNG frames",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--pillow",
        action="store_true",
        help="also write the optional Pillow readable-text frame",
    )
    mode.add_argument(
        "--marker-only",
        action="store_true",
        help="write only the deterministic marker-text frame",
    )
    args = parser.parse_args(argv)

    include_pillow = None
    if args.pillow:
        include_pillow = True
    if args.marker_only:
        include_pillow = False

    try:
        frames = render_demo_frames(args.out, include_pillow=include_pillow)
    except NativePaintError as exc:
        print(f"native portable core ui demo: {exc}", file=sys.stderr)
        return 1

    for frame in frames:
        print(f"Wrote {frame}")
    return 0


def _render_frame(
    path: Path,
    *,
    stylesheet,
    renderer_backend: NativeRendererBackend | None,
) -> Path:
    surface = NativeSurface(
        app(),
        stylesheet=stylesheet,
        renderer_backend=renderer_backend,
    )
    surface.render_png(path)
    return path


def _pillow_available() -> bool:
    return importlib.util.find_spec("PIL") is not None


if __name__ == "__main__":
    raise SystemExit(main())
