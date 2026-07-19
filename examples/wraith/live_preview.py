from __future__ import annotations

import threading
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any

from examples.live_server import (
    LivePreviewConfig,
    parse_host_port,
    render_live_page,
    run_live_preview,
)
from examples.wraith.arsenal import ArsenalView
from examples.wraith.runtime_status import RuntimeStatusCluster
from examples.wraith.topbar import TopBar
from otoe import LiveHtmlRenderer, computed, mount, signal, unmount


ROOT = Path(__file__).resolve().parents[2]
CSS_PATH = ROOT / "preview" / "wraith.css"
LIVE_CONFIG = LivePreviewConfig(
    title="Otoe Wraith Live Preview",
    css_route="/wraith.css",
    css_path=CSS_PATH,
    root_class="app-shell",
)
PAGE_SIZE = 3


class WraithLivePreview:
    def __init__(self) -> None:
        self._disposed = False
        owned_cleanups: list[Callable[[], None]] = []
        try:
            self._lock = threading.RLock()
            self.renderer = LiveHtmlRenderer()

            self.campaign = signal("Primary Campaign")
            self.wifi_state = signal("UP")
            self.stealth_active = signal(True)
            self.query = signal("")
            self.active_tag = signal("ALL")
            self.page = signal(0)
            self.status_index = 0

            self.visible_missions = computed(self._visible_missions)
            owned_cleanups.append(self.visible_missions.dispose)
            self.page_label = computed(self._page_label)
            owned_cleanups.append(self.page_label.dispose)

            self.topbar = mount(
                TopBar(
                    campaign=self.campaign,
                    wifi_state=self.wifi_state,
                    stealth_active=self.stealth_active,
                )
            )
            owned_cleanups.append(lambda: unmount(self.topbar))
            self.status = mount(RuntimeStatusCluster(probe=self._probe_runtime))
            owned_cleanups.append(lambda: unmount(self.status))
            self.arsenal = mount(
                ArsenalView(
                    query=self.query,
                    active_tag=self.active_tag,
                    missions=self.visible_missions,
                    page_label=self.page_label,
                    on_search=self._search,
                    on_next=self._next_page,
                )
            )
            owned_cleanups.append(lambda: unmount(self.arsenal))
        except BaseException as primary_error:
            self._disposed = True
            _cleanup_after_construction_failure(
                primary_error,
                reversed(owned_cleanups),
                message="Wraith live preview construction and cleanup failed.",
            )
            raise

    def render_fragment(self) -> str:
        with self._lock:
            self.renderer.clear()
            return "\n".join(
                [
                    self.renderer.render(self.topbar, pretty=True, indent=4),
                    '    <main class="preview-main">',
                    '      <section class="preview-column preview-column--left">',
                    '        <div class="preview-section-title">Runtime</div>',
                    self.renderer.render(self.status, pretty=True, indent=8),
                    "      </section>",
                    '      <section class="preview-column preview-column--main">',
                    '        <div class="preview-section-title">Arsenal</div>',
                    self.renderer.render(self.arsenal, pretty=True, indent=8),
                    "      </section>",
                    "    </main>",
                ]
            )

    def render_page(self) -> str:
        return render_live_page(self, LIVE_CONFIG)

    def dispatch_event(self, event_id: str, *args: Any) -> str:
        with self._lock:
            self.renderer.dispatch(event_id, *args)
            return self.render_fragment()

    def dispose(self) -> None:
        if getattr(self, "_disposed", False):
            return
        self._disposed = True

        errors: list[BaseException] = []
        cleanups: tuple[Callable[[], None], ...] = (
            lambda: unmount(self.arsenal),
            lambda: unmount(self.status),
            lambda: unmount(self.topbar),
            self.page_label.dispose,
            self.visible_missions.dispose,
        )
        for cleanup in cleanups:
            try:
                cleanup()
            except BaseException as exc:
                errors.append(exc)
        if errors:
            raise BaseExceptionGroup("Wraith live preview cleanup failed.", errors)

    def _search(self, value: str) -> None:
        query = value.strip()
        self.query.set(value)
        self.active_tag.set("QUERY" if query else "ALL")
        self.page.set(0)

    def _next_page(self) -> None:
        self.page.set((self.page.value + 1) % self._page_count())

    def _visible_missions(self) -> list[dict[str, str]]:
        items = self._filtered_missions()
        start = self.page.value * PAGE_SIZE
        return items[start : start + PAGE_SIZE]

    def _page_label(self) -> str:
        total_pages = self._page_count()
        current_page = min(self.page.value + 1, total_pages)
        return f"PAGE {current_page}/{total_pages}"

    def _page_count(self) -> int:
        return max(1, (len(self._filtered_missions()) + PAGE_SIZE - 1) // PAGE_SIZE)

    def _filtered_missions(self) -> list[dict[str, str]]:
        query = self.query.value.strip().lower()
        if not query:
            return list(MISSIONS)
        return [
            mission
            for mission in MISSIONS
            if query in mission["name"].lower()
            or query in mission["description"].lower()
            or query in mission["vector"].lower()
            or query in mission["opsec"].lower()
        ]

    def _probe_runtime(self) -> dict[str, str]:
        snapshot = RUNTIME_SNAPSHOTS[self.status_index % len(RUNTIME_SNAPSHOTS)]
        self.status_index += 1
        return dict(snapshot)


MISSIONS = [
    {
        "id": "wifi",
        "name": "WiFi Scan",
        "description": "Discover nearby networks.",
        "vector": "WiFi",
        "opsec": "LOW",
    },
    {
        "id": "rf",
        "name": "RF Survey",
        "description": "Inspect spectrum activity.",
        "vector": "RF",
        "opsec": "MED",
    },
    {
        "id": "lab",
        "name": "Lab Flow",
        "description": "Restricted validation path.",
        "vector": "USB",
        "opsec": "HIGH",
    },
    {
        "id": "ble",
        "name": "BLE Sweep",
        "description": "Enumerate nearby Bluetooth beacons.",
        "vector": "BLE",
        "opsec": "LOW",
    },
    {
        "id": "payload",
        "name": "Payload Stager",
        "description": "Prepare controlled delivery artifacts.",
        "vector": "USB",
        "opsec": "HIGH",
    },
]

RUNTIME_SNAPSHOTS = [
    {"wifi": "UP", "bluetooth": "READY", "cpu": "42C", "storage": "18GB"},
    {"wifi": "UP", "bluetooth": "READY", "cpu": "43C", "storage": "18GB"},
    {"wifi": "DEGRADED", "bluetooth": "READY", "cpu": "44C", "storage": "17GB"},
]


def _cleanup_after_construction_failure(
    primary_error: BaseException,
    cleanups: Iterable[Callable[[], None]],
    *,
    message: str,
) -> None:
    errors: list[BaseException] = [primary_error]
    for cleanup in cleanups:
        try:
            cleanup()
        except BaseException as cleanup_error:
            errors.append(cleanup_error)
    if len(errors) > 1:
        raise BaseExceptionGroup(message, errors) from primary_error


def run(host: str = "127.0.0.1", port: int = 8765) -> None:
    run_live_preview(
        app_factory=WraithLivePreview,
        config=LIVE_CONFIG,
        host=host,
        port=port,
        label="Otoe Wraith live preview",
    )


def main() -> None:
    args = parse_host_port(default_port=8765)
    run(args.host, args.port)


if __name__ == "__main__":
    main()
