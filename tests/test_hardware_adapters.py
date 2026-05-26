from dataclasses import replace

from examples.hardware.adapters import (
    MemoryHardwareTransport,
    TransportCommandResult,
    TransportHardwareProvider,
)
from examples.hardware.control_panel import demo_snapshot


def test_transport_provider_writes_enabled_command():
    transport = MemoryHardwareTransport(demo_snapshot())
    provider = TransportHardwareProvider(transport)

    snapshot = provider.run_command("refresh")

    assert transport.writes == ["refresh"]
    assert snapshot.mode == "Telemetry refreshed"
    assert snapshot.events[0].source == "telemetry"
    assert snapshot.events[0].message == "Immediate sample requested"
    assert snapshot.last_feedback is not None
    assert snapshot.last_feedback.title == "Telemetry refresh requested"


def test_transport_provider_blocks_disabled_command_without_write():
    transport = MemoryHardwareTransport(demo_snapshot())
    provider = TransportHardwareProvider(transport)

    snapshot = provider.run_command("safe-mode")

    assert transport.writes == []
    assert snapshot.mode == "Closed-loop monitor"
    assert snapshot.events[0].source == "safety"
    assert snapshot.events[0].message == "Arm safe mode blocked: Supervisor key required."
    assert snapshot.last_feedback is not None
    assert snapshot.last_feedback.detail == "Arm safe mode: Supervisor key required."


def test_transport_provider_surfaces_transport_rejection():
    result = TransportCommandResult(
        "refresh",
        False,
        "transport",
        "Write timeout",
        "Transport rejected command",
        "Serial write timed out before acknowledgement.",
        "danger",
    )
    transport = MemoryHardwareTransport(
        replace(demo_snapshot(), mode="Closed-loop monitor"),
        command_results={"refresh": result},
    )
    provider = TransportHardwareProvider(transport)

    snapshot = provider.run_command("refresh")

    assert transport.writes == ["refresh"]
    assert snapshot.mode == "Closed-loop monitor"
    assert snapshot.events[0].source == "transport"
    assert snapshot.events[0].message == "Write timeout"
    assert snapshot.last_feedback is not None
    assert snapshot.last_feedback.title == "Transport rejected command"
