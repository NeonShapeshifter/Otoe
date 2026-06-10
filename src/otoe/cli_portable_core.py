from __future__ import annotations

import argparse
import json

from .portable_core import format_portable_core_ui_v0, portable_core_ui_v0_matrix


def run_portable_core(args: argparse.Namespace) -> int:
    payload = portable_core_ui_v0_matrix()
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0
    print(
        format_portable_core_ui_v0(
            include_outside=args.outside,
            include_examples=args.examples,
        )
    )
    return 0
