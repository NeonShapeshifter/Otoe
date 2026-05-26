from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Protocol

from examples.hardware.control_panel import (
    CommandFeedback,
    DeviceSnapshot,
    HardwareCommand,
    HardwareEvent,
    demo_snapshot,
)


@dataclass(frozen=True)
class TransportCommandResult:
    command_id: str
    accepted: bool
    event_source: str
    event_message: str
    feedback_title: str
    feedback_detail: str
    tone: str = "info"
    mode: str | None = None


class HardwareTransport(Protocol):
    def read_snapshot(self) -> DeviceSnapshot:
        raise NotImplementedError

    def write_command(self, command_id: str) -> TransportCommandResult:
        raise NotImplementedError


class MemoryHardwareTransport:
    def __init__(
        self,
        snapshot: DeviceSnapshot | None = None,
        command_results: dict[str, TransportCommandResult] | None = None,
    ) -> None:
        self._snapshot = snapshot or demo_snapshot()
        self._command_results = command_results or {}
        self.writes: list[str] = []

    def read_snapshot(self) -> DeviceSnapshot:
        return self._snapshot

    def write_command(self, command_id: str) -> TransportCommandResult:
        self.writes.append(command_id)
        result = self._command_results.get(command_id) or _default_command_result(command_id)
        if result.accepted and result.mode is not None:
            self._snapshot = replace(self._snapshot, mode=result.mode)
        return result


class TransportHardwareProvider:
    def __init__(self, transport: HardwareTransport) -> None:
        self.transport = transport
        self._snapshot = transport.read_snapshot()
        self._runs = 0

    def snapshot(self) -> DeviceSnapshot:
        self._snapshot = self.transport.read_snapshot()
        return self._snapshot

    def run_command(self, command_id: str) -> DeviceSnapshot:
        self._runs += 1
        current = self.transport.read_snapshot()
        command = _command_by_id(current, command_id)
        if command is None:
            self._snapshot = _blocked_snapshot(
                current,
                command_id,
                "Command is not registered.",
                self._runs,
            )
            return self._snapshot
        if not command.enabled:
            reason = command.disabled_reason or "Command is currently unavailable."
            self._snapshot = _blocked_snapshot(current, command.label, reason, self._runs)
            return self._snapshot

        result = self.transport.write_command(command_id)
        latest = self.transport.read_snapshot()
        tone = result.tone if result.accepted else "danger"
        event = HardwareEvent(
            id=f"transport-{self._runs}-{command_id}",
            time=f"08:43:{self._runs:02d}",
            source=result.event_source,
            message=result.event_message,
            tone=tone,
        )
        self._snapshot = replace(
            latest,
            mode=result.mode if result.accepted and result.mode is not None else latest.mode,
            events=[event, *latest.events][:8],
            last_feedback=CommandFeedback(
                result.command_id,
                result.feedback_title,
                result.feedback_detail,
                tone,
            ),
        )
        return self._snapshot


def _default_command_result(command_id: str) -> TransportCommandResult:
    results = {
        "self-test": TransportCommandResult(
            "self-test",
            True,
            "diagnostics",
            "Self-test scheduled",
            "Self-test queued",
            "Diagnostics will run without changing output state.",
            "success",
            "Self-test queued",
        ),
        "calibrate": TransportCommandResult(
            "calibrate",
            True,
            "sensors",
            "Calibration queued",
            "Calibration queued",
            "Sensor offsets are waiting for operator review.",
            "warn",
            "Calibration queued",
        ),
        "safe-mode": TransportCommandResult(
            "safe-mode",
            True,
            "safety",
            "Safe mode armed",
            "Safe mode armed",
            "Output limits were reduced until manual release.",
            "danger",
            "Safe mode armed",
        ),
        "clear-log": TransportCommandResult(
            "clear-log",
            True,
            "events",
            "Log review acknowledged",
            "Log review acknowledged",
            "Event stream remains retained in the provider.",
            "info",
            "Log review acknowledged",
        ),
        "refresh": TransportCommandResult(
            "refresh",
            True,
            "telemetry",
            "Immediate sample requested",
            "Telemetry refresh requested",
            "The provider will return one immediate sample.",
            "info",
            "Telemetry refreshed",
        ),
    }
    return results.get(
        command_id,
        TransportCommandResult(
            command_id,
            True,
            "operator",
            f"Command {command_id} queued",
            "Command queued",
            f"{command_id} queued.",
            "info",
            "Command queued",
        ),
    )


def _blocked_snapshot(
    snapshot: DeviceSnapshot,
    command_label: str,
    reason: str,
    index: int,
) -> DeviceSnapshot:
    event = HardwareEvent(
        id=f"transport-blocked-{index}",
        time=f"08:43:{index:02d}",
        source="safety",
        message=f"{command_label} blocked: {reason}",
        tone="danger",
    )
    return replace(
        snapshot,
        events=[event, *snapshot.events][:8],
        last_feedback=CommandFeedback(
            command_label,
            "Command blocked",
            f"{command_label}: {reason}",
            "danger",
        ),
    )


def _command_by_id(snapshot: DeviceSnapshot, command_id: str) -> HardwareCommand | None:
    for command in snapshot.commands:
        if command.id == command_id:
            return command
    return None
