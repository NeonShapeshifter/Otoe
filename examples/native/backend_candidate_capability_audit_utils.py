from __future__ import annotations

from typing import Any


def increment_bucket(
    buckets: dict[str, dict[str, int]],
    bucket: str,
    property_name: str,
) -> None:
    properties = buckets.setdefault(bucket, {})
    properties[property_name] = properties.get(property_name, 0) + 1


def support_buckets(
    buckets: dict[str, dict[str, int]],
    *,
    key_name: str,
    items_name: str = "properties",
    item_key: str = "property",
) -> list[dict[str, Any]]:
    return [
        {
            key_name: bucket,
            "count": sum(properties.values()),
            items_name: property_counts(properties, item_key=item_key),
        }
        for bucket, properties in sorted(buckets.items())
    ]


def property_counts(
    counts: dict[str, int],
    *,
    item_key: str = "property",
) -> list[dict[str, Any]]:
    return [
        {item_key: property_name, "count": count}
        for property_name, count in sorted(counts.items())
    ]
