from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from otoe import (
    For,
    HStack,
    NativeRendererBackend,
    NativeSurface,
    ScrollView,
    Show,
    Text,
    VStack,
    component,
    computed,
    css,
    signal,
)
from otoe.ui import ActionButton, Badge, Card, Dialog, TabButton, Tabs, Toolbar


STYLE_PATH = Path(__file__).resolve().parents[2] / "preview" / "wraith_mission_exec.css"

LOG_FILTERS = ("ALL", "INFO", "OK", "WARN", "PROBE", "ACTION")
EVENT_FILTERS = ("ALL", "OK", "WARN", "ACTION")


@dataclass(frozen=True)
class MissionFact:
    label: str
    value: str


@dataclass(frozen=True)
class PreflightCheck:
    id: str
    label: str
    detail: str
    status: str
    tone: str


@dataclass(frozen=True)
class LogEntry:
    id: str
    time: str
    level: str
    message: str


@dataclass(frozen=True)
class EventEntry:
    id: str
    time: str
    tag: str
    severity: str
    message: str


MISSION_FACT_ROWS = (
    (
        MissionFact("TARGET", "Bench A-17"),
        MissionFact("SCOPE", "DEMO-004"),
        MissionFact("ASSET", "Relay sim"),
    ),
    (
        MissionFact("PROFILE", "Dry-run"),
        MissionFact("RUNTIME", "HTML/native"),
        MissionFact("POSTURE", "No hardware"),
    ),
)

PREFLIGHT_CHECKS = (
    PreflightCheck(
        "pf-policy",
        "Policy guard",
        "Demo fixture only.",
        "OK",
        "ok",
    ),
    PreflightCheck(
        "pf-adapter",
        "Adapter boundary",
        "Mirror adapter.",
        "OK",
        "ok",
    ),
    PreflightCheck(
        "pf-safety",
        "Safety latch",
        "State-only abort.",
        "ARMED",
        "warn",
    ),
    PreflightCheck(
        "pf-renderer",
        "Renderer target",
        "HTML, native, build.",
        "READY",
        "ok",
    ),
    PreflightCheck(
        "pf-approval",
        "Operator gate",
        "Pauses simulation.",
        "GATED",
        "warn",
    ),
)

INITIAL_LOGS = (
    LogEntry("log-001", "09:18:02", "info", "mission_exec: showcase booted with local fixture data"),
    LogEntry("log-002", "09:18:03", "ok", "renderer: native surface contract loaded"),
    LogEntry("log-003", "09:18:05", "probe", "runtime probe: frame 000 / appliance mirror ready"),
    LogEntry("log-004", "09:18:07", "action", "operator chrome: emergency path visible, no mission runner bound"),
    LogEntry("log-005", "09:18:09", "ok", "preflight: policy guard passed for DEMO-CAGE-004"),
    LogEntry("log-006", "09:18:13", "warn", "approval: destructive command remains gated"),
    LogEntry("log-007", "09:18:16", "info", "telemetry: synthetic relay temperature 31.4C"),
    LogEntry("log-008", "09:18:18", "probe", "io mirror: line voltage sample stable at 24.0V"),
)

INITIAL_EVENTS = (
    EventEntry("event-001", "09:18:02", "BOOT", "ok", "Mission Exec surface mounted"),
    EventEntry("event-002", "09:18:05", "PROBE", "ok", "Runtime probe attached to fake frame source"),
    EventEntry("event-003", "09:18:07", "SAFETY", "warn", "Abort route visible but inert"),
    EventEntry("event-004", "09:18:09", "PREFLIGHT", "ok", "Checklist reached gated-ready state"),
    EventEntry("event-005", "09:18:13", "APPROVAL", "warn", "Approval gate armed for operator review"),
)

FRAME_SAMPLES = (
    ("info", "SENSOR", "synthetic bus sample accepted"),
    ("probe", "PROBE", "native render heartbeat observed"),
    ("ok", "CHECK", "preflight mirror remained stable"),
    ("warn", "WATCH", "temperature trend crossed fake watch threshold"),
)

PREFLIGHT_STATE_CLASSES = {
    "ok": "check-state check-ok",
    "warn": "check-state check-warn",
}
PREFLIGHT_ROW_CLASSES = {
    "ok": "preflight-row preflight-ok",
    "warn": "preflight-row preflight-warn",
}
LOG_LEVEL_CLASSES = {
    "action": "log-level level-action",
    "info": "log-level level-info",
    "ok": "log-level level-ok",
    "probe": "log-level level-probe",
    "warn": "log-level level-warn",
}
LOG_ROW_CLASSES = {
    "action": "log-line log-row-action",
    "info": "log-line log-row-info",
    "ok": "log-line log-row-ok",
    "probe": "log-line log-row-probe",
    "warn": "log-line log-row-warn",
}
EVENT_TAG_CLASSES = {
    "action": "event-tag event-action",
    "ok": "event-tag event-ok",
    "warn": "event-tag event-warn",
}
EVENT_ROW_CLASSES = {
    "action": "event-row event-row-action",
    "ok": "event-row event-row-ok",
    "warn": "event-row event-row-warn",
}


def app():
    return MissionExecShowcaseModel().view()


def load_stylesheet():
    return css(STYLE_PATH.read_text(encoding="utf-8"))


class MissionExecShowcaseDemo:
    def __init__(
        self,
        *,
        renderer_backend: NativeRendererBackend | None = None,
    ) -> None:
        self.model = MissionExecShowcaseModel()
        self.surface = NativeSurface(
            self.model.view(),
            stylesheet=load_stylesheet(),
            background="#080b0f",
            renderer_backend=renderer_backend,
        )

    def click_text(self, text: str, *, occurrence: int = 0):
        box = self.box_with_text(text, event="onClick", occurrence=occurrence)
        return self.surface.click(box.x + 2, box.y + 2)

    def box_with_text(
        self,
        text: str,
        *,
        event: str | None = None,
        occurrence: int = 0,
    ):
        self.surface.refresh()
        matches = [box for box in self.surface.layout.boxes if box.text == text]
        if event is not None:
            matches = [box for box in matches if event in box.events]
        if occurrence < len(matches):
            return matches[occurrence]
        raise KeyError(f"No native box with text {text!r}.")

    def visible_texts(self) -> list[str]:
        self.surface.refresh()
        return [box.text for box in self.surface.layout.boxes if box.text]


class MissionExecShowcaseModel:
    def __init__(self) -> None:
        self.status = signal("RUNNING")
        self.elapsed_seconds = signal(142)
        self.paused = signal(False)
        self.active_filter = signal("ALL")
        self.active_event_filter = signal("ALL")
        self.logs = signal(list(INITIAL_LOGS))
        self.events = signal(list(INITIAL_EVENTS))
        self.pending_approval = signal(None)
        self.log_scroll_y = signal(0)
        self.event_scroll_y = signal(0)
        self.runtime_probe = signal(
            {
                "frame": 0,
                "tone": "ok",
                "label": "Runtime probe online",
                "last": "Fake appliance mirror is feeding deterministic telemetry.",
            }
        )
        self.elapsed = computed(lambda: _format_elapsed(self.elapsed_seconds.value))
        self.status_tone = computed(lambda: _status_tone(self.status.value))
        self.visible_logs = computed(self._visible_logs)
        self.visible_events = computed(self._visible_events)
        self.log_count = computed(lambda: f"{len(self.visible_logs.value)} lines")
        self.event_count = computed(lambda: f"{len(self.visible_events.value)} events")
        self.pause_label = computed(
            lambda: "RESUME SIMULATION" if self.paused.value else "PAUSE SIMULATION"
        )
        self.approval_open = computed(lambda: self.pending_approval.value is not None)

    def view(self):
        return MissionExecShowcaseScreen(model=self)

    def set_filter(self, value: str) -> None:
        self.active_filter.set(value)
        self.log_scroll_y.set(0)
        self._set_probe("ok", f"{value} log filter active", "Terminal viewport changed.")

    def set_event_filter(self, value: str) -> None:
        self.active_event_filter.set(value)
        self.event_scroll_y.set(0)
        self._set_probe("ok", f"{value} event filter active", "Timeline viewport changed.")

    def queue_approval(self) -> None:
        self.pending_approval.set(
            {
                "step_id": "relay-isolation",
                "summary": "Operator approval required",
                "detail": (
                    "Fake relay-isolation step. No appliance, bridge, or runner is called."
                ),
            }
        )
        self.status.set("APPROVAL PENDING")
        self.paused.set(True)
        self._append_log("warn", "approval: relay-isolation is waiting for operator review")
        self._append_event("APPROVAL", "warn", "Relay isolation step requires approval")
        self._set_probe("warn", "Approval queued", "Simulation paused at operator gate.")

    def approve_approval(self) -> None:
        step_id = self._approval_step()
        self.pending_approval.set(None)
        self.status.set("RUNNING")
        self.paused.set(False)
        self._append_log("ok", f"approval: {step_id} approved; fake execution resumed")
        self._append_event("APPROVE", "ok", f"Approved fake step {step_id}")
        self._set_probe("ok", "Approval accepted", "Simulation resumed after approval.")

    def deny_approval(self) -> None:
        step_id = self._approval_step()
        self.pending_approval.set(None)
        self.status.set("ABORT STAGED")
        self.paused.set(True)
        self._append_log("warn", f"approval: {step_id} denied; abort path staged")
        self._append_event("ABORT", "warn", f"Denied fake step {step_id}")
        self._set_probe("warn", "Approval denied", "Abort path staged without side effects.")

    def cancel_approval(self) -> None:
        self.pending_approval.set(None)
        self.status.set("PAUSED")
        self.paused.set(True)
        self._append_log("info", "approval: operator closed review dialog")
        self._append_event("REVIEW", "action", "Approval review closed")
        self._set_probe("ok", "Approval review closed", "Simulation remains paused.")

    def toggle_pause(self) -> None:
        next_value = not self.paused.value
        self.paused.set(next_value)
        self.status.set("PAUSED" if next_value else "RUNNING")
        self._append_log(
            "warn" if next_value else "ok",
            "operator: simulation paused" if next_value else "operator: simulation resumed",
        )
        self._append_event(
            "PAUSE" if next_value else "RESUME",
            "warn" if next_value else "ok",
            "Simulation paused" if next_value else "Simulation resumed",
        )
        self._set_probe(
            "warn" if next_value else "ok",
            "Simulation paused" if next_value else "Simulation resumed",
            "Elapsed state and UI labels updated deterministically.",
        )

    def stage_abort(self) -> None:
        self.status.set("ABORT STAGED")
        self.paused.set(True)
        self.pending_approval.set(None)
        self._append_log("warn", "operator: abort path staged; no external command dispatched")
        self._append_event("ABORT", "warn", "Abort path staged for fake mission")
        self._set_probe("warn", "Abort staged", "Deterministic local state changed only.")

    def clear_logs(self) -> None:
        self.logs.set([])
        self.log_scroll_y.set(0)
        self._set_probe("ok", "Terminal cleared", "Visible telemetry buffer is empty.")

    def export_logs(self) -> None:
        self._append_log("action", "export: prepared deterministic telemetry bundle")
        self._append_event("EXPORT", "action", "Fake telemetry bundle prepared")
        self._set_probe("ok", "Export prepared", "No filesystem write performed by the UI action.")

    def simulate_frame(self) -> None:
        frame = int(self.runtime_probe.value["frame"]) + 1
        level, tag, message = FRAME_SAMPLES[(frame - 1) % len(FRAME_SAMPLES)]
        self.elapsed_seconds.set(self.elapsed_seconds.value + 9)
        self._append_log(level, f"frame {frame:03d}: {message}")
        self._append_event(
            tag,
            "warn" if level == "warn" else "ok",
            f"Frame {frame:03d}: {message}",
        )
        self._set_probe(
            "warn" if level == "warn" else "ok",
            f"Frame {frame:03d} accepted",
            message,
            frame=frame,
        )

    def on_log_scroll(self, next_scroll_y: int) -> None:
        self.log_scroll_y.set(next_scroll_y)

    def on_event_scroll(self, next_scroll_y: int) -> None:
        self.event_scroll_y.set(next_scroll_y)

    def _visible_logs(self) -> list[LogEntry]:
        active = self.active_filter.value.lower()
        if active == "all":
            return list(self.logs.value)
        return [line for line in self.logs.value if line.level == active]

    def _visible_events(self) -> list[EventEntry]:
        active = self.active_event_filter.value.lower()
        if active == "all":
            return list(self.events.value)
        return [event for event in self.events.value if event.severity == active]

    def _append_log(self, level: str, message: str) -> None:
        index = len(self.logs.value) + 1
        self.logs.set(
            [
                *self.logs.value,
                LogEntry(
                    f"log-live-{index:03d}",
                    f"09:19:{index:02d}",
                    level,
                    message,
                ),
            ][-64:]
        )

    def _append_event(self, tag: str, severity: str, message: str) -> None:
        index = len(self.events.value) + 1
        self.events.set(
            [
                *self.events.value,
                EventEntry(
                    f"event-live-{index:03d}",
                    f"09:19:{index:02d}",
                    tag,
                    severity,
                    message,
                ),
            ][-24:]
        )

    def _set_probe(
        self,
        tone: str,
        label: str,
        last: str,
        *,
        frame: int | None = None,
    ) -> None:
        current = self.runtime_probe.value
        self.runtime_probe.set(
            {
                "frame": current["frame"] if frame is None else frame,
                "tone": tone,
                "label": label,
                "last": last,
            }
        )

    def _approval_step(self) -> str:
        approval = self.pending_approval.value
        if not isinstance(approval, dict):
            return "step"
        return str(approval.get("step_id") or "step")


@component
def MissionExecShowcaseScreen(*, model: MissionExecShowcaseModel):
    return VStack(
        OperatorTopbar(model=model),
        ApprovalDialog(model=model),
        HStack(
            VStack(
                MissionBrief(),
                StatusPanel(model=model),
                PreflightPanel(),
                EmergencyControls(model=model),
                className="mission-left",
                gap=12,
            ),
            VStack(
                RuntimeProbePanel(model=model),
                TelemetryPanel(model=model),
                EventTimelinePanel(model=model),
                className="mission-right",
                gap=12,
            ),
            className="mission-exec-main",
            gap=16,
        ),
        className="mission-exec-shell",
        gap=6,
    )


@component
def OperatorTopbar(*, model: MissionExecShowcaseModel):
    return Toolbar(
        VStack(
            Text("OTOE", className="brand-mark"),
            Text("Mission Exec", className="brand-title"),
            className="brand-lockup",
            gap=2,
        ),
        Text("Operator Console / appliance runtime showcase", className="brand-subtitle"),
        Badge("PRE-ALPHA", tone="warn", className="chrome-badge"),
        Badge("FAKE DATA", tone="neutral", className="chrome-badge"),
        Badge(model.status, tone=model.status_tone, className="chrome-badge status-badge"),
        Badge(model.elapsed, tone="info", className="chrome-badge elapsed-badge"),
        className="topbar mission-chrome",
        gap=10,
    )


@component
def MissionBrief():
    return Card(
        VStack(
            Text("Mission brief", className="section-kicker"),
            Text("Mission Exec", className="mission-title"),
            Text("Standalone Otoe operator surface.", className="mission-copy"),
            Text(
                "All mission state is fake and local.",
                className="mission-copy",
            ),
            VStack(
                HStack(
                    FactTile(fact=MISSION_FACT_ROWS[0][0]),
                    FactTile(fact=MISSION_FACT_ROWS[0][1]),
                    FactTile(fact=MISSION_FACT_ROWS[0][2]),
                    className="mission-fact-row",
                    gap=8,
                ),
                HStack(
                    FactTile(fact=MISSION_FACT_ROWS[1][0]),
                    FactTile(fact=MISSION_FACT_ROWS[1][1]),
                    FactTile(fact=MISSION_FACT_ROWS[1][2]),
                    className="mission-fact-row",
                    gap=8,
                ),
                className="mission-facts",
                gap=6,
            ),
            className="mission-brief",
            gap=10,
        ),
        className="mission-brief-card",
    )


@component
def FactTile(*, fact: MissionFact):
    return VStack(
        Text(fact.label, className="fact-label"),
        Text(fact.value, className="fact-value"),
        className="mission-fact",
        gap=3,
    )


@component
def StatusPanel(*, model: MissionExecShowcaseModel):
    status_class = computed(
        lambda: "status-value status-paused" if model.paused.value else "status-value"
    )
    return Card(
        VStack(
            HStack(
                VStack(
                    Text("Status", className="status-label"),
                    Text(model.status, className=status_class),
                    className="status-block",
                    gap=4,
                ),
                VStack(
                    Text("Elapsed", className="status-label align-right"),
                    Text(model.elapsed, className="clock-value"),
                    className="status-block clock-block",
                    gap=4,
                ),
                className="status-grid",
                gap=12,
            ),
            Show(
                Text("Simulation paused; actions remain local.", className="paused-strip"),
                when=model.paused,
                fallback=Text("Running on local fixture data.", className="status-note"),
            ),
            className="status-body",
            gap=10,
        ),
        className="status-card",
    )


@component
def PreflightPanel():
    return Card(
        VStack(
            HStack(
                Text("Preflight", className="section-title"),
                Badge("5/5 CHECKED", tone="success", className="ready-meter"),
                className="preflight-head",
                gap=8,
            ),
            Text("Preflight checklist", className="section-kicker"),
            VStack(
                For(
                    each=PREFLIGHT_CHECKS,
                    key=lambda item: item.id,
                    children=lambda item: PreflightRow(item=item),
                ),
                className="preflight-list",
                gap=7,
            ),
            className="preflight-body",
            gap=8,
        ),
        className="preflight-card",
    )


@component
def PreflightRow(*, item: PreflightCheck):
    return HStack(
        Text(item.status, className=_preflight_state_class(item.tone)),
        VStack(
            Text(item.label, className="check-label"),
            Text(item.detail, className="check-detail"),
            className="check-copy",
            gap=2,
        ),
        className=_preflight_row_class(item.tone),
        gap=8,
    )


@component
def EmergencyControls(*, model: MissionExecShowcaseModel):
    return Card(
        VStack(
            Text("Emergency Controls", className="danger-title"),
            Text(
                "State-only abort; no hardware call.",
                className="danger-copy",
            ),
            HStack(
                ActionButton(
                    "STAGE ABORT",
                    variant="danger",
                    className="stage-abort-button",
                    onClick=model.stage_abort,
                ),
                ActionButton(
                    model.pause_label,
                    variant="ghost",
                    className="pause-button",
                    onClick=model.toggle_pause,
                ),
                className="emergency-buttons",
                gap=8,
            ),
            className="emergency-body",
            gap=8,
        ),
        className="emergency-card",
    )


@component
def RuntimeProbePanel(*, model: MissionExecShowcaseModel):
    probe_label = computed(lambda: str(model.runtime_probe.value["tone"]).upper())
    probe_tone = computed(
        lambda: "warn" if str(model.runtime_probe.value["tone"]) == "warn" else "success"
    )
    return Card(
        HStack(
            VStack(
                HStack(
                    Text(
                        computed(lambda: f"FRAME {int(model.runtime_probe.value['frame']):03d}"),
                        className="probe-frame",
                    ),
                    Badge(probe_label, tone=probe_tone, className="probe-badge"),
                    className="probe-head",
                    gap=8,
                ),
                Text("Runtime probe panel", className="probe-title"),
                Text(computed(lambda: str(model.runtime_probe.value["label"])), className="probe-copy"),
                Text(computed(lambda: str(model.runtime_probe.value["last"])), className="probe-last"),
                className="probe-copy-stack",
                gap=4,
            ),
            VStack(
                ActionButton(
                    "SIMULATE FRAME",
                    variant="info",
                    className="probe-button",
                    onClick=model.simulate_frame,
                ),
                ActionButton(
                    "QUEUE APPROVAL",
                    variant="ghost",
                    className="probe-button",
                    onClick=model.queue_approval,
                ),
                ActionButton(
                    "EXPORT",
                    variant="ghost",
                    size="sm",
                    className="probe-button compact-button",
                    onClick=model.export_logs,
                ),
                className="probe-actions",
                gap=7,
            ),
            className="runtime-probe",
            gap=14,
        ),
        className="probe-card",
    )


@component
def TelemetryPanel(*, model: MissionExecShowcaseModel):
    return Card(
        VStack(
            HStack(
                Text("Live Telemetry", className="section-title"),
                Badge(model.log_count, tone="neutral", className="count-badge"),
                className="telemetry-head",
                gap=8,
            ),
            HStack(
                Tabs(
                    *[
                        FilterTab(
                            label=label,
                            active_filter=model.active_filter,
                            on_filter=model.set_filter,
                        )
                        for label in LOG_FILTERS
                    ],
                    className="telemetry-tabs",
                    gap=6,
                ),
                ActionButton(
                    "CLEAR",
                    variant="ghost",
                    size="sm",
                    className="toolbar-button",
                    onClick=model.clear_logs,
                ),
                className="telemetry-filter-row",
                gap=8,
            ),
            ScrollView(
                Show(
                    VStack(
                        For(
                            each=model.visible_logs,
                            key=lambda line: line.id,
                            children=lambda line: LogLine(line=line),
                        ),
                        className="terminal-lines",
                        gap=5,
                    ),
                    when=computed(lambda: len(model.visible_logs.value) > 0),
                    fallback=EmptyLogState(),
                ),
                className="terminal-scroll",
                scrollY=model.log_scroll_y,
                onScroll=model.on_log_scroll,
            ),
            className="telemetry-body",
            gap=9,
        ),
        className="telemetry-card",
    )


@component
def EventTimelinePanel(*, model: MissionExecShowcaseModel):
    return Card(
        VStack(
            HStack(
                Text("Event Timeline", className="section-title"),
                Badge(model.event_count, tone="neutral", className="count-badge"),
                className="timeline-head",
                gap=8,
            ),
            Tabs(
                *[
                    FilterTab(
                        label=label,
                        active_filter=model.active_event_filter,
                        on_filter=model.set_event_filter,
                    )
                    for label in EVENT_FILTERS
                ],
                className="event-tabs",
                gap=6,
            ),
            ScrollView(
                VStack(
                    For(
                        each=model.visible_events,
                        key=lambda event: event.id,
                        children=lambda event: EventRow(event=event),
                    ),
                    className="event-list",
                    gap=6,
                ),
                className="timeline-scroll",
                scrollY=model.event_scroll_y,
                onScroll=model.on_event_scroll,
            ),
            className="timeline-body",
            gap=8,
        ),
        className="timeline-card",
    )


def FilterTab(*, label: str, active_filter, on_filter):
    return TabButton(
        label,
        active=computed(lambda: active_filter.value == label),
        className="filter-button",
        onClick=lambda: on_filter(label),
    )


@component
def LogLine(*, line: LogEntry):
    return HStack(
        Text(line.time, className="log-time"),
        Text(line.level.upper(), className=_log_level_class(line.level)),
        Text(line.message, className="log-message"),
        className=_log_row_class(line.level),
        gap=8,
    )


@component
def EventRow(*, event: EventEntry):
    return HStack(
        Text(event.time, className="event-time"),
        Text(event.tag, className=_event_tag_class(event.severity)),
        Text(event.message, className="event-message"),
        className=_event_row_class(event.severity),
        gap=8,
    )


@component
def EmptyLogState():
    return VStack(
        Text("No telemetry lines", className="empty-title"),
        Text("Filters or CLEAR can empty the visible terminal buffer.", className="empty-copy"),
        className="empty-state",
        gap=4,
    )


@component
def ApprovalDialog(*, model: MissionExecShowcaseModel):
    return Dialog(
        Text(computed(lambda: f"STEP / {_approval_field(model, 'step_id', '--')}"), className="approval-step"),
        Text(computed(lambda: _approval_field(model, "detail", "")), className="approval-copy"),
        HStack(
            ActionButton(
                "APPROVE STEP",
                variant="success",
                className="approval-approve",
                onClick=model.approve_approval,
            ),
            ActionButton(
                "DENY REQUEST",
                variant="danger",
                className="approval-deny",
                onClick=model.deny_approval,
            ),
            ActionButton(
                "CANCEL REVIEW",
                variant="ghost",
                className="approval-cancel",
                onClick=model.cancel_approval,
            ),
            className="approval-actions",
            gap=8,
        ),
        open=model.approval_open,
        title="Operator approval required",
        description=computed(lambda: _approval_field(model, "summary", "Approval pending.")),
        className="approval-dialog",
    )


def _approval_field(model: MissionExecShowcaseModel, field: str, default: str) -> str:
    value: Any = model.pending_approval.value
    if not isinstance(value, dict):
        return default
    return str(value.get(field) or default)


def _preflight_state_class(tone: str) -> str:
    return PREFLIGHT_STATE_CLASSES.get(tone, PREFLIGHT_STATE_CLASSES["ok"])


def _preflight_row_class(tone: str) -> str:
    return PREFLIGHT_ROW_CLASSES.get(tone, PREFLIGHT_ROW_CLASSES["ok"])


def _log_level_class(level: str) -> str:
    return LOG_LEVEL_CLASSES.get(level, LOG_LEVEL_CLASSES["info"])


def _log_row_class(level: str) -> str:
    return LOG_ROW_CLASSES.get(level, LOG_ROW_CLASSES["info"])


def _event_tag_class(severity: str) -> str:
    return EVENT_TAG_CLASSES.get(severity, EVENT_TAG_CLASSES["ok"])


def _event_row_class(severity: str) -> str:
    return EVENT_ROW_CLASSES.get(severity, EVENT_ROW_CLASSES["ok"])


def _format_elapsed(seconds: int) -> str:
    minutes, secs = divmod(max(0, int(seconds)), 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def _status_tone(status: str) -> str:
    normalized = status.upper()
    if "ABORT" in normalized:
        return "danger"
    if "APPROVAL" in normalized or normalized == "PAUSED":
        return "warn"
    if normalized == "RUNNING":
        return "success"
    return "neutral"
