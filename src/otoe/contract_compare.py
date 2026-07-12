from __future__ import annotations

import json
from typing import Any


class ContractCompareError(ValueError):
    pass


def compare_json_contracts(expected: Any, actual: Any) -> list[dict[str, Any]]:
    differences: list[dict[str, Any]] = []
    _collect_json_contract_differences(
        expected,
        actual,
        pointer="",
        differences=differences,
    )
    return differences


def delete_json_pointer(payload: Any, pointer: str) -> None:
    parts = _parse_json_pointer(pointer)
    current = payload
    for part in parts[:-1]:
        if isinstance(current, dict):
            if part not in current:
                return
            current = current[part]
        elif isinstance(current, list):
            index = _json_pointer_list_index(part)
            if index is None or index >= len(current):
                return
            current = current[index]
        else:
            return

    key = parts[-1]
    if isinstance(current, dict):
        current.pop(key, None)
    elif isinstance(current, list):
        index = _json_pointer_list_index(key)
        if index is not None and index < len(current):
            del current[index]


def format_contract_difference(difference: dict[str, Any]) -> str:
    path = _display_json_pointer(str(difference["path"]))
    kind = difference["kind"]
    if kind == "missing":
        return (
            f"- {path}: missing in actual; "
            f"expected {_format_contract_value(difference['expected'])}"
        )
    if kind == "extra":
        return (
            f"- {path}: extra in actual; "
            f"actual {_format_contract_value(difference['actual'])}"
        )
    if kind == "type":
        return (
            f"- {path}: type {difference['expectedType']} != "
            f"{difference['actualType']}"
        )
    if kind == "length":
        return f"- {path}: length {difference['expected']} != {difference['actual']}"
    return (
        f"- {path}: expected {_format_contract_value(difference['expected'])}, "
        f"actual {_format_contract_value(difference['actual'])}"
    )


def _collect_json_contract_differences(
    expected: Any,
    actual: Any,
    *,
    pointer: str,
    differences: list[dict[str, Any]],
) -> None:
    expected_type = _json_type_name(expected)
    actual_type = _json_type_name(actual)
    if expected_type != actual_type:
        differences.append(
            {
                "path": pointer,
                "kind": "type",
                "expectedType": expected_type,
                "actualType": actual_type,
                "expected": _summarize_contract_value(expected),
                "actual": _summarize_contract_value(actual),
            }
        )
        return

    if isinstance(expected, dict):
        expected_keys = set(expected)
        actual_keys = set(actual)
        for key in sorted(expected_keys - actual_keys):
            differences.append(
                {
                    "path": _json_pointer_child(pointer, key),
                    "kind": "missing",
                    "expected": _summarize_contract_value(expected[key]),
                    "actual": None,
                }
            )
        for key in sorted(actual_keys - expected_keys):
            differences.append(
                {
                    "path": _json_pointer_child(pointer, key),
                    "kind": "extra",
                    "expected": None,
                    "actual": _summarize_contract_value(actual[key]),
                }
            )
        for key in sorted(expected_keys & actual_keys):
            _collect_json_contract_differences(
                expected[key],
                actual[key],
                pointer=_json_pointer_child(pointer, key),
                differences=differences,
            )
        return

    if isinstance(expected, list):
        if len(expected) != len(actual):
            differences.append(
                {
                    "path": pointer,
                    "kind": "length",
                    "expected": len(expected),
                    "actual": len(actual),
                }
            )
        for index, (expected_item, actual_item) in enumerate(
            zip(expected, actual, strict=False)
        ):
            _collect_json_contract_differences(
                expected_item,
                actual_item,
                pointer=_json_pointer_child(pointer, str(index)),
                differences=differences,
            )
        return

    if expected != actual:
        differences.append(
            {
                "path": pointer,
                "kind": "value",
                "expected": expected,
                "actual": actual,
            }
        )


def _json_type_name(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, dict):
        return "object"
    if isinstance(value, list):
        return "array"
    if isinstance(value, int | float):
        return "number"
    if isinstance(value, str):
        return "string"
    return type(value).__name__


def _json_pointer_child(pointer: str, key: str) -> str:
    escaped = key.replace("~", "~0").replace("/", "~1")
    return f"{pointer}/{escaped}"


def _parse_json_pointer(pointer: str) -> tuple[str, ...]:
    if not pointer.startswith("/"):
        raise ContractCompareError(
            f"ignore path must be a JSON pointer starting with '/': {pointer!r}"
        )
    return tuple(_unescape_json_pointer_part(part) for part in pointer.split("/")[1:])


def _unescape_json_pointer_part(part: str) -> str:
    chars: list[str] = []
    index = 0
    while index < len(part):
        char = part[index]
        if char != "~":
            chars.append(char)
            index += 1
            continue
        if index + 1 >= len(part) or part[index + 1] not in {"0", "1"}:
            raise ContractCompareError(
                f"invalid JSON pointer escape in ignore path: {part!r}"
            )
        chars.append("~" if part[index + 1] == "0" else "/")
        index += 2
    return "".join(chars)


def _json_pointer_list_index(part: str) -> int | None:
    if not part.isdigit():
        return None
    return int(part)


def _display_json_pointer(pointer: str) -> str:
    return "$" if not pointer else pointer


def _summarize_contract_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            "type": "object",
            "keys": sorted(str(key) for key in value),
        }
    if isinstance(value, list):
        return {
            "type": "array",
            "length": len(value),
        }
    return value


def _format_contract_value(value: Any) -> str:
    return json.dumps(value, sort_keys=True)
