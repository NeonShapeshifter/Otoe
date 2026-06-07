from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from pprint import pformat

_EXPECTED_FRAMEWORK_SENTINEL = '"__OTOE_EXPECTED_FRAMEWORK_FILES__"'
_TEMPLATE_FILENAME = "build_runner_template.py"


def build_runner_source(expected_framework_files: Mapping[str, Sequence[str]]) -> str:
    source = (Path(__file__).with_name(_TEMPLATE_FILENAME)).read_text(
        encoding="utf-8"
    )
    if _EXPECTED_FRAMEWORK_SENTINEL not in source:
        raise RuntimeError(
            f"{_TEMPLATE_FILENAME}: missing expected framework file sentinel"
        )
    return source.replace(
        _EXPECTED_FRAMEWORK_SENTINEL,
        pformat(_normalize_expected_framework_files(expected_framework_files), width=88),
    )


def _normalize_expected_framework_files(
    expected_framework_files: Mapping[str, Sequence[str]],
) -> dict[str, tuple[str, ...]]:
    return {
        backend: tuple(files)
        for backend, files in expected_framework_files.items()
    }
