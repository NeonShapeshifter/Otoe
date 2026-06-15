from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

from .plan import PlanDiagnostic
from .runtime_files import RuntimeFileError, auto_target_runtime_files
from .ui_safelist import UI_COMPONENT_EXPORTS, UI_DYNAMIC_CLASS_CANDIDATES


@dataclass(frozen=True)
class StaticClassScan:
    class_names: tuple[str, ...]
    framework_class_candidates: tuple[str, ...]
    diagnostics: tuple[PlanDiagnostic, ...]


def static_class_scan_for_target(target: str) -> StaticClassScan:
    try:
        runtime_files = auto_target_runtime_files(target)
    except RuntimeFileError as exc:
        raise RuntimeFileError(str(exc)) from exc

    class_names: list[str] = []
    framework_class_candidates: list[str] = []
    diagnostics: list[PlanDiagnostic] = []
    for runtime_file in runtime_files:
        scan = static_class_scan_from_file(runtime_file.source)
        class_names.extend(scan.class_names)
        framework_class_candidates.extend(scan.framework_class_candidates)
        diagnostics.extend(scan.diagnostics)
    return StaticClassScan(
        class_names=tuple(dict.fromkeys(class_names)),
        framework_class_candidates=tuple(dict.fromkeys(framework_class_candidates)),
        diagnostics=tuple(dict.fromkeys(diagnostics)),
    )


def static_class_scan_from_file(path: Path) -> StaticClassScan:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError as exc:
        raise RuntimeFileError(
            f"could not parse runtime module {str(path)!r}: {exc}"
        ) from exc
    assignments = _static_class_expr_assignments(tree)
    class_names: list[str] = []
    diagnostics: list[PlanDiagnostic] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        for keyword in node.keywords:
            if keyword.arg == "className":
                scan = _static_class_scan_from_expr(
                    keyword.value,
                    assignments=assignments,
                    path=path,
                    line=getattr(keyword.value, "lineno", None),
                )
                class_names.extend(scan.class_names)
                diagnostics.extend(scan.diagnostics)
    return StaticClassScan(
        class_names=tuple(dict.fromkeys(class_names)),
        framework_class_candidates=(
            UI_DYNAMIC_CLASS_CANDIDATES if _uses_ui_kit(tree) else ()
        ),
        diagnostics=tuple(dict.fromkeys(diagnostics)),
    )


def _static_class_expr_assignments(tree: ast.AST) -> dict[str, tuple[ast.AST, ...]]:
    assignments: dict[str, list[ast.AST]] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    assignments.setdefault(target.id, []).append(node.value)
        elif (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.value is not None
        ):
            assignments.setdefault(node.target.id, []).append(node.value)
    return {name: tuple(values) for name, values in assignments.items()}


def _uses_ui_kit(tree: ast.AST) -> bool:
    ui_exports = set(UI_COMPONENT_EXPORTS)
    imported_otoe_aliases: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "otoe.ui" or alias.name.startswith("otoe.ui."):
                    return True
                if alias.name == "otoe":
                    imported_otoe_aliases.add(alias.asname or "otoe")
        elif isinstance(node, ast.ImportFrom):
            if node.module == "otoe.ui" or (
                isinstance(node.module, str) and node.module.startswith("otoe.ui.")
            ):
                return True
            if node.module == "otoe":
                for alias in node.names:
                    if alias.name in ui_exports:
                        return True

    if not imported_otoe_aliases:
        return False
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Attribute)
            and node.attr in ui_exports
            and isinstance(node.value, ast.Name)
            and node.value.id in imported_otoe_aliases
        ):
            return True
    return False


def _static_class_scan_from_expr(
    node: ast.AST,
    *,
    assignments: dict[str, tuple[ast.AST, ...]],
    path: Path,
    line: int | None,
) -> StaticClassScan:
    class_names: list[str] = []
    diagnostics: list[PlanDiagnostic] = []
    visiting_names: set[str] = set()

    def visit(current: ast.AST) -> None:
        if isinstance(current, ast.Constant) and isinstance(current.value, str):
            class_names.extend(_split_static_class_literal(current.value))
            return
        if isinstance(current, ast.Name) and current.id in assignments:
            if current.id in visiting_names:
                return
            visiting_names.add(current.id)
            try:
                for assigned in assignments[current.id]:
                    visit(assigned)
            finally:
                visiting_names.remove(current.id)
            return
        if isinstance(current, ast.IfExp):
            visit(current.body)
            visit(current.orelse)
            return
        if isinstance(current, ast.BoolOp):
            for value in current.values:
                visit(value)
            return
        if isinstance(current, ast.Lambda):
            visit(current.body)
            return
        if isinstance(current, ast.Call):
            call_name = _static_call_name(current)
            if call_name == "class_names":
                for arg in current.args:
                    visit(arg)
                for keyword in current.keywords:
                    visit(keyword.value)
                return
            if call_name == "computed" and current.args:
                visit(current.args[0])
                return
            if _is_dynamic_string_operation(current):
                diagnostics.append(
                    _dynamic_class_name_diagnostic(
                        path,
                        line=line,
                        reason="string interpolation or concatenation",
                    )
                )
            return
        if isinstance(current, ast.JoinedStr):
            literal_parts: list[str] = []
            literal_only = True
            for value in current.values:
                if not isinstance(value, ast.Constant) or not isinstance(value.value, str):
                    literal_only = False
                    break
                literal_parts.append(value.value)
            if literal_only:
                class_names.extend(
                    _split_static_class_literal("".join(literal_parts))
                )
            else:
                diagnostics.append(
                    _dynamic_class_name_diagnostic(
                        path,
                        line=line,
                        reason="f-string interpolation",
                    )
                )
            return
        if _is_dynamic_string_operation(current):
            diagnostics.append(
                _dynamic_class_name_diagnostic(
                    path,
                    line=line,
                    reason="string interpolation or concatenation",
                )
            )
            return

    visit(node)
    return StaticClassScan(
        class_names=tuple(dict.fromkeys(class_names)),
        framework_class_candidates=(),
        diagnostics=tuple(dict.fromkeys(diagnostics)),
    )


def _static_call_name(node: ast.Call) -> str | None:
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute):
        return node.func.attr
    return None


def _is_dynamic_string_operation(node: ast.AST) -> bool:
    if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Mod)):
        return _contains_string_literal(node)
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
        return (
            node.func.attr == "format"
            and isinstance(node.func.value, ast.Constant)
            and isinstance(node.func.value.value, str)
        )
    return False


def _contains_string_literal(node: ast.AST) -> bool:
    return any(
        isinstance(child, ast.Constant) and isinstance(child.value, str)
        for child in ast.walk(node)
    )


def _dynamic_class_name_diagnostic(
    path: Path,
    *,
    line: int | None,
    reason: str,
) -> PlanDiagnostic:
    location = path.name if line is None else f"{path.name}:{line}"
    return PlanDiagnostic(
        "warning",
        "dynamic className expression "
        f"in {location} uses {reason}; safelist possible output classes "
        "for hardware/cage builds",
    )


def _split_static_class_literal(value: str) -> tuple[str, ...]:
    return tuple(name for name in value.split() if _is_static_class_token(name))


def _is_static_class_token(value: str) -> bool:
    return bool(value) and "{" not in value and "}" not in value
