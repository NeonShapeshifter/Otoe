from __future__ import annotations

from helpers import bundle_items, bundle_title
from otoe import Button, HStack, Text, VStack


def app():
    rows = tuple(
        HStack(
            Text(item["label"], className="text-sm text-ink"),
            Text(item["status"], className=f"text-sm {item['tone']}"),
            className="p-3 gap-4 bg-panel-soft border border-line rounded-md justify-between",
        )
        for item in bundle_items()
    )
    return VStack(
        Text(bundle_title(), className="text-lg text-ink"),
        Text(
            "Build, validate, and pack this app before it touches hardware.",
            className="text-sm text-muted",
        ),
        *rows,
        Button("Offline ready", onClick=lambda: None, className="bg-accent"),
        className="p-4 gap-3 bg-panel border border-line rounded-lg",
    )
