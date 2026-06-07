from __future__ import annotations

import ast
import sys
from dataclasses import dataclass
from pathlib import Path

from .profile_types import ProfileRuntimeFile


class RuntimeFileError(ValueError):
    pass


@dataclass(frozen=True)
class _RuntimeModule:
    module_name: str
    path: Path
    root: Path


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
    module = _runtime_module(module_name)
    if module is None:
        return ()
    return tuple(_local_runtime_files(module, copied=set(), processed=set()))


def _parse_target_spec(spec: str) -> tuple[str, str]:
    module_name, separator, object_path = spec.partition(":")
    if not separator or not module_name or not object_path:
        raise RuntimeFileError("target must use MODULE:OBJECT syntax")
    return module_name, object_path


def _runtime_module(module_name: str) -> _RuntimeModule | None:
    found = _find_runtime_module(module_name)
    if found is not None:
        path, root = found
        return _RuntimeModule(module_name=module_name, path=path, root=root)

    module = sys.modules.get(module_name)
    source = getattr(module, "__file__", None)
    if source is not None:
        path = Path(source)
        if path.suffix == ".py" and path.is_file():
            root = _runtime_root(module_name, path)
            return _RuntimeModule(module_name=module_name, path=path, root=root)
    return None


def _find_runtime_module(module_name: str) -> tuple[Path, Path] | None:
    parts = tuple(part for part in module_name.split(".") if part)
    if not parts:
        return None
    for entry in sys.path:
        root = Path(entry or ".").resolve()
        found = _runtime_module_path_from_root(parts, root=root)
        if found is not None:
            return found, root
    return None


def _runtime_module_path_from_root(
    parts: tuple[str, ...],
    *,
    root: Path,
) -> Path | None:
    if len(parts) == 1:
        module_file = root / f"{parts[0]}.py"
        if module_file.is_file():
            return module_file
        package_init = root / parts[0] / "__init__.py"
        if package_init.is_file():
            return package_init
        return None

    package_dir = root
    for part in parts[:-1]:
        package_dir = package_dir / part
        if not package_dir.is_dir():
            return None

    module_file = package_dir / f"{parts[-1]}.py"
    if module_file.is_file():
        return module_file
    package_init = package_dir / parts[-1] / "__init__.py"
    if package_init.is_file():
        return package_init
    return None


def _runtime_root(module_name: str, path: Path) -> Path:
    parts = tuple(part for part in module_name.split(".") if part)
    if path.name == "__init__.py":
        suffix = parts
        package_dir = path.parent
    else:
        suffix = parts[:-1]
        package_dir = path.parent
    if not suffix:
        return path.parent.resolve()

    resolved_package_dir = package_dir.resolve()
    candidates = (resolved_package_dir, *resolved_package_dir.parents)
    for candidate in candidates:
        try:
            relative = resolved_package_dir.relative_to(candidate)
        except ValueError:
            continue
        if relative.parts == suffix:
            return candidate
    return path.parent.resolve()


def _local_runtime_files(
    module: _RuntimeModule,
    *,
    copied: set[Path],
    processed: set[Path],
) -> list[ProfileRuntimeFile]:
    files: list[ProfileRuntimeFile] = []
    for init_module in _ancestor_init_modules(module):
        files.extend(
            _local_runtime_files(
                init_module,
                copied=copied,
                processed=processed,
            )
        )
    _append_runtime_file(files, module.path, root=module.root, copied=copied)

    resolved = module.path.resolve()
    if resolved in processed:
        return files
    processed.add(resolved)
    for candidate in _local_import_modules(module):
        files.extend(
            _local_runtime_files(
                candidate,
                copied=copied,
                processed=processed,
            )
        )
    return files


def _append_runtime_file(
    files: list[ProfileRuntimeFile],
    path: Path,
    *,
    root: Path,
    copied: set[Path],
) -> bool:
    resolved = path.resolve()
    if resolved in copied:
        return False
    copied.add(resolved)
    try:
        relative_path = resolved.relative_to(root)
    except ValueError:
        relative_path = Path(path.name)
    files.append(ProfileRuntimeFile(source=resolved, relative_path=relative_path))
    return True


def _ancestor_init_modules(module: _RuntimeModule) -> tuple[_RuntimeModule, ...]:
    try:
        relative = module.path.resolve().relative_to(module.root)
    except ValueError:
        return ()
    parent = (
        relative.parent.parent
        if module.path.name == "__init__.py"
        else relative.parent
    )
    parent_parts = parent.parts
    init_modules = []
    current = module.root
    for part in parent_parts:
        current = current / part
        init_file = current / "__init__.py"
        if init_file.is_file():
            init_modules.append(
                _RuntimeModule(
                    module_name=_module_name_from_path(init_file, root=module.root),
                    path=init_file,
                    root=module.root,
                )
            )
    return tuple(init_modules)


def _local_import_modules(module: _RuntimeModule) -> list[_RuntimeModule]:
    try:
        tree = ast.parse(
            module.path.read_text(encoding="utf-8"),
            filename=str(module.path),
        )
    except SyntaxError as exc:
        raise RuntimeFileError(
            f"could not parse runtime module {str(module.path)!r}: {exc}"
        ) from exc

    imports: list[_RuntimeModule] = []
    seen_names = set()
    for name in _local_import_module_names(
        tree,
        current_package=_module_package_name(module),
    ):
        candidate = _resolve_local_module(name, root=module.root)
        if candidate is None or candidate.module_name in seen_names:
            continue
        seen_names.add(candidate.module_name)
        imports.append(candidate)
    return imports


def _local_import_module_names(
    tree: ast.AST,
    *,
    current_package: str,
) -> tuple[str, ...]:
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            module_name = _import_from_module_name(
                node,
                current_package=current_package,
            )
            if module_name is None:
                continue
            names.append(module_name)
            for alias in node.names:
                if alias.name != "*":
                    names.append(f"{module_name}.{alias.name}")
    return tuple(dict.fromkeys(names))


def _import_from_module_name(
    node: ast.ImportFrom,
    *,
    current_package: str,
) -> str | None:
    if node.level == 0:
        return node.module

    package_parts = current_package.split(".") if current_package else []
    if node.level > len(package_parts) + 1:
        return None
    if node.level > 1:
        package_parts = package_parts[: -(node.level - 1)]
    if node.module:
        package_parts.extend(part for part in node.module.split(".") if part)
    return ".".join(package_parts) if package_parts else None


def _module_package_name(module: _RuntimeModule) -> str:
    if module.path.name == "__init__.py":
        return module.module_name
    package, _separator, _name = module.module_name.rpartition(".")
    return package


def _resolve_local_module(module_name: str, *, root: Path) -> _RuntimeModule | None:
    parts = tuple(part for part in module_name.split(".") if part)
    if not parts:
        return None

    module_path = root / Path(*parts)
    package_init = module_path / "__init__.py"
    if package_init.is_file():
        return _RuntimeModule(
            module_name=module_name,
            path=package_init,
            root=root,
        )

    file_path = module_path.with_suffix(".py")
    if file_path.is_file():
        return _RuntimeModule(
            module_name=module_name,
            path=file_path,
            root=root,
        )
    return None


def _module_name_from_path(path: Path, *, root: Path) -> str:
    relative = path.resolve().relative_to(root)
    if relative.name == "__init__.py":
        parts = relative.parent.parts
    else:
        parts = relative.with_suffix("").parts
    return ".".join(parts)
