from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Protocol

from otoe import For, HStack, Text, VStack, component, computed
from otoe.ui import (
    ActionButton,
    AppShell,
    Badge,
    Card,
    DataTable,
    NavRoute,
    RouteView,
    SidebarNav,
    StatCard,
    TableColumn,
    Toolbar,
)


@dataclass(frozen=True)
class TelemetryMetric:
    id: str
    label: str
    value: str
    unit: str
    tone: str
    detail: str


@dataclass(frozen=True)
class HardwareEvent:
    id: str
    time: str
    source: str
    message: str
    tone: str = "neutral"


@dataclass(frozen=True)
class HardwareCommand:
    id: str
    label: str
    description: str
    tone: str = "info"
    enabled: bool = True


@dataclass(frozen=True)
class DeviceSnapshot:
    device_name: str
    connection: str
    connection_tone: str
    firmware: str
    uptime: str
    mode: str
    sample_rate: str
    metrics: list[TelemetryMetric]
    events: list[HardwareEvent]
    commands: list[HardwareCommand]


class HardwareProvider(Protocol):
    def snapshot(self) -> DeviceSnapshot:
        raise NotImplementedError

    def run_command(self, command_id: str) -> DeviceSnapshot:
        raise NotImplementedError


HARDWARE_ROUTES = [
    NavRoute("overview", "Overview", "Device state and priority signals", badge="Live", tone="success"),
    NavRoute("telemetry", "Telemetry", "Sensor readings and sample metadata", badge="8 Hz", tone="info"),
    NavRoute("controls", "Controls", "Safe operator actions", badge="4", tone="warn"),
    NavRoute("settings", "Settings", "Connection and firmware defaults", badge="USB", tone="neutral"),
]

METRIC_COLUMNS = [
    TableColumn("label", "Signal", "metric-name"),
    TableColumn("value", "Reading", "metric-value"),
    TableColumn("detail", "State", "metric-state"),
]

EVENT_COLUMNS = [
    TableColumn("time", "Time", "event-time"),
    TableColumn("source", "Source", "event-source"),
    TableColumn("message", "Message", "event-message"),
]


class FakeHardwareProvider:
    def __init__(self, snapshot: DeviceSnapshot | None = None) -> None:
        self._snapshot = snapshot or demo_snapshot()
        self._runs = 0

    def snapshot(self) -> DeviceSnapshot:
        return self._snapshot

    def run_command(self, command_id: str) -> DeviceSnapshot:
        self._runs += 1
        event = _command_event(command_id, self._runs)
        next_mode = {
            "self-test": "Self-test queued",
            "calibrate": "Calibration queued",
            "safe-mode": "Safe mode armed",
            "clear-log": "Log review acknowledged",
            "refresh": "Telemetry refreshed",
        }.get(command_id, "Command queued")
        self._snapshot = replace(
            self._snapshot,
            mode=next_mode,
            events=[event, *self._snapshot.events][:8],
        )
        return self._snapshot


@component
def HardwareControlPanel(
    *,
    snapshot,
    active_route,
    on_navigate,
    on_command,
):
    return AppShell(
        header=HardwareTopBar(snapshot=snapshot, on_command=on_command),
        sidebar=SidebarNav(
            routes=HARDWARE_ROUTES,
            active=active_route,
            on_navigate=on_navigate,
            brand=VStack(
                Text("Otoe", className="hardware-sidebar-brand"),
                Text("Hardware reference", className="hardware-sidebar-copy"),
                gap=2,
            ),
            footer=VStack(
                Text(computed(lambda: _snap(snapshot).firmware), className="hardware-sidebar-meta"),
                Text(computed(lambda: _snap(snapshot).uptime), className="hardware-sidebar-meta"),
                gap=2,
            ),
            className="hardware-sidebar",
        ),
        content=RouteView(
            route=active_route,
            routes=HARDWARE_ROUTES,
            render=lambda route: _route_view(route, snapshot=snapshot, on_command=on_command),
            className="hardware-route",
        ),
        className="hardware-app",
    )


@component
def HardwareTopBar(*, snapshot, on_command):
    return Toolbar(
        VStack(
            Text("Otoe Hardware Lab", className="hardware-brand"),
            Text(
                computed(lambda: _snap(snapshot).device_name),
                className="hardware-device",
            ),
            gap=2,
        ),
        Badge(
            computed(lambda: _snap(snapshot).connection),
            tone=computed(lambda: _snap(snapshot).connection_tone),
            className="hardware-connection",
        ),
        Text(
            computed(lambda: f"Mode: {_snap(snapshot).mode}"),
            className="hardware-mode",
        ),
        ActionButton("Refresh", variant="ghost", onClick=lambda: on_command("refresh")),
        ActionButton("Run self-test", variant="primary", onClick=lambda: on_command("self-test")),
        className="hardware-topbar",
        gap=12,
    )


@component
def OverviewView(*, snapshot, on_command):
    metrics = computed(lambda: _snap(snapshot).metrics)
    events = computed(lambda: _snap(snapshot).events[:4])
    first_metric = computed(lambda: metrics.value[0])
    second_metric = computed(lambda: metrics.value[1])
    third_metric = computed(lambda: metrics.value[2])

    return VStack(
        HStack(
            StatCard(
                label="Connection",
                value=computed(lambda: _snap(snapshot).connection),
                detail=computed(lambda: _snap(snapshot).sample_rate),
                tone=computed(lambda: _snap(snapshot).connection_tone),
                className="hardware-stat",
            ),
            SensorStat(metric=first_metric),
            SensorStat(metric=second_metric),
            SensorStat(metric=third_metric),
            className="hardware-stat-grid",
            gap=12,
        ),
        HStack(
            Card(
                VStack(
                    HStack(
                        Text("Priority telemetry", className="hardware-section-title"),
                        Badge("Live sample", tone="info", className="hardware-section-badge"),
                        className="hardware-section-heading",
                    ),
                    For(
                        each=metrics,
                        key=lambda metric: metric.id,
                        children=lambda metric: SensorRow(metric=metric),
                    ),
                    gap=10,
                ),
                className="hardware-panel hardware-telemetry-panel",
            ),
            Card(
                VStack(
                    HStack(
                        Text("Event stream", className="hardware-section-title"),
                        ActionButton(
                            "Clear",
                            variant="ghost",
                            size="sm",
                            onClick=lambda: on_command("clear-log"),
                        ),
                        className="hardware-section-heading",
                    ),
                    For(
                        each=events,
                        key=lambda event: event.id,
                        children=lambda event: EventRow(event=event),
                    ),
                    gap=10,
                ),
                className="hardware-panel hardware-events-panel",
            ),
            className="hardware-overview-grid",
            gap=14,
        ),
        className="hardware-page",
        gap=14,
    )


@component
def TelemetryView(*, snapshot):
    return Card(
        VStack(
            HStack(
                Text("Telemetry table", className="hardware-section-title"),
                Text(computed(lambda: _snap(snapshot).sample_rate), className="hardware-table-note"),
                className="hardware-section-heading",
            ),
            DataTable(
                columns=METRIC_COLUMNS,
                rows=computed(lambda: _snap(snapshot).metrics),
                key=lambda metric: metric.id,
                render_cell=_metric_cell,
                className="hardware-table",
            ),
            gap=10,
        ),
        className="hardware-panel",
    )


@component
def ControlsView(*, snapshot, on_command):
    return HStack(
        Card(
            VStack(
                Text("Operator controls", className="hardware-section-title"),
                For(
                    each=computed(lambda: _snap(snapshot).commands),
                    key=lambda command: command.id,
                    children=lambda command: CommandRow(command=command, on_command=on_command),
                ),
                gap=10,
            ),
            className="hardware-panel hardware-command-panel",
        ),
        Card(
            VStack(
                Text("Safety envelope", className="hardware-section-title"),
                SettingRow(label="Output limit", value="80% PWM ceiling"),
                SettingRow(label="Thermal guard", value="Trip at 70 deg C"),
                SettingRow(label="Command mode", value=computed(lambda: _snap(snapshot).mode)),
                SettingRow(label="Fallback", value="Manual safe mode"),
                gap=10,
            ),
            className="hardware-panel hardware-safety-panel",
        ),
        className="hardware-control-grid",
        gap=14,
    )


@component
def SettingsView(*, snapshot):
    return Card(
        VStack(
            Text("Device settings", className="hardware-section-title"),
            SettingRow(label="Transport", value="USB serial"),
            SettingRow(label="Device", value=computed(lambda: _snap(snapshot).device_name)),
            SettingRow(label="Firmware", value=computed(lambda: _snap(snapshot).firmware)),
            SettingRow(label="Sample rate", value=computed(lambda: _snap(snapshot).sample_rate)),
            SettingRow(label="Uptime", value=computed(lambda: _snap(snapshot).uptime)),
            gap=10,
        ),
        className="hardware-panel hardware-settings-panel",
    )


@component
def SensorStat(*, metric):
    return StatCard(
        label=computed(lambda: metric.value.label),
        value=computed(lambda: f"{metric.value.value}{metric.value.unit}"),
        detail=computed(lambda: metric.value.detail),
        tone=computed(lambda: metric.value.tone),
        className="hardware-stat",
    )


@component
def SensorRow(*, metric):
    return HStack(
        VStack(
            Text(metric.label, className="hardware-signal-name"),
            Text(metric.detail, className="hardware-signal-detail"),
            gap=2,
        ),
        Text(f"{metric.value}{metric.unit}", className="hardware-signal-value"),
        Badge(metric.tone.upper(), tone=metric.tone, className="hardware-signal-badge"),
        className="hardware-signal-row",
        gap=10,
    )


@component
def EventRow(*, event):
    return HStack(
        Text(event.time, className="hardware-event-time"),
        VStack(
            Text(event.source, className="hardware-event-source"),
            Text(event.message, className="hardware-event-message"),
            gap=2,
        ),
        Badge(event.tone.upper(), tone=event.tone, className="hardware-event-badge"),
        className="hardware-event-row",
        gap=10,
    )


@component
def CommandRow(*, command, on_command):
    return HStack(
        VStack(
            Text(command.label, className="hardware-command-title"),
            Text(command.description, className="hardware-command-copy"),
            gap=2,
        ),
        ActionButton(
            "Run",
            variant=command.tone,
            size="sm",
            disabled=not command.enabled,
            onClick=lambda command_id=command.id: on_command(command_id),
        ),
        className="hardware-command-row",
        gap=12,
    )


@component
def SettingRow(*, label, value):
    return HStack(
        Text(label, className="hardware-setting-label"),
        Text(value, className="hardware-setting-value"),
        className="hardware-setting-row",
    )


def demo_snapshot() -> DeviceSnapshot:
    return DeviceSnapshot(
        device_name="Bench Controller A17",
        connection="Online",
        connection_tone="success",
        firmware="FW 1.8.4",
        uptime="Uptime 04:18:22",
        mode="Closed-loop monitor",
        sample_rate="8 Hz sample",
        metrics=[
            TelemetryMetric("voltage", "Bus voltage", "24.1", "V", "success", "Within rail tolerance"),
            TelemetryMetric("current", "Motor current", "1.8", "A", "info", "Idle draw with fan load"),
            TelemetryMetric("thermal", "Thermal headroom", "18", "C", "warn", "Heatsink margin remaining"),
            TelemetryMetric("vibration", "Vibration RMS", "0.04", "g", "success", "Below maintenance threshold"),
        ],
        events=[
            HardwareEvent("boot", "08:42:18", "controller", "Device handshake accepted", "success"),
            HardwareEvent("fan", "08:42:21", "cooling", "Fan curve settled at 32%", "info"),
            HardwareEvent("temp", "08:42:29", "thermal", "Thermal margin below preferred target", "warn"),
            HardwareEvent("sample", "08:42:31", "telemetry", "Sample frame synchronized", "success"),
        ],
        commands=[
            HardwareCommand("refresh", "Refresh telemetry", "Pull one immediate sample from the provider.", "info"),
            HardwareCommand("self-test", "Run self-test", "Queue a non-destructive controller self-test.", "success"),
            HardwareCommand("calibrate", "Calibrate sensors", "Apply lab calibration offsets after operator review.", "warn"),
            HardwareCommand("safe-mode", "Arm safe mode", "Reduce output envelope until manually released.", "danger"),
        ],
    )


def _route_view(route, *, snapshot, on_command):
    if route.id == "overview":
        return OverviewView(snapshot=snapshot, on_command=on_command)
    if route.id == "telemetry":
        return TelemetryView(snapshot=snapshot)
    if route.id == "controls":
        return ControlsView(snapshot=snapshot, on_command=on_command)
    if route.id == "settings":
        return SettingsView(snapshot=snapshot)
    return Text("Route not found", className="hardware-empty")


def _metric_cell(metric: TelemetryMetric, column: TableColumn):
    if column.key == "label":
        return Text(metric.label, className="ui-table-cell hardware-table-name")
    if column.key == "value":
        return Text(f"{metric.value}{metric.unit}", className="ui-table-cell hardware-table-value")
    if column.key == "detail":
        return Badge(metric.detail, tone=metric.tone, className="hardware-table-badge")
    return Text("", className="ui-table-cell")


def _command_event(command_id: str, index: int) -> HardwareEvent:
    messages = {
        "self-test": ("diagnostics", "Self-test scheduled"),
        "calibrate": ("sensors", "Calibration queued"),
        "safe-mode": ("safety", "Safe mode armed"),
        "clear-log": ("events", "Log review acknowledged"),
        "refresh": ("telemetry", "Immediate sample requested"),
    }
    source, message = messages.get(command_id, ("operator", f"Command {command_id} queued"))
    tone = "warn" if command_id in {"calibrate", "safe-mode"} else "info"
    return HardwareEvent(
        id=f"cmd-{index}-{command_id}",
        time=f"08:43:{index:02d}",
        source=source,
        message=message,
        tone=tone,
    )


def _snap(snapshot) -> DeviceSnapshot:
    return snapshot.value if hasattr(snapshot, "value") else snapshot
