from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .cli_common import CliError, load_target
from .cli_styles import load_stylesheet
from .cli_targets import coerce_render_target
from .html import render_html
from .native import PillowNativeRendererBackend, render_native_png
from .style import StyleError


def run_render(args: argparse.Namespace) -> int:
    try:
        target = load_target(args.target)
        mounted = coerce_render_target(target)
        stylesheet = load_stylesheet(args.css)
        renderer_backend = _native_renderer_backend(args)
    except CliError as exc:
        print(f"render: {exc}", file=sys.stderr)
        return 1

    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        if args.native:
            render_native_png(
                mounted,
                output,
                stylesheet=stylesheet,
                strict_styles=args.strict_styles,
                background=args.background,
                renderer_backend=renderer_backend,
                scale=args.native_scale,
            )
            print(f"render native {args.target}: {output}")
            return 0

        output.write_text(
            render_html(
                mounted,
                pretty=args.pretty,
                indent=args.indent,
                stylesheet=stylesheet,
                strict_styles=args.strict_styles,
            ),
            encoding="utf-8",
        )
    except (StyleError, ValueError) as exc:
        print(f"render: {exc}", file=sys.stderr)
        return 1
    print(f"render {args.target}: {output}")
    return 0


def _native_renderer_backend(args: argparse.Namespace):
    native_text = getattr(args, "native_text", "marker")
    font = getattr(args, "font", None)
    native_scale = getattr(args, "native_scale", 1)
    if not args.native:
        if native_text != "marker":
            raise CliError("--native-text requires --native")
        if font is not None:
            raise CliError("--font requires --native --native-text pillow")
        if native_scale != 1:
            raise CliError("--native-scale requires --native")
        return None
    if font is not None and native_text != "pillow":
        raise CliError("--font requires --native-text pillow")
    if native_text == "pillow":
        return PillowNativeRendererBackend(font_path=font)
    return None
