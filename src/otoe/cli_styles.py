from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from .cli_common import CliError
from .style import StyleError, StyleSheet, css
from .utilities import utility_stylesheet


def load_stylesheet(path: str | Path | None) -> StyleSheet | None:
    if path is None:
        return None
    source = Path(path)
    if not source.exists():
        raise CliError(f"css file {path!r} does not exist")
    try:
        return css(source.read_text(encoding="utf-8"))
    except StyleError as exc:
        raise CliError(f"css file {path!r}: {exc}") from exc


def load_plan_stylesheet(
    paths: Sequence[str | Path],
    *,
    include_utilities: bool,
) -> StyleSheet | None:
    stylesheets: list[StyleSheet] = []
    if include_utilities:
        stylesheets.append(utility_stylesheet())
    for path in paths:
        stylesheet = load_stylesheet(path)
        if stylesheet is not None:
            stylesheets.append(stylesheet)
    if not stylesheets:
        return None
    return merge_stylesheets(stylesheets)


def merge_stylesheets(stylesheets: list[StyleSheet]) -> StyleSheet:
    rules = {}
    tokens = {}
    for stylesheet in stylesheets:
        rules.update(stylesheet.rules)
        tokens.update(stylesheet.tokens)
    return StyleSheet(rules=rules, tokens=tokens)
