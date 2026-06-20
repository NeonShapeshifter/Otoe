from __future__ import annotations

import re
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
PREVIEW = ROOT / "preview"
INDEX = PREVIEW / "index.html"
README = PREVIEW / "README.md"


class PreviewHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.hrefs: list[str] = []
        self.stylesheets: list[str] = []
        self.titles: list[str] = []
        self.code_blocks: list[str] = []
        self._title_parts: list[str] | None = None
        self._code_parts: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = {name.lower(): value or "" for name, value in attrs}
        href = attr_map.get("href")
        if href:
            self.hrefs.append(href)

        rel = {part.lower() for part in attr_map.get("rel", "").split()}
        if tag.lower() == "link" and href and "stylesheet" in rel:
            self.stylesheets.append(href)

        if tag.lower() == "title":
            self._title_parts = []
        elif tag.lower() == "code":
            self._code_parts = []

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "title" and self._title_parts is not None:
            self.titles.append(_normalize_text("".join(self._title_parts)))
            self._title_parts = None
        elif tag.lower() == "code" and self._code_parts is not None:
            self.code_blocks.append(_normalize_text("".join(self._code_parts)))
            self._code_parts = None

    def handle_data(self, data: str) -> None:
        if self._title_parts is not None:
            self._title_parts.append(data)
        if self._code_parts is not None:
            self._code_parts.append(data)


def test_index_local_hrefs_exist() -> None:
    parser = _parse_html(INDEX)

    missing = []
    for href in parser.hrefs:
        target = _local_target(INDEX, href)
        if target is not None and not target.exists():
            missing.append(_format_missing_ref(INDEX, href))

    assert missing == []


def test_each_preview_html_has_title() -> None:
    missing = [
        path.relative_to(ROOT).as_posix()
        for path in _preview_html_files()
        if not any(title for title in _parse_html(path).titles)
    ]

    assert missing == []


def test_local_stylesheets_exist() -> None:
    missing = []
    for path in _preview_html_files():
        parser = _parse_html(path)
        for href in parser.stylesheets:
            target = _local_target(path, href)
            if target is not None and not target.exists():
                missing.append(_format_missing_ref(path, href))

    assert missing == []


def test_preview_css_inventory_documents_checked_in_css_and_orphans() -> None:
    readme = README.read_text(encoding="utf-8")
    inventory = _section(readme, "CSS Inventory")
    documented_css = set(re.findall(r"`([^`]+\.css)`", inventory))
    checked_in_css = {path.name for path in PREVIEW.glob("*.css")}
    linked_css = _linked_preview_css_names()
    orphan_css = checked_in_css - linked_css

    assert checked_in_css <= documented_css
    assert orphan_css <= documented_css


def test_wraith_is_framed_as_case_study_not_readme_title() -> None:
    readme = README.read_text(encoding="utf-8")
    h1 = next(
        line.removeprefix("#").strip()
        for line in readme.splitlines()
        if line.startswith("# ")
    )
    gallery = _section(readme, "Gallery Entries")

    assert h1 == "Otoe Preview Gallery"
    assert "Wraith" not in h1
    assert "| Wraith Case Study | Case study |" in gallery
    assert "| Wraith Mission Exec Case Study | Case study |" in gallery


def test_index_regenerate_commands_are_reflected_in_readme() -> None:
    parser = _parse_html(INDEX)
    readme = _normalize_text(README.read_text(encoding="utf-8"))
    commands = [
        command
        for command in parser.code_blocks
        if "python -m " in command and "preview/" in command
    ]

    missing = []
    for command in commands:
        command_key = _strip_env_prefix(command)
        output = _command_html_output(command)
        has_pending_status = output is not None and _readme_marks_pending(output)
        if command_key not in readme and not has_pending_status:
            missing.append(command)

    assert missing == []


def _parse_html(path: Path) -> PreviewHTMLParser:
    parser = PreviewHTMLParser()
    parser.feed(path.read_text(encoding="utf-8"))
    return parser


def _preview_html_files() -> list[Path]:
    return sorted(PREVIEW.glob("*.html"))


def _local_target(source: Path, href: str) -> Path | None:
    parsed = urlsplit(href)
    if parsed.scheme or parsed.netloc:
        return None
    if not parsed.path:
        return None
    return (source.parent / unquote(parsed.path)).resolve()


def _format_missing_ref(source: Path, href: str) -> str:
    target = _local_target(source, href)
    assert target is not None
    return f"{source.relative_to(ROOT).as_posix()} -> {href} ({target})"


def _linked_preview_css_names() -> set[str]:
    linked_css: set[str] = set()
    for path in _preview_html_files():
        parser = _parse_html(path)
        for href in parser.stylesheets:
            target = _local_target(path, href)
            if (
                target is not None
                and target.parent == PREVIEW
                and target.suffix == ".css"
            ):
                linked_css.add(target.name)
    return linked_css


def _section(markdown: str, heading: str) -> str:
    start = markdown.index(f"## {heading}")
    next_heading = markdown.find("\n## ", start + 1)
    if next_heading == -1:
        return markdown[start:]
    return markdown[start:next_heading]


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", unescape(text)).strip()


def _strip_env_prefix(command: str) -> str:
    return re.sub(r"^(?:[A-Za-z_][A-Za-z0-9_]*=[^\s]+\s+)+", "", command)


def _command_html_output(command: str) -> str | None:
    output = re.search(r"(?:--out\s+|>\s*)(preview/[^\s;`]+\.html)", command)
    if output is None:
        return None
    return output.group(1)


def _readme_marks_pending(output: str) -> bool:
    readme_lines = README.read_text(encoding="utf-8").splitlines()
    return any(output in line and "pending" in line.lower() for line in readme_lines)
