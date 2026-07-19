from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from pathlib import Path
from threading import RLock
from typing import Any, TypeGuard

from .cli_common import CliError, load_target
from .cli_targets import coerce_render_target
from .html_live import LiveHtmlRenderer
from .live_server import LivePreviewApp, LivePreviewConfig, run_live_preview
from .mount import unmount


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
    return lambda: _coerce_dev_app(target)


def _coerce_dev_app(target: Any) -> LivePreviewApp:
    if _is_live_preview_app(target):
        return target
    try:
        mounted = coerce_render_target(target)
    except CliError as exc:
        raise CliError(
            "dev target must expose render_fragment() and dispatch_event(event_id, *args), "
            "or be a Node, MountedNode, or zero-argument callable returning one"
        ) from exc
    return _RenderTargetPreview(mounted)


def _is_live_preview_app(target: Any) -> TypeGuard[LivePreviewApp]:
    if callable(getattr(target, "render_fragment", None)) and callable(
        getattr(target, "dispatch_event", None)
    ):
        return True
    return False


class _RenderTargetPreview:
    def __init__(self, mounted: Any) -> None:
        self._mounted = mounted
        self._renderer = LiveHtmlRenderer()
        self._lock = RLock()

    @property
    def renderer(self) -> LiveHtmlRenderer:
        return self._renderer

    def render_fragment(self) -> str:
        with self._lock:
            self._renderer.clear()
            return self._renderer.render(self._mounted, pretty=True, indent=4)

    def dispatch_event(self, event_id: str, *args: Any) -> str:
        with self._lock:
            self._renderer.dispatch(event_id, *args)
            return self.render_fragment()

    def dispose(self) -> None:
        unmount(self._mounted)


def _dev_css_path(path: str | None) -> Path | None:
    if path is None:
        return None
    css_path = Path(path)
    if not css_path.exists():
        raise CliError(f"css file {path!r} does not exist")
    return css_path
