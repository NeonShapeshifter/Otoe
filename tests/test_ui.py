from otoe import (
    ActionButton,
    Badge,
    Card,
    StatCard,
    TabButton,
    Tabs,
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
