from otoe import Button, HStack, Text, component, computed


@component
def TopBar(*, campaign, wifi_state, stealth_active):
    stealth_class = computed(
        lambda: "topbar-stealth is-active" if stealth_active.value else "topbar-stealth"
    )
    wifi_label = computed(lambda: f"WiFi: {wifi_state.value}")

    return HStack(
        Text("WRAITH OS", className="brand"),
        Text(campaign, className="campaign"),
        Text(wifi_label, className="indicator"),
        Button(
            "ST",
            className=stealth_class,
            onClick=lambda: stealth_active.set(not stealth_active.value),
        ),
        className="topbar",
        gap=8,
    )
