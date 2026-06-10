from __future__ import annotations

import argparse
import compileall
import subprocess
import sys
from pathlib import Path

DEFAULT_CHECK_PATHS = ("src", "examples", "tests")


def run_check(args: argparse.Namespace) -> int:
    paths = tuple(args.paths) if args.paths else _default_check_paths()
    ok = True
    for path in paths:
        ok = _compile_path(path) and ok
    if not ok:
        return 1
    if args.tests:
        pytest_args = [*args.pytest_arg, *_pytest_args(args.pytest_args)]
        if not pytest_args and not Path("tests").exists():
            print("pytest: skipped (tests directory missing)")
            return 0
        command = [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            *pytest_args,
        ]
        print(f"pytest: {' '.join(command)}")
        return subprocess.run(command).returncode
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


def _pytest_args(args: list[str]) -> list[str]:
    if args and args[0] == "--":
        return args[1:]
    return args
