from otoe import HStack, Text, batch, component, computed, interval, signal


@component
def RuntimeStatusCluster(*, probe, handles=None):
    wifi = signal("--")
    bluetooth = signal("--")
    cpu = signal("--")
    storage = signal("--")

    def poll():
        snapshot = probe()

        def apply_snapshot():
            wifi.set(snapshot["wifi"])
            bluetooth.set(snapshot["bluetooth"])
            cpu.set(snapshot["cpu"])
            storage.set(snapshot["storage"])

        batch(apply_snapshot)

    handle = interval(1.0, poll, immediate=True)
    if handles is not None:
        handles.append(handle)

    return HStack(
        Text(computed(lambda: f"WiFi: {wifi.value}"), className="indicator"),
        Text(computed(lambda: f"BT: {bluetooth.value}"), className="indicator"),
        Text(computed(lambda: f"CPU: {cpu.value}"), className="indicator"),
        Text(computed(lambda: f"Disk: {storage.value}"), className="indicator"),
        className="runtime-status",
        gap=8,
    )

