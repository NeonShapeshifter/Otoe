#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path
from time import perf_counter
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from otoe import Button, For, Text, VStack, computed, mount, render_html, signal
from otoe.experimental.native import layout_native, paint_native


def timed(label: str, fn: Callable[[], Any]) -> tuple[str, float, Any]:
    start = perf_counter()
    result = fn()
    return label, perf_counter() - start, result


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


def main() -> int:
    measurements: list[dict[str, float | str]] = []

    for label, elapsed, _ in (
        timed("build_medium_tree", medium_tree),
        timed("mount_for_list", lambda: mount(for_tree())),
    ):
        measurements.append({"label": label, "seconds": elapsed})

    _, mount_elapsed, mounted = timed("mount_medium_tree", lambda: mount(medium_tree()))
    measurements.append({"label": "mount_medium_tree", "seconds": mount_elapsed})

    _, html_elapsed, _ = timed("render_html", lambda: render_html(mounted))
    measurements.append({"label": "render_html", "seconds": html_elapsed})

    _, layout_elapsed, layout = timed("layout_native", lambda: layout_native(mounted))
    measurements.append({"label": "layout_native", "seconds": layout_elapsed})

    _, paint_elapsed, _ = timed("paint_native", lambda: paint_native(layout))
    measurements.append({"label": "paint_native", "seconds": paint_elapsed})

    print(json.dumps({"format": "otoe-bench-smoke", "measurements": measurements}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
