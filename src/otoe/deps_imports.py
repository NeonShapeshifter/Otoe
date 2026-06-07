from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

from .runtime_files import RuntimeFileError


@dataclass(frozen=True)
class ImportRef:
    module: str
    line: int


@dataclass(frozen=True)
class DynamicImportRef:
    module: str | None
    line: int
    mechanism: str


def runtime_file_imports(path: Path) -> tuple[ImportRef, ...]:
    tree = _parse_runtime_file(path)
    visitor = _RuntimeImportVisitor()
    visitor.visit(tree)
    return tuple(dict.fromkeys(visitor.imports))


def runtime_file_dynamic_imports(path: Path) -> tuple[DynamicImportRef, ...]:
    tree = _parse_runtime_file(path)
    visitor = _RuntimeImportVisitor()
    visitor.preload_dynamic_import_aliases(tree)
    visitor.visit(tree)
    return tuple(dict.fromkeys(visitor.dynamic_imports))


def _parse_runtime_file(path: Path) -> ast.AST:
    try:
        return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError as exc:
        raise RuntimeFileError(
            f"could not parse runtime module {str(path)!r}: {exc}"
        ) from exc


class _RuntimeImportVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.imports: list[ImportRef] = []
        self.dynamic_imports: list[DynamicImportRef] = []
        self._importlib_names = {"importlib"}
        self._import_module_names: set[str] = set()

    def preload_dynamic_import_aliases(self, tree: ast.AST) -> None:
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "importlib":
                        self._importlib_names.add(alias.asname or alias.name)
            elif (
                isinstance(node, ast.ImportFrom)
                and node.level == 0
                and node.module == "importlib"
            ):
                for alias in node.names:
                    if alias.name == "import_module":
                        self._import_module_names.add(alias.asname or alias.name)

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            if alias.name == "importlib":
                self._importlib_names.add(alias.asname or alias.name)
            self.imports.append(
                ImportRef(
                    module=_top_level_module(alias.name),
                    line=getattr(node, "lineno", 1),
                )
            )

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.level != 0 or node.module is None:
            return
        if node.module == "importlib":
            for alias in node.names:
                if alias.name == "import_module":
                    self._import_module_names.add(alias.asname or alias.name)
        self.imports.append(
            ImportRef(
                module=_top_level_module(node.module),
                line=getattr(node, "lineno", 1),
            )
        )

    def visit_Call(self, node: ast.Call) -> None:
        mechanism = _dynamic_import_mechanism(
            node.func,
            importlib_names=self._importlib_names,
            import_module_names=self._import_module_names,
        )
        if mechanism is not None:
            self.dynamic_imports.append(
                DynamicImportRef(
                    module=_dynamic_import_module(node),
                    line=getattr(node, "lineno", 1),
                    mechanism=mechanism,
                )
            )
        self.generic_visit(node)

    def visit_If(self, node: ast.If) -> None:
        if _is_type_checking_guard(node.test):
            for child in node.orelse:
                self.visit(child)
            return
        self.generic_visit(node)


def _is_type_checking_guard(node: ast.AST) -> bool:
    if isinstance(node, ast.Name):
        return node.id == "TYPE_CHECKING"
    if isinstance(node, ast.Attribute):
        return node.attr == "TYPE_CHECKING"
    return False


def _dynamic_import_mechanism(
    func: ast.AST,
    *,
    importlib_names: set[str],
    import_module_names: set[str],
) -> str | None:
    if isinstance(func, ast.Name):
        if func.id == "__import__":
            return "__import__"
        if func.id in import_module_names:
            return "importlib.import_module"
        return None
    if (
        isinstance(func, ast.Attribute)
        and func.attr == "import_module"
        and isinstance(func.value, ast.Name)
        and func.value.id in importlib_names
    ):
        return "importlib.import_module"
    return None


def _dynamic_import_module(node: ast.Call) -> str | None:
    if not node.args:
        return None
    first_arg = node.args[0]
    if isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, str):
        return _top_level_module(first_arg.value)
    return None


def _top_level_module(module: str) -> str:
    return module.partition(".")[0]
