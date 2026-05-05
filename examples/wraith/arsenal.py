from examples.wraith.mission_card import MissionCard
from otoe import Button, For, HStack, Input, Panel, ScrollView, Show, Text, VStack, component, computed


@component
def ArsenalView(*, query, active_tag, missions, page_label, on_search, on_next):
    visible_count = computed(lambda: len(missions.value))
    summary = computed(lambda: f"{visible_count.value} QUICK ACTIONS")
    active_filter = computed(lambda: f"FILTER: {active_tag.value}")
    has_missions = computed(lambda: visible_count.value > 0)

    return VStack(
        Panel(
            HStack(
                Text(summary, className="metric"),
                Text(active_filter, className="metric"),
                Text(page_label, className="metric"),
                className="metrics",
            ),
            title="QUICK ACTIONS",
            className="hero",
        ),
        Panel(
            Input(
                value=query,
                placeholder="SEARCH QUICK ACTIONS...",
                onChange=on_search,
            ),
            title="SEARCH / FILTERS",
            className="search-panel",
        ),
        Panel(
            Show(
                ScrollView(
                    For(
                        each=missions,
                        key=lambda mission: mission["id"],
                        children=lambda mission: MissionCard(mission=mission),
                        fallback=Text("No missions", className="empty"),
                    ),
                    className="mission-scroll",
                ),
                when=has_missions,
                fallback=Text("No missions", className="empty"),
            ),
            Button("NEXT", onClick=on_next),
            title="MISSION SURFACES",
            className="mission-panel",
        ),
        className="arsenal",
        gap=12,
    )
