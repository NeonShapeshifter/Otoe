from __future__ import annotations

from dataclasses import dataclass, replace

from otoe import For, HStack, Text, VStack, component, computed
from otoe.ui import (
    AppFrame,
    ActionButton,
    EmptyState,
    FeedbackToast,
    ListRow,
    MetricGrid,
    MetricTile,
    SidebarFrame,
    SidebarItem,
    Surface,
    TopBar,
)


@dataclass(frozen=True)
class UtilityMetric:
    label: str
    value: str
    detail: str
    tone: str = "neutral"


@dataclass(frozen=True)
class UtilityJob:
    id: str
    name: str
    owner: str
    status: str
    eta: str
    tone: str = "neutral"


@dataclass(frozen=True)
class UtilityEvent:
    id: str
    time: str
    label: str
    tone: str = "neutral"


@dataclass(frozen=True)
class UtilityFeedback:
    title: str
    detail: str
    tone: str = "info"


@dataclass(frozen=True)
class UtilitySnapshot:
    workspace: str
    status: str
    status_tone: str
    metrics: list[UtilityMetric]
    jobs: list[UtilityJob]
    events: list[UtilityEvent]
    last_feedback: UtilityFeedback | None = None


class MemoryUtilityOpsProvider:
    def __init__(self, snapshot: UtilitySnapshot | None = None) -> None:
        self._snapshot = snapshot or demo_utility_snapshot()
        self._runs = 0

    def snapshot(self) -> UtilitySnapshot:
        return self._snapshot

    def run_action(self, action_id: str) -> UtilitySnapshot:
        self._runs += 1
        if action_id == "refresh":
            self._snapshot = replace(
                self._snapshot,
                status="Synced",
                status_tone="success",
                events=[
                    UtilityEvent(f"event-{self._runs}", "now", "Utility surface refreshed", "info"),
                    *self._snapshot.events,
                ][:5],
                last_feedback=UtilityFeedback(
                    "Surface refreshed",
                    "The utility-first reference snapshot was reloaded.",
                    "success",
                ),
            )
            return self._snapshot
        if action_id == "run_check":
            self._snapshot = replace(
                self._snapshot,
                status="Checking",
                status_tone="info",
                last_feedback=UtilityFeedback(
                    "Check queued",
                    "A fake quality gate was queued through the provider.",
                    "info",
                ),
            )
            return self._snapshot
        if action_id.startswith("open:"):
            job_id = action_id.split(":", 1)[1]
            self._snapshot = replace(
                self._snapshot,
                last_feedback=UtilityFeedback(
                    "Job opened",
                    f"{_job_name(self._snapshot.jobs, job_id)} is ready for inspection.",
                    "neutral",
                ),
            )
            return self._snapshot
        self._snapshot = replace(
            self._snapshot,
            last_feedback=UtilityFeedback(
                "Unknown action",
                f"{action_id} is not registered for this utility demo.",
                "danger",
            ),
        )
        return self._snapshot


@component
def UtilityOpsConsole(*, snapshot, on_action):
    return AppFrame(
        sidebar=UtilitySidebar(snapshot=snapshot),
        topbar=UtilityTopBar(snapshot=snapshot, on_action=on_action),
        feedback=FeedbackToast(
            computed(lambda: _snap(snapshot).last_feedback),
            className="shadow-none",
        ),
        content=VStack(
            UtilityMetrics(snapshot=snapshot),
            HStack(
                QueuePanel(snapshot=snapshot, on_action=on_action),
                VStack(
                    ReadinessPanel(snapshot=snapshot, on_action=on_action),
                    ActivityPanel(snapshot=snapshot, on_action=on_action),
                    className="w-80 min-w-0 gap-4",
                ),
                className="gap-4 items-start flex-wrap",
            ),
            className="gap-4",
        ),
        className="utility-app",
        shellClassName="utility-shell",
    )


@component
def UtilitySidebar(*, snapshot):
    return SidebarFrame(
        SidebarItem(label="Overview", tone="success", detail="Live surface", active=True),
        SidebarItem(label="Jobs", tone="info", detail="Provider queue"),
        SidebarItem(label="Native", tone="warn", detail="Portable subset"),
        brand="Otoe",
        subtitle="Utility Ops",
        footer=VStack(
            Text("No app CSS", className="text-sm font-semibold text-white"),
            Text(
                computed(lambda: f"{len(_snap(snapshot).jobs)} jobs / {len(_snap(snapshot).events)} events"),
                className="text-xs text-accent-soft",
            ),
            gap=1,
            className="p-3 bg-muted rounded-md",
        ),
    )


@component
def UtilityTopBar(*, snapshot, on_action):
    return TopBar(
        "Operations command surface",
        subtitle=computed(lambda: f"{_snap(snapshot).workspace} - modern Otoe preset app"),
        status=computed(lambda: _snap(snapshot).status),
        status_tone=computed(lambda: _snap(snapshot).status_tone),
        actions=HStack(
            ActionButton(
                "Run check",
                variant="primary",
                size="sm",
                onClick=lambda: on_action("run_check"),
            ),
            ActionButton(
                "Sync",
                variant="ghost",
                size="sm",
                onClick=lambda: on_action("refresh"),
            ),
            className="gap-2",
        ),
    )


@component
def UtilityMetrics(*, snapshot):
    return MetricGrid(
        *[
            MetricTile(
                label=metric.label,
                value=metric.value,
                detail=metric.detail,
                tone=metric.tone,
            )
            for metric in _snap(snapshot).metrics
        ],
    )


@component
def QueuePanel(*, snapshot, on_action):
    return Surface(
        For(
            each=computed(lambda: _snap(snapshot).jobs),
            key=lambda job: job.id,
            children=lambda job: JobRow(job=job, on_action=on_action),
            fallback=EmptyState(
                "No active jobs",
                description="The fake provider returned an empty queue.",
                action_label="Refresh",
                on_action=lambda: on_action("refresh"),
            ),
        ),
        title="Active jobs",
        detail=computed(lambda: f"{len(_snap(snapshot).jobs)} visible jobs"),
        badge="Presets",
        badge_tone="info",
        actions=ActionButton(
            "Run check",
            variant="ghost",
            size="sm",
            onClick=lambda: on_action("run_check"),
        ),
        className="flex-1 min-w-0",
    )


@component
def JobRow(*, job: UtilityJob, on_action):
    return ListRow(
        title=job.name,
        detail=job.owner,
        badge=job.status,
        badge_tone=job.tone,
        meta=job.eta,
        tone=job.tone,
        action_label="Open",
        on_action=lambda: on_action(f"open:{job.id}"),
    )


@component
def ReadinessPanel(*, snapshot, on_action):
    return Surface(
        VStack(
            ListRow(title="Portable utilities", badge="HTML", badge_tone="success", tone="success"),
            ListRow(title="Native subset", badge="Strict", badge_tone="info", tone="info"),
            ListRow(title="Custom CSS", badge="None", badge_tone="neutral", tone="soft"),
            gap=2,
        ),
        ActionButton(
            "Refresh readiness",
            variant="ghost",
            size="sm",
            full_width=True,
            onClick=lambda: on_action("refresh"),
        ),
        title="Readiness",
        detail=computed(lambda: f"{_snap(snapshot).status} provider state"),
        badge=computed(lambda: _snap(snapshot).status),
        badge_tone=computed(lambda: _snap(snapshot).status_tone),
    )


@component
def ActivityPanel(*, snapshot, on_action):
    return Surface(
        For(
            each=computed(lambda: _snap(snapshot).events),
            key=lambda event: event.id,
            children=lambda event: ListRow(
                title=event.label,
                badge=event.time,
                badge_tone=event.tone,
                tone="soft",
            ),
            fallback=EmptyState("No activity", description="Provider events will appear here."),
        ),
        title="Activity",
        detail="Recent provider events",
        actions=ActionButton(
            "Refresh",
            variant="ghost",
            size="sm",
            onClick=lambda: on_action("refresh"),
        ),
        className="utility-activity min-w-0",
    )


def demo_utility_snapshot() -> UtilitySnapshot:
    return UtilitySnapshot(
        workspace="Forvara Workshop",
        status="Ready",
        status_tone="success",
        metrics=[
            UtilityMetric("Velocity", "31 ms", "preview render", "success"),
            UtilityMetric("Coverage", "356", "tests passing", "info"),
            UtilityMetric("Friction", "low", "no custom CSS", "good"),
        ],
        jobs=[
            UtilityJob("job-1", "Utility layer smoke", "Design systems", "Ready", "2m", "success"),
            UtilityJob("job-2", "Reference app scan", "Workshop", "Review", "8m", "warn"),
            UtilityJob("job-3", "Native subset check", "Renderer", "Queued", "12m", "info"),
        ],
        events=[
            UtilityEvent("evt-1", "09:12", "Utility stylesheet generated", "success"),
            UtilityEvent("evt-2", "09:08", "Section helper built its action", "info"),
            UtilityEvent("evt-3", "09:01", "Card body spacing applied", "neutral"),
        ],
        last_feedback=UtilityFeedback(
            "Utility app loaded",
            "This surface uses helpers plus low-level utility classes.",
            "info",
        ),
    )


def empty_utility_snapshot() -> UtilitySnapshot:
    snapshot = demo_utility_snapshot()
    return replace(
        snapshot,
        jobs=[],
        events=[],
        status="Empty",
        status_tone="warn",
        last_feedback=UtilityFeedback(
            "Empty provider state",
            "The utility-first surface is rendering fallback controls.",
            "warn",
        ),
    )


def _snap(snapshot) -> UtilitySnapshot:
    return snapshot.value if hasattr(snapshot, "value") else snapshot


def _job_name(jobs: list[UtilityJob], job_id: str) -> str:
    for job in jobs:
        if job.id == job_id:
            return job.name
    return job_id
