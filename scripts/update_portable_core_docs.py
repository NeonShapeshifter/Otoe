#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from otoe.api_status import API_TIERS
from otoe.portable_core import portable_core_ui_v0_matrix


JSON_PATH = ROOT / "docs" / "portable-core-ui-v0.json"
MARKDOWN_PATH = ROOT / "docs" / "portable-core-ui-v0.md"
API_TIERS_PATH = ROOT / "docs" / "api-tiers.md"

MATRIX_START = "<!-- portable-core-ui-v0:matrix:start -->"
MATRIX_END = "<!-- portable-core-ui-v0:matrix:end -->"
EXAMPLES_START = "<!-- portable-core-ui-v0:examples:start -->"
EXAMPLES_END = "<!-- portable-core-ui-v0:examples:end -->"
OUTSIDE_START = "<!-- portable-core-ui-v0:outside:start -->"
OUTSIDE_END = "<!-- portable-core-ui-v0:outside:end -->"
API_EXPORT_MAP_START = "<!-- api-tiers:top-level-export-map:start -->"
API_EXPORT_MAP_END = "<!-- api-tiers:top-level-export-map:end -->"


def render_json() -> str:
    return json.dumps(portable_core_ui_v0_matrix(), indent=2) + "\n"


def render_markdown(source: str) -> str:
    matrix = portable_core_ui_v0_matrix()
    source = _replace_marked_section(
        source,
        MATRIX_START,
        MATRIX_END,
        _render_support_table(matrix["entries"]),
    )
    source = _replace_marked_section(
        source,
        EXAMPLES_START,
        EXAMPLES_END,
        _render_examples_table(matrix["entries"]),
    )
    source = _replace_marked_section(
        source,
        OUTSIDE_START,
        OUTSIDE_END,
        _render_outside_table(matrix["outsidePortableCore"]),
    )
    return source


def render_api_tiers_markdown(source: str) -> str:
    return _replace_marked_section(
        source,
        API_EXPORT_MAP_START,
        API_EXPORT_MAP_END,
        _render_api_tiers_table(),
    )


def _render_support_table(entries: list[dict[str, Any]]) -> str:
    rows = [
        _markdown_row(
            [
                entry["label"],
                entry["html"],
                entry["liveHtml"],
                entry["nativeHeadless"],
                entry["nativeWindowDriver"],
                entry["status"],
            ]
        )
        for entry in entries
    ]
    return "\n".join(
        [
            "| Primitive | HTML | Live HTML | Native Headless | Native Window Driver | Status |",
            "| --- | --- | --- | --- | --- | --- |",
            *rows,
        ]
    )


def _render_examples_table(entries: list[dict[str, Any]]) -> str:
    rows = [
        _markdown_row([entry["label"], f"`{entry['exampleTarget']}`"])
        for entry in entries
    ]
    return "\n".join(
        [
            "| Primitive | Example Target |",
            "| --- | --- |",
            *rows,
        ]
    )


def _render_outside_table(items: list[dict[str, Any]]) -> str:
    rows = [
        _markdown_row(
            [
                f"`{item['id']}`",
                item["classification"],
                ", ".join(f"`{symbol}`" for symbol in item["symbols"]),
            ]
        )
        for item in items
    ]
    return "\n".join(
        [
            "| Group | Classification | Symbols |",
            "| --- | --- | --- |",
            *rows,
        ]
    )


def _render_api_tiers_table() -> str:
    rows = [
        _markdown_row([f"`{tier}`", _format_code_list(sorted(names))])
        for tier, names in API_TIERS.items()
    ]
    return "\n".join(
        [
            "| Tier | Top-Level Names |",
            "| --- | --- |",
            *rows,
        ]
    )


def _format_code_list(values: list[str]) -> str:
    return ", ".join(f"`{value}`" for value in values)


def _markdown_row(values: list[str]) -> str:
    return "| " + " | ".join(values) + " |"


def _replace_marked_section(
    source: str,
    start_marker: str,
    end_marker: str,
    replacement: str,
) -> str:
    start = source.find(start_marker)
    end = source.find(end_marker)
    if start == -1 or end == -1 or end < start:
        raise ValueError(
            f"missing generated Markdown markers: {start_marker} / {end_marker}"
        )
    before = source[: start + len(start_marker)]
    after = source[end:]
    return before + "\n" + replacement.rstrip() + "\n" + after


def _check_current(
    expected_json: str,
    expected_markdown: str,
    expected_api_tiers: str,
) -> list[str]:
    errors = []
    if JSON_PATH.read_text(encoding="utf-8") != expected_json:
        errors.append(str(JSON_PATH.relative_to(ROOT)))
    if MARKDOWN_PATH.read_text(encoding="utf-8") != expected_markdown:
        errors.append(str(MARKDOWN_PATH.relative_to(ROOT)))
    if API_TIERS_PATH.read_text(encoding="utf-8") != expected_api_tiers:
        errors.append(str(API_TIERS_PATH.relative_to(ROOT)))
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="regenerate Portable Core UI v0 JSON and Markdown docs"
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify generated docs are current without writing files",
    )
    args = parser.parse_args(argv)

    current_markdown = MARKDOWN_PATH.read_text(encoding="utf-8")
    current_api_tiers = API_TIERS_PATH.read_text(encoding="utf-8")
    expected_json = render_json()
    expected_markdown = render_markdown(current_markdown)
    expected_api_tiers = render_api_tiers_markdown(current_api_tiers)

    if args.check:
        out_of_date = _check_current(
            expected_json,
            expected_markdown,
            expected_api_tiers,
        )
        if out_of_date:
            print(
                "generated docs out of date: "
                + ", ".join(out_of_date)
                + "; run python scripts/update_portable_core_docs.py",
                file=sys.stderr,
            )
            return 1
        print("portable core docs: ok")
        print("api tiers docs: ok")
        return 0

    JSON_PATH.write_text(expected_json, encoding="utf-8")
    MARKDOWN_PATH.write_text(expected_markdown, encoding="utf-8")
    API_TIERS_PATH.write_text(expected_api_tiers, encoding="utf-8")
    print("updated docs/portable-core-ui-v0.json")
    print("updated docs/portable-core-ui-v0.md")
    print("updated docs/api-tiers.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
