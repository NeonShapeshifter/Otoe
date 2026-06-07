from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .cli_common import CliError, load_target
from .live_server import LivePreviewApp, LivePreviewConfig, run_live_preview


def run_dev(args: argparse.Namespace) -> int:
    try:
        target = load_target(args.target)
        app_factory = _coerce_dev_app_factory(target)
        css_path = _dev_css_path(args.css)
    except CliError as exc:
        print(f"dev: {exc}", file=sys.stderr)
        return 1

    config = LivePreviewConfig(
        title=args.title,
        css_route=args.css_route,
        css_path=css_path,
        root_class=args.root_class,
    )
    try:
        run_live_preview(
            app_factory=app_factory,
            config=config,
            host=args.host,
            port=args.port,
            label="Otoe dev",
        )
    except CliError as exc:
        print(f"dev: {exc}", file=sys.stderr)
        return 1
    return 0


def _coerce_dev_app_factory(target: Any) -> Callable[[], LivePreviewApp]:
    if _is_live_preview_app(target):
        return lambda: target
    if callable(target):
        return lambda: _coerce_dev_app(target())
    return _coerce_dev_app(target)


def _coerce_dev_app(target: Any) -> LivePreviewApp:
    if _is_live_preview_app(target):
        return target
    raise CliError(
        "dev target must expose render_fragment() and dispatch_event(event_id, *args)"
    )


def _is_live_preview_app(target: Any) -> bool:
    if callable(getattr(target, "render_fragment", None)) and callable(
        getattr(target, "dispatch_event", None)
    ):
        return True
    return False


def _dev_css_path(path: str | None) -> Path | None:
    if path is None:
        return None
    css_path = Path(path)
    if not css_path.exists():
        raise CliError(f"css file {path!r} does not exist")
    return css_path
