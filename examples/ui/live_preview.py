from __future__ import annotations

import threading
from pathlib import Path
from typing import Any

from examples.live_server import (
    LivePreviewConfig,
    parse_host_port,
    render_live_page,
    run_live_preview,
)
from examples.ui.kitchen_sink import UIKitKitchenSink
from otoe import LiveHtmlRenderer, mount, signal


ROOT = Path(__file__).resolve().parents[2]
CSS_PATH = ROOT / "preview" / "ui.css"
LIVE_CONFIG = LivePreviewConfig(
    title="Otoe UI Kit Live Preview",
    css_route="/ui.css",
    css_path=CSS_PATH,
)


class UIKitLivePreview:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self.renderer = LiveHtmlRenderer()

        self.query = signal("")
        self.selected = signal(None)
        self.dialog_open = signal(False)

        self.app = mount(
            UIKitKitchenSink(
                query=self.query,
                selected=self.selected,
                dialog_open=self.dialog_open,
                on_query=self._query,
                on_select=self._select,
                on_toggle_dialog=self._toggle_dialog,
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

    def _query(self, value: str) -> None:
        self.query.set(value)

    def _select(self, command_id: str) -> None:
        self.selected.set(command_id)
        self.dialog_open.set(True)

    def _toggle_dialog(self) -> None:
        self.dialog_open.set(not self.dialog_open.value)


def run(host: str = "127.0.0.1", port: int = 8768) -> None:
    run_live_preview(
        app_factory=UIKitLivePreview,
        config=LIVE_CONFIG,
        host=host,
        port=port,
        label="Otoe UI kit live preview",
    )


def main() -> None:
    args = parse_host_port(default_port=8768)
    run(args.host, args.port)


if __name__ == "__main__":
    main()
