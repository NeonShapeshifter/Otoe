from __future__ import annotations

import argparse
import compileall
import importlib
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from .html import render_html
from .live_server import LivePreviewApp, LivePreviewConfig, run_live_preview
from .mount import MountedNode, mount
from .native import render_native_png
from .node import Node
from .style import StyleError, StyleSheet, css

DEFAULT_CHECK_PATHS = ("src", "examples", "tests")


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="otoe")
    subcommands = parser.add_subparsers(dest="command", required=True)

    check = subcommands.add_parser("check", help="run local Otoe health checks")
    check.add_argument(
        "--path",
        action="append",
        dest="paths",
        help="path to compile; may be passed more than once",
    )
    check.add_argument(
        "--tests",
        action="store_true",
        help="also run pytest after compile checks",
    )
    check.set_defaults(func=_check)

    render = subcommands.add_parser("render", help="render an Otoe target")
    render.add_argument("target", help="import target in MODULE:OBJECT form")
    render.add_argument("--out", required=True, help="output HTML path")
    render.add_argument("--pretty", action="store_true", help="pretty-print HTML")
    render.add_argument("--indent", type=int, default=0, help="base HTML indent")
    render.add_argument(
        "--css",
        help="optional Otoe CSS file to apply inline during render",
    )
    render.add_argument(
        "--no-strict-styles",
        action="store_false",
        default=True,
        dest="strict_styles",
        help="ignore class names missing from --css",
    )
    render.add_argument(
        "--native",
        action="store_true",
        help="render a native PNG frame",
    )
    render.add_argument(
        "--background",
        default="#ffffff",
        help="native PNG background",
    )
    render.set_defaults(func=_render)

    dev = subcommands.add_parser("dev", help="run a local live preview app")
    dev.add_argument("target", help="app target in MODULE:APP form")
    dev.add_argument("--host", default="127.0.0.1")
    dev.add_argument("--port", default=8767, type=int)
    dev.add_argument("--title", default="Otoe Dev")
    dev.add_argument("--css", help="optional CSS file to serve")
    dev.add_argument("--css-route", default="/otoe.css")
    dev.set_defaults(func=_dev)

    new = subcommands.add_parser("new", help="scaffold a small Otoe app")
    new.add_argument("path", help="directory to create or populate")
    new.add_argument(
        "--name",
        help="display name for the generated app; defaults to the directory name",
    )
    new.add_argument(
        "--force",
        action="store_true",
        help="overwrite existing scaffold files",
    )
    new.set_defaults(func=_new)

    return parser


def _check(args: argparse.Namespace) -> int:
    paths = tuple(args.paths or DEFAULT_CHECK_PATHS)
    ok = True
    for path in paths:
        ok = _compile_path(path) and ok
    if not ok:
        return 1
    if args.tests:
        return subprocess.run([sys.executable, "-m", "pytest", "-q"]).returncode
    return 0


def _compile_path(path: str) -> bool:
    target = Path(path)
    if not target.exists():
        print(f"compile {path}: missing", file=sys.stderr)
        return False
    if target.is_dir():
        ok = compileall.compile_dir(str(target), quiet=1)
    else:
        ok = compileall.compile_file(str(target), quiet=1)
    print(f"compile {path}: {'ok' if ok else 'failed'}")
    return bool(ok)


def _render(args: argparse.Namespace) -> int:
    try:
        target = _load_target(args.target)
        mounted = _coerce_render_target(target)
        stylesheet = _load_stylesheet(args.css)
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


def _dev(args: argparse.Namespace) -> int:
    try:
        target = _load_target(args.target)
        app = _coerce_dev_app(target)
    except CliError as exc:
        print(f"dev: {exc}", file=sys.stderr)
        return 1

    css_path = Path(args.css) if args.css else None
    config = LivePreviewConfig(
        title=args.title,
        css_route=args.css_route,
        css_path=css_path,
    )
    run_live_preview(
        app_factory=lambda: app,
        config=config,
        host=args.host,
        port=args.port,
        label="Otoe dev",
    )
    return 0


def _new(args: argparse.Namespace) -> int:
    target = Path(args.path)
    app_name = args.name or _display_name_from_path(target)
    try:
        target.mkdir(parents=True, exist_ok=True)
        _write_scaffold_file(
            target / "app.py",
            _app_template(app_name),
            force=args.force,
        )
        _write_scaffold_file(
            target / "README.md",
            _readme_template(app_name),
            force=args.force,
        )
    except CliError as exc:
        print(f"new: {exc}", file=sys.stderr)
        return 1
    print(f"new {app_name}: {target}")
    return 0


def _load_target(spec: str) -> Any:
    module_name, separator, object_path = spec.partition(":")
    if not separator or not module_name or not object_path:
        raise CliError("target must use MODULE:OBJECT syntax")
    try:
        value = importlib.import_module(module_name)
    except Exception as exc:
        raise CliError(f"could not import module {module_name!r}") from exc
    for part in object_path.split("."):
        try:
            value = getattr(value, part)
        except AttributeError as exc:
            raise CliError(f"{spec!r} could not resolve attribute {part!r}") from exc
    return value


def _load_stylesheet(path: str | None) -> StyleSheet | None:
    if path is None:
        return None
    source = Path(path)
    if not source.exists():
        raise CliError(f"css file {path!r} does not exist")
    try:
        return css(source.read_text(encoding="utf-8"))
    except StyleError as exc:
        raise CliError(f"css file {path!r}: {exc}") from exc


def _coerce_render_target(target: Any) -> MountedNode:
    if isinstance(target, MountedNode):
        return target
    if isinstance(target, Node):
        return mount(target)
    if callable(target):
        return _coerce_render_target(target())
    raise CliError(
        "render target must be a Node, MountedNode, or zero-argument callable "
        f"returning one; got {type(target).__name__}"
    )


def _coerce_dev_app(target: Any) -> LivePreviewApp:
    if _is_live_preview_app(target):
        return target
    app = target() if callable(target) else target
    if _is_live_preview_app(app):
        return app
    raise CliError(
        "dev target must expose render_fragment() and dispatch_event(event_id, *args)"
    )


def _is_live_preview_app(target: Any) -> bool:
    if callable(getattr(target, "render_fragment", None)) and callable(
        getattr(target, "dispatch_event", None)
    ):
        return True
    return False


def _write_scaffold_file(path: Path, content: str, *, force: bool) -> None:
    if path.exists() and not force:
        raise CliError(f"{path} already exists; pass --force to overwrite")
    path.write_text(content, encoding="utf-8")


def _display_name_from_path(path: Path) -> str:
    name = path.name.strip().replace("_", " ").replace("-", " ")
    return name.title() if name else "Otoe App"


def _app_template(app_name: str) -> str:
    return (
        "from otoe import Button, Text, VStack, computed, signal\n"
        "\n"
        "\n"
        "count = signal(0)\n"
        "\n"
        "\n"
        "def app():\n"
        f"    title = {app_name!r}\n"
        "    label = computed(lambda: f\"Count: {count.value}\")\n"
        "    return VStack(\n"
        "        Text(title),\n"
        "        Text(label),\n"
        "        Button(\"Increment\", onClick=lambda: count.set(count.value + 1)),\n"
        "        gap=8,\n"
        "        padding=12,\n"
        "    )\n"
    )


def _readme_template(app_name: str) -> str:
    return (
        f"# {app_name}\n"
        "\n"
        "Render the app from this directory:\n"
        "\n"
        "```bash\n"
        "otoe render app:app --out preview.html --pretty\n"
        "otoe render app:app --out preview.png --native\n"
        "```\n"
    )


class CliError(ValueError):
    pass
