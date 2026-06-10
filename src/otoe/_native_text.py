from __future__ import annotations

from dataclasses import dataclass
from math import ceil
from typing import Protocol


@dataclass(frozen=True)
class NativeTextMetrics:
    width: int
    height: int


class NativeTextMeasurer(Protocol):
    def __call__(self, text: str, *, font_size: int) -> NativeTextMetrics:
        ...


def measure_native_text(text: str, *, font_size: int) -> NativeTextMetrics:
    """Deterministic marker-text metrics for the current headless renderer."""
    return NativeTextMetrics(
        width=max(1, ceil(len(text) * font_size * 0.55)),
        height=max(1, ceil(font_size * 1.25)),
    )
