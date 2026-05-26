from __future__ import annotations

import threading
from pathlib import Path
from typing import Any

from examples.admin.settings_console import AdminSettingsConsole, MemoryAdminSettingsProvider
from examples.live_server import (
    LivePreviewConfig,
    parse_host_port,
    render_live_page,
    run_live_preview,
)
from examples.reference_theme import REFERENCE_THEME_STYLESHEET
from otoe import LiveHtmlRenderer, mount, signal


ROOT = Path(__file__).resolve().parents[2]
CSS_PATH = ROOT / "preview" / "admin.css"
LIVE_CONFIG = LivePreviewConfig(
    title="Otoe Local Admin Live Preview",
    css_route="/admin.css",
    css_path=CSS_PATH,
    extra_css=(REFERENCE_THEME_STYLESHEET,),
)


class AdminLivePreview:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self.provider = MemoryAdminSettingsProvider()
        self.renderer = LiveHtmlRenderer()
        self.snapshot = signal(self.provider.snapshot())
        self.active_route = signal("overview")
        self.app = mount(
            AdminSettingsConsole(
                snapshot=self.snapshot,
                active_route=self.active_route,
                on_navigate=self._navigate,
                on_setting_change=self._update_setting,
                on_action=self._run_action,
                on_rule_toggle=self._toggle_rule,
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

    def _update_setting(self, setting_id: str, value: str) -> None:
        self.snapshot.set(self.provider.update_setting(setting_id, value))

    def _run_action(self, action_id: str) -> None:
        self.snapshot.set(self.provider.run_action(action_id))

    def _toggle_rule(self, rule_id: str) -> None:
        self.snapshot.set(self.provider.toggle_access_rule(rule_id))


def run(host: str = "127.0.0.1", port: int = 8770) -> None:
    run_live_preview(
        app_factory=AdminLivePreview,
        config=LIVE_CONFIG,
        host=host,
        port=port,
        label="Otoe local admin live preview",
    )


def main() -> None:
    args = parse_host_port(default_port=8770)
    run(args.host, args.port)


if __name__ == "__main__":
    main()
