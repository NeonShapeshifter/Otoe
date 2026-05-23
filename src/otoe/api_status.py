from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ApiStatus:
    name: str
    category: str
    detail: str


PREVIEW_DETAIL = (
    "Pre-alpha framework API. It is intended for feedback and examples, but "
    "does not carry a stable compatibility promise yet."
)
EXPERIMENTAL_NATIVE_DETAIL = (
    "Experimental native/window API. It is exported for the current headless "
    "renderer and manual-window spike, but should not be treated as a stable "
    "backend compatibility promise."
)
UNKNOWN_DETAIL = (
    "No API status has been declared for this name. Treat it as internal unless "
    "the documentation says otherwise."
)

PREVIEW_APIS = frozenset(
    {
        "API_STATUSES",
        "ActionButton",
        "AppShell",
        "ApiStatus",
        "Badge",
        "Button",
        "Card",
        "Command",
        "CommandPalette",
        "CommandRegistry",
        "Computed",
        "CORE_PREVIEW_APIS",
        "DataTable",
        "Dialog",
        "DuplicatePrimaryPropError",
        "Effect",
        "EventHandlerArityError",
        "EventHandlerError",
        "EventSignature",
        "EXPERIMENTAL_APIS",
        "EXPERIMENTAL_NATIVE_APIS",
        "FakeWidget",
        "FocusScope",
        "For",
        "HStack",
        "Input",
        "Interval",
        "LiveEvent",
        "LiveHtmlRenderer",
        "Menu",
        "MenuItem",
        "MountedNode",
        "NavItem",
        "NavRoute",
        "Node",
        "OtoeError",
        "PREVIEW_APIS",
        "Panel",
        "ReactiveDisposedError",
        "ReactiveMutationError",
        "RouteView",
        "ScrollView",
        "Select",
        "SelectOption",
        "Show",
        "ShortcutScope",
        "SidebarNav",
        "Size",
        "Signal",
        "StatCard",
        "StyleError",
        "StyleRule",
        "StyleSheet",
        "StyleSyntaxError",
        "TabButton",
        "TableColumn",
        "Tabs",
        "TemplateError",
        "Text",
        "Toast",
        "Token",
        "Toolbar",
        "UI_EVENT_SIGNATURES",
        "UnknownEventError",
        "UnknownPropError",
        "UnknownStyleClassError",
        "VStack",
        "Widget",
        "api_status",
        "batch",
        "class_names",
        "component",
        "computed",
        "css",
        "effect",
        "event_signature_for",
        "format_event_signature",
        "interval",
        "is_experimental_api",
        "mount",
        "on_cleanup",
        "on_mount",
        "render_html",
        "root_widget",
        "signal",
        "snapshot",
        "snapshot_text",
        "template",
        "unmount",
    }
)

EXPERIMENTAL_NATIVE_APIS = frozenset(
    {
        "LayoutBox",
        "NativeBackendAdapter",
        "NativeLayout",
        "NativeLayoutError",
        "NativePaint",
        "NativePaintError",
        "NativeSurface",
        "NativeWindowDriver",
        "NativeWindowEvent",
        "PaintCommand",
        "TkNativeBackendAdapter",
        "TkNativeWindow",
        "dispatch_native_click",
        "edit_native_input_value",
        "hit_test_native",
        "layout_native",
        "native_backend_adapter",
        "native_backend_names",
        "paint_native",
        "render_native_png",
        "run_native",
        "write_native_png",
    }
)

EXPERIMENTAL_APIS = EXPERIMENTAL_NATIVE_APIS
CORE_PREVIEW_APIS = PREVIEW_APIS

API_STATUSES = {
    **{
        name: ApiStatus(name=name, category="preview", detail=PREVIEW_DETAIL)
        for name in PREVIEW_APIS
    },
    **{
        name: ApiStatus(
            name=name,
            category="experimental-native",
            detail=EXPERIMENTAL_NATIVE_DETAIL,
        )
        for name in EXPERIMENTAL_NATIVE_APIS
    },
}


def api_status(name: str) -> ApiStatus:
    return API_STATUSES.get(
        name,
        ApiStatus(name=name, category="unknown", detail=UNKNOWN_DETAIL),
    )


def is_experimental_api(name: str) -> bool:
    return name in EXPERIMENTAL_APIS
