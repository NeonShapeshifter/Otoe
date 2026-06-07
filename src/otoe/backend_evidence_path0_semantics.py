from __future__ import annotations

import math
from typing import Any


def path0_output_semantic_validation(output: Any) -> dict[str, Any]:
    errors = path0_output_semantic_errors(output)
    return {
        "passed": not errors,
        "errors": errors,
    }


def path0_output_semantic_errors(output: Any) -> list[str]:
    if not isinstance(output, dict):
        return ["evidence.path0.output must be a JSON object"]
    layout = output.get("layout")
    paint = output.get("paint")
    if not isinstance(layout, dict):
        return ["evidence.path0.output.layout must be a JSON object"]
    if not isinstance(paint, dict):
        return ["evidence.path0.output.paint must be a JSON object"]

    errors: list[str] = []
    layout_paths: set[tuple[int, ...]] = set()
    boxes = layout.get("boxes")
    root_path = _path_tuple(layout.get("rootPath"))
    if root_path is None:
        errors.append("evidence.path0.output.layout.rootPath must be a path list")
    if isinstance(boxes, list):
        seen_paths: set[tuple[int, ...]] = set()
        for index, box in enumerate(boxes):
            label = f"evidence.path0.output.layout.boxes[{index}]"
            if not isinstance(box, dict):
                errors.append(f"{label} must be a JSON object")
                continue
            path = _path_tuple(box.get("path"))
            if path is None:
                errors.append(f"{label}.path must be a path list")
            elif path in seen_paths:
                errors.append(f"{label}.path must be unique")
            else:
                seen_paths.add(path)
                layout_paths.add(path)
            if not _valid_bounds(box.get("bounds")):
                errors.append(
                    f"{label}.bounds must be finite numbers with non-negative size"
                )
            children = box.get("children")
            if isinstance(children, list):
                for child_index, child in enumerate(children):
                    child_path = _path_tuple(child)
                    if child_path is None:
                        errors.append(
                            f"{label}.children[{child_index}] must be a path list"
                        )
                    elif path is not None and child_path == path:
                        errors.append(
                            f"{label}.children[{child_index}] must not reference itself"
                        )
            else:
                errors.append(f"{label}.children must be a list")
        if root_path is not None and root_path not in layout_paths:
            errors.append("evidence.path0.output.layout.rootPath must reference a box")

        for index, box in enumerate(boxes):
            if not isinstance(box, dict):
                continue
            children = box.get("children")
            if not isinstance(children, list):
                continue
            for child_index, child in enumerate(children):
                child_path = _path_tuple(child)
                if child_path is not None and child_path not in layout_paths:
                    errors.append(
                        "evidence.path0.output.layout.boxes"
                        f"[{index}].children[{child_index}] must reference a box"
                    )

    commands = paint.get("commands")
    if isinstance(commands, list):
        for index, command in enumerate(commands):
            label = f"evidence.path0.output.paint.commands[{index}]"
            if not isinstance(command, dict):
                errors.append(f"{label} must be a JSON object")
                continue
            kind = command.get("kind")
            if kind not in {"rect", "text"}:
                errors.append(f"{label}.kind must be 'rect' or 'text'")
            path = _path_tuple(command.get("path"))
            if path is None:
                errors.append(f"{label}.path must be a path list")
            elif path not in layout_paths:
                errors.append(f"{label}.path must reference a layout box")
            if not _valid_bounds(command.get("bounds")):
                errors.append(
                    f"{label}.bounds must be finite numbers with non-negative size"
                )
            clip = command.get("clip")
            if clip is not None and not _valid_bounds(clip):
                errors.append(
                    f"{label}.clip must be null or finite bounds with non-negative size"
                )
            if not _non_negative_number(command.get("strokeWidth")):
                errors.append(f"{label}.strokeWidth must be a non-negative number")
            if not _non_negative_number(command.get("radius")):
                errors.append(f"{label}.radius must be a non-negative number")
            if kind == "rect" and not (
                isinstance(command.get("fill"), str)
                or isinstance(command.get("stroke"), str)
            ):
                errors.append(f"{label} rect must have fill or stroke")
            if kind == "text":
                if not isinstance(command.get("text"), str) or not command.get("text"):
                    errors.append(f"{label}.text must be a non-empty string")
                if not isinstance(command.get("color"), str) or not command.get("color"):
                    errors.append(f"{label}.color must be a non-empty string")
                if not _positive_number(command.get("fontSize")):
                    errors.append(f"{label}.fontSize must be a positive number")
    return errors


def _path_tuple(value: Any) -> tuple[int, ...] | None:
    if not isinstance(value, list):
        return None
    result: list[int] = []
    for item in value:
        if type(item) is not int or item < 0:
            return None
        result.append(item)
    return tuple(result)


def _valid_bounds(value: Any) -> bool:
    if not isinstance(value, list) or len(value) != 4:
        return False
    if not all(_finite_number(item) for item in value):
        return False
    _x, _y, width, height = value
    return width >= 0 and height >= 0


def _finite_number(value: Any) -> bool:
    return type(value) in {int, float} and math.isfinite(value)


def _non_negative_number(value: Any) -> bool:
    return _finite_number(value) and value >= 0


def _positive_number(value: Any) -> bool:
    return _finite_number(value) and value > 0
