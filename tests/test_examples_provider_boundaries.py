from __future__ import annotations

import re
from dataclasses import replace

from examples.admin.live_preview import AdminLivePreview
from examples.admin.preview import build_preview_html as build_admin_html
from examples.admin.settings_console import (
    MemoryAdminSettingsProvider,
    demo_admin_snapshot,
)
from examples.data_workflow.live_preview import DataWorkflowLivePreview
from examples.data_workflow.preview import build_preview_html as build_data_workflow_html
from examples.data_workflow.workbench import (
    MemoryDataWorkflowProvider,
    WorkflowRecord,
    demo_workflow_snapshot,
)


class RecordingAdminSettingsProvider(MemoryAdminSettingsProvider):
    def __init__(self):
        super().__init__(demo_admin_snapshot())
        self.updates: list[tuple[str, str]] = []

    def update_setting(self, setting_id, value):
        self.updates.append((setting_id, value))
        return super().update_setting(setting_id, value)


class RecordingDataWorkflowProvider(MemoryDataWorkflowProvider):
    def __init__(self):
        super().__init__(demo_workflow_snapshot())
        self.queries: list[str] = []

    def set_query(self, value):
        self.queries.append(value)
        return super().set_query(value)


def _change_id_after(html, marker):
    segment = html[html.index(marker) :]
    match = re.search(r'data-otoe-change="([^"]+)"', segment)
    assert match is not None
    return match.group(1)


def _click_id_before(html, marker):
    segment = html[: html.index(marker)]
    matches = re.findall(r'data-otoe-click="([^"]+)"', segment)
    assert matches
    return matches[-1]


def test_admin_preview_accepts_provider_boundary():
    snapshot = replace(
        demo_admin_snapshot(),
        workspace="Provider Admin Workspace",
        environment="Injected local provider",
    )
    provider = MemoryAdminSettingsProvider(snapshot)

    html = build_admin_html(provider=provider)

    assert "Provider Admin Workspace" in html
    assert "Injected local provider" in html
    assert "Local Workspace" not in html


def test_admin_live_preview_uses_injected_provider_for_setting_updates():
    provider = RecordingAdminSettingsProvider()
    app = AdminLivePreview(provider=provider)
    html = app.render_fragment()
    settings_id = _click_id_before(html, "Settings")

    html = app.dispatch_event(settings_id)
    change_id = _change_id_after(html, "Workspace name")
    html = app.dispatch_event(change_id, "Injected Console")

    assert provider.updates == [("workspace_name", "Injected Console")]
    assert "Injected Console" in html
    assert "Unsaved changes" in html


def test_data_workflow_preview_accepts_provider_boundary():
    snapshot = replace(
        demo_workflow_snapshot(),
        title="Provider supplied intake",
        source="Injected in-memory provider",
        records=[
            WorkflowRecord(
                "rec-provider",
                "Provider Labs",
                "Nia",
                "Review",
                "Ready",
                "$7,400",
                "10:10",
                "Loaded through provider injection.",
                "success",
            )
        ],
    )
    provider = MemoryDataWorkflowProvider(snapshot)

    html = build_data_workflow_html(provider=provider)

    assert "Provider supplied intake" in html
    assert "Injected in-memory provider" in html
    assert "Provider Labs" in html
    assert "Arcadia Finance" not in html


def test_data_workflow_live_preview_uses_injected_provider_for_search():
    provider = RecordingDataWorkflowProvider()
    app = DataWorkflowLivePreview(provider=provider)
    html = app.render_fragment()
    change_id = _change_id_after(html, "Search records")

    html = app.dispatch_event(change_id, "helio")

    assert provider.queries == ["helio"]
    assert 'value="helio"' in html
    assert "Helio Works" in html
    assert "Arcadia Finance" not in html
