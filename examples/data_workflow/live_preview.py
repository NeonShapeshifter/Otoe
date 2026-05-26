from __future__ import annotations

import threading
from pathlib import Path
from typing import Any

from examples.data_workflow.workbench import DataWorkflowWorkbench, MemoryDataWorkflowProvider
from examples.live_server import (
    LivePreviewConfig,
    parse_host_port,
    render_live_page,
    run_live_preview,
)
from examples.reference_theme import REFERENCE_THEME_STYLESHEET
from otoe import LiveHtmlRenderer, mount, signal


ROOT = Path(__file__).resolve().parents[2]
CSS_PATH = ROOT / "preview" / "data_workflow.css"
LIVE_CONFIG = LivePreviewConfig(
    title="Otoe Data Workflow Live Preview",
    css_route="/data_workflow.css",
    css_path=CSS_PATH,
    extra_css=(REFERENCE_THEME_STYLESHEET,),
)


class DataWorkflowLivePreview:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self.provider = MemoryDataWorkflowProvider()
        self.renderer = LiveHtmlRenderer()
        self.snapshot = signal(self.provider.snapshot())
        self.active_route = signal("queue")
        self.app = mount(
            DataWorkflowWorkbench(
                snapshot=self.snapshot,
                active_route=self.active_route,
                on_navigate=self._navigate,
                on_query=self._set_query,
                on_stage_filter=self._set_stage_filter,
                on_toggle_record=self._toggle_record,
                on_action=self._run_action,
            )
        )

    def render_fragment(self) -> str:
        with self._lock:
            self.renderer.clear()
            return self.renderer.render(self.app, pretty=True, indent=4)

    def render_page(self) -> str:
        return render_live_page(self, LIVE_CONFIG)

    def dispatch_event(self, event_id: str, *args: Any) -> str:
        with self._lock:
            self.renderer.dispatch(event_id, *args)
            return self.render_fragment()

    def _navigate(self, route_id: str) -> None:
        self.active_route.set(route_id)

    def _set_query(self, value: str) -> None:
        self.snapshot.set(self.provider.set_query(value))

    def _set_stage_filter(self, value: str) -> None:
        self.snapshot.set(self.provider.set_stage_filter(value))

    def _toggle_record(self, record_id: str) -> None:
        self.snapshot.set(self.provider.toggle_record(record_id))

    def _run_action(self, action_id: str) -> None:
        self.snapshot.set(self.provider.run_action(action_id))


def run(host: str = "127.0.0.1", port: int = 8771) -> None:
    run_live_preview(
        app_factory=DataWorkflowLivePreview,
        config=LIVE_CONFIG,
        host=host,
        port=port,
        label="Otoe data workflow live preview",
    )


def main() -> None:
    args = parse_host_port(default_port=8771)
    run(args.host, args.port)


if __name__ == "__main__":
    main()
