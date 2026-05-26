from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Protocol

from otoe import For, HStack, Input, Text, VStack, component, computed
from otoe.ui import (
    ActionButton,
    AppShell,
    Badge,
    Card,
    DataTable,
    EmptyState,
    FeedbackToast,
    NavRoute,
    RouteView,
    SectionHeader,
    SidebarNav,
    StatCard,
    TabButton,
    TableColumn,
    Tabs,
    Toolbar,
)


@dataclass(frozen=True)
class WorkflowRecord:
    id: str
    account: str
    owner: str
    stage: str
    status: str
    amount: str
    updated: str
    note: str
    tone: str = "neutral"
    selected: bool = False


@dataclass(frozen=True)
class WorkflowEvent:
    id: str
    time: str
    action: str
    detail: str
    tone: str = "neutral"


@dataclass(frozen=True)
class WorkflowFeedback:
    title: str
    detail: str
    tone: str = "info"


@dataclass(frozen=True)
class WorkflowSnapshot:
    title: str
    source: str
    sync_state: str
    sync_tone: str
    query: str
    stage_filter: str
    records: list[WorkflowRecord]
    events: list[WorkflowEvent]
    last_feedback: WorkflowFeedback | None = None


class DataWorkflowProvider(Protocol):
    def snapshot(self) -> WorkflowSnapshot:
        raise NotImplementedError

    def set_query(self, value: str) -> WorkflowSnapshot:
        raise NotImplementedError

    def set_stage_filter(self, value: str) -> WorkflowSnapshot:
        raise NotImplementedError

    def toggle_record(self, record_id: str) -> WorkflowSnapshot:
        raise NotImplementedError

    def run_action(self, action_id: str) -> WorkflowSnapshot:
        raise NotImplementedError


DATA_ROUTES = [
    NavRoute(
        "queue",
        "Queue",
        "Search, filter, select, and process rows",
        badge="Table",
        tone="info",
    ),
    NavRoute(
        "selected",
        "Selected",
        "Review the active batch before action",
        badge="Batch",
        tone="warn",
    ),
    NavRoute("history", "History", "Recent workflow activity", badge="Log", tone="neutral"),
]

STAGE_FILTERS = ["All", "Intake", "Review", "Approved", "Blocked"]

RECORD_COLUMNS = [
    TableColumn("select", "", "select"),
    TableColumn("account", "Account", "account"),
    TableColumn("stage", "Stage", "stage"),
    TableColumn("status", "Status", "status"),
    TableColumn("owner", "Owner", "owner"),
    TableColumn("amount", "Amount", "amount"),
    TableColumn("updated", "Updated", "updated"),
]


class MemoryDataWorkflowProvider:
    def __init__(self, snapshot: WorkflowSnapshot | None = None) -> None:
        self._snapshot = snapshot or demo_workflow_snapshot()
        self._runs = 0

    def snapshot(self) -> WorkflowSnapshot:
        return self._snapshot

    def set_query(self, value: str) -> WorkflowSnapshot:
        self._snapshot = replace(
            self._snapshot,
            query=value,
            last_feedback=WorkflowFeedback(
                "Search updated",
                _visible_count_text(self._snapshot, query=value),
                "info",
            ),
        )
        return self._snapshot

    def set_stage_filter(self, value: str) -> WorkflowSnapshot:
        self._snapshot = replace(
            self._snapshot,
            stage_filter=value,
            last_feedback=WorkflowFeedback(
                "Filter applied",
                f"{value} rows are visible.",
                "info",
            ),
        )
        return self._snapshot

    def toggle_record(self, record_id: str) -> WorkflowSnapshot:
        records = [
            replace(record, selected=not record.selected)
            if record.id == record_id
            else record
            for record in self._snapshot.records
        ]
        record = _record_by_id(records, record_id)
        state = "selected" if record and record.selected else "removed"
        self._snapshot = replace(
            self._snapshot,
            records=records,
            last_feedback=WorkflowFeedback(
                "Selection updated",
                f"{_record_label(records, record_id)} was {state}.",
                "info",
            ),
        )
        return self._snapshot

    def run_action(self, action_id: str) -> WorkflowSnapshot:
        self._runs += 1
        if action_id == "approve":
            return self._approve_selected()
        if action_id == "clear":
            records = [
                replace(record, selected=False)
                for record in self._snapshot.records
            ]
            self._snapshot = replace(
                self._snapshot,
                records=records,
                last_feedback=WorkflowFeedback(
                    "Selection cleared",
                    "The active batch is empty.",
                    "neutral",
                ),
            )
            return self._snapshot
        if action_id == "export":
            count = len(filtered_records(self._snapshot))
            event = _event(
                self._runs,
                "Exported filtered table",
                f"{count} rows prepared for CSV.",
                "success",
            )
            self._snapshot = replace(
                self._snapshot,
                events=[event, *self._snapshot.events][:8],
                last_feedback=WorkflowFeedback(
                    "Export prepared",
                    f"{count} rows are ready for download.",
                    "success",
                ),
            )
            return self._snapshot
        self._snapshot = replace(
            self._snapshot,
            last_feedback=WorkflowFeedback("Unknown action", f"{action_id} is not registered.", "danger"),
        )
        return self._snapshot

    def _approve_selected(self) -> WorkflowSnapshot:
        selected = selected_records(self._snapshot)
        if not selected:
            self._snapshot = replace(
                self._snapshot,
                last_feedback=WorkflowFeedback("Nothing selected", "Select rows before approving a batch.", "warn"),
            )
            return self._snapshot
        blocked = [record for record in selected if record.stage == "Blocked"]
        if blocked:
            self._snapshot = replace(
                self._snapshot,
                last_feedback=WorkflowFeedback(
                    "Approval blocked",
                    "Blocked rows need remediation before approval.",
                    "danger",
                ),
            )
            return self._snapshot
        selected_ids = {record.id for record in selected}
        records = [
            replace(record, stage="Approved", status="Approved", tone="success", selected=False)
            if record.id in selected_ids
            else record
            for record in self._snapshot.records
        ]
        event = _event(
            self._runs,
            "Approved selected records",
            f"{len(selected)} rows moved to approved.",
            "success",
        )
        self._snapshot = replace(
            self._snapshot,
            records=records,
            events=[event, *self._snapshot.events][:8],
            last_feedback=WorkflowFeedback(
                "Batch approved",
                f"{len(selected)} records were approved.",
                "success",
            ),
        )
        return self._snapshot


@component
def DataWorkflowWorkbench(
    *,
    snapshot,
    active_route,
    on_navigate,
    on_query,
    on_stage_filter,
    on_toggle_record,
    on_action,
):
    return AppShell(
        header=DataTopBar(snapshot=snapshot, on_action=on_action),
        sidebar=SidebarNav(
            routes=DATA_ROUTES,
            active=active_route,
            on_navigate=on_navigate,
            brand=VStack(
                Text("Otoe", className="data-sidebar-brand"),
                Text("Data Workflow", className="data-sidebar-copy"),
                gap=2,
            ),
            footer=VStack(
                Text(computed(lambda: _snap(snapshot).source), className="data-sidebar-meta"),
                Text(
                    computed(lambda: f"{len(selected_records(_snap(snapshot)))} selected"),
                    className="data-sidebar-meta",
                ),
                gap=2,
            ),
            className="data-sidebar",
        ),
        content=VStack(
            FeedbackPanel(snapshot=snapshot),
            RouteView(
                route=active_route,
                routes=DATA_ROUTES,
                render=lambda route: _route_view(
                    route,
                    snapshot=snapshot,
                    on_query=on_query,
                    on_stage_filter=on_stage_filter,
                    on_toggle_record=on_toggle_record,
                    on_action=on_action,
                ),
                className="data-route",
            ),
            className="data-route-shell",
            gap=14,
        ),
        className="data-app",
    )


@component
def DataTopBar(*, snapshot, on_action):
    return Toolbar(
        VStack(
            Text("Data Workflow Console", className="data-brand"),
            Text(computed(lambda: _snap(snapshot).title), className="data-subtitle"),
            gap=2,
        ),
        Badge(
            computed(lambda: _snap(snapshot).sync_state),
            tone=computed(lambda: _snap(snapshot).sync_tone),
            className="data-sync-badge",
        ),
        Badge(
            computed(lambda: f"{len(filtered_records(_snap(snapshot)))} visible"),
            tone="info",
            className="data-count-badge",
        ),
        ActionButton(
            "Clear selection",
            variant="ghost",
            disabled=computed(lambda: not selected_records(_snap(snapshot))),
            onClick=lambda: on_action("clear"),
        ),
        ActionButton("Export table", variant="ghost", onClick=lambda: on_action("export")),
        ActionButton(
            "Approve selected",
            variant="primary",
            disabled=computed(lambda: not selected_records(_snap(snapshot))),
            onClick=lambda: on_action("approve"),
        ),
        className="data-topbar",
        gap=12,
    )


@component
def FeedbackPanel(*, snapshot):
    return FeedbackToast(
        computed(lambda: _snap(snapshot).last_feedback),
        className="data-feedback",
    )


@component
def QueueView(*, snapshot, on_query, on_stage_filter, on_toggle_record):
    return VStack(
        HStack(
            StatCard(
                label="Rows",
                value=computed(lambda: str(len(filtered_records(_snap(snapshot))))),
                detail="match current filters",
                tone="info",
                className="data-stat",
            ),
            StatCard(
                label="Selected",
                value=computed(lambda: str(len(selected_records(_snap(snapshot))))),
                detail="ready for bulk action",
                tone=computed(lambda: "warn" if selected_records(_snap(snapshot)) else "neutral"),
                className="data-stat",
            ),
            StatCard(
                label="Quality gate",
                value=computed(lambda: str(_ready_count(_snap(snapshot)))),
                detail="review-ready records",
                tone="success",
                className="data-stat",
            ),
            className="data-stat-grid",
            gap=12,
        ),
        Card(
            VStack(
                HStack(
                    Input(
                        value=computed(lambda: _snap(snapshot).query),
                        placeholder="Search records",
                        onChange=on_query,
                        className="data-search-input",
                    ),
                    StageTabs(snapshot=snapshot, on_stage_filter=on_stage_filter),
                    className="data-filter-row",
                    gap=12,
                ),
                DataTable(
                    columns=RECORD_COLUMNS,
                    rows=computed(lambda: filtered_records(_snap(snapshot))),
                    key=lambda record: record.id,
                    render_cell=lambda record, column: _record_cell(
                        record,
                        column,
                        on_toggle_record,
                    ),
                    className="data-record-table",
                    empty=EmptyState(
                        "No records match current filters",
                        className="data-empty-state",
                    ),
                ),
                gap=12,
            ),
            className="data-panel data-table-panel",
        ),
        className="data-page",
        gap=14,
    )


@component
def StageTabs(*, snapshot, on_stage_filter):
    return Tabs(
        *[
            TabButton(
                stage,
                active=computed(lambda stage=stage: _snap(snapshot).stage_filter == stage),
                onClick=lambda stage=stage: on_stage_filter(stage),
                className="data-stage-tab",
            )
            for stage in STAGE_FILTERS
        ],
        className="data-stage-tabs",
        gap=6,
    )


@component
def SelectedView(*, snapshot, on_toggle_record, on_action):
    return Card(
        VStack(
            SectionHeader(
                "Selected records",
                badge=computed(lambda: f"{len(selected_records(_snap(snapshot)))} rows"),
                badge_tone="warn",
                className="data-section-heading",
            ),
            For(
                each=computed(lambda: selected_records(_snap(snapshot))),
                key=lambda record: record.id,
                children=lambda record: SelectedRecord(
                    record=record,
                    on_toggle_record=on_toggle_record,
                ),
                fallback=EmptyState("No records selected", className="data-empty-state"),
            ),
            HStack(
                ActionButton("Clear selection", variant="ghost", onClick=lambda: on_action("clear")),
                ActionButton("Approve selected", variant="primary", onClick=lambda: on_action("approve")),
                className="data-selected-actions",
                gap=10,
            ),
            gap=12,
        ),
        className="data-panel data-selected-panel",
    )


@component
def SelectedRecord(*, record, on_toggle_record):
    return HStack(
        VStack(
            Text(record.account, className="data-selected-account"),
            Text(record.note, className="data-selected-note"),
            gap=2,
        ),
        Badge(record.stage, tone=record.tone, className="data-stage-badge"),
        ActionButton(
            "Remove",
            variant="ghost",
            size="sm",
            onClick=lambda record_id=record.id: on_toggle_record(record_id),
        ),
        className="data-selected-row",
        gap=12,
    )


@component
def HistoryView(*, snapshot):
    return Card(
        VStack(
            SectionHeader("Workflow history"),
            For(
                each=computed(lambda: _snap(snapshot).events),
                key=lambda event: event.id,
                children=lambda event: HistoryEvent(event=event),
                fallback=EmptyState("No workflow events", className="data-empty-state"),
            ),
            gap=10,
        ),
        className="data-panel data-history-panel",
    )


@component
def HistoryEvent(*, event):
    return HStack(
        Text(event.time, className="data-event-time"),
        VStack(
            Text(event.action, className="data-event-action"),
            Text(event.detail, className="data-event-detail"),
            gap=2,
        ),
        Badge(event.tone.upper(), tone=event.tone, className="data-event-badge"),
        className="data-event-row",
        gap=10,
    )


def demo_workflow_snapshot() -> WorkflowSnapshot:
    return WorkflowSnapshot(
        title="Quarterly intake review",
        source="Local CSV import",
        sync_state="Ready",
        sync_tone="success",
        query="",
        stage_filter="All",
        records=[
            WorkflowRecord(
                "rec-101",
                "Arcadia Finance",
                "Mara",
                "Review",
                "Needs approval",
                "$42,800",
                "09:22",
                "Contract values reconciled.",
                "warn",
            ),
            WorkflowRecord(
                "rec-102",
                "Northstar Analytics",
                "Ilya",
                "Intake",
                "Ready",
                "$18,400",
                "09:28",
                "Imported from partner feed.",
                "info",
            ),
            WorkflowRecord(
                "rec-103",
                "Mercury Labs",
                "Ren",
                "Blocked",
                "Missing owner",
                "$9,600",
                "09:31",
                "Owner mapping is incomplete.",
                "danger",
            ),
            WorkflowRecord(
                "rec-104",
                "Helio Works",
                "Sana",
                "Review",
                "Ready",
                "$27,300",
                "09:35",
                "Usage and billing match.",
                "success",
            ),
            WorkflowRecord(
                "rec-105",
                "Juniper Systems",
                "Mara",
                "Approved",
                "Approved",
                "$13,900",
                "09:40",
                "Cleared in previous batch.",
                "success",
            ),
        ],
        events=[
            WorkflowEvent(
                "import",
                "09:18",
                "Imported records",
                "5 rows loaded from the local source.",
                "success",
            ),
            WorkflowEvent(
                "quality",
                "09:20",
                "Ran quality gate",
                "1 row blocked by validation.",
                "warn",
            ),
            WorkflowEvent(
                "view",
                "09:21",
                "Prepared review queue",
                "Review and intake rows are ready.",
                "info",
            ),
        ],
    )


def empty_workflow_snapshot() -> WorkflowSnapshot:
    return replace(
        demo_workflow_snapshot(),
        query="zzz",
        last_feedback=WorkflowFeedback("Search updated", "0 records visible.", "info"),
    )


def filtered_records(snapshot: WorkflowSnapshot) -> list[WorkflowRecord]:
    query = snapshot.query.strip().lower()
    records = snapshot.records
    if snapshot.stage_filter != "All":
        records = [record for record in records if record.stage == snapshot.stage_filter]
    if query:
        records = [
            record
            for record in records
            if _matches_query(record, query)
        ]
    return records


def selected_records(snapshot: WorkflowSnapshot) -> list[WorkflowRecord]:
    return [record for record in snapshot.records if record.selected]


def _route_view(route, *, snapshot, on_query, on_stage_filter, on_toggle_record, on_action):
    if route.id == "queue":
        return QueueView(
            snapshot=snapshot,
            on_query=on_query,
            on_stage_filter=on_stage_filter,
            on_toggle_record=on_toggle_record,
        )
    if route.id == "selected":
        return SelectedView(
            snapshot=snapshot,
            on_toggle_record=on_toggle_record,
            on_action=on_action,
        )
    if route.id == "history":
        return HistoryView(snapshot=snapshot)
    return EmptyState("Route not found", className="data-empty-state")


def _record_cell(record: WorkflowRecord, column: TableColumn, on_toggle_record):
    if column.key == "select":
        return ActionButton(
            "Selected" if record.selected else "Select",
            variant="ghost" if record.selected else "primary",
            size="sm",
            className="data-select-button",
            onClick=lambda record_id=record.id: on_toggle_record(record_id),
        )
    if column.key == "account":
        return VStack(
            Text(record.account, className="ui-table-cell data-record-account"),
            Text(record.note, className="data-record-note"),
            gap=2,
        )
    if column.key == "stage":
        return Badge(record.stage, tone=record.tone, className="data-stage-badge")
    if column.key == "status":
        return Text(record.status, className="ui-table-cell data-record-status")
    if column.key == "owner":
        return Text(record.owner, className="ui-table-cell data-record-owner")
    if column.key == "amount":
        return Text(record.amount, className="ui-table-cell data-record-amount")
    if column.key == "updated":
        return Text(record.updated, className="ui-table-cell data-record-updated")
    return Text("", className="ui-table-cell")


def _visible_count_text(snapshot: WorkflowSnapshot, *, query: str) -> str:
    return f"{len(filtered_records(replace(snapshot, query=query)))} records visible."


def _ready_count(snapshot: WorkflowSnapshot) -> int:
    return sum(
        1
        for record in filtered_records(snapshot)
        if record.stage in {"Intake", "Review"} and record.tone != "danger"
    )


def _matches_query(record: WorkflowRecord, query: str) -> bool:
    fields = [
        record.id,
        record.account,
        record.owner,
        record.stage,
        record.status,
        record.note,
    ]
    return query in " ".join(fields).lower()


def _record_by_id(records: list[WorkflowRecord], record_id: str) -> WorkflowRecord | None:
    for record in records:
        if record.id == record_id:
            return record
    return None


def _record_label(records: list[WorkflowRecord], record_id: str) -> str:
    record = _record_by_id(records, record_id)
    return record.account if record else record_id


def _event(index: int, action: str, detail: str, tone: str) -> WorkflowEvent:
    return WorkflowEvent(f"event-{index}", f"09:4{index}", action, detail, tone)


def _snap(snapshot) -> WorkflowSnapshot:
    return snapshot.value if hasattr(snapshot, "value") else snapshot
