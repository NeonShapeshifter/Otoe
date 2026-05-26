from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Protocol

from otoe import For, HStack, Input, Show, Text, VStack, component, computed
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
    TableColumn,
    Toolbar,
)


@dataclass(frozen=True)
class AdminSetting:
    id: str
    label: str
    description: str
    value: str
    draft_value: str
    group: str
    tone: str = "neutral"
    error: str | None = None
    disabled: bool = False


@dataclass(frozen=True)
class AccessRule:
    id: str
    label: str
    description: str
    enabled: bool
    tone: str = "success"


@dataclass(frozen=True)
class AdminAuditEvent:
    id: str
    time: str
    actor: str
    action: str
    tone: str = "neutral"


@dataclass(frozen=True)
class AdminFeedback:
    title: str
    detail: str
    tone: str = "info"


@dataclass(frozen=True)
class AdminSnapshot:
    workspace: str
    environment: str
    status: str
    status_tone: str
    settings: list[AdminSetting]
    access_rules: list[AccessRule]
    audit_events: list[AdminAuditEvent]
    pending_changes: int = 0
    last_feedback: AdminFeedback | None = None


class AdminSettingsProvider(Protocol):
    def snapshot(self) -> AdminSnapshot:
        raise NotImplementedError

    def update_setting(self, setting_id: str, value: str) -> AdminSnapshot:
        raise NotImplementedError

    def run_action(self, action_id: str) -> AdminSnapshot:
        raise NotImplementedError

    def toggle_access_rule(self, rule_id: str) -> AdminSnapshot:
        raise NotImplementedError


ADMIN_ROUTES = [
    NavRoute("overview", "Overview", "Status, pending work, and recent activity", badge="Local", tone="info"),
    NavRoute("settings", "Settings", "Editable workspace and runtime defaults", badge="5", tone="warn"),
    NavRoute("access", "Access", "Local permissions and safety controls", badge="3", tone="success"),
    NavRoute("audit", "Audit", "Recent local admin activity", badge="Log", tone="neutral"),
]

AUDIT_COLUMNS = [
    TableColumn("time", "Time", "audit-time"),
    TableColumn("actor", "Actor", "audit-actor"),
    TableColumn("action", "Action", "audit-action"),
]


class MemoryAdminSettingsProvider:
    def __init__(self, snapshot: AdminSnapshot | None = None) -> None:
        self._snapshot = snapshot or demo_admin_snapshot()
        self._runs = 0

    def snapshot(self) -> AdminSnapshot:
        return self._snapshot

    def update_setting(self, setting_id: str, value: str) -> AdminSnapshot:
        settings = [
            _update_setting(setting, value) if setting.id == setting_id else setting
            for setting in self._snapshot.settings
        ]
        self._snapshot = _with_state(
            replace(
                self._snapshot,
                settings=settings,
                last_feedback=AdminFeedback(
                    "Draft updated",
                    f"{_setting_label(settings, setting_id)} is staged for review.",
                    "info",
                ),
            )
        )
        return self._snapshot

    def run_action(self, action_id: str) -> AdminSnapshot:
        self._runs += 1
        if action_id == "save":
            self._snapshot = self._save()
            return self._snapshot
        if action_id == "reset":
            settings = [
                replace(setting, draft_value=setting.value, error=None)
                for setting in self._snapshot.settings
            ]
            self._snapshot = _with_state(
                replace(
                    self._snapshot,
                    settings=settings,
                    last_feedback=AdminFeedback("Draft reset", "Unsaved local changes were discarded.", "neutral"),
                )
            )
            return self._snapshot
        if action_id == "reload":
            event = _audit_event(self._runs, "system", "Reloaded local settings", "info")
            self._snapshot = replace(
                self._snapshot,
                audit_events=[event, *self._snapshot.audit_events][:8],
                last_feedback=AdminFeedback("Settings reloaded", "Provider snapshot refreshed from local memory.", "info"),
            )
            return self._snapshot
        self._snapshot = replace(
            self._snapshot,
            last_feedback=AdminFeedback("Unknown action", f"{action_id} is not registered.", "danger"),
        )
        return self._snapshot

    def toggle_access_rule(self, rule_id: str) -> AdminSnapshot:
        self._runs += 1
        rules = [
            replace(rule, enabled=not rule.enabled, tone="success" if not rule.enabled else "warn")
            if rule.id == rule_id
            else rule
            for rule in self._snapshot.access_rules
        ]
        rule = _rule_by_id(rules, rule_id)
        state = "enabled" if rule and rule.enabled else "disabled"
        event = _audit_event(self._runs, "operator", f"{_rule_label(rules, rule_id)} {state}", "info")
        self._snapshot = replace(
            self._snapshot,
            access_rules=rules,
            audit_events=[event, *self._snapshot.audit_events][:8],
            last_feedback=AdminFeedback("Access rule updated", f"{_rule_label(rules, rule_id)} is now {state}.", "info"),
        )
        return self._snapshot

    def _save(self) -> AdminSnapshot:
        if any(setting.error for setting in self._snapshot.settings):
            return replace(
                self._snapshot,
                status="Validation failed",
                status_tone="danger",
                last_feedback=AdminFeedback(
                    "Save blocked",
                    "Fix validation errors before applying local settings.",
                    "danger",
                ),
            )
        settings = [
            replace(setting, value=setting.draft_value, error=None)
            for setting in self._snapshot.settings
        ]
        event = _audit_event(self._runs, "operator", "Applied local settings", "success")
        return _with_state(
            replace(
                self._snapshot,
                workspace=_setting_value(settings, "workspace_name", self._snapshot.workspace),
                settings=settings,
                audit_events=[event, *self._snapshot.audit_events][:8],
                last_feedback=AdminFeedback(
                    "Settings saved",
                    "Workspace defaults were applied to the local provider.",
                    "success",
                ),
            )
        )


@component
def AdminSettingsConsole(
    *,
    snapshot,
    active_route,
    on_navigate,
    on_setting_change,
    on_action,
    on_rule_toggle,
):
    return AppShell(
        header=AdminTopBar(snapshot=snapshot, on_action=on_action),
        sidebar=SidebarNav(
            routes=ADMIN_ROUTES,
            active=active_route,
            on_navigate=on_navigate,
            brand=VStack(
                Text("Otoe", className="admin-sidebar-brand"),
                Text("Local Admin", className="admin-sidebar-copy"),
                gap=2,
            ),
            footer=VStack(
                Text(computed(lambda: _snap(snapshot).environment), className="admin-sidebar-meta"),
                Text(computed(lambda: f"{_snap(snapshot).pending_changes} pending"), className="admin-sidebar-meta"),
                gap=2,
            ),
            className="admin-sidebar",
        ),
        content=VStack(
            FeedbackPanel(snapshot=snapshot),
            RouteView(
                route=active_route,
                routes=ADMIN_ROUTES,
                render=lambda route: _route_view(
                    route,
                    snapshot=snapshot,
                    on_setting_change=on_setting_change,
                    on_action=on_action,
                    on_rule_toggle=on_rule_toggle,
                ),
                className="admin-route",
            ),
            className="admin-route-shell",
            gap=14,
        ),
        className="admin-app",
    )


@component
def AdminTopBar(*, snapshot, on_action):
    return Toolbar(
        VStack(
            Text("Otoe Admin Console", className="admin-brand"),
            Text(computed(lambda: _snap(snapshot).workspace), className="admin-workspace"),
            gap=2,
        ),
        Badge(
            computed(lambda: _snap(snapshot).environment),
            tone="info",
            className="admin-env-badge",
        ),
        Badge(
            computed(lambda: _snap(snapshot).status),
            tone=computed(lambda: _snap(snapshot).status_tone),
            className="admin-status-badge",
        ),
        ActionButton("Reload", variant="ghost", onClick=lambda: on_action("reload")),
        ActionButton(
            "Reset",
            variant="ghost",
            disabled=computed(lambda: _snap(snapshot).pending_changes == 0),
            onClick=lambda: on_action("reset"),
        ),
        ActionButton(
            "Save changes",
            variant="primary",
            disabled=computed(lambda: _snap(snapshot).pending_changes == 0),
            onClick=lambda: on_action("save"),
        ),
        className="admin-topbar",
        gap=12,
    )


@component
def FeedbackPanel(*, snapshot):
    return FeedbackToast(
        computed(lambda: _snap(snapshot).last_feedback),
        className="admin-feedback",
    )


@component
def OverviewView(*, snapshot):
    return VStack(
        HStack(
            StatCard(
                label="Status",
                value=computed(lambda: _snap(snapshot).status),
                detail=computed(lambda: _snap(snapshot).environment),
                tone=computed(lambda: _snap(snapshot).status_tone),
                className="admin-stat",
            ),
            StatCard(
                label="Pending",
                value=computed(lambda: str(_snap(snapshot).pending_changes)),
                detail="settings staged",
                tone=computed(lambda: "warn" if _snap(snapshot).pending_changes else "success"),
                className="admin-stat",
            ),
            StatCard(
                label="Access",
                value=computed(lambda: f"{_enabled_rules(_snap(snapshot))}/{len(_snap(snapshot).access_rules)}"),
                detail="rules enabled",
                tone="info",
                className="admin-stat",
            ),
            className="admin-stat-grid",
            gap=12,
        ),
        HStack(
            Card(
                VStack(
                    SectionHeader("Settings requiring review"),
                    For(
                        each=computed(lambda: _dirty_settings(_snap(snapshot))),
                        key=lambda setting: setting.id,
                        children=lambda setting: DirtySettingRow(setting=setting),
                        fallback=EmptyState("No pending settings", className="admin-empty-state"),
                    ),
                    gap=10,
                ),
                className="admin-panel admin-review-panel",
            ),
            Card(
                VStack(
                    SectionHeader("Recent activity"),
                    For(
                        each=computed(lambda: _snap(snapshot).audit_events[:4]),
                        key=lambda event: event.id,
                        children=lambda event: AuditEventRow(event=event),
                    ),
                    gap=10,
                ),
                className="admin-panel admin-audit-panel",
            ),
            className="admin-overview-grid",
            gap=14,
        ),
        className="admin-page",
        gap=14,
    )


@component
def SettingsView(*, snapshot, on_setting_change):
    return Card(
        VStack(
            SectionHeader("Workspace settings"),
            For(
                each=computed(lambda: _snap(snapshot).settings),
                key=lambda setting: setting.id,
                children=lambda setting: SettingEditor(setting=setting, on_setting_change=on_setting_change),
            ),
            gap=12,
        ),
        className="admin-panel admin-settings-panel",
    )


@component
def AccessView(*, snapshot, on_rule_toggle):
    return Card(
        VStack(
            SectionHeader("Access rules"),
            For(
                each=computed(lambda: _snap(snapshot).access_rules),
                key=lambda rule: rule.id,
                children=lambda rule: AccessRuleRow(rule=rule, on_rule_toggle=on_rule_toggle),
            ),
            gap=12,
        ),
        className="admin-panel admin-access-panel",
    )


@component
def AuditView(*, snapshot):
    return Card(
        VStack(
            SectionHeader(
                "Audit trail",
                detail="Local-only activity log",
                className="admin-section-heading",
            ),
            DataTable(
                columns=AUDIT_COLUMNS,
                rows=computed(lambda: _snap(snapshot).audit_events),
                key=lambda event: event.id,
                render_cell=_audit_cell,
                className="admin-table",
                empty="No audit events",
            ),
            gap=10,
        ),
        className="admin-panel",
    )


@component
def SettingEditor(*, setting, on_setting_change):
    return HStack(
        VStack(
            HStack(
                Text(setting.label, className="admin-setting-label"),
                Badge("Dirty" if _is_dirty(setting) else "Saved", tone="warn" if _is_dirty(setting) else "success"),
                className="admin-setting-heading",
            ),
            Text(setting.description, className="admin-setting-description"),
            Show(
                Text(setting.error, className="admin-setting-error"),
                when=setting.error,
            ),
            gap=4,
        ),
        Input(
            value=setting.draft_value,
            placeholder=setting.label,
            disabled=setting.disabled,
            onChange=lambda value, setting_id=setting.id: on_setting_change(setting_id, value),
            className="admin-setting-input",
        ),
        className="admin-setting-row",
        gap=14,
    )


@component
def AccessRuleRow(*, rule, on_rule_toggle):
    return HStack(
        VStack(
            Text(rule.label, className="admin-rule-label"),
            Text(rule.description, className="admin-rule-description"),
            gap=3,
        ),
        Badge("Enabled" if rule.enabled else "Disabled", tone=rule.tone, className="admin-rule-badge"),
        ActionButton(
            "Disable" if rule.enabled else "Enable",
            variant="ghost",
            size="sm",
            onClick=lambda rule_id=rule.id: on_rule_toggle(rule_id),
        ),
        className="admin-rule-row",
        gap=12,
    )


@component
def DirtySettingRow(*, setting):
    return HStack(
        VStack(
            Text(setting.label, className="admin-dirty-label"),
            Text(f"{setting.value} -> {setting.draft_value}", className="admin-dirty-copy"),
            gap=2,
        ),
        Badge("Invalid" if setting.error else "Ready", tone="danger" if setting.error else "warn"),
        className="admin-dirty-row",
        gap=10,
    )


@component
def AuditEventRow(*, event):
    return HStack(
        Text(event.time, className="admin-event-time"),
        VStack(
            Text(event.actor, className="admin-event-actor"),
            Text(event.action, className="admin-event-action"),
            gap=2,
        ),
        Badge(event.tone.upper(), tone=event.tone, className="admin-event-badge"),
        className="admin-event-row",
        gap=10,
    )


def demo_admin_snapshot() -> AdminSnapshot:
    return _with_state(
        AdminSnapshot(
            workspace="Local Workspace",
            environment="Lab machine",
            status="Saved",
            status_tone="success",
            settings=[
                AdminSetting(
                    "workspace_name",
                    "Workspace name",
                    "Name shown in local admin surfaces.",
                    "Local Workspace",
                    "Local Workspace",
                    "workspace",
                ),
                AdminSetting(
                    "admin_email",
                    "Admin email",
                    "Local contact for audit and notification records.",
                    "ops@example.local",
                    "ops@example.local",
                    "workspace",
                ),
                AdminSetting(
                    "http_port",
                    "HTTP port",
                    "Port used by the local preview or service bridge.",
                    "8765",
                    "8765",
                    "runtime",
                ),
                AdminSetting(
                    "retention_days",
                    "Audit retention",
                    "Days of local audit history to keep.",
                    "30",
                    "30",
                    "runtime",
                ),
                AdminSetting(
                    "update_channel",
                    "Update channel",
                    "Release lane used by local update checks.",
                    "stable",
                    "stable",
                    "release",
                ),
            ],
            access_rules=[
                AccessRule("approval", "Require operator approval", "Block sensitive actions until a local operator approves.", True),
                AccessRule("audit", "Write audit events", "Record setting and permission changes in the local audit trail.", True),
                AccessRule("remote", "Remote admin bridge", "Allow LAN clients to reach this admin surface.", False, "warn"),
            ],
            audit_events=[
                AdminAuditEvent("boot", "09:14:02", "system", "Loaded local settings", "success"),
                AdminAuditEvent("audit", "09:14:05", "system", "Audit retention verified", "info"),
                AdminAuditEvent("remote", "09:14:08", "operator", "Remote admin bridge disabled", "warn"),
            ],
        )
    )


def invalid_admin_snapshot() -> AdminSnapshot:
    provider = MemoryAdminSettingsProvider(demo_admin_snapshot())
    return provider.update_setting("http_port", "70000")


def _route_view(route, *, snapshot, on_setting_change, on_action, on_rule_toggle):
    if route.id == "overview":
        return OverviewView(snapshot=snapshot)
    if route.id == "settings":
        return SettingsView(snapshot=snapshot, on_setting_change=on_setting_change)
    if route.id == "access":
        return AccessView(snapshot=snapshot, on_rule_toggle=on_rule_toggle)
    if route.id == "audit":
        return AuditView(snapshot=snapshot)
    return EmptyState("Route not found", className="admin-empty-state")


def _update_setting(setting: AdminSetting, value: str) -> AdminSetting:
    error = _validate_setting(setting.id, value)
    return replace(
        setting,
        draft_value=value,
        error=error,
        tone="danger" if error else "warn" if value != setting.value else "success",
    )


def _validate_setting(setting_id: str, value: str) -> str | None:
    cleaned = value.strip()
    if setting_id in {"workspace_name", "admin_email", "update_channel"} and not cleaned:
        return "Required"
    if setting_id == "workspace_name" and len(cleaned) < 3:
        return "Use at least 3 characters"
    if setting_id == "admin_email" and "@" not in cleaned:
        return "Use a local contact email"
    if setting_id == "http_port":
        try:
            port = int(cleaned)
        except ValueError:
            return "Use a numeric port"
        if port < 1 or port > 65535:
            return "Use a port from 1 to 65535"
    if setting_id == "retention_days":
        try:
            days = int(cleaned)
        except ValueError:
            return "Use a number of days"
        if days < 1 or days > 365:
            return "Use 1 to 365 days"
    return None


def _with_state(snapshot: AdminSnapshot) -> AdminSnapshot:
    pending = sum(1 for setting in snapshot.settings if _is_dirty(setting))
    has_errors = any(setting.error for setting in snapshot.settings)
    if has_errors:
        return replace(snapshot, pending_changes=pending, status="Validation failed", status_tone="danger")
    if pending:
        return replace(snapshot, pending_changes=pending, status="Unsaved changes", status_tone="warn")
    return replace(snapshot, pending_changes=0, status="Saved", status_tone="success")


def _is_dirty(setting: AdminSetting) -> bool:
    return setting.value != setting.draft_value


def _dirty_settings(snapshot: AdminSnapshot) -> list[AdminSetting]:
    return [setting for setting in snapshot.settings if _is_dirty(setting)]


def _setting_label(settings: list[AdminSetting], setting_id: str) -> str:
    for setting in settings:
        if setting.id == setting_id:
            return setting.label
    return setting_id


def _setting_value(settings: list[AdminSetting], setting_id: str, default: str) -> str:
    for setting in settings:
        if setting.id == setting_id:
            return setting.draft_value
    return default


def _enabled_rules(snapshot: AdminSnapshot) -> int:
    return sum(1 for rule in snapshot.access_rules if rule.enabled)


def _rule_by_id(rules: list[AccessRule], rule_id: str) -> AccessRule | None:
    for rule in rules:
        if rule.id == rule_id:
            return rule
    return None


def _rule_label(rules: list[AccessRule], rule_id: str) -> str:
    rule = _rule_by_id(rules, rule_id)
    return rule.label if rule else rule_id


def _audit_event(index: int, actor: str, action: str, tone: str) -> AdminAuditEvent:
    return AdminAuditEvent(f"event-{index}", f"09:15:{index:02d}", actor, action, tone)


def _audit_cell(event: AdminAuditEvent, column: TableColumn):
    if column.key == "time":
        return Text(event.time, className="ui-table-cell admin-table-time")
    if column.key == "actor":
        return Text(event.actor, className="ui-table-cell admin-table-actor")
    if column.key == "action":
        return Badge(event.action, tone=event.tone, className="admin-table-badge")
    return Text("", className="ui-table-cell")


def _snap(snapshot) -> AdminSnapshot:
    return snapshot.value if hasattr(snapshot, "value") else snapshot
