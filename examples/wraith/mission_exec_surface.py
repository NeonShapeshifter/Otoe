from __future__ import annotations

from otoe import Button, For, HStack, Panel, ScrollView, Text, VStack, component, computed


FILTERS = ["ALL", "INFO", "OK", "WARN", "SIG", "CMD"]


@component
def MissionExecSurface(
    *,
    mission,
    log_lines,
    events,
    active_filter,
    status,
    elapsed,
    paused,
    runtime_probe,
    on_filter,
    on_abort,
    on_pause,
    on_clear,
    on_export,
    on_simulate,
):
    visible_lines = computed(lambda: _visible_lines(log_lines.value, active_filter.value))
    filtered_count = computed(lambda: f"{len(visible_lines.value)} lines")
    pause_label = computed(lambda: "RESUME CAPTURE" if paused.value else "PAUSE CAPTURE")
    status_class = computed(
        lambda: "exec-status-value is-paused" if paused.value else "exec-status-value"
    )
    probe_frame = computed(lambda: f"FRAME {runtime_probe.value['frame']:03d}")
    probe_badge = computed(lambda: runtime_probe.value["tone"].upper())
    probe_badge_class = computed(
        lambda: f"exec-probe-badge is-{runtime_probe.value['tone']}"
    )

    return VStack(
        HStack(
            Text("WRAITH OS", className="brand"),
            Text("Mission Exec / Handshake Hunter", className="campaign"),
            Text(status, className="indicator"),
            Text(elapsed, className="indicator"),
            className="topbar",
            gap=8,
        ),
        HStack(
            VStack(
                MissionBrief(mission=mission),
                Panel(
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
                Panel(
                    VStack(
                        Text("EMERGENCY CONTROLS", className="danger-label"),
                        Button("ABORT MISSION", className="danger-button", onClick=on_abort),
                        Button(pause_label, className="ghost-button", onClick=on_pause),
                        className="exec-actions",
                        gap=10,
                    ),
                    className="exec-danger-panel",
                ),
                className="exec-left",
                gap=12,
            ),
            VStack(
                Panel(
                    HStack(
                        VStack(
                            HStack(
                                Text("CAPTURE FEED", className="section-heading"),
                                Text(probe_badge, className=probe_badge_class),
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
                        Button("SIMULATE FRAME", className="probe-button", onClick=on_simulate),
                        className="exec-probe",
                        gap=14,
                    ),
                    className="exec-probe-panel",
                ),
                Panel(
                    VStack(
                        HStack(
                            Text("LIVE TELEMETRY / wlan1mon", className="section-heading"),
                            Text(filtered_count, className="exec-count"),
                            className="exec-toolbar-head",
                        ),
                        HStack(
                            *[
                                FilterButton(
                                    label=label,
                                    active_filter=active_filter,
                                    on_filter=on_filter,
                                )
                                for label in FILTERS
                            ],
                            Button("CLEAR", className="ghost-button compact", onClick=on_clear),
                            Button("EXPORT", className="ghost-button compact", onClick=on_export),
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
                Panel(
                    VStack(
                        HStack(
                            Text("EVENT TIMELINE", className="section-heading"),
                            Text(computed(lambda: f"{len(events.value)} events"), className="exec-count"),
                            className="exec-toolbar-head",
                        ),
                        For(
                            each=events,
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
        className="mission-exec-shell",
        gap=0,
    )


@component
def MissionBrief(*, mission):
    return Panel(
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
    return Panel(
        VStack(
            HStack(
                Text("PREFLIGHT", className="section-heading"),
                Text("5/5 READY", className="ready-pill"),
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


def FilterButton(*, label, active_filter, on_filter):
    class_name = computed(
        lambda: "filter-button is-active" if active_filter.value == label else "filter-button"
    )
    return Button(label, className=class_name, onClick=lambda: on_filter(label))


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
