from __future__ import annotations

import argparse
import json
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

from .cli_common import CliError, load_json_artifact
from .contract_compare import (
    ContractCompareError,
    compare_json_contracts,
    delete_json_pointer,
    format_contract_difference,
)


def run_compare_contract(args: argparse.Namespace) -> int:
    try:
        expected = load_json_artifact(Path(args.expected), label="expected")
        actual = load_json_artifact(Path(args.actual), label="actual")
        ignored_paths = tuple(args.ignore_path or ())
        if ignored_paths:
            expected = deepcopy(expected)
            actual = deepcopy(actual)
            for pointer in ignored_paths:
                delete_json_pointer(expected, pointer)
                delete_json_pointer(actual, pointer)
    except (CliError, ContractCompareError) as exc:
        print(f"compare-contract: {exc}", file=sys.stderr)
        return 1

    report = compare_contract_report(
        expected,
        actual,
        expected_path=Path(args.expected),
        actual_path=Path(args.actual),
        ignored_paths=ignored_paths,
        max_diffs=args.max_diffs,
    )
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    elif report["matched"]:
        print(f"contracts match: {Path(args.expected)} == {Path(args.actual)}")
    else:
        print(
            f"contracts differ: {report['differenceCount']} difference(s) between "
            f"{Path(args.expected)} and {Path(args.actual)}"
        )
        for difference in report["differences"]:
            print(format_contract_difference(difference))
        if report["truncated"]:
            remaining = report["differenceCount"] - len(report["differences"])
            print(f"... {remaining} more difference(s)")

    return 0 if report["matched"] else 1


def compare_contract_report(
    expected: Any,
    actual: Any,
    *,
    expected_path: Path,
    actual_path: Path,
    ignored_paths: tuple[str, ...],
    max_diffs: int,
) -> dict[str, Any]:
    differences = compare_json_contracts(expected, actual)
    max_diffs = max(max_diffs, 0)
    shown_differences = differences[:max_diffs]
    return {
        "schemaVersion": 1,
        "expected": str(expected_path),
        "actual": str(actual_path),
        "matched": not differences,
        "differenceCount": len(differences),
        "differences": shown_differences,
        "ignoredPaths": list(ignored_paths),
        "truncated": len(shown_differences) < len(differences),
    }
