from otoe import Show, Text, component, interval, mount, on_mount, root_widget, signal, unmount


def test_interval_ticks_until_cancelled():
    count = signal(0)
    handle = interval(1.0, lambda: count.set(count.value + 1))

    handle.tick()
    handle.tick()
    handle.cancel()
    handle.tick()

    assert count.value == 2


def test_interval_immediate_runs_once_on_creation():
    count = signal(0)

    interval(5.0, lambda: count.set(count.value + 1), immediate=True)

    assert count.value == 1


def test_interval_registered_inside_component_is_cancelled_on_unmount():
    count = signal(0)
    handles = []

    @component
    def PollingLabel():
        handle = interval(1.0, lambda: count.set(count.value + 1))
        handles.append(handle)
        return Text(count)

    mounted = mount(PollingLabel())
    widget = root_widget(mounted)
    handle = handles[0]

    handle.tick()

    assert count.value == 1
    assert widget.props["content"] == 1

    unmount(mounted)
    handle.tick()

    assert handle.active is False
    assert count.value == 1
    assert widget.props["content"] == 1


def test_interval_can_be_created_on_mount():
    count = signal(0)
    handles = []

    @component
    def MountedPollingLabel():
        on_mount(lambda: handles.append(interval(1.0, lambda: count.set(7))))
        return Text(count)

    mounted = mount(MountedPollingLabel())
    widget = root_widget(mounted)

    handles[0].tick()

    assert widget.props["content"] == 7

    unmount(mounted)
    assert handles[0].active is False


def test_interval_created_when_show_branch_activates_is_owned_by_branch():
    visible = signal(False)
    handles = []

    @component
    def PollingBranch():
        on_mount(lambda: handles.append(interval(1.0, lambda: None)))
        return Text("Polling")

    mounted = mount(Show(PollingBranch(), when=visible, fallback=Text("Idle")))

    visible.set(True)
    assert handles[0].active is True

    visible.set(False)
    assert handles[0].active is False

    unmount(mounted)
