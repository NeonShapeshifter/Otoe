from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ApiStatus:
    name: str
    category: str
    detail: str
    tier: str = "unknown"
    preferred_import: str | None = None


API_METADATA_DETAIL = (
    "API metadata preview surface. It describes Otoe's public tiers, but does "
    "not make the named APIs stable yet."
)
CORE_PREVIEW_DETAIL = (
    "Core app-authoring preview API. It is the first surface Otoe intends to "
    "protect, but it does not carry a stable compatibility promise yet."
)
PRODUCT_PREVIEW_UI_DETAIL = (
    "Product-preview UI primitive. Prefer importing it from otoe.ui; top-level "
    "aliases remain for compatibility during pre-alpha."
)
PREVIEW_SUPPORT_DETAIL = (
    "Preview support API. It is useful for app authors and examples, but it is "
    "outside the smallest core programming model."
)
EXPERIMENTAL_NATIVE_DETAIL = (
    "Experimental native/window API. It is exported for the current headless "
    "renderer and manual-window spike, but should not be treated as a stable "
    "backend compatibility promise."
)
EXPERIMENTAL_BACKEND_DETAIL = (
    "Experimental backend-evidence API. It supports renderer candidates, "
    "RenderTree/style artifacts, and bundle verification rather than primary "
    "app authoring."
)
UNKNOWN_DETAIL = (
    "No API status has been declared for this name. Treat it as internal unless "
    "the documentation says otherwise."
)

API_METADATA_APIS = frozenset(
    {
        "API_METADATA_APIS",
        "API_STATUSES",
        "API_TIERS",
        "ApiStatus",
        "CORE_PREVIEW_APIS",
        "EXPERIMENTAL_APIS",
        "EXPERIMENTAL_BACKEND_APIS",
        "EXPERIMENTAL_NATIVE_APIS",
        "PREVIEW_APIS",
        "PREVIEW_SUPPORT_APIS",
        "PRODUCT_PREVIEW_UI_APIS",
        "api_status",
        "is_experimental_api",
    }
)

CORE_PREVIEW_APIS = frozenset(
    {
        "Button",
        "Computed",
        "DuplicatePrimaryPropError",
        "Effect",
        "EventHandlerArityError",
        "EventHandlerError",
        "EventSignature",
        "For",
        "HStack",
        "Input",
        "Node",
        "OtoeError",
        "Panel",
        "ReactiveDisposedError",
        "ReactiveMutationError",
        "Signal",
        "ScrollView",
        "Show",
        "Size",
        "StyleError",
        "StyleRule",
        "StyleSheet",
        "StyleSyntaxError",
        "Text",
        "Token",
        "UnknownEventError",
        "UnknownPropError",
        "UnknownStyleClassError",
        "VStack",
        "Widget",
        "batch",
        "component",
        "computed",
        "css",
        "effect",
        "event_signature_for",
        "format_event_signature",
        "mount",
        "on_cleanup",
        "on_mount",
        "render_html",
        "root_widget",
        "signal",
        "snapshot",
        "snapshot_text",
        "unmount",
    }
)

PRODUCT_PREVIEW_UI_APIS = frozenset(
    {
        "ActionButton",
        "AppFrame",
        "AppShell",
        "Badge",
        "Card",
        "Command",
        "CommandPalette",
        "CommandRegistry",
        "DataTable",
        "Dialog",
        "EmptyState",
        "FeedbackToast",
        "FocusScope",
        "ListRow",
        "MetricGrid",
        "MetricTile",
        "Menu",
        "MenuItem",
        "NavItem",
        "NavRoute",
        "RouteView",
        "SectionHeader",
        "Select",
        "SelectOption",
        "SidebarFrame",
        "SidebarItem",
        "ShortcutScope",
        "SidebarNav",
        "StatCard",
        "StatusPill",
        "Surface",
        "TabButton",
        "TableColumn",
        "Tabs",
        "Toast",
        "TopBar",
        "Toolbar",
        "UI_EVENT_SIGNATURES",
        "class_names",
    }
)

PREVIEW_SUPPORT_APIS = frozenset(
    {
        "DEFAULT_UTILITY_TOKENS",
        "FakeWidget",
        "Interval",
        "LiveEvent",
        "LiveHtmlRenderer",
        "MountedNode",
        "TemplateError",
        "interval",
        "template",
        "utility_css",
        "utility_stylesheet",
    }
)

EXPERIMENTAL_NATIVE_APIS = frozenset(
    {
        "LayoutBox",
        "ComposedNativeRendererBackend",
        "NativeBackendAdapter",
        "NativeLayout",
        "NativeLayoutBackend",
        "NativeLayoutError",
        "NativePaint",
        "NativePaintBackend",
        "NativePaintError",
        "NativeRasterBackend",
        "NativeRendererBackend",
        "NativeSurface",
        "NativeWindowDriver",
        "NativeWindowEvent",
        "PYTHON_NATIVE_RENDERER_BACKEND",
        "PaintCommand",
        "PillowNativeRendererBackend",
        "PythonNativeRendererBackend",
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
        "write_pillow_native_png",
        "write_native_png",
    }
)

EXPERIMENTAL_BACKEND_APIS = frozenset(
    {
        "RENDER_TREE_SCHEMA_VERSION",
        "ResolvedStyleMap",
        "RenderIRError",
        "RenderNode",
        "RenderTree",
        "assert_render_tree_valid",
        "load_render_tree_artifact",
        "render_node_to_dict",
        "render_tree_from_dict",
        "render_tree_from_target",
        "render_tree_to_dict",
        "resolved_style_map_from_style_ops_artifact",
        "validate_render_tree",
        "walk_render_nodes",
    }
)

PREVIEW_APIS = (
    API_METADATA_APIS
    | CORE_PREVIEW_APIS
    | PRODUCT_PREVIEW_UI_APIS
    | PREVIEW_SUPPORT_APIS
)
EXPERIMENTAL_APIS = EXPERIMENTAL_NATIVE_APIS | EXPERIMENTAL_BACKEND_APIS

API_TIERS = {
    "api-metadata": API_METADATA_APIS,
    "core-preview": CORE_PREVIEW_APIS,
    "product-preview-ui": PRODUCT_PREVIEW_UI_APIS,
    "preview-support": PREVIEW_SUPPORT_APIS,
    "experimental-native": EXPERIMENTAL_NATIVE_APIS,
    "experimental-backend": EXPERIMENTAL_BACKEND_APIS,
}

API_STATUSES = {
    **{
        name: ApiStatus(
            name=name,
            category="preview",
            detail=API_METADATA_DETAIL,
            tier="api-metadata",
            preferred_import="otoe",
        )
        for name in API_METADATA_APIS
    },
    **{
        name: ApiStatus(
            name=name,
            category="preview",
            detail=CORE_PREVIEW_DETAIL,
            tier="core-preview",
            preferred_import="otoe",
        )
        for name in CORE_PREVIEW_APIS
    },
    **{
        name: ApiStatus(
            name=name,
            category="preview",
            detail=PRODUCT_PREVIEW_UI_DETAIL,
            tier="product-preview-ui",
            preferred_import="otoe.ui",
        )
        for name in PRODUCT_PREVIEW_UI_APIS
    },
    **{
        name: ApiStatus(
            name=name,
            category="preview",
            detail=PREVIEW_SUPPORT_DETAIL,
            tier="preview-support",
            preferred_import="otoe",
        )
        for name in PREVIEW_SUPPORT_APIS
    },
    **{
        name: ApiStatus(
            name=name,
            category="experimental-native",
            detail=EXPERIMENTAL_NATIVE_DETAIL,
            tier="experimental-native",
            preferred_import="otoe.experimental.native",
        )
        for name in EXPERIMENTAL_NATIVE_APIS
    },
    **{
        name: ApiStatus(
            name=name,
            category="experimental-backend",
            detail=EXPERIMENTAL_BACKEND_DETAIL,
            tier="experimental-backend",
            preferred_import="otoe.experimental.backend",
        )
        for name in EXPERIMENTAL_BACKEND_APIS
    },
}


def api_status(name: str) -> ApiStatus:
    return API_STATUSES.get(
        name,
        ApiStatus(name=name, category="unknown", detail=UNKNOWN_DETAIL),
    )


def is_experimental_api(name: str) -> bool:
    return name in EXPERIMENTAL_APIS
