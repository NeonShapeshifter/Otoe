from otoe import (
    ActionButton,
    AppShell,
    Badge,
    Card,
    Command,
    CommandPalette,
    CommandRegistry,
    DataTable,
    Dialog,
    NavRoute,
    RouteView,
    ShortcutScope,
    SidebarNav,
    StatCard,
    TabButton,
    TableColumn,
    Tabs,
    Text,
    Toast,
    VStack,
    class_names,
    mount,
    root_widget,
    signal,
)


def test_class_names_deduplicates_and_skips_empty_parts():
    assert class_names("ui-button primary", None, "", "primary extra") == "ui-button primary extra"


def test_badge_and_action_button_mount_with_ui_classes_and_events():
    clicked = signal(False)
    badge = root_widget(mount(Badge("Ready", tone="success", className="custom")))
    button = root_widget(
        mount(
            ActionButton(
                "Run",
                variant="ghost",
                size="sm",
                onClick=lambda: clicked.set(True),
            )
        )
    )

    assert badge.name == "Text"
    assert badge.props["className"] == "ui-badge is-success custom"
    assert button.name == "Button"
    assert button.props["className"] == "ui-button is-ghost is-sm"

    button.trigger("onClick")

    assert clicked.value is True


def test_badge_reacts_to_tone_signal():
    tone = signal("neutral")
    badge = root_widget(mount(Badge("State", tone=tone)))

    assert badge.props["className"] == "ui-badge is-neutral"

    tone.set("success")

    assert badge.props["className"] == "ui-badge is-success"


def test_card_tabs_and_stat_card_compose_primitives():
    card = root_widget(
        mount(
            Card(
                Tabs(
                    TabButton("Overview", active=True),
                    TabButton("Revenue"),
                    orientation="vertical",
                ),
                className="sidebar",
            )
        )
    )
    stat = root_widget(
        mount(
            StatCard(
                label="Pipeline",
                value="$42,000",
                detail="+12%",
                tone="good",
            )
        )
    )

    assert card.name == "Panel"
    assert card.props["className"] == "ui-card is-default sidebar"
    tabs = card.children[0]
    assert tabs.name == "VStack"
    assert tabs.props["className"] == "ui-tabs is-vertical"
    assert tabs.children[0].props["className"] == "ui-tab is-active"

    assert stat.name == "Panel"
    body = stat.children[0]
    assert body.children[0].props["content"] == "Pipeline"
    assert body.children[1].props["content"] == "$42,000"


def test_tab_button_reacts_to_active_signal():
    active = signal(False)
    button = root_widget(mount(TabButton("Customers", active=active)))

    assert button.props["className"] == "ui-tab"

    active.set(True)

    assert button.props["className"] == "ui-tab is-active"


def test_stat_card_hides_reactive_empty_detail():
    detail = signal(None)
    card = root_widget(mount(StatCard(label="NPS", value="72", detail=detail)))
    body = card.children[0]
    detail_show = body.children[2]

    assert detail_show.children == []

    detail.set("+6")

    assert detail_show.children[0].props["content"] == "+6"


def test_data_table_renders_columns_rows_and_custom_cells():
    rows = signal(
        [
            {"id": "one", "name": "Arcadia", "health": "Healthy"},
        ]
    )

    def render_cell(row, column):
        if column.key == "health":
            return Badge(row["health"], tone="success", className="health")
        return None

    def safe_cell(row, column):
        custom = render_cell(row, column)
        if custom is not None:
            return custom
        return Badge(row[column.key], tone="neutral")

    table = root_widget(
        mount(
            DataTable(
                columns=[
                    TableColumn("name", "Account", "account"),
                    {"key": "health", "label": "Health"},
                ],
                rows=rows,
                key=lambda row: row["id"],
                render_cell=safe_cell,
            )
        )
    )

    assert table.props["className"] == "ui-table"
    assert table.children[0].props["className"] == "ui-table-head"
    row_list = table.children[1]
    row = row_list.children[0]
    assert row.props["className"] == "ui-table-row"
    assert row.children[0].props["content"] == "Arcadia"
    assert row.children[1].props["className"] == "ui-badge is-success health"


def test_dialog_tracks_open_signal():
    open_dialog = signal(False)
    dialog = root_widget(
        mount(
            Dialog(
                Badge("Synced", tone="success"),
                open=open_dialog,
                title="Workspace settings",
                description="Defaults updated.",
            )
        )
    )

    assert dialog.children == []

    open_dialog.set(True)

    backdrop = dialog.children[0]
    panel = backdrop.children[0]
    body = panel.children[0]
    assert backdrop.props["className"] == "ui-dialog-backdrop"
    assert body.children[0].children[0].props["content"] == "Workspace settings"
    assert body.children[2].props["content"] == "Synced"


def test_toast_hides_empty_description():
    toast = root_widget(mount(Toast("Saved", tone="success")))
    copy = toast.children[0]
    description_show = copy.children[1]

    assert toast.props["className"] == "ui-toast is-success"
    assert copy.children[0].props["content"] == "Saved"
    assert description_show.children == []


def test_toast_reacts_to_tone_signal():
    tone = signal("neutral")
    toast = root_widget(mount(Toast("Command state", tone=tone)))
    badge = toast.children[1]

    assert toast.props["className"] == "ui-toast is-neutral"
    assert badge.props["className"] == "ui-badge is-neutral ui-toast-badge"
    assert badge.props["content"] == "NEUTRAL"

    tone.set("success")

    assert toast.props["className"] == "ui-toast is-success"
    assert badge.props["className"] == "ui-badge is-success ui-toast-badge"
    assert badge.props["content"] == "SUCCESS"


def test_command_palette_filters_and_dispatches_selection():
    query = signal("")
    selected = signal(None)
    commands = [
        {
            "id": "mission",
            "label": "Open Mission Exec",
            "description": "Jump to the active Wraith mission.",
            "group": "Wraith",
            "shortcut": "M",
        },
        {
            "id": "customers",
            "label": "Open Customers",
            "description": "Review account health.",
            "group": "SaaS",
            "shortcut": "C",
        },
    ]

    palette = root_widget(
        mount(
            CommandPalette(
                query=query,
                commands=commands,
                on_query=lambda value: query.set(value),
                on_select=lambda command_id: selected.set(command_id),
            )
        )
    )

    assert palette.props["className"] == "ui-card is-default ui-command-card"
    body = palette.children[0]
    command_list = body.children[2]
    assert len(command_list.children) == 2

    query.set("mission")

    assert len(command_list.children) == 1
    item = command_list.children[0]
    assert item.name == "Button"
    assert item.children[0].children[0].children[0].props["content"] == "Open Mission Exec"

    item.trigger("onClick")

    assert selected.value == "mission"


def test_command_palette_enter_selects_first_visible_command():
    query = signal("")
    selected = signal(None)
    commands = [
        {
            "id": "mission",
            "label": "Open Mission Exec",
            "description": "Jump to the active Wraith mission.",
        },
        {
            "id": "customers",
            "label": "Open Customers",
            "description": "Review account health.",
        },
    ]

    palette = root_widget(
        mount(
            CommandPalette(
                query=query,
                commands=commands,
                on_query=lambda value: query.set(value),
                on_select=lambda command_id: selected.set(command_id),
            )
        )
    )
    input_widget = palette.children[0].children[1]

    input_widget.trigger("onKeyDown", "Escape")

    assert selected.value is None

    input_widget.trigger("onKeyDown", "Enter")

    assert selected.value == "mission"

    query.set("customers")
    input_widget.trigger("onKeyDown", "Enter")

    assert selected.value == "customers"


def test_command_palette_can_mark_input_for_autofocus():
    query = signal("")
    palette = root_widget(
        mount(
            CommandPalette(
                query=query,
                commands=[
                    {
                        "id": "mission",
                        "label": "Open Mission Exec",
                    },
                ],
                on_query=lambda value: query.set(value),
                on_select=lambda command_id: None,
                autoFocus=True,
            )
        )
    )

    input_widget = palette.children[0].children[1]

    assert input_widget.props["autoFocus"] is True


def test_command_registry_normalizes_filters_and_matches_shortcuts():
    registry = CommandRegistry(
        [
            Command("mission", "Open Mission Exec", "Jump to Wraith.", "Wraith", "M"),
            {"id": "customers", "label": "Review Customers", "group": "SaaS", "shortcut": "C"},
        ]
    )

    assert [command.id for command in registry.commands] == ["mission", "customers"]
    assert registry.first("wraith").id == "mission"
    assert registry.find("customers").label == "Review Customers"
    assert registry.find_shortcut("c").id == "customers"
    assert registry.find_shortcut("x") is None


def test_shortcut_scope_registers_global_keydown_handler():
    payload = signal(None)
    scope = root_widget(
        mount(
            ShortcutScope(
                Text("App"),
                onKeyDown=lambda event: payload.set(event),
                className="workspace",
            )
        )
    )

    assert scope.name == "ShortcutScope"
    assert scope.props["className"] == "ui-shortcut-scope workspace"
    assert scope.children[0].props["content"] == "App"

    scope.trigger("onGlobalKeyDown", {"key": "k", "ctrlKey": True})

    assert payload.value == {"key": "k", "ctrlKey": True}


def test_app_shell_composes_header_sidebar_and_content_slots():
    shell = root_widget(
        mount(
            AppShell(
                header=Text("Topbar"),
                sidebar=Text("Sidebar"),
                content=Text("Content"),
                className="workspace",
            )
        )
    )

    assert shell.name == "VStack"
    assert shell.props["className"] == "ui-app-shell workspace"
    assert shell.children[0].props["className"] == "ui-app-header"
    assert shell.children[0].children[0].props["content"] == "Topbar"

    main = shell.children[1]
    assert main.props["className"] == "ui-app-main"
    assert main.children[0].props["className"] == "ui-app-sidebar"
    assert main.children[0].children[0].props["content"] == "Sidebar"
    assert main.children[1].props["className"] == "ui-app-content"
    assert main.children[1].children[0].props["content"] == "Content"


def test_sidebar_nav_tracks_active_route_and_dispatches_navigation():
    active = signal("overview")
    selected = signal(None)
    routes = [
        NavRoute("overview", "Overview", "Workspace state", badge="3", tone="info"),
        {"id": "wraith", "label": "Wraith", "description": "Mission surface"},
    ]
    nav = root_widget(
        mount(
            SidebarNav(
                routes=routes,
                active=active,
                on_navigate=lambda route_id: selected.set(route_id),
                brand=Text("Otoe"),
                footer="Ready",
            )
        )
    )

    assert nav.props["className"] == "ui-sidebar-nav"
    assert nav.children[0].props["className"] == "ui-sidebar-brand"
    route_list = nav.children[1]
    first, second = route_list.children
    assert first.props["className"] == "ui-nav-item is-active"
    assert first.children[0].children[0].children[0].props["content"] == "Overview"
    assert first.children[0].children[1].children[0].props["content"] == "3"
    assert second.props["className"] == "ui-nav-item"

    active.set("wraith")

    assert first.props["className"] == "ui-nav-item"
    assert second.props["className"] == "ui-nav-item is-active"

    second.trigger("onClick")

    assert selected.value == "wraith"


def test_route_view_renders_active_route_and_fallback():
    active = signal("ui")
    routes = [
        NavRoute("ui", "UI Kit"),
        NavRoute("saas", "SaaS"),
    ]

    view = root_widget(
        mount(
            RouteView(
                route=active,
                routes=routes,
                render=lambda route: VStack(
                    Text(route.label, className="route-title"),
                    className=f"route-{route.id}",
                ),
            )
        )
    )

    route_list = view.children[0]
    assert route_list.children[0].props["className"] == "route-ui"
    assert route_list.children[0].children[0].props["content"] == "UI Kit"

    active.set("saas")

    assert route_list.children[0].props["className"] == "route-saas"
    assert route_list.children[0].children[0].props["content"] == "SaaS"

    active.set("missing")

    assert route_list.children[0].props["content"] == "Route not found"
