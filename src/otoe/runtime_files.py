from __future__ import annotations

import ast
import sys
from pathlib import Path

from .profile_types import ProfileRuntimeFile


class RuntimeFileError(ValueError):
    pass


def build_runtime_files(
    target: str,
    profile_runtime_files: tuple[ProfileRuntimeFile, ...],
) -> tuple[ProfileRuntimeFile, ...]:
    files = [*auto_target_runtime_files(target), *profile_runtime_files]
    deduped: list[ProfileRuntimeFile] = []
    seen = set()
    for file in files:
        key = file.relative_path.as_posix()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(file)
    return tuple(deduped)


def auto_target_runtime_files(target: str) -> tuple[ProfileRuntimeFile, ...]:
    module_name, _ = _parse_target_spec(target)
    if "." in module_name:
        return ()
    module = sys.modules.get(module_name)
    source = getattr(module, "__file__", None)
    if source is None:
        return ()
    path = Path(source)
    if path.suffix != ".py" or path.name != f"{module_name}.py":
        return ()
    if not path.is_file():
        return ()
    return tuple(_local_runtime_files(path, seen=set()))


def _parse_target_spec(spec: str) -> tuple[str, str]:
    module_name, separator, object_path = spec.partition(":")
    if not separator or not module_name or not object_path:
        raise RuntimeFileError("target must use MODULE:OBJECT syntax")
    return module_name, object_path


def _local_runtime_files(
    path: Path,
    *,
    seen: set[Path],
) -> list[ProfileRuntimeFile]:
    resolved = path.resolve()
    if resolved in seen:
        return []
    seen.add(resolved)

    files = [ProfileRuntimeFile(source=path, relative_path=Path(path.name))]
    for candidate in _local_import_files(path):
        files.extend(_local_runtime_files(candidate, seen=seen))
    return files


def _local_import_files(path: Path) -> list[Path]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError as exc:
        raise RuntimeFileError(
            f"could not parse runtime module {str(path)!r}: {exc}"
        ) from exc

    imports: list[Path] = []
    for name in _local_import_module_names(tree):
        candidate = path.parent / f"{name}.py"
        if candidate.is_file():
            imports.append(candidate)
    return imports


def _local_import_module_names(tree: ast.AST) -> tuple[str, ...]:
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if "." not in alias.name:
                    names.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0 and node.module and "." not in node.module:
                names.append(node.module)
    return tuple(dict.fromkeys(names))
