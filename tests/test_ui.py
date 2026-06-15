from otoe import (
    ActionButton,
    AppFrame,
    AppShell,
    Badge,
    Card,
    Command,
    CommandPalette,
    CommandRegistry,
    DataTable,
    Dialog,
    EmptyState,
    FeedbackToast,
    Menu,
    MenuItem,
    NavRoute,
    RouteView,
    SectionHeader,
    ShortcutScope,
    Select,
    SelectOption,
    SidebarFrame,
    SidebarItem,
    SidebarNav,
    ListRow,
    MetricGrid,
    MetricTile,
    StatCard,
    Surface,
    TabButton,
    TableColumn,
    Tabs,
    Text,
    Toast,
    TopBar,
    VStack,
    class_names,
    mount,
    root_widget,
    signal,
)


def _focus_panel(show_widget):
    return show_widget.children[0].children[0]


def _menu_items(menu_widget):
    panel = _focus_panel(menu_widget)
    return panel.children[0].children[0].children


def _select_items(select_widget):
    focus_scope = select_widget.children[1].children[0]
    panel = focus_scope.children[0]
    return panel.children[0].children[0].children


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


def test_action_button_supports_content_slots_and_full_width():
    clicked = signal(False)
    button = root_widget(
        mount(
            ActionButton(
                "Deploy",
                leading="*",
                trailing="Enter",
                full_width=True,
                onClick=lambda: clicked.set(True),
            )
        )
    )

    assert button.name == "Button"
    assert button.props["label"] == "Deploy"
    assert button.props["className"] == "ui-button is-primary is-md is-full"
    content = button.children[0]
    assert content.props["className"] == "ui-button-content"
    assert content.children[0].props["className"] == "ui-button-leading"
    assert content.children[1].props["className"] == "ui-button-label"
    assert content.children[1].props["content"] == "Deploy"
    assert content.children[2].props["className"] == "ui-button-trailing"

    button.trigger("onClick")

    assert clicked.value is True


def test_badge_reacts_to_tone_signal():
    tone = signal("neutral")
    badge = root_widget(mount(Badge("State", tone=tone)))

    assert badge.props["className"] == "ui-badge is-neutral"

    tone.set("success")

    assert badge.props["className"] == "ui-badge is-success"


def test_stat_card_reacts_to_tone_signal():
    tone = signal("info")
    stat = root_widget(
        mount(
            StatCard(
                label="Thermal",
                value="18C",
                detail="Headroom",
                tone=tone,
            )
        )
    )
    detail = stat.children[0].children[2].children[0]

    assert detail.props["className"] == "ui-stat-detail is-info"

    tone.set("warn")

    assert detail.props["className"] == "ui-stat-detail is-warn"


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


def test_card_can_wrap_children_with_spacing_body():
    card = root_widget(
        mount(
            Card(
                Text("Summary"),
                padding=16,
                gap=8,
                className="surface",
            )
        )
    )

    assert card.name == "Panel"
    assert card.props["className"] == "ui-card is-default surface"
    body = card.children[0]
    assert body.name == "VStack"
    assert body.props["className"] == "ui-card-body"
    assert body.props["padding"] == 16
    assert body.props["gap"] == 8
    assert body.children[0].props["content"] == "Summary"


def test_modern_presets_compose_default_utility_surfaces():
    clicked = signal(None)
    frame = root_widget(
        mount(
            AppFrame(
                sidebar=SidebarFrame(
                    SidebarItem("Overview", detail="Live", tone="success", active=True),
                    brand="Otoe",
                    subtitle="Modern",
                ),
                topbar=TopBar(
                    "Command surface",
                    subtitle="Preset defaults",
                    status="Ready",
                    status_tone="success",
                    actions=ActionButton("Sync", size="sm", onClick=lambda: clicked.set("sync")),
                ),
                feedback=Toast("Loaded", tone="info"),
                content=VStack(
                    MetricGrid(
                        MetricTile(label="Velocity", value="31 ms", detail="render", tone="success"),
                    ),
                    Surface(
                        ListRow(
                            title="Utility layer smoke",
                            detail="Design systems",
                            badge="Ready",
                            badge_tone="success",
                            meta="2m",
                            tone="success",
                            action_label="Open",
                            on_action=lambda: clicked.set("open"),
                        ),
                        title="Jobs",
                        detail="1 visible",
                        badge="Preset",
                        badge_tone="info",
                    ),
                    gap=4,
                ),
                className="custom-frame",
            )
        )
    )

    assert frame.props["className"] == "ui-frame min-h-screen bg-bg text-ink custom-frame"
    shell = frame.children[0]
    assert shell.props["className"] == (
        "ui-frame-shell max-w-7xl mx-auto w-full p-6 gap-4 items-start flex-wrap"
    )
    sidebar = shell.children[0]
    assert sidebar.props["className"] == "ui-sidebar-frame w-72 shrink-0 p-4 gap-5 bg-ink rounded-xl shadow-md"
    assert sidebar.children[1].children[0].props["className"] == (
        "ui-sidebar-item p-3 gap-3 rounded-md bg-muted is-active"
    )
    main = shell.children[1]
    topbar = main.children[0]
    assert topbar.props["className"] == (
        "ui-toolbar ui-topbar justify-between p-5 bg-panel border border-line rounded-xl shadow-md"
    )
    sync = topbar.children[1].children[1]
    sync.trigger("onClick")
    assert clicked.value == "sync"

    content = main.children[2]
    metric = content.children[0].children[0]
    assert metric.props["className"] == (
        "ui-card is-default ui-stat-card ui-metric-tile flex-1 min-w-0 "
        "rounded-xl shadow-sm bg-success-soft border border-success"
    )
    surface = content.children[1]
    assert surface.props["className"] == (
        "ui-card is-default ui-surface rounded-xl shadow-sm bg-panel border border-line"
    )
    row = surface.children[0].children[1]
    assert row.props["className"] == (
        "ui-list-row p-3 gap-3 rounded-lg items-center bg-success-soft border border-success"
    )
    row.children[-1].trigger("onClick")
    assert clicked.value == "open"


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
    focus_scope = backdrop.children[0]
    panel = focus_scope.children[0]
    body = panel.children[0]
    assert backdrop.props["className"] == "ui-dialog-backdrop"
    assert focus_scope.name == "FocusScope"
    assert focus_scope.props["className"] == "ui-focus-scope ui-dialog-focus-scope"
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


def test_reference_app_helpers_compose_common_markup():
    header = root_widget(
        mount(
            SectionHeader(
                "Telemetry table",
                detail="1s sample rate",
                badge="Live",
                badge_tone="info",
                className="custom-section",
            )
        )
    )
    empty = root_widget(
        mount(
            EmptyState(
                "No records",
                description="Try another filter.",
                className="custom-empty",
            )
        )
    )

    assert header.name == "HStack"
    assert header.props["className"] == "ui-section-header custom-section"
    copy = header.children[0]
    assert copy.children[0].props["content"] == "Telemetry table"
    assert copy.children[0].props["className"] == "ui-section-title"
    assert copy.children[1].children[0].props["content"] == "1s sample rate"
    assert header.children[1].children[0].props["content"] == "Live"
    assert header.children[1].children[0].props["className"] == "ui-badge is-info ui-section-badge"

    assert empty.name == "VStack"
    assert empty.props["className"] == "ui-empty-state custom-empty"
    assert empty.children[0].props["content"] == "No records"
    assert empty.children[1].children[0].props["content"] == "Try another filter."


def test_section_header_and_empty_state_can_build_actions():
    selected = signal(None)
    header = root_widget(
        mount(
            SectionHeader(
                "Providers",
                action_label="Refresh",
                on_action=lambda: selected.set("header"),
            )
        )
    )
    empty = root_widget(
        mount(
            EmptyState(
                "No providers",
                action_label="Create",
                action_variant="primary",
                on_action=lambda: selected.set("empty"),
            )
        )
    )

    header_action = header.children[2].children[0]
    empty_action = empty.children[2].children[0]
    assert header_action.props["className"] == "ui-button is-ghost is-sm"
    assert empty_action.props["className"] == "ui-button is-primary is-sm"

    header_action.trigger("onClick")
    assert selected.value == "header"

    empty_action.trigger("onClick")
    assert selected.value == "empty"


def test_feedback_toast_renders_when_feedback_is_present():
    feedback = signal(None)
    toast = root_widget(mount(FeedbackToast(feedback, className="custom-feedback")))

    assert toast.children == []

    feedback.set({"title": "Saved", "detail": "Provider accepted changes.", "tone": "success"})

    rendered = toast.children[0]
    assert rendered.props["className"] == "ui-toast is-success custom-feedback"
    assert rendered.children[0].children[0].props["content"] == "Saved"
    assert rendered.children[0].children[1].children[0].props["content"] == "Provider accepted changes."


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


def test_command_palette_accepts_literal_query():
    selected = signal(None)

    palette = root_widget(
        mount(
            CommandPalette(
                query="mission",
                commands=[
                    {
                        "id": "mission",
                        "label": "Open Mission Exec",
                    },
                    {
                        "id": "customers",
                        "label": "Review Customers",
                    },
                ],
                on_query=lambda value: None,
                on_select=lambda command_id: selected.set(command_id),
            )
        )
    )

    command_list = palette.children[0].children[2]

    assert len(command_list.children) == 1
    command_list.children[0].trigger("onClick")
    assert selected.value == "mission"


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


def test_menu_renders_active_items_and_ignores_disabled_selection():
    selected = signal(None)
    active = signal("edit")
    menu = root_widget(
        mount(
            Menu(
                items=[
                    MenuItem("edit", "Edit view", "Tune current surface.", "E", tone="info"),
                    {"id": "delete", "label": "Delete view", "disabled": True, "tone": "danger"},
                ],
                active=active,
                on_select=lambda item_id: selected.set(item_id),
            )
        )
    )

    focus_scope = menu.children[0]
    panel = focus_scope.children[0]
    first, second = _menu_items(menu)

    assert focus_scope.props["className"] == "ui-focus-scope ui-menu-focus-scope"
    assert panel.props["className"] == "ui-card is-default ui-menu"
    assert first.props["className"] == "ui-menu-item is-info is-active"
    assert first.children[0].children[0].children[0].props["content"] == "Edit view"
    assert second.props["className"] == "ui-menu-item is-danger is-disabled"
    assert second.props["disabled"] is True

    second.trigger("onClick")

    assert selected.value is None

    first.trigger("onClick")

    assert selected.value == "edit"


def test_menu_tracks_open_signal():
    open_menu = signal(False)
    menu = root_widget(
        mount(
            Menu(
                items=[{"id": "edit", "label": "Edit view"}],
                open=open_menu,
                on_select=lambda item_id: None,
            )
        )
    )

    assert menu.children == []

    open_menu.set(True)

    button = _menu_items(menu)[0]
    assert button.children[0].children[0].children[0].props["content"] == "Edit view"


def test_menu_keyboard_moves_focus_selects_and_closes():
    selected = signal(None)
    focused = signal("edit")
    open_menu = signal(True)
    menu = root_widget(
        mount(
            Menu(
                items=[
                    MenuItem("edit", "Edit view", tone="info"),
                    MenuItem("duplicate", "Duplicate view", tone="success"),
                    MenuItem("archive", "Archive view", disabled=True, tone="warn"),
                ],
                open=open_menu,
                focused=focused,
                on_focus=lambda item_id: focused.set(item_id),
                on_select=lambda item_id: selected.set(item_id),
                on_open_change=lambda value: open_menu.set(value),
            )
        )
    )
    edit, duplicate, archive = _menu_items(menu)

    edit.trigger("onKeyDown", "ArrowDown")

    assert focused.value == "duplicate"
    assert edit.props["className"] == "ui-menu-item is-info"
    assert duplicate.props["className"] == "ui-menu-item is-success is-active"

    duplicate.trigger("onKeyDown", "ArrowDown")

    assert focused.value == "edit"

    assert archive.props["className"] == "ui-menu-item is-warn is-disabled"
    assert selected.value is None

    edit.trigger("onKeyDown", "Enter")

    assert selected.value == "edit"
    assert open_menu.value is False
    assert menu.children == []


def test_menu_keyboard_escape_closes_without_selecting():
    selected = signal(None)
    open_menu = signal(True)
    menu = root_widget(
        mount(
            Menu(
                items=[{"id": "edit", "label": "Edit view"}],
                open=open_menu,
                focused=signal("edit"),
                on_select=lambda item_id: selected.set(item_id),
                on_open_change=lambda value: open_menu.set(value),
            )
        )
    )
    button = _menu_items(menu)[0]

    button.trigger("onKeyDown", "Escape")

    assert selected.value is None
    assert open_menu.value is False
    assert menu.children == []


def test_select_renders_selected_option_and_dispatches_change():
    selected = signal("compact")
    open_select = signal(False)
    select = root_widget(
        mount(
            Select(
                options=[
                    SelectOption("compact", "Compact", "Dense operational rhythm.", tone="info"),
                    {"value": "roomy", "label": "Roomy", "description": "More air for SaaS pages.", "tone": "success"},
                ],
                value=selected,
                open=open_select,
                on_change=lambda value: selected.set(value),
                on_open_change=lambda value: open_select.set(value),
                placeholder="Choose density",
            )
        )
    )

    trigger = select.children[0]
    assert select.props["className"] == "ui-select"
    assert trigger.props["className"] == "ui-select-trigger"
    assert trigger.children[0].children[0].children[0].props["content"] == "Compact"
    assert len(select.children[1].children) == 0

    trigger.trigger("onClick")

    assert open_select.value is True
    assert trigger.props["className"] == "ui-select-trigger is-active"

    focus_scope = select.children[1].children[0]
    compact, roomy = _select_items(select)
    assert focus_scope.props["className"] == "ui-focus-scope ui-select-focus-scope"
    assert compact.props["className"] == "ui-select-option is-active"
    assert roomy.children[0].children[0].children[0].props["content"] == "Roomy"

    roomy.trigger("onClick")

    assert selected.value == "roomy"
    assert open_select.value is False
    assert trigger.children[0].children[0].children[0].props["content"] == "Roomy"


def test_select_ignores_disabled_options():
    selected = signal("compact")
    open_select = signal(True)
    select = root_widget(
        mount(
            Select(
                options=[
                    {"value": "compact", "label": "Compact"},
                    {"value": "locked", "label": "Locked", "disabled": True},
                ],
                value=selected,
                open=open_select,
                on_change=lambda value: selected.set(value),
                on_open_change=lambda value: open_select.set(value),
            )
        )
    )
    locked = _select_items(select)[1]

    assert locked.props["className"] == "ui-select-option is-disabled"
    assert locked.props["disabled"] is True

    locked.trigger("onClick")

    assert selected.value == "compact"
    assert open_select.value is True


def test_select_keyboard_opens_moves_selection_and_closes():
    selected = signal("compact")
    open_select = signal(False)
    select = root_widget(
        mount(
            Select(
                options=[
                    SelectOption("compact", "Compact", tone="info"),
                    SelectOption("locked", "Locked", disabled=True, tone="warn"),
                    SelectOption("roomy", "Roomy", tone="success"),
                ],
                value=selected,
                open=open_select,
                on_change=lambda value: selected.set(value),
                on_open_change=lambda value: open_select.set(value),
            )
        )
    )
    trigger = select.children[0]

    trigger.trigger("onKeyDown", "ArrowDown")

    assert selected.value == "roomy"
    assert open_select.value is True
    assert trigger.children[0].children[0].children[0].props["content"] == "Roomy"

    compact, locked, roomy = _select_items(select)
    assert locked.props["className"] == "ui-select-option is-disabled"
    assert roomy.props["className"] == "ui-select-option is-active"

    roomy.trigger("onKeyDown", "ArrowDown")

    assert selected.value == "compact"
    assert compact.props["className"] == "ui-select-option is-active"

    compact.trigger("onKeyDown", "Escape")

    assert open_select.value is False
    assert len(select.children[1].children) == 0


def test_select_keyboard_enter_selects_focused_option():
    selected = signal("compact")
    open_select = signal(True)
    select = root_widget(
        mount(
            Select(
                options=[
                    SelectOption("compact", "Compact"),
                    SelectOption("roomy", "Roomy"),
                ],
                value=selected,
                open=open_select,
                on_change=lambda value: selected.set(value),
                on_open_change=lambda value: open_select.set(value),
            )
        )
    )
    roomy = _select_items(select)[1]

    roomy.trigger("onKeyDown", "Enter")

    assert selected.value == "roomy"
    assert open_select.value is False


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
