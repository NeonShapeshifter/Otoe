from __future__ import annotations

import argparse
import compileall
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path


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
