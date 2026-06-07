from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from .runtime_files import RuntimeFileError


RuntimePolicyCategory = Literal["network", "subprocess"]


@dataclass(frozen=True)
class ImportRef:
    module: str
    line: int


@dataclass(frozen=True)
class DynamicImportRef:
    module: str | None
    line: int
    mechanism: str


@dataclass(frozen=True)
class RuntimePolicyRef:
    category: RuntimePolicyCategory
    module: str
    line: int
    mechanism: str


NETWORK_MODULES = frozenset(
    {
        "ftplib",
        "http",
        "imaplib",
        "poplib",
        "smtplib",
        "socket",
        "telnetlib",
        "urllib",
        "xmlrpc",
    }
)
SUBPROCESS_MODULES = frozenset({"pty", "subprocess"})
OS_PROCESS_CALLS = frozenset(
    {
        "execl",
        "execle",
        "execlp",
        "execlpe",
        "execv",
        "execve",
        "execvp",
        "execvpe",
        "popen",
        "posix_spawn",
        "posix_spawnp",
        "spawnl",
        "spawnle",
        "spawnlp",
        "spawnlpe",
        "spawnv",
        "spawnve",
        "spawnvp",
        "spawnvpe",
        "system",
    }
)


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


def runtime_file_policy_refs(path: Path) -> tuple[RuntimePolicyRef, ...]:
    tree = _parse_runtime_file(path)
    visitor = _RuntimePolicyVisitor()
    visitor.preload_aliases(tree)
    visitor.visit(tree)
    return tuple(dict.fromkeys(visitor.refs))


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


class _RuntimePolicyVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.refs: list[RuntimePolicyRef] = []
        self._os_names = {"os"}
        self._os_process_call_names: dict[str, str] = {}

    def preload_aliases(self, tree: ast.AST) -> None:
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "os":
                        self._os_names.add(alias.asname or alias.name)
            elif (
                isinstance(node, ast.ImportFrom)
                and node.level == 0
                and node.module == "os"
            ):
                for alias in node.names:
                    if alias.name in OS_PROCESS_CALLS:
                        self._os_process_call_names[alias.asname or alias.name] = (
                            f"os.{alias.name}"
                        )

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            module = _top_level_module(alias.name)
            if module == "os":
                self._os_names.add(alias.asname or alias.name)
            self._append_import_ref(
                module=module,
                mechanism=f"import {alias.name}",
                line=getattr(node, "lineno", 1),
            )

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.level != 0 or node.module is None:
            return
        module = _top_level_module(node.module)
        if node.module == "os":
            for alias in node.names:
                if alias.name in OS_PROCESS_CALLS:
                    self._os_process_call_names[alias.asname or alias.name] = (
                        f"os.{alias.name}"
                    )
        self._append_import_ref(
            module=module,
            mechanism=f"from {node.module} import ...",
            line=getattr(node, "lineno", 1),
        )

    def visit_Call(self, node: ast.Call) -> None:
        mechanism = self._os_process_call_mechanism(node.func)
        if mechanism is not None:
            self.refs.append(
                RuntimePolicyRef(
                    category="subprocess",
                    module="os",
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

    def _append_import_ref(self, *, module: str, mechanism: str, line: int) -> None:
        category = _policy_import_category(module)
        if category is None:
            return
        self.refs.append(
            RuntimePolicyRef(
                category=category,
                module=module,
                line=line,
                mechanism=mechanism,
            )
        )

    def _os_process_call_mechanism(self, func: ast.AST) -> str | None:
        if isinstance(func, ast.Name):
            return self._os_process_call_names.get(func.id)
        if (
            isinstance(func, ast.Attribute)
            and func.attr in OS_PROCESS_CALLS
            and isinstance(func.value, ast.Name)
            and func.value.id in self._os_names
        ):
            return f"os.{func.attr}"
        return None


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


def _policy_import_category(module: str) -> RuntimePolicyCategory | None:
    if module in NETWORK_MODULES:
        return "network"
    if module in SUBPROCESS_MODULES:
        return "subprocess"
    return None
