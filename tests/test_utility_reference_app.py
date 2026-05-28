import re

from examples.utility.ops_console import (
    MemoryUtilityOpsProvider,
    UtilityOpsConsole,
    demo_utility_snapshot,
    empty_utility_snapshot,
)
from examples.utility.preview import build_preview_html
from otoe import mount, root_widget, signal


def test_utility_preview_contains_utility_first_surface():
    html = build_preview_html()

    assert "<!doctype html>" in html
    assert "<title>Otoe Utility Ops Preview</title>" in html
    assert '<link rel="stylesheet" href="reference_theme.css">' in html
    assert "<style>" in html
    assert "--otoe-panel: #ffffff;" in html
    assert ".p-6 {" in html
    assert ".shadow-sm {" in html
    assert "Otoe Utility Ops" in html
    assert "Forvara Workshop" in html
    assert "Operations command surface" in html
    assert "No app CSS" in html
    assert "Utility layer smoke" in html
    assert "This surface uses helpers plus low-level utility classes." in html
    assert "ui-frame min-h-screen bg-bg text-ink utility-app" in html
    assert "ui-frame-shell max-w-7xl mx-auto w-full p-6 gap-4 items-start flex-wrap utility-shell" in html
    assert "ui-topbar justify-between p-5 bg-panel border border-line rounded-xl shadow-md" in html
    assert "ui-list-row p-3 gap-3 rounded-lg items-center bg-success-soft border border-success" in html
    assert "bg-success-soft border border-success" in html
    assert "rounded-xl shadow-md" in html
    assert "Computed object" not in html
    assert "UtilityOpsConsole" not in html


def test_utility_preview_renders_empty_state_actions():
    html = build_preview_html(empty_utility_snapshot())

    assert "Empty provider state" in html
    assert "No active jobs" in html
    assert "No activity" in html
    assert re.search(
        r'<button class="otoe-button ui-button is-ghost is-sm"[^>]*>Refresh</button>',
        html,
    )


def test_utility_provider_runs_actions_and_preserves_boundaries():
    provider = MemoryUtilityOpsProvider(demo_utility_snapshot())

    snapshot = provider.run_action("refresh")
    assert snapshot.status == "Synced"
    assert snapshot.last_feedback is not None
    assert snapshot.last_feedback.title == "Surface refreshed"
    assert snapshot.events[0].label == "Utility surface refreshed"

    snapshot = provider.run_action("open:job-2")
    assert snapshot.last_feedback is not None
    assert snapshot.last_feedback.title == "Job opened"
    assert "Reference app scan" in snapshot.last_feedback.detail

    snapshot = provider.run_action("missing")
    assert snapshot.last_feedback is not None
    assert snapshot.last_feedback.tone == "danger"


def test_utility_component_uses_helper_ergonomics_and_dispatches_actions():
    selected = signal(None)
    app = root_widget(
        mount(
            UtilityOpsConsole(
                snapshot=signal(demo_utility_snapshot()),
                on_action=lambda action_id: selected.set(action_id),
            )
        )
    )

    assert app.props["className"] == "ui-frame min-h-screen bg-bg text-ink utility-app"
    shell = app.children[0]
    assert shell.props["className"] == (
        "ui-frame-shell max-w-7xl mx-auto w-full p-6 gap-4 items-start flex-wrap utility-shell"
    )
    sidebar = shell.children[0]
    assert sidebar.props["className"] == "ui-sidebar-frame w-72 shrink-0 p-4 gap-5 bg-ink rounded-xl shadow-md"
    main = shell.children[1]
    content = main.children[2]
    header = main.children[0]
    assert header.props["className"] == (
        "ui-toolbar ui-topbar justify-between p-5 bg-panel border border-line rounded-xl shadow-md"
    )
    stats = content.children[0]
    assert stats.props["className"] == "ui-metric-grid gap-3 flex-wrap"
    queue_card = content.children[1].children[0]
    queue_body = queue_card.children[0]
    section_header = queue_body.children[0]
    assert queue_body.props["className"] == "ui-card-body"
    assert section_header.props["className"] == "ui-section-header"

    run_check = section_header.children[2].children[0]
    assert run_check.props["className"] == "ui-button is-ghost is-sm"
    run_check.trigger("onClick")
    assert selected.value == "run_check"

    first_job = queue_body.children[1].children[0]
    open_button = first_job.children[3]
    open_button.trigger("onClick")
    assert selected.value == "open:job-1"
