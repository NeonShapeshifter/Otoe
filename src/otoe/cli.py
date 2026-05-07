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
from .mount import MountedNode, mount
from .node import Node

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
    render.set_defaults(func=_render)

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
    except CliError as exc:
        print(f"render: {exc}", file=sys.stderr)
        return 1

    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        render_html(mounted, pretty=args.pretty, indent=args.indent),
        encoding="utf-8",
    )
    print(f"render {args.target}: {output}")
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


class CliError(ValueError):
    pass
