from __future__ import annotations

from labels import OFFLINE_ITEMS


def bundle_title() -> str:
    return "Offline bundle reference"


def bundle_items() -> tuple[dict[str, str], ...]:
    return OFFLINE_ITEMS
