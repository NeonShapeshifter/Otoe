from otoe import For, HStack, Input, Panel, Show, Text, VStack, component, computed
from otoe.ui import (
    ActionButton,
    Badge,
    Card,
    DataTable,
    StatCard,
    TabButton,
    TableColumn,
    Tabs,
    Toast,
    Toolbar,
)


NAV_ITEMS = ["Overview", "Customers", "Revenue", "Automations", "Settings"]
CUSTOMER_COLUMNS = [
    TableColumn("name", "Account", "account"),
    TableColumn("plan", "Plan"),
    TableColumn("health", "Health"),
    TableColumn("next_step", "Next step", "next-step"),
]

PAGE_COPY = {
    "Overview": (
        "Customer pipeline",
        "Revenue signals, renewals, and account activity for the growth team.",
    ),
    "Customers": (
        "Customer intelligence",
        "Account health, plan mix, and follow-up priority in one place.",
    ),
    "Revenue": (
        "Revenue cockpit",
        "Pipeline value, expansion motion, and forecast confidence.",
    ),
    "Automations": (
        "Automation center",
        "Playbooks and handoffs that keep account work moving.",
    ),
    "Settings": (
        "Workspace settings",
        "Team access, notification preferences, and account defaults.",
    ),
}


@component
def SaaSTopBar(*, workspace, health_label, on_invite):
    return Toolbar(
        Text("LumaOps", className="saas-brand"),
        Text(workspace, className="saas-workspace"),
        Badge(health_label, tone="success", className="saas-status"),
        ActionButton("Invite", className="saas-invite", onClick=on_invite),
        className="saas-topbar",
        gap=12,
    )


@component
def MetricCard(*, label, value, delta, tone):
    return StatCard(
        label=label,
        value=value,
        detail=delta,
        tone=tone,
        className="saas-metric-card",
    )


def NavItem(*, label, active_section, on_nav):
    return TabButton(
        label,
        active=computed(lambda: active_section.value == label),
        className="nav-item",
        onClick=lambda: on_nav(label),
    )


@component
def PipelineCard(*, deal):
    return Panel(
        VStack(
            HStack(
                Text(deal["stage"], className="deal-stage"),
                Text(deal["confidence"], className="deal-confidence"),
                className="deal-meta",
            ),
            Text(deal["name"], className="deal-name"),
            Text(deal["owner"], className="deal-owner"),
            Text(deal["amount"], className="deal-amount"),
            className="deal-body",
        ),
        className="pipeline-card",
    )


@component
def CustomerRow(*, customer):
    return HStack(
        Text(customer["name"], className="customer-name"),
        Text(customer["plan"], className="customer-plan"),
        Text(customer["health"], className=f"customer-health {customer['tone']}"),
        className="customer-row",
    )


@component
def OverviewView(*, deals, customers, on_invite):
    return HStack(
        Panel(
            VStack(
                HStack(
                    Text("Priority deals", className="section-heading"),
                    ActionButton(
                        "New deal",
                        variant="ghost",
                        className="ghost-button",
                        onClick=on_invite,
                    ),
                    className="section-header",
                ),
                For(
                    each=deals,
                    key=lambda deal: deal["id"],
                    children=lambda deal: PipelineCard(deal=deal),
                ),
                className="pipeline-list",
                gap=12,
            ),
            className="pipeline-panel",
        ),
        Panel(
            VStack(
                Text("Customer health", className="section-heading"),
                For(
                    each=customers,
                    key=lambda customer: customer["id"],
                    children=lambda customer: CustomerRow(customer=customer),
                ),
                className="customer-list",
                gap=10,
            ),
            className="customer-panel",
        ),
        className="content-grid",
        gap=14,
    )


@component
def CustomersView(*, customers):
    return Panel(
        VStack(
            DataTable(
                columns=CUSTOMER_COLUMNS,
                rows=customers,
                key=lambda customer: customer["id"],
                render_cell=_customer_cell,
                className="customer-table",
            ),
            className="customer-table-wrap",
            gap=8,
        ),
        className="view-panel",
    )


@component
def RevenueView(*, deals):
    return HStack(
        Panel(
            VStack(
                Text("Forecast mix", className="section-heading"),
                Text("64% weighted pipeline", className="forecast-value"),
                Text("Expansion and renewal motion are carrying this cycle.", className="forecast-note"),
                className="forecast-card",
            ),
            className="forecast-panel",
        ),
        Panel(
            VStack(
                Text("Revenue queue", className="section-heading"),
                For(
                    each=deals,
                    key=lambda deal: deal["id"],
                    children=lambda deal: HStack(
                        Text(deal["name"], className="queue-name"),
                        Text(deal["amount"], className="queue-amount"),
                        className="queue-row",
                    ),
                ),
                className="queue-list",
                gap=10,
            ),
            className="queue-panel",
        ),
        className="split-view",
        gap=14,
    )


@component
def AutomationsView():
    return Panel(
        VStack(
            AutomationRule(
                title="Renewal risk alert",
                description="Notify customer success when health drops below target.",
                state="Enabled",
            ),
            AutomationRule(
                title="Expansion handoff",
                description="Create an AE task when a Scale account reaches 80% usage.",
                state="Enabled",
            ),
            AutomationRule(
                title="Inactive trial nudge",
                description="Send a reminder after three quiet days in trial.",
                state="Draft",
            ),
            className="automation-list",
            gap=12,
        ),
        className="view-panel",
    )


@component
def AutomationRule(*, title, description, state):
    return HStack(
        VStack(
            Text(title, className="automation-title"),
            Text(description, className="automation-description"),
            className="automation-copy",
        ),
        Text(state, className="automation-state"),
        className="automation-row",
    )


@component
def SettingsView():
    return Panel(
        VStack(
            Toast(
                "Workspace saved",
                description="Notification and region defaults are synced.",
                tone="success",
                className="settings-toast",
            ),
            SettingsRow(label="Workspace name", value="Growth workspace"),
            SettingsRow(label="Default owner", value="Revenue operations"),
            SettingsRow(label="Notifications", value="Digest and critical alerts"),
            SettingsRow(label="Data region", value="US East"),
            className="settings-list",
            gap=10,
        ),
        className="view-panel",
    )


@component
def SettingsRow(*, label, value):
    return HStack(
        Text(label, className="settings-label"),
        Text(value, className="settings-value"),
        className="settings-row",
    )


@component
def SectionBody(*, active_section, deals, customers, on_invite):
    return VStack(
        Show(
            OverviewView(deals=deals, customers=customers, on_invite=on_invite),
            when=computed(lambda: active_section.value == "Overview"),
        ),
        Show(
            CustomersView(customers=customers),
            when=computed(lambda: active_section.value == "Customers"),
        ),
        Show(
            RevenueView(deals=deals),
            when=computed(lambda: active_section.value == "Revenue"),
        ),
        Show(
            AutomationsView(),
            when=computed(lambda: active_section.value == "Automations"),
        ),
        Show(
            SettingsView(),
            when=computed(lambda: active_section.value == "Settings"),
        ),
        className="section-body",
        gap=0,
    )


@component
def SaaSOverview(
    *,
    query,
    workspace,
    active_section,
    deals,
    customers,
    on_search,
    on_invite,
    on_nav,
):
    total_pipeline = computed(lambda: f"${sum(deal['value'] for deal in deals.value):,.0f}")
    active_count = computed(lambda: f"{len(deals.value)} active")
    health_label = computed(lambda: "94% retention")
    page_title = computed(lambda: PAGE_COPY[active_section.value][0])
    page_subtitle = computed(lambda: PAGE_COPY[active_section.value][1])

    return VStack(
        SaaSTopBar(
            workspace=workspace,
            health_label=health_label,
            on_invite=on_invite,
        ),
        HStack(
            Card(
                Tabs(
                    *[
                        NavItem(
                            label=item,
                            active_section=active_section,
                            on_nav=on_nav,
                        )
                        for item in NAV_ITEMS
                    ],
                    className="saas-nav",
                    gap=8,
                    orientation="vertical",
                ),
                className="saas-sidebar",
            ),
            VStack(
                HStack(
                    VStack(
                        Text(page_title, className="page-title"),
                        Text(page_subtitle, className="page-subtitle"),
                        className="page-heading",
                    ),
                    Input(
                        value=query,
                        placeholder="Search customers, deals, owners...",
                        className="saas-search",
                        onChange=on_search,
                    ),
                    className="page-header",
                    gap=16,
                ),
                HStack(
                    MetricCard(
                        label="Pipeline",
                        value=total_pipeline,
                        delta="+18.4% this month",
                        tone="good",
                    ),
                    MetricCard(
                        label="Accounts",
                        value=active_count,
                        delta="7 ready for outreach",
                        tone="info",
                    ),
                    MetricCard(
                        label="NPS",
                        value="72",
                        delta="+6 from last cycle",
                        tone="good",
                    ),
                    className="metric-grid",
                    gap=14,
                ),
                SectionBody(
                    active_section=active_section,
                    deals=deals,
                    customers=customers,
                    on_invite=on_invite,
                ),
                className="saas-main",
                gap=16,
            ),
            className="saas-layout",
            gap=18,
        ),
        className="saas-app",
        gap=0,
    )


def _next_step(customer):
    if customer["tone"] == "good":
        return "Share expansion brief"
    if customer["tone"] == "warn":
        return "Schedule success check"
    return "Escalate retention plan"


def _customer_cell(customer, column):
    if column.key == "name":
        return Text(customer["name"], className="ui-table-cell table-cell account")
    if column.key == "plan":
        return Text(customer["plan"], className="ui-table-cell table-cell")
    if column.key == "health":
        return Badge(customer["health"], tone=customer["tone"], className="customer-health")
    if column.key == "next_step":
        return Text(_next_step(customer), className="ui-table-cell table-cell next-step")
    return Text("", className="ui-table-cell table-cell")
