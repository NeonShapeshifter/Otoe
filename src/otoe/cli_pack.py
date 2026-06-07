from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .pack import PackError, pack_bundle


def run_pack(args: argparse.Namespace) -> int:
    try:
        result = pack_bundle(Path(args.bundle), Path(args.out))
    except PackError as exc:
        print(f"pack: {exc}", file=sys.stderr)
        return 1

    print(f"pack {Path(args.bundle)}: {Path(args.out)}")
    print(f"files: {result.files}")
    print(f"size: {result.size}")
    print(f"sha256: {result.sha256}")
    return 0
