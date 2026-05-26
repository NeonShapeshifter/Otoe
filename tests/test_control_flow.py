import pytest

from otoe import For, HStack, Show, Text, component, effect, mount, on_cleanup, root_widget, signal


def test_show_switches_between_branch_and_fallback():
    visible = signal(False)
    mounted = mount(
        Show(
            Text("Visible"),
            when=visible,
            fallback=Text("Hidden"),
        )
    )
    root = root_widget(mounted)

    assert root.name == "Show"
    assert root.children[0].props["content"] == "Hidden"

    visible.set(True)

    assert len(root.children) == 1
    assert root.children[0].props["content"] == "Visible"


def test_show_disposes_hidden_branch_owner():
    visible = signal(True)
    events = []

    @component
    def Branch():
        effect(lambda: events.append("effect"))
        on_cleanup(lambda: events.append("cleanup"))
        return Text("Branch")

    mounted = mount(Show(Branch(), when=visible, fallback=Text("Fallback")))

    assert root_widget(mounted).children[0].props["content"] == "Branch"
    assert events == ["effect"]

    visible.set(False)

    assert root_widget(mounted).children[0].props["content"] == "Fallback"
    assert events == ["effect", "cleanup"]


def test_for_renders_keyed_items_and_reorders_without_remounting():
    missions = signal(
        [
            {"id": "wifi", "name": "WiFi Scan"},
            {"id": "bt", "name": "Bluetooth Sweep"},
        ]
    )
    mounted_ids = []

    @component
    def MissionRow(*, mission):
        mounted_ids.append(mission["id"])
        return HStack(Text(mission["name"]))

    mounted = mount(
        For(
            each=missions,
            key=lambda mission: mission["id"],
            children=lambda mission: MissionRow(mission=mission),
        )
    )
    root = root_widget(mounted)
    first_bt_widget = root.children[1]

    assert [child.children[0].props["content"] for child in root.children] == [
        "WiFi Scan",
        "Bluetooth Sweep",
    ]

    missions.set(
        [
            {"id": "bt", "name": "Bluetooth Sweep"},
            {"id": "wifi", "name": "WiFi Scan"},
            {"id": "rf", "name": "RF Survey"},
        ]
    )

    assert [child.children[0].props["content"] for child in root.children] == [
        "Bluetooth Sweep",
        "WiFi Scan",
        "RF Survey",
    ]
    assert root.children[0] is first_bt_widget
    assert mounted_ids == ["wifi", "bt", "rf"]


def test_for_updates_same_key_when_item_data_changes():
    missions = signal([{"id": "wifi", "name": "WiFi Scan"}])
    events = []

    @component
    def MissionRow(*, mission):
        events.append(f"mount:{mission['name']}")
        on_cleanup(lambda: events.append(f"cleanup:{mission['name']}"))
        return Text(mission["name"])

    mounted = mount(
        For(
            each=missions,
            key=lambda mission: mission["id"],
            children=lambda mission: MissionRow(mission=mission),
        )
    )
    root = root_widget(mounted)
    first_widget = root.children[0]

    assert first_widget.props["content"] == "WiFi Scan"

    missions.set([{"id": "wifi", "name": "WiFi Survey"}])

    assert root.children[0].props["content"] == "WiFi Survey"
    assert root.children[0] is not first_widget
    assert events == [
        "mount:WiFi Scan",
        "cleanup:WiFi Scan",
        "mount:WiFi Survey",
    ]


def test_for_rejects_duplicate_keys():
    missions = signal(
        [
            {"id": "wifi", "name": "WiFi Scan"},
            {"id": "wifi", "name": "WiFi Survey"},
        ]
    )

    with pytest.raises(ValueError, match="duplicate key 'wifi'"):
        mount(
            For(
                each=missions,
                key=lambda mission: mission["id"],
                children=lambda mission: Text(mission["name"]),
            )
        )


def test_for_disposes_removed_key_and_renders_fallback():
    missions = signal([{"id": "wifi", "name": "WiFi Scan"}])
    events = []

    @component
    def MissionRow(*, mission):
        on_cleanup(lambda: events.append(f"cleanup:{mission['id']}"))
        return Text(mission["name"])

    mounted = mount(
        For(
            each=missions,
            key=lambda mission: mission["id"],
            children=lambda mission: MissionRow(mission=mission),
            fallback=Text("No missions"),
        )
    )
    root = root_widget(mounted)

    assert root.children[0].props["content"] == "WiFi Scan"

    missions.set([])

    assert root.children[0].props["content"] == "No missions"
    assert events == ["cleanup:wifi"]
