import re

from examples.data_workflow.live_preview import DataWorkflowLivePreview
from examples.data_workflow.preview import build_preview_html
from examples.data_workflow.workbench import (
    MemoryDataWorkflowProvider,
    demo_workflow_snapshot,
    empty_workflow_snapshot,
    filtered_records,
)


def _click_id_before(html, marker):
    segment = html[: html.index(marker)]
    matches = re.findall(r'data-otoe-click="([^"]+)"', segment)
    assert matches
    return matches[-1]


def _change_id_after(html, marker):
    segment = html[html.index(marker) :]
    match = re.search(r'data-otoe-change="([^"]+)"', segment)
    assert match is not None
    return match.group(1)


def _button_click_id(html, label):
    match = re.search(
        rf'<button[^>]*data-otoe-click="([^"]+)"[^>]*>{label}</button>',
        html,
    )
    assert match is not None
    return match.group(1)


def test_data_workflow_preview_contains_reference_app_surface():
    html = build_preview_html()

    assert "<!doctype html>" in html
    assert "<title>Otoe Data Workflow Console</title>" in html
    assert "Data Workflow Console" in html
    assert "Quarterly intake review" in html
    assert "Quality gate" in html
    assert "Arcadia Finance" in html
    assert "Computed object" not in html
    assert "DataWorkflowWorkbench" not in html


def test_data_workflow_preview_renders_empty_filter_state():
    html = build_preview_html(empty_workflow_snapshot())

    assert "Search updated" in html
    assert "No records match current filters" in html
    assert "zzz" in html


def test_data_workflow_provider_filters_search_and_stage():
    provider = MemoryDataWorkflowProvider(demo_workflow_snapshot())

    snapshot = provider.set_query("mara")
    assert [record.account for record in filtered_records(snapshot)] == [
        "Arcadia Finance",
        "Juniper Systems",
    ]

    snapshot = provider.set_stage_filter("Review")
    assert [record.account for record in filtered_records(snapshot)] == ["Arcadia Finance"]


def test_data_workflow_provider_approves_selected_batch():
    provider = MemoryDataWorkflowProvider(demo_workflow_snapshot())

    provider.toggle_record("rec-101")
    snapshot = provider.run_action("approve")

    record = next(record for record in snapshot.records if record.id == "rec-101")
    assert record.stage == "Approved"
    assert record.selected is False
    assert snapshot.events[0].action == "Approved selected records"
    assert snapshot.last_feedback is not None
    assert snapshot.last_feedback.title == "Batch approved"


def test_data_workflow_provider_blocks_invalid_batch():
    provider = MemoryDataWorkflowProvider(demo_workflow_snapshot())

    provider.toggle_record("rec-103")
    snapshot = provider.run_action("approve")

    record = next(record for record in snapshot.records if record.id == "rec-103")
    assert record.stage == "Blocked"
    assert record.selected is True
    assert snapshot.last_feedback is not None
    assert snapshot.last_feedback.title == "Approval blocked"


def test_data_workflow_live_preview_filters_search():
    app = DataWorkflowLivePreview()
    html = app.render_fragment()
    change_id = _change_id_after(html, "Search records")

    html = app.dispatch_event(change_id, "mercury")

    assert 'value="mercury"' in html
    assert "Mercury Labs" in html
    assert "Arcadia Finance" not in html
    assert "1 records visible." in html


def test_data_workflow_live_preview_filters_stage():
    app = DataWorkflowLivePreview()
    html = app.render_fragment()
    blocked_id = _button_click_id(html, "Blocked")

    html = app.dispatch_event(blocked_id)

    assert "Filter applied" in html
    assert "Blocked rows are visible." in html
    assert "Mercury Labs" in html
    assert "Helio Works" not in html


def test_data_workflow_live_preview_selects_and_approves_batch():
    app = DataWorkflowLivePreview()
    html = app.render_fragment()
    select_id = _click_id_before(html, "Arcadia Finance")

    html = app.dispatch_event(select_id)
    assert "Selection updated" in html
    assert "1 selected" in html

    approve_id = _click_id_before(html, "Approve selected")
    html = app.dispatch_event(approve_id)

    assert "Batch approved" in html
    assert "1 records were approved." in html
    assert "Contract values reconciled." in html
    assert "Needs approval" not in html
