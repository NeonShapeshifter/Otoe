#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from statistics import median
from time import perf_counter
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from otoe import Button, For, Text, VStack, computed, mount, render_html, signal
from otoe.experimental.native import layout_native, paint_native


PERFORMANCE_BUDGETS = {
    "build_medium_tree": 0.10,
    "mount_for_list": 0.50,
    "mount_medium_tree": 0.50,
    "render_html": 0.50,
    "layout_native": 1.00,
    "paint_native": 0.50,
}


def timed(
    label: str,
    fn: Callable[[], Any],
    *,
    repeat: int = 5,
) -> tuple[str, float, float, Any]:
    samples = []
    result: Any = None
    for _ in range(repeat):
        start = perf_counter()
        result = fn()
        samples.append(perf_counter() - start)
    return label, median(samples), max(samples), result


def medium_tree():
    count = signal(0)
    label = computed(lambda: f"Count: {count.value}")
    rows = [{"id": f"row-{index}", "label": f"Row {index}"} for index in range(120)]
    return VStack(
        Text(label),
        Button("Increment", onClick=lambda: count.set(count.value + 1)),
        For(
            each=rows,
            key=lambda item: item["id"],
            children=lambda item: Text(item["label"]),
        ),
        gap=4,
        padding=8,
    )


def for_tree():
    items = [{"id": f"item-{index}", "label": f"Item {index}"} for index in range(300)]
    return VStack(
        For(
            each=items,
            key=lambda item: item["id"],
            children=lambda item: Text(item["label"]),
        )
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail when a median measurement exceeds its regression budget",
    )
    args = parser.parse_args(argv)
    measurements: list[dict[str, float | str]] = []

    for label, elapsed, maximum, _ in (
        timed("build_medium_tree", medium_tree),
        timed("mount_for_list", lambda: mount(for_tree())),
    ):
        measurements.append(
            {"label": label, "seconds": elapsed, "maxSeconds": maximum}
        )

    _, mount_elapsed, mount_max, mounted = timed(
        "mount_medium_tree", lambda: mount(medium_tree())
    )
    measurements.append(
        {"label": "mount_medium_tree", "seconds": mount_elapsed, "maxSeconds": mount_max}
    )

    _, html_elapsed, html_max, _ = timed("render_html", lambda: render_html(mounted))
    measurements.append(
        {"label": "render_html", "seconds": html_elapsed, "maxSeconds": html_max}
    )

    _, layout_elapsed, layout_max, layout = timed(
        "layout_native", lambda: layout_native(mounted)
    )
    measurements.append(
        {"label": "layout_native", "seconds": layout_elapsed, "maxSeconds": layout_max}
    )

    _, paint_elapsed, paint_max, _ = timed("paint_native", lambda: paint_native(layout))
    measurements.append(
        {"label": "paint_native", "seconds": paint_elapsed, "maxSeconds": paint_max}
    )

    failures = [
        {
            "label": measurement["label"],
            "seconds": measurement["seconds"],
            "budgetSeconds": PERFORMANCE_BUDGETS[str(measurement["label"])],
        }
        for measurement in measurements
        if float(measurement["seconds"])
        > PERFORMANCE_BUDGETS[str(measurement["label"])]
    ]
    print(
        json.dumps(
            {
                "format": "otoe-bench-smoke",
                "sampleCount": 5,
                "measurements": measurements,
                "budgets": PERFORMANCE_BUDGETS,
                "failures": failures,
            },
            indent=2,
        )
    )
    return 1 if args.check and failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
