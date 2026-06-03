from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class LiveEvent:
    event_id: str
    args: tuple[Any, ...]
    client_id: str | None = None
    sequence: int | None = None


@dataclass
class LiveEventSequenceTracker:
    latest_sequences: dict[str, int] = field(default_factory=dict)

    def accept(self, event: LiveEvent) -> bool:
        if event.sequence is None:
            return True
        latest = self.latest_sequences.get(event.client_id or "", 0)
        if event.sequence <= latest:
            return False
        self.latest_sequences[event.client_id or ""] = event.sequence
        return True


def live_event_from_payload(payload: dict[str, Any]) -> LiveEvent:
    event_id = payload["id"]
    args = payload.get("args", [])
    if not isinstance(args, list):
        raise TypeError("event args must be a list")

    client_id = payload.get("clientId")
    sequence = payload.get("sequence")
    if sequence is not None:
        if not isinstance(client_id, str) or not client_id:
            raise TypeError("event clientId must be a non-empty string")
        if not isinstance(sequence, int) or sequence < 1:
            raise TypeError("event sequence must be a positive integer")

    return LiveEvent(
        event_id=event_id,
        args=tuple(args),
        client_id=client_id,
        sequence=sequence,
    )
