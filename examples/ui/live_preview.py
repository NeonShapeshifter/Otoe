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
from examples.ui.kitchen_sink import COMMAND_REGISTRY, UIKitKitchenSink
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
        self.palette_open = signal(False)
        self.menu_open = signal(False)
        self.menu_action = signal(None)
        self.menu_focus = signal("inspect")
        self.density = signal("balanced")
        self.density_open = signal(False)
        self.active_route = signal("ui")

        self.app = mount(
            UIKitKitchenSink(
                query=self.query,
                selected=self.selected,
                dialog_open=self.dialog_open,
                palette_open=self.palette_open,
                menu_open=self.menu_open,
                menu_action=self.menu_action,
                menu_focus=self.menu_focus,
                density=self.density,
                density_open=self.density_open,
                active_route=self.active_route,
                on_query=self._query,
                on_select=self._select,
                on_open_palette=self._open_palette,
                on_toggle_dialog=self._toggle_dialog,
                on_toggle_menu=self._toggle_menu,
                on_menu_select=self._menu_select,
                on_menu_focus=self._menu_focus,
                on_menu_open_change=self._menu_open_change,
                on_density_change=self._density_change,
                on_density_open_change=self._density_open_change,
                on_navigate=self._navigate,
                on_shortcut=self._shortcut,
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
        self.active_route.set(_route_for_command(command_id))
        self.palette_open.set(False)
        self.dialog_open.set(True)

    def _open_palette(self) -> None:
        self.active_route.set("ui")
        self.palette_open.set(True)

    def _toggle_dialog(self) -> None:
        self.dialog_open.set(not self.dialog_open.value)

    def _toggle_menu(self) -> None:
        next_open = not self.menu_open.value
        if next_open and self.menu_focus.value is None:
            self.menu_focus.set(self.menu_action.value or "inspect")
        self.menu_open.set(next_open)

    def _menu_select(self, item_id: str) -> None:
        self.menu_action.set(item_id)
        self.menu_focus.set(item_id)
        self.menu_open.set(False)

    def _menu_focus(self, item_id: str) -> None:
        self.menu_focus.set(item_id)

    def _menu_open_change(self, value: bool) -> None:
        if value and self.menu_focus.value is None:
            self.menu_focus.set(self.menu_action.value or "inspect")
        self.menu_open.set(value)

    def _density_change(self, value: str) -> None:
        self.density.set(value)

    def _density_open_change(self, value: bool) -> None:
        self.density_open.set(value)

    def _navigate(self, route_id: str) -> None:
        self.active_route.set(route_id)
        self.palette_open.set(False)
        self.menu_open.set(False)
        self.density_open.set(False)

    def _shortcut(self, payload: dict[str, Any]) -> None:
        key = str(payload.get("key", ""))
        is_modifier_command = bool(payload.get("ctrlKey") or payload.get("metaKey"))
        if is_modifier_command and key.lower() == "k":
            self.active_route.set("ui")
            self.query.set("")
            self.palette_open.set(True)
            self.dialog_open.set(False)
            self.menu_open.set(False)
            self.density_open.set(False)
            return
        if key == "Escape":
            self.palette_open.set(False)
            self.dialog_open.set(False)
            self.menu_open.set(False)
            self.density_open.set(False)
            self.query.set("")
            return
        command = COMMAND_REGISTRY.find_shortcut(key)
        if command is not None:
            self._select(command.id)


def _route_for_command(command_id: str) -> str:
    if command_id in {"customers", "settings"}:
        return "saas"
    if command_id in {"mission", "export"}:
        return "wraith"
    return "ui"


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
