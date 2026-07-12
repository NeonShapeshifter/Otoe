from __future__ import annotations

import argparse
import compileall
import subprocess
import sys
from pathlib import Path

from .cli_common import CliError, load_target
from .cli_styles import load_stylesheet

DEFAULT_CHECK_PATHS = ("src", "examples", "tests")


def run_check(args: argparse.Namespace) -> int:
    paths = tuple(args.paths) if args.paths else _default_check_paths()
    ok = True
    for path in paths:
        ok = _compile_path(path) and ok
    target = getattr(args, "target", None)
    css_paths = tuple(getattr(args, "css", ()) or ())
    if ok:
        ok = _check_target(target) and ok
    if ok:
        for css_path in css_paths:
            ok = _check_css(css_path) and ok
    if not ok:
        return 1
    if args.tests:
        pytest_args = [*args.pytest_arg, *_pytest_args(args.pytest_args)]
        if not pytest_args and not Path("tests").exists():
            print("pytest: skipped (tests directory missing)")
            _print_generated_app_next_steps(paths, args)
            return 0
        command = [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            *pytest_args,
        ]
        print(f"pytest: {' '.join(command)}")
        result = subprocess.run(command).returncode
        if result != 0:
            return result
    _print_generated_app_next_steps(paths, args)
    return 0


def _default_check_paths() -> tuple[str, ...]:
    if all(Path(path).exists() for path in DEFAULT_CHECK_PATHS):
        return DEFAULT_CHECK_PATHS
    if Path("app.py").is_file():
        return ("app.py",)
    return (".",)


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


def _check_target(target: str | None) -> bool:
    if target is None:
        return True
    try:
        load_target(target)
    except CliError as exc:
        print(f"target {target}: failed: {exc}", file=sys.stderr)
        return False
    print(f"target {target}: ok")
    return True


def _check_css(path: str) -> bool:
    try:
        stylesheet = load_stylesheet(path)
    except CliError as exc:
        print(f"css {path}: failed: {exc}", file=sys.stderr)
        return False
    rule_count = len(stylesheet.rules) if stylesheet is not None else 0
    print(f"css {path}: ok ({rule_count} rule{'s' if rule_count != 1 else ''})")
    return True


def _print_generated_app_next_steps(
    paths: tuple[str, ...],
    args: argparse.Namespace,
) -> None:
    if paths != ("app.py",) or not Path("app.py").is_file():
        return
    css_arg = " --css styles.css" if Path("styles.css").is_file() else ""
    if args.target is None:
        print(f"next: validate target with `otoe check --target app:app{css_arg}`")
    print(f"next: render HTML with `otoe render app:app --out preview.html{css_arg} --pretty`")


def _pytest_args(args: list[str]) -> list[str]:
    if args and args[0] == "--":
        return args[1:]
    return args
