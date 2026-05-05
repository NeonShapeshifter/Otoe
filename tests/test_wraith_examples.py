from examples.wraith.arsenal import ArsenalView
from examples.wraith.runtime_status import RuntimeStatusCluster
from examples.wraith.topbar import TopBar
from otoe import mount, root_widget, signal, unmount


def test_wraith_topbar_example_reacts_and_dispatches_events():
    campaign = signal("Primary Campaign")
    wifi = signal("UP")
    stealth = signal(False)

    mounted = mount(
        TopBar(campaign=campaign, wifi_state=wifi, stealth_active=stealth)
    )
    root = root_widget(mounted)

    brand, campaign_text, wifi_text, stealth_button = root.children

    assert root.name == "HStack"
    assert brand.props["content"] == "WRAITH OS"
    assert campaign_text.props["content"] == "Primary Campaign"
    assert wifi_text.props["content"] == "WiFi: UP"
    assert stealth_button.props["className"] == "topbar-stealth"

    campaign.set("Night Ops")
    wifi.set("DEGRADED")
    stealth_button.trigger("onClick")

    assert campaign_text.props["content"] == "Night Ops"
    assert wifi_text.props["content"] == "WiFi: DEGRADED"
    assert stealth.value is True
    assert stealth_button.props["className"] == "topbar-stealth is-active"


def test_wraith_arsenal_example_mounts_search_and_metrics():
    query = signal("")
    active_tag = signal("ALL")
    missions = signal(
        [
            {
                "id": "wifi",
                "name": "WiFi Scan",
                "description": "Discover nearby networks.",
                "vector": "WiFi",
                "opsec": "LOW",
            },
            {
                "id": "rf",
                "name": "RF Survey",
                "description": "Inspect spectrum activity.",
                "vector": "RF",
                "opsec": "MED",
            },
        ]
    )
    page_label = signal("PAGE 1/2")

    def on_search(value):
        query.set(value)
        missions.set(
            [
                {
                    "id": "lab",
                    "name": "Lab Flow",
                    "description": "Restricted validation path.",
                    "vector": "USB",
                    "opsec": "HIGH",
                }
            ]
        )

    mounted = mount(
        ArsenalView(
            query=query,
            active_tag=active_tag,
            missions=missions,
            page_label=page_label,
            on_search=on_search,
            on_next=lambda: page_label.set("PAGE 2/2"),
        )
    )
    root = root_widget(mounted)
    hero, search_panel, mission_panel = root.children
    metrics = hero.children[0]
    search_input = search_panel.children[0]
    mission_show = mission_panel.children[0]
    mission_scroll = mission_show.children[0]
    mission_list = mission_scroll.children[0]
    next_button = mission_panel.children[1]

    assert metrics.children[0].props["content"] == "2 QUICK ACTIONS"
    assert metrics.children[1].props["content"] == "FILTER: ALL"
    assert metrics.children[2].props["content"] == "PAGE 1/2"
    assert search_input.props["value"] == ""
    assert len(mission_list.children) == 2
    assert mission_list.children[0].children[0].children[1].props["content"] == "WiFi Scan"

    search_input.trigger("onChange", "lab")
    active_tag.set("OPSEC")
    next_button.trigger("onClick")

    assert search_input.props["value"] == "lab"
    assert metrics.children[0].props["content"] == "1 QUICK ACTIONS"
    assert metrics.children[1].props["content"] == "FILTER: OPSEC"
    assert metrics.children[2].props["content"] == "PAGE 2/2"
    mission_show = mission_panel.children[0]
    mission_scroll = mission_show.children[0]
    mission_list = mission_scroll.children[0]
    assert len(mission_list.children) == 1
    assert mission_list.children[0].children[0].children[1].props["content"] == "Lab Flow"


def test_wraith_arsenal_example_renders_empty_state():
    mounted = mount(
        ArsenalView(
            query=signal(""),
            active_tag=signal("ALL"),
            missions=signal([]),
            page_label=signal("PAGE 0/0"),
            on_search=lambda value: None,
            on_next=lambda: None,
        )
    )
    root = root_widget(mounted)
    mission_panel = root.children[2]
    mission_show = mission_panel.children[0]

    assert mission_show.children[0].props["content"] == "No missions"


def test_wraith_runtime_status_cluster_polls_and_cleans_up():
    snapshots = [
        {"wifi": "UP", "bluetooth": "READY", "cpu": "42C", "storage": "18GB"},
        {"wifi": "DEGRADED", "bluetooth": "READY", "cpu": "44C", "storage": "17GB"},
    ]
    handles = []

    def probe():
        return snapshots.pop(0)

    mounted = mount(RuntimeStatusCluster(probe=probe, handles=handles))
    root = root_widget(mounted)
    handle = handles[0]

    assert [child.props["content"] for child in root.children] == [
        "WiFi: UP",
        "BT: READY",
        "CPU: 42C",
        "Disk: 18GB",
    ]

    handle.tick()

    assert [child.props["content"] for child in root.children] == [
        "WiFi: DEGRADED",
        "BT: READY",
        "CPU: 44C",
        "Disk: 17GB",
    ]

    unmount(mounted)

    assert handle.active is False
