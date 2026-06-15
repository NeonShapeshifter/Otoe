from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from otoe import (
    Button,
    For,
    HStack,
    Input,
    NativeRendererBackend,
    NativeSurface,
    Panel,
    ScrollView,
    ShortcutScope,
    Show,
    Text,
    VStack,
    component,
    computed,
    css,
    signal,
)
from otoe.ui import ActionButton, Card, Dialog, FocusScope, ListRow, StatusPill


STYLE_PATH = Path(__file__).resolve().parents[1] / "preview" / "wraith_input_console.css"


@dataclass(frozen=True)
class Mission:
    id: str
    name: str
    status: str
    status_tone: str
    risk: str
    risk_tone: str
    last_run: str
    description: str
    owner: str
    zone: str
    mode: str


@dataclass(frozen=True)
class LogEntry:
    id: str
    time: str
    severity: str
    message: str


MISSIONS = (
    Mission(
        id="WR-018",
        name="Thermal Guard",
        status="Ready",
        status_tone="success",
        risk="Low",
        risk_tone="success",
        last_run="08:14",
        description="Validate cooling envelope and idle actuator state before handoff.",
        owner="Ops",
        zone="Cage A",
        mode="Read-only probe",
    ),
    Mission(
        id="WR-027",
        name="Relay Sweep",
        status="Queued",
        status_tone="info",
        risk="Medium",
        risk_tone="warn",
        last_run="07:48",
        description="Exercise non-destructive relay diagnostics against the staging bus.",
        owner="Runtime",
        zone="Bench 3",
        mode="Dry-run default",
    ),
    Mission(
        id="WR-031",
        name="Latch Audit",
        status="Needs confirm",
        status_tone="warn",
        risk="High",
        risk_tone="danger",
        last_run="yesterday",
        description="Inspect latch metadata and require operator confirmation before execute.",
        owner="Safety",
        zone="Panel B",
        mode="Operator gated",
    ),
    Mission(
        id="WR-044",
        name="Sensor Mirror",
        status="Pinned",
        status_tone="neutral",
        risk="Low",
        risk_tone="success",
        last_run="06:35",
        description="Mirror telemetry headers for appliance display validation.",
        owner="Telemetry",
        zone="Rack 1",
        mode="Passive capture",
    ),
)


INITIAL_LOGS = (
    LogEntry("log-001", "08:10:03", "info", "console booted in portable input mode"),
    LogEntry("log-002", "08:10:06", "ok", "mission WR-018 selected as primary target"),
    LogEntry("log-003", "08:10:09", "warn", "execute remains confirmation-gated"),
    LogEntry("log-004", "08:10:12", "info", "secondary actions available through More"),
)


def app():
    return WraithInputConsoleModel().view()


def load_stylesheet():
    return css(STYLE_PATH.read_text(encoding="utf-8"))


class WraithInputConsoleDemo:
    def __init__(
        self,
        *,
        renderer_backend: NativeRendererBackend | None = None,
    ) -> None:
        self.model = WraithInputConsoleModel()
        self.surface = NativeSurface(
            self.model.view(),
            stylesheet=load_stylesheet(),
            background="#0b1117",
            renderer_backend=renderer_backend,
        )

    def click_text(self, text: str):
        box = self.box_with_text(text, event="onClick")
        return self.surface.click(box.x + 2, box.y + 2)

    def key_down(self, key: str, **modifiers: Any):
        return self.surface.key_down(key, **modifiers)

    def type_search(self, value: str):
        return self.surface.input_text(value, path=self.first_box("Input").path)

    def scroll_logs(self, delta_y: int):
        box = self.first_box("ScrollView")
        return self.surface.scroll(box.x + 2, box.y + 2, delta_y)

    def box_with_text(self, text: str, *, event: str | None = None):
        self.surface.refresh()
        matches = [
            box
            for box in self.surface.layout.boxes
            if box.text == text
        ]
        if event is not None:
            for box in matches:
                if event in box.events:
                    return box
            for box in matches:
                if box.events:
                    return box
        if matches:
            return matches[0]
        raise KeyError(f"No native box with text {text!r}.")

    def first_box(self, name: str):
        self.surface.refresh()
        for box in self.surface.layout.boxes:
            if box.name == name:
                return box
        raise KeyError(f"No native box named {name!r}.")

    def visible_texts(self) -> list[str]:
        self.surface.refresh()
        return [
            box.text
            for box in self.surface.layout.boxes
            if box.text and box.name != "Input"
        ]


class WraithInputConsoleModel:
    def __init__(self) -> None:
        self.query = signal("")
        self.selected_mission_id = signal(MISSIONS[0].id)
        self.runtime_status = signal("Ready")
        self.safe_mode = signal(False)
        self.confirm_open = signal(False)
        self.context_open = signal(False)
        self.command_open = signal(False)
        self.raw_open = signal(False)
        self.pinned_ids = signal((MISSIONS[3].id,))
        self.logs = signal(list(INITIAL_LOGS))
        self.log_scroll_y = signal(0)
        self.visible_missions = computed(self._visible_missions)
        self.selected_mission = computed(self._selected_mission)

    def _visible_missions(self) -> list[Mission]:
        query = self.query.value.strip().lower()
        if not query:
            return list(MISSIONS)
        return [
            mission
            for mission in MISSIONS
            if query in _mission_search_text(mission)
        ]

    def _selected_mission(self) -> Mission:
        for mission in MISSIONS:
            if mission.id == self.selected_mission_id.value:
                return mission
        return MISSIONS[0]

    def set_query(self, value: str) -> None:
        self.query.set(value)
        self.log_scroll_y.set(0)

    def select_mission(self, mission_id: str) -> None:
        self.selected_mission_id.set(mission_id)
        self.raw_open.set(False)
        mission = self.selected_mission.value
        self._append_log("info", f"selected {mission.id} for operator review")

    def dry_run(self) -> None:
        mission = self.selected_mission.value
        self.runtime_status.set("Dry run queued")
        self.command_open.set(False)
        self._append_log("ok", f"dry run queued for {mission.id}")

    def request_execute(self) -> None:
        self.confirm_open.set(True)
        self.context_open.set(False)
        self.command_open.set(False)

    def confirm_execute(self) -> None:
        mission = self.selected_mission.value
        self.confirm_open.set(False)
        self.runtime_status.set("Executing")
        self._append_log("warn", f"confirmed execute for {mission.id}")

    def cancel_execute(self) -> None:
        self.confirm_open.set(False)
        self._append_log("info", "execute cancelled by operator")

    def toggle_safe_mode(self) -> None:
        next_value = not self.safe_mode.value
        self.safe_mode.set(next_value)
        self.runtime_status.set("Safe mode" if next_value else "Ready")
        self._append_log("ok" if next_value else "info", _safe_mode_message(next_value))

    def open_context_actions(self) -> None:
        self.context_open.set(True)
        self.command_open.set(False)
        self.raw_open.set(False)

    def close_context_actions(self) -> None:
        self.context_open.set(False)
        self.raw_open.set(False)

    def copy_mission_id(self) -> None:
        mission = self.selected_mission.value
        self._append_log("info", f"copied mission id {mission.id}")

    def copy_selected_log_line(self) -> None:
        log = self.logs.value[-1]
        self._append_log("info", f"copied selected log line {log.id}")

    def toggle_pin(self) -> None:
        mission = self.selected_mission.value
        pinned = tuple(self.pinned_ids.value)
        if mission.id in pinned:
            self.pinned_ids.set(tuple(item for item in pinned if item != mission.id))
            self._append_log("info", f"unpinned {mission.id}")
            return
        self.pinned_ids.set((*pinned, mission.id))
        self._append_log("ok", f"pinned {mission.id}")

    def inspect_raw_details(self) -> None:
        self.raw_open.set(True)
        self._append_log("info", f"opened raw details for {self.selected_mission.value.id}")

    def open_command_panel(self) -> None:
        self.command_open.set(True)
        self.context_open.set(False)
        self.confirm_open.set(False)
        self._append_log("info", "command panel opened from keyboard shortcut")

    def close_command_panel(self) -> None:
        self.command_open.set(False)

    def set_log_scroll(self, next_scroll_y: int) -> None:
        self.log_scroll_y.set(next_scroll_y)

    def handle_shortcut(self, payload: dict[str, Any]) -> None:
        key = str(payload.get("key") or "")
        if key == "Escape":
            self._dismiss_top_layer()
            return
        if key.lower() == "k" and (payload.get("ctrlKey") or payload.get("metaKey")):
            self.open_command_panel()

    def _dismiss_top_layer(self) -> None:
        if self.confirm_open.value:
            self.confirm_open.set(False)
            return
        if self.command_open.value:
            self.command_open.set(False)
            return
        if self.context_open.value:
            self.close_context_actions()

    def _append_log(self, severity: str, message: str) -> None:
        next_index = len(self.logs.value) + 1
        entry = LogEntry(
            id=f"log-{next_index:03d}",
            time=f"08:{10 + next_index:02d}:{(next_index * 7) % 60:02d}",
            severity=severity,
            message=message,
        )
        self.logs.set([*self.logs.value, entry][-12:])

    def view(self):
        return WraithInputConsole(
            query=self.query,
            visible_missions=self.visible_missions,
            selected_mission=self.selected_mission,
            selected_mission_id=self.selected_mission_id,
            runtime_status=self.runtime_status,
            safe_mode=self.safe_mode,
            confirm_open=self.confirm_open,
            context_open=self.context_open,
            command_open=self.command_open,
            raw_open=self.raw_open,
            pinned_ids=self.pinned_ids,
            logs=self.logs,
            log_scroll_y=self.log_scroll_y,
            on_query=self.set_query,
            on_select_mission=self.select_mission,
            on_dry_run=self.dry_run,
            on_request_execute=self.request_execute,
            on_confirm_execute=self.confirm_execute,
            on_cancel_execute=self.cancel_execute,
            on_toggle_safe_mode=self.toggle_safe_mode,
            on_open_context=self.open_context_actions,
            on_close_context=self.close_context_actions,
            on_copy_mission_id=self.copy_mission_id,
            on_copy_log_line=self.copy_selected_log_line,
            on_toggle_pin=self.toggle_pin,
            on_inspect_raw=self.inspect_raw_details,
            on_open_command=self.open_command_panel,
            on_close_command=self.close_command_panel,
            on_log_scroll=self.set_log_scroll,
            on_shortcut=self.handle_shortcut,
        )


@component
def WraithInputConsole(
    *,
    query,
    visible_missions,
    selected_mission,
    selected_mission_id,
    runtime_status,
    safe_mode,
    confirm_open,
    context_open,
    command_open,
    raw_open,
    pinned_ids,
    logs,
    log_scroll_y,
    on_query,
    on_select_mission,
    on_dry_run,
    on_request_execute,
    on_confirm_execute,
    on_cancel_execute,
    on_toggle_safe_mode,
    on_open_context,
    on_close_context,
    on_copy_mission_id,
    on_copy_log_line,
    on_toggle_pin,
    on_inspect_raw,
    on_open_command,
    on_close_command,
    on_log_scroll,
    on_shortcut,
):
    return ShortcutScope(
        VStack(
            HeaderBar(
                runtime_status=runtime_status,
                safe_mode=safe_mode,
                logs=logs,
                on_open_command=on_open_command,
            ),
            HStack(
                MissionSidebar(
                    query=query,
                    missions=visible_missions,
                    selected_mission_id=selected_mission_id,
                    pinned_ids=pinned_ids,
                    on_query=on_query,
                    on_select=on_select_mission,
                ),
                VStack(
                    MissionDetail(selected_mission=selected_mission, runtime_status=runtime_status),
                    ActionStrip(
                        safe_mode=safe_mode,
                        on_dry_run=on_dry_run,
                        on_request_execute=on_request_execute,
                        on_toggle_safe_mode=on_toggle_safe_mode,
                        on_open_context=on_open_context,
                    ),
                    LogPanel(logs=logs, scroll_y=log_scroll_y, on_scroll=on_log_scroll),
                    className="detail-column",
                    gap=12,
                ),
                className="console-main",
                gap=14,
            ),
            ExecuteDialog(
                open=confirm_open,
                mission=selected_mission,
                on_confirm=on_confirm_execute,
                on_cancel=on_cancel_execute,
            ),
            ContextActionsPanel(
                open=context_open,
                mission=selected_mission,
                pinned_ids=pinned_ids,
                raw_open=raw_open,
                on_copy_mission_id=on_copy_mission_id,
                on_copy_log_line=on_copy_log_line,
                on_toggle_pin=on_toggle_pin,
                on_inspect_raw=on_inspect_raw,
                on_close=on_close_context,
            ),
            CommandPanel(
                open=command_open,
                on_dry_run=on_dry_run,
                on_request_execute=on_request_execute,
                on_open_context=on_open_context,
                on_close=on_close_command,
            ),
            className="wraith-console",
            gap=12,
        ),
        onKeyDown=on_shortcut,
    )


@component
def HeaderBar(*, runtime_status, safe_mode, logs, on_open_command):
    return HStack(
        VStack(
            Text("Wraith Input Console", className="app-title"),
            Text("Portable touch, mouse, and keyboard validation surface", className="app-subtitle"),
            className="brand-stack",
            gap=2,
        ),
        StatusPill(runtime_status, tone=computed(lambda: _runtime_tone(runtime_status.value))),
        StatusPill(
            computed(lambda: "Safe Mode On" if safe_mode.value else "Safe Mode Off"),
            tone=computed(lambda: "success" if safe_mode.value else "neutral"),
        ),
        Text(computed(lambda: f"{len(logs.value)} logs"), className="topbar-meta"),
        Button("Ctrl+K", className="shortcut-button", onClick=on_open_command),
        className="topbar",
        gap=10,
    )


@component
def MissionSidebar(*, query, missions, selected_mission_id, pinned_ids, on_query, on_select):
    return Card(
        VStack(
            HStack(
                Text("Missions", className="section-title"),
                StatusPill(computed(lambda: f"{len(missions.value)} visible"), tone="info"),
                className="sidebar-header",
                gap=8,
            ),
            Input(
                value=query,
                placeholder="Search missions",
                className="mission-search",
                autoFocus=True,
                onChange=on_query,
            ),
            ScrollView(
                VStack(
                    For(
                        each=missions,
                        key=lambda mission: mission.id,
                        children=lambda mission: MissionRow(
                            mission=mission,
                            active=computed(lambda mission_id=mission.id: selected_mission_id.value == mission_id),
                            pinned=computed(lambda mission_id=mission.id: mission_id in pinned_ids.value),
                            on_select=on_select,
                        ),
                        fallback=Text("No missions match", className="muted-copy"),
                    ),
                    className="mission-list",
                    gap=8,
                ),
                className="mission-scroll",
            ),
            className="sidebar-body",
            gap=10,
        ),
        className="mission-sidebar-card",
    )


@component
def MissionRow(*, mission: Mission, active, pinned, on_select):
    row_class = computed(lambda: "mission-row is-selected" if active.value else "mission-row")
    meta = computed(lambda: f"{mission.last_run} / {'pinned' if pinned.value else mission.owner}")
    return ListRow(
        title=mission.name,
        detail=mission.description,
        meta=meta,
        badge=mission.risk,
        badge_tone=mission.risk_tone,
        tone=computed(lambda: "info" if active.value else "default"),
        action=Button(
            "Open",
            className="mission-open-button",
            onClick=lambda mission_id=mission.id: on_select(mission_id),
        ),
        className=row_class,
    )


@component
def MissionDetail(*, selected_mission, runtime_status):
    return Card(
        VStack(
            HStack(
                VStack(
                    Text(computed(lambda: selected_mission.value.name), className="detail-title"),
                    Text(computed(lambda: selected_mission.value.description), className="detail-copy"),
                    className="detail-heading",
                    gap=4,
                ),
                StatusPill(
                    computed(lambda: selected_mission.value.status),
                    tone=computed(lambda: selected_mission.value.status_tone),
                ),
                StatusPill(
                    computed(lambda: selected_mission.value.risk),
                    tone=computed(lambda: selected_mission.value.risk_tone),
                ),
                className="detail-header",
                gap=10,
            ),
            HStack(
                MetaTile("Mission ID", computed(lambda: selected_mission.value.id)),
                MetaTile("Status", runtime_status),
                MetaTile("Owner", computed(lambda: selected_mission.value.owner)),
                MetaTile("Zone", computed(lambda: selected_mission.value.zone)),
                className="meta-grid",
                gap=8,
            ),
            Panel(
                Text("Metadata", className="metadata-title"),
                Text(computed(lambda: f"mode={selected_mission.value.mode}"), className="metadata-line"),
                Text(computed(lambda: f"lastRun={selected_mission.value.last_run}"), className="metadata-line"),
                Text(computed(lambda: f"selectedMissionId={selected_mission.value.id}"), className="metadata-line"),
                className="metadata-panel",
            ),
            className="detail-card-body",
            gap=12,
        ),
        className="detail-card",
    )


@component
def MetaTile(label, value):
    return VStack(
        Text(label, className="meta-label"),
        Text(value, className="meta-value"),
        className="meta-tile",
        gap=3,
    )


@component
def ActionStrip(
    *,
    safe_mode,
    on_dry_run,
    on_request_execute,
    on_toggle_safe_mode,
    on_open_context,
):
    return Card(
        HStack(
            ActionButton("Dry Run", variant="primary", onClick=on_dry_run),
            ActionButton(
                "Execute",
                variant="danger",
                className="execute-button",
                onClick=on_request_execute,
            ),
            ActionButton(
                computed(lambda: "Safe Mode On" if safe_mode.value else "Safe Mode"),
                variant="ghost",
                className="safe-button",
                onClick=on_toggle_safe_mode,
            ),
            Button("More", className="secondary-button", onClick=on_open_context),
            className="action-strip",
            gap=8,
        ),
        className="action-card",
    )


@component
def LogPanel(*, logs, scroll_y, on_scroll):
    return Card(
        VStack(
            HStack(
                Text("Operator Log", className="section-title"),
                StatusPill(computed(lambda: f"{len(logs.value)} lines"), tone="neutral"),
                className="log-header",
                gap=8,
            ),
            ScrollView(
                VStack(
                    For(
                        each=logs,
                        key=lambda line: line.id,
                        children=lambda line: LogLine(line=line),
                    ),
                    className="log-list",
                    gap=6,
                ),
                className="log-scroll",
                scrollY=scroll_y,
                onScroll=on_scroll,
            ),
            className="log-panel-body",
            gap=10,
        ),
        className="log-card",
    )


@component
def LogLine(*, line: LogEntry):
    return HStack(
        Text(line.time, className="log-time"),
        Text(line.severity.upper(), className=f"log-severity log-{line.severity}"),
        Text(line.message, className="log-message"),
        className=f"log-row log-row-{line.severity}",
        gap=8,
    )


@component
def ExecuteDialog(*, open, mission, on_confirm, on_cancel):
    return Dialog(
        Text(
            computed(lambda: f"Mission {mission.value.id} / {mission.value.name}"),
            className="confirm-copy",
        ),
        HStack(
            ActionButton(
                "Confirm Execute",
                variant="danger",
                className="danger-action",
                onClick=on_confirm,
            ),
            ActionButton("Cancel", variant="ghost", onClick=on_cancel),
            className="dialog-actions",
            gap=8,
        ),
        open=open,
        title="Confirm Execute",
        description="Execution is operator-gated and must be confirmed before it changes appliance state.",
        className="confirm-dialog",
    )


@component
def ContextActionsPanel(
    *,
    open,
    mission,
    pinned_ids,
    raw_open,
    on_copy_mission_id,
    on_copy_log_line,
    on_toggle_pin,
    on_inspect_raw,
    on_close,
):
    pin_label = computed(
        lambda: "Unpin mission" if mission.value.id in pinned_ids.value else "Pin mission"
    )
    return Show(
        FocusScope(
            Panel(
                Text("Secondary actions", className="panel-title"),
                Text(
                    "Visible More button stands in for right click, long press, and keyboard context.",
                    className="panel-copy",
                ),
                HStack(
                    ActionButton("Copy mission ID", variant="ghost", size="sm", onClick=on_copy_mission_id),
                    ActionButton("Copy selected log line", variant="ghost", size="sm", onClick=on_copy_log_line),
                    ActionButton(pin_label, variant="ghost", size="sm", onClick=on_toggle_pin),
                    ActionButton("Inspect raw details", variant="ghost", size="sm", onClick=on_inspect_raw),
                    className="context-actions",
                    gap=8,
                ),
                Show(
                    Panel(
                        Text(computed(lambda: f"id={mission.value.id}"), className="metadata-line"),
                        Text(computed(lambda: f"status={mission.value.status}"), className="metadata-line"),
                        Text(computed(lambda: f"risk={mission.value.risk}"), className="metadata-line"),
                        Text(computed(lambda: f"mode={mission.value.mode}"), className="metadata-line"),
                        className="raw-panel",
                    ),
                    when=raw_open,
                ),
                ActionButton("Close", variant="ghost", size="sm", onClick=on_close),
                className="context-panel",
            ),
            className="context-focus",
        ),
        when=open,
    )


@component
def CommandPanel(*, open, on_dry_run, on_request_execute, on_open_context, on_close):
    return Show(
        FocusScope(
            Panel(
                Text("Command panel", className="panel-title"),
                Text("Opened with Ctrl+K. Escape dismisses this panel.", className="panel-copy"),
                HStack(
                    ActionButton("Run Dry Run", variant="primary", size="sm", onClick=on_dry_run),
                    ActionButton("Arm Execute", variant="danger", size="sm", onClick=on_request_execute),
                    ActionButton("Open More", variant="ghost", size="sm", onClick=on_open_context),
                    ActionButton("Close", variant="ghost", size="sm", onClick=on_close),
                    className="command-actions",
                    gap=8,
                ),
                className="command-panel",
            ),
            className="command-focus",
        ),
        when=open,
    )


def _mission_search_text(mission: Mission) -> str:
    return " ".join(
        [
            mission.id,
            mission.name,
            mission.status,
            mission.risk,
            mission.owner,
            mission.zone,
            mission.mode,
        ]
    ).lower()


def _runtime_tone(status: str) -> str:
    if status in {"Ready", "Dry run queued"}:
        return "success"
    if status == "Safe mode":
        return "info"
    if status == "Executing":
        return "warn"
    return "neutral"


def _safe_mode_message(enabled: bool) -> str:
    if enabled:
        return "safe mode enabled for all primary actions"
    return "safe mode disabled by operator"
