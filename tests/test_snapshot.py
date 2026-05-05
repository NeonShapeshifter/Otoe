from examples.wraith.arsenal import ArsenalView
from examples.wraith.runtime_status import RuntimeStatusCluster
from examples.wraith.topbar import TopBar
from otoe import mount, signal, snapshot, snapshot_text


def test_snapshot_serializes_widget_props_events_and_children():
    campaign = signal("Primary")
    wifi = signal("UP")
    stealth = signal(False)

    mounted = mount(
        TopBar(campaign=campaign, wifi_state=wifi, stealth_active=stealth)
    )
    tree = snapshot(mounted)

    assert tree["name"] == "HStack"
    assert tree["props"] == {"className": "topbar", "gap": 8}
    assert tree["children"][0]["props"] == {
        "className": "brand",
        "content": "WRAITH OS",
    }
    assert tree["children"][3]["events"] == ["onClick"]


def test_snapshot_reflects_topbar_state_changes():
    campaign = signal("Primary")
    wifi = signal("UP")
    stealth = signal(False)
    mounted = mount(
        TopBar(campaign=campaign, wifi_state=wifi, stealth_active=stealth)
    )

    campaign.set("Night Ops")
    wifi.set("DEGRADED")
    stealth.set(True)

    text = snapshot_text(mounted)

    assert '"content": "Night Ops"' in text
    assert '"content": "WiFi: DEGRADED"' in text
    assert '"className": "topbar-stealth is-active"' in text


def test_snapshot_tracks_arsenal_list_changes():
    missions = signal(
        [
            {
                "id": "wifi",
                "name": "WiFi Scan",
                "description": "Discover nearby networks.",
                "vector": "WiFi",
                "opsec": "LOW",
            }
        ]
    )

    mounted = mount(
        ArsenalView(
            query=signal(""),
            active_tag=signal("ALL"),
            missions=missions,
            page_label=signal("PAGE 1/1"),
            on_search=lambda value: None,
            on_next=lambda: None,
        )
    )

    before = snapshot_text(mounted)
    missions.set([])
    after = snapshot_text(mounted)

    assert "WiFi Scan" in before
    assert "No missions" not in before
    assert "WiFi Scan" not in after
    assert "No missions" in after


def test_snapshot_tracks_runtime_status_polling():
    snapshots = [
        {"wifi": "UP", "bluetooth": "READY", "cpu": "42C", "storage": "18GB"},
        {"wifi": "DOWN", "bluetooth": "READY", "cpu": "45C", "storage": "17GB"},
    ]
    handles = []

    mounted = mount(
        RuntimeStatusCluster(probe=lambda: snapshots.pop(0), handles=handles)
    )

    before = snapshot_text(mounted)
    handles[0].tick()
    after = snapshot_text(mounted)

    assert "WiFi: UP" in before
    assert "CPU: 42C" in before
    assert "WiFi: DOWN" in after
    assert "CPU: 45C" in after

