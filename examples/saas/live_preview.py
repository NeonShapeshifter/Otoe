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
from examples.saas.overview import SaaSOverview
from examples.saas.preview import CUSTOMERS, DEALS
from otoe import LiveHtmlRenderer, computed, mount, signal, unmount


ROOT = Path(__file__).resolve().parents[2]
CSS_PATH = ROOT / "preview" / "saas.css"
LIVE_CONFIG = LivePreviewConfig(
    title="Otoe SaaS Live Preview",
    css_route="/saas.css",
    css_path=CSS_PATH,
)


class SaaSLivePreview:
    def __init__(self) -> None:
        self._disposed = False
        owned_cleanups: list[Callable[[], None]] = []
        try:
            self._lock = threading.RLock()
            self.renderer = LiveHtmlRenderer()

            self.query = signal("")
            self.invites = signal(0)
            self.active_section = signal("Overview")
            self.all_deals = signal([dict(deal) for deal in DEALS])
            self.all_customers = signal([dict(customer) for customer in CUSTOMERS])
            self.workspace = computed(self._workspace_label)
            owned_cleanups.append(self.workspace.dispose)
            self.filtered_deals = computed(self._filtered_deals)
            owned_cleanups.append(self.filtered_deals.dispose)
            self.filtered_customers = computed(self._filtered_customers)
            owned_cleanups.append(self.filtered_customers.dispose)

            self.app = mount(
                SaaSOverview(
                    query=self.query,
                    workspace=self.workspace,
                    active_section=self.active_section,
                    deals=self.filtered_deals,
                    customers=self.filtered_customers,
                    on_search=self._search,
                    on_invite=self._add_opportunity,
                    on_nav=self._navigate,
                )
            )
            owned_cleanups.append(lambda: unmount(self.app))
        except BaseException as primary_error:
            self._disposed = True
            _cleanup_after_construction_failure(
                primary_error,
                reversed(owned_cleanups),
                message="SaaS live preview construction and cleanup failed.",
            )
            raise

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

    def dispose(self) -> None:
        if getattr(self, "_disposed", False):
            return
        self._disposed = True

        errors: list[BaseException] = []
        cleanups: tuple[Callable[[], None], ...] = (
            lambda: unmount(self.app),
            self.filtered_customers.dispose,
            self.filtered_deals.dispose,
            self.workspace.dispose,
        )
        for cleanup in cleanups:
            try:
                cleanup()
            except BaseException as exc:
                errors.append(exc)
        if errors:
            raise BaseExceptionGroup("SaaS live preview cleanup failed.", errors)

    def _workspace_label(self) -> str:
        if self.invites.value == 0:
            return "Growth workspace"
        if self.invites.value == 1:
            return "Growth workspace · 1 update"
        return f"Growth workspace · {self.invites.value} updates"

    def _search(self, value: str) -> None:
        self.query.set(value)

    def _navigate(self, section: str) -> None:
        self.active_section.set(section)

    def _add_opportunity(self) -> None:
        next_index = self.invites.value + 1
        self.invites.set(next_index)
        self.all_deals.set(
            [
                _new_deal(next_index),
                *self.all_deals.value,
            ]
        )
        self.all_customers.set(
            [
                _new_customer(next_index),
                *self.all_customers.value,
            ]
        )

    def _filtered_deals(self) -> list[dict[str, Any]]:
        query = self.query.value.strip().lower()
        deals = self.all_deals.value
        if not query:
            return list(deals)
        return [
            deal
            for deal in deals
            if query in deal["name"].lower()
            or query in deal["owner"].lower()
            or query in deal["stage"].lower()
        ]

    def _filtered_customers(self) -> list[dict[str, str]]:
        query = self.query.value.strip().lower()
        customers = self.all_customers.value
        if not query:
            return list(customers)
        return [
            customer
            for customer in customers
            if query in customer["name"].lower()
            or query in customer["plan"].lower()
            or query in customer["health"].lower()
        ]


def _new_deal(index: int) -> dict[str, Any]:
    value = 12000 + index * 3400
    return {
        "id": f"new-{index}",
        "stage": "Qualified",
        "confidence": "58%",
        "name": f"Brightline Systems {index}",
        "owner": "Avery Stone",
        "amount": f"${value:,.0f}",
        "value": value,
    }


def _new_customer(index: int) -> dict[str, str]:
    return {
        "id": f"new-{index}",
        "name": f"Brightline Systems {index}",
        "plan": "Pro",
        "health": "New",
        "tone": "good",
    }


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


def run(host: str = "127.0.0.1", port: int = 8766) -> None:
    run_live_preview(
        app_factory=SaaSLivePreview,
        config=LIVE_CONFIG,
        host=host,
        port=port,
        label="Otoe SaaS live preview",
    )


def main() -> None:
    args = parse_host_port(default_port=8766)
    run(args.host, args.port)


if __name__ == "__main__":
    main()
