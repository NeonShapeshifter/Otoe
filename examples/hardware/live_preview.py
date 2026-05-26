from __future__ import annotations

import threading
from pathlib import Path
from typing import Any

from examples.hardware.adapters import MemoryHardwareTransport, TransportHardwareProvider
from examples.hardware.control_panel import HardwareControlPanel
from examples.live_server import (
    LivePreviewConfig,
    parse_host_port,
    render_live_page,
    run_live_preview,
)
from examples.reference_theme import REFERENCE_THEME_STYLESHEET
from otoe import LiveHtmlRenderer, mount, signal


ROOT = Path(__file__).resolve().parents[2]
CSS_PATH = ROOT / "preview" / "hardware.css"
LIVE_CONFIG = LivePreviewConfig(
    title="Otoe Hardware Live Preview",
    css_route="/hardware.css",
    css_path=CSS_PATH,
    extra_css=(REFERENCE_THEME_STYLESHEET,),
)


class HardwareLivePreview:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self.provider = TransportHardwareProvider(MemoryHardwareTransport())
        self.renderer = LiveHtmlRenderer()
        self.snapshot = signal(self.provider.snapshot())
        self.active_route = signal("overview")
        self.app = mount(
            HardwareControlPanel(
                snapshot=self.snapshot,
                active_route=self.active_route,
                on_navigate=self._navigate,
                on_command=self._run_command,
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

    def _run_command(self, command_id: str) -> None:
        self.snapshot.set(self.provider.run_command(command_id))


def run(host: str = "127.0.0.1", port: int = 8769) -> None:
    run_live_preview(
        app_factory=HardwareLivePreview,
        config=LIVE_CONFIG,
        host=host,
        port=port,
        label="Otoe hardware live preview",
    )


def main() -> None:
    args = parse_host_port(default_port=8769)
    run(args.host, args.port)


if __name__ == "__main__":
    main()
