from __future__ import annotations

from copy import deepcopy
from typing import Any


PORTABLE_CORE_UI_V0_FORMAT = "otoe-portable-core-ui-v0"
PORTABLE_CORE_UI_V0_SCHEMA_VERSION = 1

_ENTRIES: list[dict[str, Any]] = [
    {
        "id": "text",
        "label": "`Text`",
        "symbols": ["Text"],
        "exampleTarget": "examples.portable_core_ui:text_example",
        "portableCore": True,
        "html": "yes",
        "liveHtml": "n/a",
        "nativeHeadless": "yes",
        "nativeWindowDriver": "n/a",
        "status": "core preview",
        "nativeWidgets": ["Text"],
    },
    {
        "id": "button",
        "label": "`Button`",
        "symbols": ["Button"],
        "exampleTarget": "examples.portable_core_ui:button_example",
        "portableCore": True,
        "html": "yes",
        "liveHtml": "click/key events",
        "nativeHeadless": "click/focus/key",
        "nativeWindowDriver": "click/focus/key",
        "status": "core preview",
        "nativeWidgets": ["Button"],
    },
    {
        "id": "input",
        "label": "`Input`",
        "symbols": ["Input"],
        "exampleTarget": "examples.portable_core_ui:input_example",
        "portableCore": True,
        "html": "yes",
        "liveHtml": "change/key/focus",
        "nativeHeadless": "focus/key/text",
        "nativeWindowDriver": "focus/key/text",
        "status": "core preview",
        "nativeWidgets": ["Input"],
    },
    {
        "id": "vstack",
        "label": "`VStack`",
        "symbols": ["VStack"],
        "exampleTarget": "examples.portable_core_ui:vstack_example",
        "portableCore": True,
        "html": "yes",
        "liveHtml": "n/a",
        "nativeHeadless": "stack layout",
        "nativeWindowDriver": "n/a",
        "status": "core preview",
        "nativeWidgets": ["Text", "VStack"],
    },
    {
        "id": "hstack",
        "label": "`HStack`",
        "symbols": ["HStack"],
        "exampleTarget": "examples.portable_core_ui:hstack_example",
        "portableCore": True,
        "html": "yes",
        "liveHtml": "n/a",
        "nativeHeadless": "stack layout",
        "nativeWindowDriver": "n/a",
        "status": "core preview",
        "nativeWidgets": ["HStack", "Text"],
    },
    {
        "id": "panel",
        "label": "`Panel`",
        "symbols": ["Panel"],
        "exampleTarget": "examples.portable_core_ui:panel_example",
        "portableCore": True,
        "html": "yes",
        "liveHtml": "n/a",
        "nativeHeadless": "basic layout/paint",
        "nativeWindowDriver": "n/a",
        "status": "core preview",
        "nativeWidgets": ["Panel", "Text"],
    },
    {
        "id": "scrollview",
        "label": "`ScrollView`",
        "symbols": ["ScrollView"],
        "exampleTarget": "examples.portable_core_ui:scrollview_example",
        "portableCore": True,
        "html": "yes",
        "liveHtml": "scroll event shape",
        "nativeHeadless": "clipped paint/hit test/scroll",
        "nativeWindowDriver": "wheel dispatch",
        "status": "core preview",
        "nativeWidgets": ["Button", "ScrollView"],
    },
    {
        "id": "card",
        "label": "`Card`",
        "symbols": ["Card"],
        "exampleTarget": "examples.portable_core_ui:card_example",
        "portableCore": True,
        "html": "yes",
        "liveHtml": "n/a",
        "nativeHeadless": "through composed widgets/styles",
        "nativeWindowDriver": "n/a",
        "status": "product preview",
        "nativeWidgets": ["Panel", "Text", "VStack"],
    },
    {
        "id": "badge",
        "label": "`Badge`",
        "symbols": ["Badge"],
        "exampleTarget": "examples.portable_core_ui:badge_example",
        "portableCore": True,
        "html": "yes",
        "liveHtml": "n/a",
        "nativeHeadless": "through composed widgets/styles",
        "nativeWindowDriver": "n/a",
        "status": "product preview",
        "nativeWidgets": ["Text"],
    },
    {
        "id": "action-button",
        "label": "`ActionButton`",
        "symbols": ["ActionButton"],
        "exampleTarget": "examples.portable_core_ui:action_button_example",
        "portableCore": True,
        "html": "yes",
        "liveHtml": "click",
        "nativeHeadless": "through `Button` behavior",
        "nativeWindowDriver": "through `Button` behavior",
        "status": "product preview",
        "nativeWidgets": ["Button"],
    },
    {
        "id": "tabs",
        "label": "`Tabs`/`TabButton`",
        "symbols": ["Tabs", "TabButton"],
        "exampleTarget": "examples.portable_core_ui:tabs_example",
        "portableCore": True,
        "html": "yes",
        "liveHtml": "click",
        "nativeHeadless": "partial through buttons/layout",
        "nativeWindowDriver": "partial through buttons/layout",
        "status": "product preview",
        "nativeWidgets": ["Button", "HStack"],
    },
    {
        "id": "dialog",
        "label": "`Dialog`",
        "symbols": ["Dialog"],
        "exampleTarget": "examples.portable_core_ui:dialog_example",
        "portableCore": False,
        "html": "yes",
        "liveHtml": "focus overlay behavior in live path",
        "nativeHeadless": "partial layout/paint",
        "nativeWindowDriver": "partial focus behavior",
        "status": "experimental UI",
        "nativeWidgets": ["FocusScope", "HStack", "Panel", "Show", "Text", "VStack"],
    },
    {
        "id": "list-row",
        "label": "`ListRow`",
        "symbols": ["ListRow"],
        "exampleTarget": "examples.portable_core_ui:list_row_example",
        "portableCore": True,
        "html": "yes",
        "liveHtml": "n/a",
        "nativeHeadless": "through composed widgets/styles",
        "nativeWindowDriver": "n/a",
        "status": "product preview",
        "nativeWidgets": ["Button", "HStack", "Text", "VStack"],
    },
    {
        "id": "metric-tile",
        "label": "`MetricTile`",
        "symbols": ["MetricTile"],
        "exampleTarget": "examples.portable_core_ui:metric_tile_example",
        "portableCore": True,
        "html": "yes",
        "liveHtml": "n/a",
        "nativeHeadless": "through composed widgets/styles",
        "nativeWindowDriver": "n/a",
        "status": "product preview",
        "nativeWidgets": ["Panel", "Text", "VStack"],
    },
    {
        "id": "app-frame",
        "label": "`AppFrame`",
        "symbols": ["AppFrame"],
        "exampleTarget": "examples.portable_core_ui:app_frame_example",
        "portableCore": True,
        "html": "yes",
        "liveHtml": "n/a",
        "nativeHeadless": "app-shaped layout smoke",
        "nativeWindowDriver": "n/a",
        "status": "product preview",
        "nativeWidgets": ["HStack", "Text", "VStack"],
    },
]

_OUTSIDE_PORTABLE_CORE: list[dict[str, Any]] = [
    {
        "id": "app-shell-navigation",
        "symbols": ["AppShell", "NavItem", "NavRoute", "RouteView", "SidebarNav"],
        "classification": "product-preview-app-shell",
        "reason": "Used by reference apps today; not counted in v0 until route/sidebar native-window behavior has a dedicated contract.",
    },
    {
        "id": "app-shell-presets",
        "symbols": ["SidebarFrame", "SidebarItem", "TopBar"],
        "classification": "product-preview-app-shell",
        "reason": "Preset composition helpers for app shells; useful in HTML/native layout smoke, but not a minimal portable primitive.",
    },
    {
        "id": "surface-composites",
        "symbols": [
            "EmptyState",
            "MetricGrid",
            "SectionHeader",
            "StatCard",
            "StatusPill",
            "Surface",
            "Toolbar",
        ],
        "classification": "product-preview-composite",
        "reason": "Composed from portable widgets and utility classes; kept outside v0 until each helper has explicit native parity examples.",
    },
    {
        "id": "data-table",
        "symbols": ["DataTable"],
        "classification": "product-preview-composite",
        "reason": "Works in reference apps, but table-specific native layout, cell sizing, and scroll behavior are not v0 contracts.",
    },
    {
        "id": "transient-feedback",
        "symbols": ["FeedbackToast", "Toast"],
        "classification": "product-preview-composite",
        "reason": "Composed feedback surfaces; native timing, dismissal, and overlay semantics are not v0 contracts.",
    },
    {
        "id": "interactive-overlays",
        "symbols": ["CommandPalette", "FocusScope", "Menu", "Select", "ShortcutScope"],
        "classification": "interactive-preview",
        "reason": "Live HTML keyboard behavior is covered, but native focus, overlay, shortcut, and selection parity are not v0 contracts.",
    },
    {
        "id": "ui-models-and-helpers",
        "symbols": [
            "Command",
            "CommandRegistry",
            "MenuItem",
            "SelectOption",
            "TableColumn",
            "UI_EVENT_SIGNATURES",
            "class_names",
        ],
        "classification": "support-model",
        "reason": "Public helpers or data models used by UI primitives; they are not renderable primitives.",
    },
]


def portable_core_ui_v0_matrix() -> dict[str, Any]:
    return {
        "schemaVersion": PORTABLE_CORE_UI_V0_SCHEMA_VERSION,
        "format": PORTABLE_CORE_UI_V0_FORMAT,
        "entries": deepcopy(_ENTRIES),
        "outsidePortableCore": deepcopy(_OUTSIDE_PORTABLE_CORE),
    }


def portable_core_ui_v0_entries() -> list[dict[str, Any]]:
    return deepcopy(_ENTRIES)


def outside_portable_core_ui_v0() -> list[dict[str, Any]]:
    return deepcopy(_OUTSIDE_PORTABLE_CORE)


def format_portable_core_ui_v0(
    *,
    include_outside: bool = False,
    include_examples: bool = False,
) -> str:
    entries = portable_core_ui_v0_entries()
    portable_count = sum(1 for entry in entries if entry["portableCore"])
    lines = [
        "Portable Core UI v0",
        f"{portable_count} portable primitives, {len(entries) - portable_count} outside-v0 primitive listed for visibility.",
        "",
    ]
    lines.extend(
        _format_table(
            entries,
            [
                ("Primitive", "label"),
                ("HTML", "html"),
                ("Live HTML", "liveHtml"),
                ("Native Headless", "nativeHeadless"),
                ("Native Window", "nativeWindowDriver"),
                ("Status", "status"),
            ],
        )
    )
    if include_examples:
        lines.extend(
            [
                "",
                "Example Targets",
                *_format_table(
                    entries,
                    [
                        ("Primitive", "label"),
                        ("Target", "exampleTarget"),
                    ],
                ),
            ]
        )
    if include_outside:
        outside = outside_portable_core_ui_v0()
        lines.extend(
            [
                "",
                "Outside Portable Core v0",
                *_format_table(
                    outside,
                    [
                        ("Group", "id"),
                        ("Classification", "classification"),
                        ("Symbols", "symbols"),
                    ],
                ),
            ]
        )
    return "\n".join(lines)


def _format_table(rows: list[dict[str, Any]], columns: list[tuple[str, str]]) -> list[str]:
    rendered_rows = [
        [_display_value(row[key]) for _heading, key in columns]
        for row in rows
    ]
    headings = [heading for heading, _key in columns]
    widths = [
        max(len(heading), *(len(row[index]) for row in rendered_rows))
        for index, heading in enumerate(headings)
    ]
    lines = [
        "  ".join(heading.ljust(widths[index]) for index, heading in enumerate(headings)),
        "  ".join("-" * width for width in widths),
    ]
    for row in rendered_rows:
        lines.append(
            "  ".join(value.ljust(widths[index]) for index, value in enumerate(row))
        )
    return lines


def _display_value(value: Any) -> str:
    if isinstance(value, list):
        return ", ".join(str(item) for item in value)
    return str(value)
