from __future__ import annotations

from ._ui_helpers import _active_class, _has_value, _list_value, _slot_node, _value, class_names
from ._ui_models import NavRoute, _normalize_route
from ._ui_surfaces import Badge
from .component import component
from .control import For, Show
from .node import Node
from .reactive import computed
from .widgets import Button, HStack, Text, VStack

__all__ = [
    "SidebarNav",
    "NavItem",
    "RouteView",
]

@component
def SidebarNav(
    *,
    routes,
    active,
    on_navigate,
    brand=None,
    footer=None,
    className: str | None = None,
    empty="No routes",
):
    normalized_routes = computed(lambda: [_normalize_route(route) for route in _list_value(routes)])
    children = []
    if brand is not None:
        children.append(_slot_node(brand, "ui-sidebar-brand"))
    children.append(
        For(
            each=normalized_routes,
            key=lambda route: route.id,
            children=lambda route: NavItem(
                route=route,
                active=computed(lambda: route.id == _value(active)),
                on_navigate=on_navigate,
            ),
            fallback=empty if isinstance(empty, Node) else Text(empty, className="ui-nav-empty"),
        )
    )
    if footer is not None:
        children.append(_slot_node(footer, "ui-sidebar-footer"))
    return VStack(
        *children,
        className=class_names("ui-sidebar-nav", className),
        gap=8,
    )

@component
def NavItem(
    *,
    route,
    active,
    on_navigate,
    className: str | None = None,
):
    normalized = _normalize_route(route)
    return Button(
        "",
        HStack(
            VStack(
                Text(normalized.label, className="ui-nav-label"),
                Show(
                    Text(normalized.description, className="ui-nav-description"),
                    when=computed(lambda: _has_value(normalized.description)),
                ),
                className="ui-nav-copy",
                gap=2,
            ),
            Show(
                Badge(normalized.badge, tone=normalized.tone, className="ui-nav-badge"),
                when=computed(lambda: _has_value(normalized.badge)),
            ),
            className="ui-nav-row",
            gap=10,
        ),
        className=_active_class("ui-nav-item", active, class_names(normalized.className, className)),
        onClick=lambda: on_navigate(normalized.id),
    )

@component
def RouteView(
    *,
    route,
    routes,
    render,
    className: str | None = None,
    fallback="Route not found",
):
    normalized_routes = computed(lambda: [_normalize_route(item) for item in _list_value(routes)])
    active_routes = computed(lambda: _matching_routes(normalized_routes.value, _value(route)))
    fallback_node = fallback if isinstance(fallback, Node) else Text(fallback, className="ui-route-empty")

    return VStack(
        For(
            each=active_routes,
            key=lambda item: item.id,
            children=lambda item: _render_route(item, render),
            fallback=fallback_node,
        ),
        className=class_names("ui-route-view", className),
        gap=0,
    )

def _matching_routes(routes: list[NavRoute], route_id: str) -> list[NavRoute]:
    return [route for route in routes if route.id == route_id]

def _render_route(route: NavRoute, render) -> Node:
    view = render(route)
    if not isinstance(view, Node):
        raise TypeError("RouteView render must return a Node.")
    return view
