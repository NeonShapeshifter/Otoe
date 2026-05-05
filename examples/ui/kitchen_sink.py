from __future__ import annotations

from otoe import HStack, Text, VStack, component, computed
from otoe.ui import (
    ActionButton,
    Badge,
    Card,
    CommandPalette,
    DataTable,
    Dialog,
    StatCard,
    TabButton,
    TableColumn,
    Tabs,
    Toast,
    Toolbar,
)


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

TABLE_COLUMNS = [
    TableColumn("surface", "Surface", "surface"),
    TableColumn("status", "Status"),
    TableColumn("owner", "Owner"),
]

SURFACES = [
    {"id": "mission", "surface": "Mission Exec", "status": "Operational", "tone": "success", "owner": "Wraith"},
    {"id": "saas", "surface": "SaaS Dashboard", "status": "Product", "tone": "info", "owner": "Otoe"},
    {"id": "kit", "surface": "UI Kit", "status": "Growing", "tone": "warn", "owner": "Core"},
]


@component
def UIKitKitchenSink(*, query, selected, dialog_open, on_query, on_select, on_toggle_dialog):
    selected_label = computed(lambda: _selected_label(selected.value))
    selected_tone = computed(lambda: "success" if selected.value else "neutral")

    return VStack(
        Toolbar(
            Text("Otoe UI", className="ui-demo-brand"),
            Text("Components that work for SaaS and Wraith-shaped surfaces.", className="ui-demo-copy"),
            Badge(selected_label, tone=selected_tone, className="ui-demo-status"),
            ActionButton("Toggle Dialog", variant="ghost", onClick=on_toggle_dialog),
            className="ui-demo-topbar",
            gap=12,
        ),
        HStack(
            StatCard(
                label="Primitives",
                value="11",
                detail="Shared surface",
                tone="good",
                className="ui-demo-stat",
            ),
            StatCard(
                label="Case studies",
                value="2",
                detail="SaaS + Wraith",
                tone="info",
                className="ui-demo-stat",
            ),
            StatCard(
                label="Tests",
                value="70+",
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
                        columns=TABLE_COLUMNS,
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
                    description="This proves composite UI primitives before the native backend exists.",
                    className="ui-demo-dialog",
                ),
                className="ui-demo-right",
                gap=14,
            ),
            className="ui-demo-grid",
            gap=16,
        ),
        className="ui-demo-shell",
        gap=16,
    )


def _selected_label(command_id):
    if not command_id:
        return "No command"
    for command in COMMANDS:
        if command["id"] == command_id:
            return command["label"]
    return str(command_id)


def _surface_cell(row, column):
    if column.key == "surface":
        return Text(row["surface"], className="ui-table-cell surface")
    if column.key == "status":
        return Badge(row["status"], tone=row["tone"], className="ui-demo-status-pill")
    return Text(row[column.key], className="ui-table-cell")
