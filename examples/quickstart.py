from __future__ import annotations

from otoe import Button, Text, VStack, component


@component
def QuickstartSurface():
    return VStack(
        Text("Otoe quickstart", className="eyebrow"),
        Text("A small render target for the Otoe CLI."),
        Button("Primary action", onClick=lambda: None),
        className="quickstart-surface",
        gap=12,
        padding=16,
    )


app = QuickstartSurface()
