from __future__ import annotations

from otoe import HStack, Text, VStack, component, computed
from otoe.ui import (
    ActionButton,
    AppShell,
    Badge,
    Card,
    CommandPalette,
    DataTable,
    Dialog,
    NavRoute,
    RouteView,
    SidebarNav,
    StatCard,
    TabButton,
    TableColumn,
    Tabs,
    Toast,
    Toolbar,
)


ROUTES = [
    NavRoute("ui", "UI Kit", "Shared primitives", badge="15", tone="info"),
    NavRoute("saas", "SaaS", "Commercial dashboard", badge="Live", tone="success"),
    NavRoute("wraith", "Wraith", "Operational surface", badge="Ops", tone="warn"),
]

COMMANDS = [
    {
        "id": "mission",
        "label": "Open Mission Exec",
        "description": "Jump to the Wraith operational surface.",
        "group": "Wraith",
        "shortcut": "M",
    },
    {
        "id": "customers",
        "label": "Review Customers",
        "description": "Open account health and next-step table.",
        "group": "SaaS",
        "shortcut": "C",
    },
    {
        "id": "export",
        "label": "Export Evidence",
        "description": "Prepare a review bundle for handoff.",
        "group": "Wraith",
        "shortcut": "E",
    },
    {
        "id": "settings",
        "label": "Workspace Settings",
        "description": "Open team access and defaults.",
        "group": "SaaS",
        "shortcut": ",",
    },
]

SURFACE_COLUMNS = [
    TableColumn("surface", "Surface", "surface"),
    TableColumn("status", "Status"),
    TableColumn("owner", "Owner"),
]

SURFACES = [
    {"id": "mission", "surface": "Mission Exec", "status": "Operational", "tone": "success", "owner": "Wraith"},
    {"id": "saas", "surface": "SaaS Dashboard", "status": "Product", "tone": "info", "owner": "Otoe"},
    {"id": "kit", "surface": "UI Kit", "status": "Growing", "tone": "warn", "owner": "Core"},
]

PIPELINE_COLUMNS = [
    TableColumn("account", "Account", "surface"),
    TableColumn("stage", "Stage"),
    TableColumn("health", "Health"),
]

PIPELINE = [
    {"id": "arcadia", "account": "Arcadia Finance", "stage": "Expansion", "health": "Healthy", "tone": "success"},
    {"id": "northstar", "account": "Northstar Analytics", "stage": "Renewal", "health": "Watch", "tone": "warn"},
    {"id": "mercury", "account": "Mercury Labs", "stage": "Onboarding", "health": "New", "tone": "info"},
]

TELEMETRY_COLUMNS = [
    TableColumn("event", "Event", "surface"),
    TableColumn("state", "State"),
    TableColumn("age", "Age"),
]

TELEMETRY = [
    {"id": "radio", "event": "Radio frame accepted", "state": "OK", "age": "00:01"},
    {"id": "capture", "event": "Capture window armed", "state": "SIG", "age": "00:07"},
    {"id": "export", "event": "Evidence bundle staged", "state": "CMD", "age": "00:12"},
]


@component
def UIKitKitchenSink(
    *,
    query,
    selected,
    dialog_open,
    active_route,
    on_query,
    on_select,
    on_toggle_dialog,
    on_navigate,
):
    active_label = computed(lambda: _route_label(active_route.value))

    return AppShell(
        header=Toolbar(
            Text("Otoe UI", className="ui-demo-brand"),
            Text("Signal-routed app shell over shared primitives.", className="ui-demo-copy"),
            Badge(active_label, tone="info", className="ui-demo-status"),
            ActionButton("Toggle Dialog", variant="ghost", onClick=on_toggle_dialog),
            className="ui-demo-topbar",
            gap=12,
        ),
        sidebar=SidebarNav(
            routes=ROUTES,
            active=active_route,
            on_navigate=on_navigate,
            brand=VStack(
                Text("Otoe", className="ui-demo-sidebar-brand-title"),
                Text("Framework shell", className="ui-demo-sidebar-brand-copy"),
                gap=2,
            ),
            footer=Text(
                computed(lambda: f"Route: {_route_label(active_route.value)}"),
                className="ui-demo-sidebar-footnote",
            ),
            className="ui-demo-sidebar",
        ),
        content=RouteView(
            route=active_route,
            routes=ROUTES,
            render=lambda route: _route_surface(
                route,
                query=query,
                selected=selected,
                dialog_open=dialog_open,
                on_query=on_query,
                on_select=on_select,
            ),
            className="ui-demo-route",
        ),
        className="ui-demo-shell",
    )


def _route_surface(route, *, query, selected, dialog_open, on_query, on_select):
    if route.id == "saas":
        return SaaSRoute()
    if route.id == "wraith":
        return WraithRoute()
    return UIKitRoute(
        query=query,
        selected=selected,
        dialog_open=dialog_open,
        on_query=on_query,
        on_select=on_select,
    )


@component
def UIKitRoute(*, query, selected, dialog_open, on_query, on_select):
    selected_label = computed(lambda: _selected_label(selected.value))
    selected_tone = computed(lambda: "success" if selected.value else "neutral")

    return VStack(
        HStack(
            StatCard(
                label="Primitives",
                value="15",
                detail="Shared surface",
                tone="good",
                className="ui-demo-stat",
            ),
            StatCard(
                label="Routes",
                value="3",
                detail="Signal switched",
                tone="info",
                className="ui-demo-stat",
            ),
            StatCard(
                label="Tests",
                value="81",
                detail="Runtime covered",
                tone="good",
                className="ui-demo-stat",
            ),
            className="ui-demo-stats",
            gap=14,
        ),
        HStack(
            VStack(
                CommandPalette(
                    query=query,
                    commands=COMMANDS,
                    on_query=on_query,
                    on_select=on_select,
                    placeholder="Search Wraith, SaaS, export...",
                    className="ui-demo-command",
                ),
                Toast(
                    "Command state",
                    description=computed(lambda: f"Selected: {_selected_label(selected.value)}"),
                    tone=selected_tone,
                    className="ui-demo-toast",
                ),
                className="ui-demo-left",
                gap=14,
            ),
            VStack(
                Card(
                    Tabs(
                        TabButton("Overview", active=True),
                        TabButton("Runtime"),
                        TabButton("Design"),
                        className="ui-demo-tabs",
                    ),
                    className="ui-demo-tabs-card",
                ),
                Card(
                    DataTable(
                        columns=SURFACE_COLUMNS,
                        rows=SURFACES,
                        key=lambda row: row["id"],
                        render_cell=_surface_cell,
                        className="ui-demo-table",
                    ),
                    className="ui-demo-table-card",
                ),
                Dialog(
                    Toast(
                        "Dialog body",
                        description="Dialog is mounted through the same control-flow primitives.",
                        tone="info",
                    ),
                    open=dialog_open,
                    title="Renderer boundary ready",
                    description="Composite UI primitives now sit inside a routed app shell.",
                    className="ui-demo-dialog",
                ),
                className="ui-demo-right",
                gap=14,
            ),
            className="ui-demo-grid",
            gap=16,
        ),
        className="ui-demo-surface ui-demo-ui-route",
        gap=16,
    )


@component
def SaaSRoute():
    return VStack(
        HStack(
            StatCard(label="MRR", value="$128k", detail="+14%", tone="good", className="ui-demo-stat"),
            StatCard(label="Health", value="91", detail="4 watch", tone="info", className="ui-demo-stat"),
            StatCard(label="Tasks", value="18", detail="7 automated", tone="good", className="ui-demo-stat"),
            className="ui-demo-stats",
            gap=14,
        ),
        HStack(
            Card(
                VStack(
                    Text("SaaS route loaded", className="ui-route-title"),
                    Text(
                        "The same shell can hold a softer commercial dashboard without Wraith-specific code.",
                        className="ui-route-copy",
                    ),
                    DataTable(
                        columns=PIPELINE_COLUMNS,
                        rows=PIPELINE,
                        key=lambda row: row["id"],
                        render_cell=_pipeline_cell,
                        className="ui-demo-table",
                    ),
                    gap=12,
                ),
                className="ui-route-card ui-route-card-wide",
            ),
            Card(
                VStack(
                    Text("Workflow", className="ui-route-title"),
                    Toast(
                        "Renewal risk alert",
                        description="Automation queued for Northstar Analytics.",
                        tone="warn",
                    ),
                    ActionButton("Create Brief", variant="primary"),
                    gap=12,
                ),
                className="ui-route-card",
            ),
            className="ui-demo-grid",
            gap=16,
        ),
        className="ui-demo-surface ui-demo-saas-route",
        gap=16,
    )


@component
def WraithRoute():
    return VStack(
        HStack(
            StatCard(label="Mission", value="Armed", detail="Handshake Hunter", tone="good", className="ui-demo-stat"),
            StatCard(label="Runtime", value="Live", detail="wlan1mon", tone="info", className="ui-demo-stat"),
            StatCard(label="Events", value="3", detail="No drift", tone="good", className="ui-demo-stat"),
            className="ui-demo-stats",
            gap=14,
        ),
        HStack(
            Card(
                VStack(
                    HStack(
                        Text("Wraith route loaded", className="ui-route-title"),
                        Badge("OPERATIONAL", tone="success", className="ui-route-badge"),
                        className="ui-route-heading",
                        gap=8,
                    ),
                    Text(
                        "This route keeps the dense operational rhythm while using the same shell contract.",
                        className="ui-route-copy",
                    ),
                    DataTable(
                        columns=TELEMETRY_COLUMNS,
                        rows=TELEMETRY,
                        key=lambda row: row["id"],
                        render_cell=_telemetry_cell,
                        className="ui-demo-table",
                    ),
                    gap=12,
                ),
                className="ui-route-card ui-route-card-wide",
            ),
            Card(
                VStack(
                    Text("Mission controls", className="ui-route-title"),
                    ActionButton("Simulate Frame", variant="info"),
                    ActionButton("Abort Mission", variant="danger"),
                    Toast(
                        "Runtime boundary",
                        description="Events remain explicit through Otoe handlers.",
                        tone="info",
                    ),
                    gap=12,
                ),
                className="ui-route-card",
            ),
            className="ui-demo-grid",
            gap=16,
        ),
        className="ui-demo-surface ui-demo-wraith-route",
        gap=16,
    )


def _selected_label(command_id):
    if not command_id:
        return "No command"
    for command in COMMANDS:
        if command["id"] == command_id:
            return command["label"]
    return str(command_id)


def _route_label(route_id):
    for route in ROUTES:
        if route.id == route_id:
            return str(route.label)
    return str(route_id)


def _surface_cell(row, column):
    if column.key == "surface":
        return Text(row["surface"], className="ui-table-cell surface")
    if column.key == "status":
        return Badge(row["status"], tone=row["tone"], className="ui-demo-status-pill")
    return Text(row[column.key], className="ui-table-cell")


def _pipeline_cell(row, column):
    if column.key == "account":
        return Text(row[column.key], className="ui-table-cell surface")
    if column.key == "health":
        return Badge(row["health"], tone=row["tone"], className="ui-demo-status-pill")
    return Text(row[column.key], className="ui-table-cell")


def _telemetry_cell(row, column):
    if column.key == "event":
        return Text(row[column.key], className="ui-table-cell surface")
    if column.key == "state":
        return Badge(row["state"], tone="neutral", className="ui-demo-status-pill")
    return Text(row[column.key], className="ui-table-cell")
