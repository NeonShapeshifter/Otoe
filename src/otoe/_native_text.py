from __future__ import annotations

from dataclasses import dataclass
from math import ceil


@dataclass(frozen=True)
class NativeTextMetrics:
    width: int
    height: int


def measure_native_text(text: str, *, font_size: int) -> NativeTextMetrics:
    """Deterministic marker-text metrics for the current headless renderer."""
    return NativeTextMetrics(
        width=max(1, ceil(len(text) * font_size * 0.55)),
        height=max(1, ceil(font_size * 1.25)),
    )
