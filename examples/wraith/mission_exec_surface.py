from __future__ import annotations

from otoe import For, HStack, ScrollView, Text, VStack, component, computed
from otoe.ui import ActionButton, Badge, Card, Dialog, TabButton, Tabs, Toolbar


FILTERS = ["ALL", "INFO", "OK", "WARN", "SIG", "CMD"]
EVENT_FILTERS = ["ALL", "OK", "WARN"]


@component
def MissionExecSurface(
    *,
    mission,
    log_lines,
    events,
    active_filter,
    active_event_filter,
    pending_approval,
    status,
    elapsed,
    paused,
    runtime_probe,
    on_filter,
    on_event_filter,
    on_request_approval,
    on_approve_approval,
    on_deny_approval,
    on_abort,
    on_pause,
    on_clear,
    on_export,
    on_simulate,
):
    visible_lines = computed(lambda: _visible_lines(log_lines.value, active_filter.value))
    visible_events = computed(lambda: _visible_events(events.value, active_event_filter.value))
    filtered_count = computed(lambda: f"{len(visible_lines.value)} lines")
    filtered_event_count = computed(lambda: f"{len(visible_events.value)} events")
    pause_label = computed(lambda: "RESUME CAPTURE" if paused.value else "PAUSE CAPTURE")
    status_class = computed(
        lambda: "exec-status-value is-paused" if paused.value else "exec-status-value"
    )
    probe_frame = computed(lambda: f"FRAME {runtime_probe.value['frame']:03d}")
    probe_badge = computed(lambda: runtime_probe.value["tone"].upper())
    approval_open = computed(lambda: pending_approval.value is not None)

    return VStack(
        Toolbar(
            Text("WRAITH OS", className="brand"),
            Text("Mission Exec / Handshake Hunter", className="campaign"),
            Badge(status, tone="success", className="indicator"),
            Badge(elapsed, tone="neutral", className="indicator"),
            className="topbar",
            gap=8,
        ),
        HStack(
            VStack(
                MissionBrief(mission=mission),
                Card(
                    HStack(
                        VStack(
                            Text("STATUS", className="eyebrow"),
                            Text(status, className=status_class),
                            className="exec-status-copy",
                        ),
                        VStack(
                            Text("ELAPSED", className="eyebrow align-right"),
                            Text(elapsed, className="exec-timer"),
                            className="exec-timer-box",
                        ),
                        className="exec-status-row",
                        gap=12,
                    ),
                    className="exec-status-panel",
                ),
                PreflightPanel(mission=mission),
                Card(
                    VStack(
                        Text("EMERGENCY CONTROLS", className="danger-label"),
                        ActionButton(
                            "ABORT MISSION",
                            variant="danger",
                            className="danger-button",
                            onClick=on_abort,
                        ),
                        ActionButton(
                            pause_label,
                            variant="ghost",
                            className="ghost-button",
                            onClick=on_pause,
                        ),
                        className="exec-actions",
                        gap=10,
                    ),
                    className="exec-danger-panel",
                ),
                className="exec-left",
                gap=12,
            ),
            VStack(
                Card(
                    HStack(
                        VStack(
                            HStack(
                                Text("CAPTURE FEED", className="section-heading"),
                                Badge(
                                    probe_badge,
                                    tone=computed(lambda: runtime_probe.value["tone"]),
                                    className="exec-probe-badge",
                                ),
                                className="exec-probe-head",
                                gap=8,
                            ),
                            Text(probe_frame, className="exec-probe-frame"),
                            Text(
                                computed(lambda: runtime_probe.value["label"]),
                                className="exec-probe-label",
                            ),
                            Text(
                                computed(lambda: runtime_probe.value["last"]),
                                className="exec-probe-copy",
                            ),
                            className="exec-probe-main",
                            gap=4,
                        ),
                        VStack(
                            ActionButton(
                                "SIMULATE FRAME",
                                variant="info",
                                className="probe-button",
                                onClick=on_simulate,
                            ),
                            ActionButton(
                                "QUEUE APPROVAL",
                                variant="ghost",
                                className="probe-button approval-queue-button",
                                onClick=on_request_approval,
                            ),
                            className="probe-actions",
                            gap=8,
                        ),
                        className="exec-probe",
                        gap=14,
                    ),
                    className="exec-probe-panel",
                ),
                Card(
                    VStack(
                        HStack(
                            Text("LIVE TELEMETRY / wlan1mon", className="section-heading"),
                            Badge(filtered_count, tone="neutral", className="exec-count"),
                            className="exec-toolbar-head",
                        ),
                        Tabs(
                            *[
                                FilterButton(
                                    label=label,
                                    active_filter=active_filter,
                                    on_filter=on_filter,
                                )
                                for label in FILTERS
                            ],
                            ActionButton(
                                "CLEAR",
                                variant="ghost",
                                size="sm",
                                className="ghost-button compact",
                                onClick=on_clear,
                            ),
                            ActionButton(
                                "EXPORT",
                                variant="ghost",
                                size="sm",
                                className="ghost-button compact",
                                onClick=on_export,
                            ),
                            className="exec-filters",
                            gap=8,
                        ),
                        ScrollView(
                            For(
                                each=visible_lines,
                                key=lambda line: line["id"],
                                children=lambda line: LogLine(line=line),
                            ),
                            className="exec-terminal",
                        ),
                        className="exec-telemetry",
                        gap=12,
                    ),
                    className="exec-terminal-panel",
                ),
                Card(
                    VStack(
                        HStack(
                            Text("EVENT TIMELINE", className="section-heading"),
                            Badge(filtered_event_count, tone="neutral", className="exec-count"),
                            className="exec-toolbar-head",
                        ),
                        Tabs(
                            *[
                                FilterButton(
                                    label=label,
                                    active_filter=active_event_filter,
                                    on_filter=on_event_filter,
                                )
                                for label in EVENT_FILTERS
                            ],
                            className="exec-filters exec-event-filters",
                            gap=8,
                        ),
                        For(
                            each=visible_events,
                            key=lambda event: event["id"],
                            children=lambda event: EventRow(event=event),
                        ),
                        className="exec-events",
                        gap=8,
                    ),
                    className="exec-events-panel",
                ),
                className="exec-right",
                gap=12,
            ),
            className="mission-exec",
            gap=16,
        ),
        ApprovalDialog(
            approval=pending_approval,
            open=approval_open,
            on_approve=on_approve_approval,
            on_deny=on_deny_approval,
        ),
        className="mission-exec-shell",
        gap=0,
    )


@component
def MissionBrief(*, mission):
    return Card(
        VStack(
            Text(
                computed(
                    lambda: (
                        f"MISSION / {mission.value['vector']} / "
                        f"OPSEC {mission.value['opsec']}"
                    )
                ),
                className="mission-brief-tag",
            ),
            Text(computed(lambda: mission.value["name"]), className="mission-brief-title"),
            Text(
                computed(lambda: mission.value["description"]),
                className="mission-brief-copy",
            ),
            HStack(
                MissionFact(label="TARGET", value=computed(lambda: mission.value["target"])),
                MissionFact(label="SCOPE", value=computed(lambda: mission.value["scope"])),
                MissionFact(label="ASSET", value=computed(lambda: mission.value["asset"])),
                MissionFact(label="PROFILE", value=computed(lambda: mission.value["profile"])),
                MissionFact(label="VALIDATION", value=computed(lambda: mission.value["validation"])),
                MissionFact(label="POSTURE", value=computed(lambda: mission.value["posture"])),
                className="mission-facts",
                gap=10,
            ),
            className="mission-brief",
            gap=12,
        ),
        className="mission-brief-panel",
    )


@component
def MissionFact(*, label, value):
    return VStack(
        Text(label, className="fact-label"),
        Text(value, className="fact-value"),
        className="mission-fact",
        gap=4,
    )


@component
def PreflightPanel(*, mission):
    return Card(
        VStack(
            HStack(
                Text("PREFLIGHT", className="section-heading"),
                Badge("5/5 READY", tone="success", className="ready-pill"),
                className="exec-toolbar-head",
            ),
            CheckRow(label="Policy guard", value=computed(lambda: f"{mission.value['scope']} approved")),
            CheckRow(label="Hardware", value=computed(lambda: f"{mission.value['asset']} / monitor")),
            CheckRow(label="Scope", value=computed(lambda: mission.value["target"])),
            CheckRow(label="Posture", value="stealth / passive"),
            CheckRow(label="Vault", value="sealed / demo-key"),
            className="preflight-list",
            gap=8,
        ),
        className="preflight-panel",
    )


@component
def CheckRow(*, label, value):
    return HStack(
        Text("OK", className="check-icon"),
        Text(label, className="check-label"),
        Text(value, className="check-value"),
        className="check-row",
        gap=10,
    )


@component
def ApprovalDialog(*, approval, open, on_approve, on_deny):
    return Dialog(
        VStack(
            Text(computed(lambda: f"STEP / {_approval_value(approval, 'step_id', '--')}"), className="approval-step"),
            Text(computed(lambda: _approval_value(approval, "detail", "")), className="approval-copy"),
            HStack(
                ActionButton(
                    "APPROVE STEP",
                    variant="success",
                    className="approval-approve",
                    onClick=on_approve,
                ),
                ActionButton(
                    "DENY / ABORT",
                    variant="danger",
                    className="approval-deny",
                    onClick=on_deny,
                ),
                className="approval-actions",
                gap=10,
            ),
            className="approval-body",
            gap=12,
        ),
        open=open,
        title="Operator approval required",
        description=computed(lambda: _approval_value(approval, "summary", "Combo step is waiting.")),
        className="approval-dialog",
    )


def FilterButton(*, label, active_filter, on_filter):
    return TabButton(
        label,
        active=computed(lambda: active_filter.value == label),
        className="filter-button",
        onClick=lambda: on_filter(label),
    )


@component
def LogLine(*, line):
    return HStack(
        Text(line["ts"], className="log-ts"),
        Text(line["lvl"], className=f"log-level is-{line['lvl']}"),
        Text(line["msg"], className="log-message"),
        className=f"log-line is-{line['lvl']}",
        gap=10,
    )


@component
def EventRow(*, event):
    return HStack(
        Text(event["ts"], className="event-ts"),
        Text(event["tag"], className=f"event-tag is-{event['sev']}"),
        Text(event["msg"], className="event-message"),
        className=f"event-row is-{event['sev']}",
        gap=10,
    )


def _visible_lines(lines, active_filter):
    if active_filter == "ALL":
        return list(lines)
    tone = active_filter.lower()
    return [line for line in lines if line["lvl"] == tone]


def _visible_events(events, active_filter):
    if active_filter == "ALL":
        return list(events)
    tone = active_filter.lower()
    return [event for event in events if event["sev"] == tone]


def _approval_value(approval, key, default):
    current = approval.value
    if not current:
        return default
    return current.get(key) or default
