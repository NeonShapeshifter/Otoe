from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .plan import SUPPORTED_PLAN_PROFILES


DEFAULT_PROFILE_FILENAME = "otoe.profile.toml"


class ProfileError(ValueError):
    pass


@dataclass(frozen=True)
class ProfileAsset:
    source: Path
    relative_path: Path


@dataclass(frozen=True)
class ProfileRuntimeFile:
    source: Path
    relative_path: Path


@dataclass(frozen=True)
class PlanProfileConfig:
    profile: str = "cage"
    utilities: bool = False
    css_paths: tuple[Path, ...] = ()
    assets: tuple[ProfileAsset, ...] = ()
    runtime_files: tuple[ProfileRuntimeFile, ...] = ()
    allow_runtime_installs: bool = False
    backend_name: str | None = None
    dependency_packages: tuple[str, ...] = ()
    dependency_extras: tuple[str, ...] = ()


def load_plan_profile(path: str | Path) -> PlanProfileConfig:
    profile_path = Path(path)
    if not profile_path.exists():
        raise ProfileError(f"profile file {str(profile_path)!r} does not exist")
    try:
        data = tomllib.loads(profile_path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise ProfileError(f"profile file {str(profile_path)!r}: {exc}") from exc

    _require_table(data, "profile file")
    _reject_unknown(
        data,
        "profile file",
        {"profile", "utilities", "css", "assets", "runtime", "backend", "deps"},
    )

    profile = _string_value(data, "profile", default="cage", context="profile file")
    if profile not in SUPPORTED_PLAN_PROFILES:
        supported = ", ".join(sorted(SUPPORTED_PLAN_PROFILES))
        raise ProfileError(f"unsupported profile {profile!r}; supported: {supported}")

    utilities = _bool_value(
        data,
        "utilities",
        default=False,
        context="profile file",
    )
    css_paths = _css_paths(data.get("css"), base=profile_path.parent)
    assets = _assets(data.get("assets"), base=profile_path.parent)

    runtime = _table_value(data, "runtime", context="profile file")
    _reject_unknown(runtime, "[runtime]", {"allow_runtime_installs", "files"})
    allow_runtime_installs = _bool_value(
        runtime,
        "allow_runtime_installs",
        default=False,
        context="[runtime]",
    )
    if profile == "cage" and allow_runtime_installs:
        raise ProfileError("profile 'cage' forbids runtime installs")
    runtime_files = _runtime_files(runtime.get("files"), base=profile_path.parent)

    backend = _table_value(data, "backend", context="profile file")
    _reject_unknown(backend, "[backend]", {"name"})
    backend_name = _optional_string(backend, "name", context="[backend]")

    deps = _table_value(data, "deps", context="profile file")
    _reject_unknown(deps, "[deps]", {"packages", "extras"})
    dependency_packages = _string_array(
        deps,
        "packages",
        context="[deps]",
    )
    dependency_extras = _string_array(
        deps,
        "extras",
        context="[deps]",
    )

    return PlanProfileConfig(
        profile=profile,
        utilities=utilities,
        css_paths=css_paths,
        assets=assets,
        runtime_files=runtime_files,
        allow_runtime_installs=allow_runtime_installs,
        backend_name=backend_name,
        dependency_packages=dependency_packages,
        dependency_extras=dependency_extras,
    )


def _css_paths(value: Any, *, base: Path) -> tuple[Path, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise ProfileError("profile file key 'css' must be an array of strings")
    paths = []
    for index, item in enumerate(value):
        if not isinstance(item, str):
            raise ProfileError(f"profile file key 'css[{index}]' must be a string")
        paths.append(base / item)
    return tuple(paths)


def _assets(value: Any, *, base: Path) -> tuple[ProfileAsset, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise ProfileError("profile file key 'assets' must be an array of strings")
    assets = []
    for index, item in enumerate(value):
        if not isinstance(item, str):
            raise ProfileError(f"profile file key 'assets[{index}]' must be a string")
        relative = Path(item)
        _validate_relative_file_path(relative, key=f"assets[{index}]")
        assets.append(ProfileAsset(source=base / relative, relative_path=relative))
    return tuple(assets)


def _runtime_files(value: Any, *, base: Path) -> tuple[ProfileRuntimeFile, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise ProfileError("[runtime] key 'files' must be an array of strings")
    files = []
    for index, item in enumerate(value):
        if not isinstance(item, str):
            raise ProfileError(f"[runtime] key 'files[{index}]' must be a string")
        relative = Path(item)
        _validate_relative_file_path(relative, key=f"runtime.files[{index}]")
        files.append(ProfileRuntimeFile(source=base / relative, relative_path=relative))
    return tuple(files)


def _validate_relative_file_path(path: Path, *, key: str) -> None:
    if path.is_absolute():
        raise ProfileError(f"profile file key {key!r} must be a relative path")
    if any(part in {"", ".", ".."} for part in path.parts):
        raise ProfileError(
            f"profile file key {key!r} must not contain '.', '..', or empty parts"
        )


def _table_value(data: dict[str, Any], key: str, *, context: str) -> dict[str, Any]:
    value = data.get(key)
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ProfileError(f"{context} key {key!r} must be a table")
    return value


def _string_value(
    data: dict[str, Any],
    key: str,
    *,
    default: str,
    context: str,
) -> str:
    value = data.get(key, default)
    if not isinstance(value, str):
        raise ProfileError(f"{context} key {key!r} must be a string")
    return value


def _optional_string(
    data: dict[str, Any],
    key: str,
    *,
    context: str,
) -> str | None:
    value = data.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ProfileError(f"{context} key {key!r} must be a string")
    return value


def _string_array(
    data: dict[str, Any],
    key: str,
    *,
    context: str,
) -> tuple[str, ...]:
    value = data.get(key)
    if value is None:
        return ()
    if not isinstance(value, list):
        raise ProfileError(f"{context} key {key!r} must be an array of strings")
    strings = []
    for index, item in enumerate(value):
        if not isinstance(item, str):
            raise ProfileError(f"{context} key {key}[{index}] must be a string")
        strings.append(item)
    return tuple(strings)


def _bool_value(
    data: dict[str, Any],
    key: str,
    *,
    default: bool,
    context: str,
) -> bool:
    value = data.get(key, default)
    if not isinstance(value, bool):
        raise ProfileError(f"{context} key {key!r} must be a boolean")
    return value


def _require_table(value: Any, context: str) -> None:
    if not isinstance(value, dict):
        raise ProfileError(f"{context} must be a TOML table")


def _reject_unknown(data: dict[str, Any], context: str, allowed: set[str]) -> None:
    unknown = sorted(set(data) - allowed)
    if unknown:
        keys = ", ".join(repr(key) for key in unknown)
        raise ProfileError(f"{context} has unsupported keys: {keys}")
