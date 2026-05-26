from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Protocol

from otoe import For, HStack, Show, Text, VStack, component, computed
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
    disabled_reason: str | None = None


@dataclass(frozen=True)
class CommandFeedback:
    command_id: str
    title: str
    detail: str
    tone: str = "info"


@dataclass(frozen=True)
class DeviceSnapshot:
    device_name: str
    connection: str
    connection_tone: str
    status: str
    status_detail: str
    firmware: str
    uptime: str
    mode: str
    sample_rate: str
    metrics: list[TelemetryMetric]
    events: list[HardwareEvent]
    commands: list[HardwareCommand]
    last_feedback: CommandFeedback | None = None


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
        command = _command_by_id(self._snapshot, command_id)
        if command is None:
            event = _blocked_event(command_id, "Command is not registered.", self._runs)
            self._snapshot = replace(
                self._snapshot,
                events=[event, *self._snapshot.events][:8],
                last_feedback=_blocked_feedback(command_id, "Command is not registered."),
            )
            return self._snapshot
        if not command.enabled:
            reason = command.disabled_reason or "Command is currently unavailable."
            event = _blocked_event(command.label, reason, self._runs)
            self._snapshot = replace(
                self._snapshot,
                events=[event, *self._snapshot.events][:8],
                last_feedback=_blocked_feedback(command.label, reason),
            )
            return self._snapshot

        event = _command_event(command_id, self._runs)
        feedback = _command_feedback(command_id)
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
            last_feedback=feedback,
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
        content=VStack(
            CommandFeedbackPanel(snapshot=snapshot),
            RouteView(
                route=active_route,
                routes=HARDWARE_ROUTES,
                render=lambda route: _route_view(route, snapshot=snapshot, on_command=on_command),
                className="hardware-route",
            ),
            className="hardware-route-shell",
            gap=14,
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
        ActionButton(
            "Refresh",
            variant="ghost",
            disabled=computed(lambda: not _command_enabled(_snap(snapshot), "refresh")),
            onClick=lambda: on_command("refresh"),
        ),
        ActionButton(
            "Run self-test",
            variant="primary",
            disabled=computed(lambda: not _command_enabled(_snap(snapshot), "self-test")),
            onClick=lambda: on_command("self-test"),
        ),
        className="hardware-topbar",
        gap=12,
    )


@component
def OverviewView(*, snapshot, on_command):
    metrics = computed(lambda: _snap(snapshot).metrics)
    events = computed(lambda: _snap(snapshot).events[:4])
    first_metric = computed(lambda: _metric_at(metrics.value, 0, "Bus voltage"))
    second_metric = computed(lambda: _metric_at(metrics.value, 1, "Motor current"))
    third_metric = computed(lambda: _metric_at(metrics.value, 2, "Thermal headroom"))

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
        StatusBanner(snapshot=snapshot),
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
                        fallback=Text("No telemetry samples", className="hardware-empty-state"),
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
                        fallback=Text("No hardware events", className="hardware-empty-state"),
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
def CommandFeedbackPanel(*, snapshot):
    return Show(
        Card(
            HStack(
                Badge(
                    computed(lambda: _snap(snapshot).last_feedback.tone.upper()),
                    tone=computed(lambda: _snap(snapshot).last_feedback.tone),
                    className="hardware-feedback-badge",
                ),
                VStack(
                    Text(computed(lambda: _snap(snapshot).last_feedback.title), className="hardware-feedback-title"),
                    Text(computed(lambda: _snap(snapshot).last_feedback.detail), className="hardware-feedback-copy"),
                    gap=2,
                ),
                className="hardware-feedback-row",
                gap=12,
            ),
            className=computed(lambda: f"hardware-feedback is-{_snap(snapshot).last_feedback.tone}"),
        ),
        when=computed(lambda: _snap(snapshot).last_feedback is not None),
    )


@component
def StatusBanner(*, snapshot):
    return Card(
        HStack(
            Badge(
                computed(lambda: _snap(snapshot).status.upper()),
                tone=computed(lambda: _snap(snapshot).connection_tone),
                className="hardware-status-badge",
            ),
            VStack(
                Text(computed(lambda: _snap(snapshot).connection), className="hardware-status-title"),
                Text(computed(lambda: _snap(snapshot).status_detail), className="hardware-status-copy"),
                gap=2,
            ),
            className="hardware-status-row",
            gap=12,
        ),
        className=computed(lambda: f"hardware-status is-{_snap(snapshot).status}"),
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
                empty="No telemetry samples",
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
                HStack(
                    Text("Operator controls", className="hardware-section-title"),
                    Badge(
                        computed(lambda: _snap(snapshot).status.upper()),
                        tone=computed(lambda: _snap(snapshot).connection_tone),
                        className="hardware-section-badge",
                    ),
                    className="hardware-section-heading",
                ),
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
            SettingRow(label="Provider state", value=computed(lambda: _snap(snapshot).status)),
            SettingRow(label="State detail", value=computed(lambda: _snap(snapshot).status_detail)),
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
            Show(
                Text(command.disabled_reason, className="hardware-command-reason"),
                when=command.disabled_reason,
            ),
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
        status="ready",
        status_detail="Provider healthy. Telemetry is live and operator controls are available.",
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
            HardwareCommand(
                "safe-mode",
                "Arm safe mode",
                "Reduce output envelope until manually released.",
                "danger",
                enabled=False,
                disabled_reason="Supervisor key required.",
            ),
        ],
    )


def loading_snapshot() -> DeviceSnapshot:
    return replace(
        demo_snapshot(),
        connection="Connecting",
        connection_tone="info",
        status="loading",
        status_detail="Opening USB serial and waiting for the first heartbeat.",
        firmware="Detecting firmware",
        uptime="No active session",
        mode="Handshake pending",
        sample_rate="Waiting for sample",
        metrics=_placeholder_metrics("Waiting for sample", "info"),
        events=[
            HardwareEvent("connect", "08:41:58", "transport", "Opening USB serial", "info"),
        ],
        commands=_lock_commands(
            demo_snapshot().commands,
            reason="Waiting for provider handshake.",
            allow={"refresh"},
        ),
        last_feedback=CommandFeedback(
            "connect",
            "Connecting to provider",
            "Telemetry and operator controls unlock after the first heartbeat.",
            "info",
        ),
    )


def offline_snapshot() -> DeviceSnapshot:
    return replace(
        demo_snapshot(),
        connection="Offline",
        connection_tone="danger",
        status="offline",
        status_detail="Last heartbeat missed. Controls are locked until the provider reconnects.",
        firmware="Unknown",
        uptime="No active session",
        mode="Waiting for device",
        sample_rate="No live sample",
        metrics=_placeholder_metrics("No signal", "danger"),
        events=[
            HardwareEvent("offline", "08:44:02", "transport", "Heartbeat timeout", "danger"),
            HardwareEvent("lock", "08:44:03", "safety", "Operator controls locked", "warn"),
        ],
        commands=_lock_commands(
            demo_snapshot().commands,
            reason="Device is offline.",
            allow={"refresh"},
        ),
        last_feedback=CommandFeedback(
            "offline",
            "Provider offline",
            "Refresh is available; all output-affecting commands remain locked.",
            "danger",
        ),
    )


def error_snapshot() -> DeviceSnapshot:
    return replace(
        demo_snapshot(),
        connection="Error",
        connection_tone="danger",
        status="error",
        status_detail="Provider rejected the latest frame checksum. Inspect transport logs.",
        mode="Transport fault",
        sample_rate="Sample rejected",
        metrics=_placeholder_metrics("Frame invalid", "danger"),
        events=[
            HardwareEvent("crc", "08:45:11", "transport", "Checksum mismatch on sample frame", "danger"),
            HardwareEvent("hold", "08:45:12", "safety", "Calibration and output commands held", "warn"),
        ],
        commands=_lock_commands(
            demo_snapshot().commands,
            reason="Resolve provider error first.",
            allow={"refresh"},
        ),
        last_feedback=CommandFeedback(
            "error",
            "Provider error",
            "Inspect transport logs before running calibration or output commands.",
            "danger",
        ),
    )


def empty_snapshot() -> DeviceSnapshot:
    return replace(
        demo_snapshot(),
        status_detail="Provider is connected, but no telemetry sample has arrived yet.",
        sample_rate="Awaiting first sample",
        metrics=[],
        events=[],
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


def _command_feedback(command_id: str) -> CommandFeedback:
    feedback = {
        "self-test": ("Self-test queued", "Diagnostics will run without changing output state.", "success"),
        "calibrate": ("Calibration queued", "Sensor offsets are waiting for operator review.", "warn"),
        "safe-mode": ("Safe mode armed", "Output limits were reduced until manual release.", "danger"),
        "clear-log": ("Log review acknowledged", "Event stream remains retained in the provider.", "info"),
        "refresh": ("Telemetry refresh requested", "The provider will return one immediate sample.", "info"),
    }
    title, detail, tone = feedback.get(command_id, ("Command queued", f"{command_id} queued.", "info"))
    return CommandFeedback(command_id, title, detail, tone)


def _blocked_feedback(command_label: str, reason: str) -> CommandFeedback:
    return CommandFeedback(
        command_label,
        "Command blocked",
        f"{command_label}: {reason}",
        "danger",
    )


def _blocked_event(command_label: str, reason: str, index: int) -> HardwareEvent:
    return HardwareEvent(
        id=f"blocked-{index}",
        time=f"08:43:{index:02d}",
        source="safety",
        message=f"{command_label} blocked: {reason}",
        tone="danger",
    )


def _command_by_id(snapshot: DeviceSnapshot, command_id: str) -> HardwareCommand | None:
    for command in snapshot.commands:
        if command.id == command_id:
            return command
    return None


def _command_enabled(snapshot: DeviceSnapshot, command_id: str) -> bool:
    command = _command_by_id(snapshot, command_id)
    return bool(command and command.enabled)


def _lock_commands(
    commands: list[HardwareCommand],
    *,
    reason: str,
    allow: set[str] | None = None,
) -> list[HardwareCommand]:
    allowed = allow or set()
    locked: list[HardwareCommand] = []
    for command in commands:
        if command.id in allowed:
            locked.append(command)
            continue
        locked.append(replace(command, enabled=False, disabled_reason=reason))
    return locked


def _placeholder_metrics(detail: str, tone: str) -> list[TelemetryMetric]:
    return [
        TelemetryMetric("voltage", "Bus voltage", "--", "", tone, detail),
        TelemetryMetric("current", "Motor current", "--", "", tone, detail),
        TelemetryMetric("thermal", "Thermal headroom", "--", "", tone, detail),
        TelemetryMetric("vibration", "Vibration RMS", "--", "", tone, detail),
    ]


def _metric_at(metrics: list[TelemetryMetric], index: int, label: str) -> TelemetryMetric:
    if index < len(metrics):
        return metrics[index]
    return TelemetryMetric(f"empty-{index}", label, "--", "", "neutral", "No telemetry sample")


def _snap(snapshot) -> DeviceSnapshot:
    return snapshot.value if hasattr(snapshot, "value") else snapshot
