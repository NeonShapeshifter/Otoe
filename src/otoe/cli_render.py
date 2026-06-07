from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .cli_common import CliError, load_target
from .cli_styles import load_stylesheet
from .cli_targets import coerce_render_target
from .html import render_html
from .native import render_native_png
from .style import StyleError


def run_render(args: argparse.Namespace) -> int:
    try:
        target = load_target(args.target)
        mounted = coerce_render_target(target)
        stylesheet = load_stylesheet(args.css)
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
