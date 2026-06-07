from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any, cast

from .capabilities import CapabilityProfileError, backend_capability_profile
from .plan import SUPPORTED_PLAN_PROFILES
from .profile_types import (
    PlanProfileConfig,
    ProfileAsset,
    ProfileRuntimeFile,
    RuntimePolicyAction,
    RuntimePolicyConfig,
)


DEFAULT_PROFILE_FILENAME = "otoe.profile.toml"
RUNTIME_POLICY_ACTIONS = frozenset({"allow", "warn", "error"})


class ProfileError(ValueError):
    pass


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
        {
            "profile",
            "utilities",
            "css",
            "styles",
            "assets",
            "runtime",
            "backend",
            "deps",
        },
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
    styles = _table_value(data, "styles", context="profile file")
    _reject_unknown(styles, "[styles]", {"safelist"})
    style_safelist = _style_safelist(styles.get("safelist"))
    assets = _assets(data.get("assets"), base=profile_path.parent)

    runtime = _table_value(data, "runtime", context="profile file")
    _reject_unknown(runtime, "[runtime]", {"allow_runtime_installs", "files", "policy"})
    allow_runtime_installs = _bool_value(
        runtime,
        "allow_runtime_installs",
        default=False,
        context="[runtime]",
    )
    if profile == "cage" and allow_runtime_installs:
        raise ProfileError("profile 'cage' forbids runtime installs")
    runtime_files = _runtime_files(runtime.get("files"), base=profile_path.parent)
    runtime_policy = _runtime_policy(runtime.get("policy"))

    backend = _table_value(data, "backend", context="profile file")
    _reject_unknown(
        backend,
        "[backend]",
        {
            "name",
            "capability",
            "capability_profile",
            "coverage_requirements",
            "package",
        },
    )
    backend_name = _optional_string(backend, "name", context="[backend]")
    backend_capability = _optional_string(backend, "capability", context="[backend]")
    backend_capability_profile_path = _optional_backend_profile_path(
        backend,
        base=profile_path.parent,
    )
    backend_coverage_requirements_path = _optional_backend_coverage_requirements_path(
        backend,
        base=profile_path.parent,
    )
    backend_package = _table_value(backend, "package", context="[backend]")
    _reject_unknown(backend_package, "[backend.package]", {"manifest"})
    backend_package_manifest_path = _optional_backend_package_manifest_path(
        backend_package,
        base=profile_path.parent,
    )
    if backend_capability is not None and backend_capability_profile_path is not None:
        raise ProfileError(
            "[backend] capability and capability_profile are mutually exclusive"
        )
    if backend_capability is not None:
        try:
            backend_capability = backend_capability_profile(backend_capability).name
        except CapabilityProfileError as exc:
            raise ProfileError(str(exc)) from exc

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
        style_safelist=style_safelist,
        assets=assets,
        runtime_files=runtime_files,
        allow_runtime_installs=allow_runtime_installs,
        runtime_policy=runtime_policy,
        backend_name=backend_name,
        backend_capability=backend_capability,
        backend_capability_profile=backend_capability_profile_path,
        backend_coverage_requirements=backend_coverage_requirements_path,
        backend_package_manifest=backend_package_manifest_path,
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


def _style_safelist(value: Any) -> tuple[str, ...]:
    class_names = _string_array({"safelist": value}, "safelist", context="[styles]")
    for index, class_name in enumerate(class_names):
        if class_name.strip() != class_name or len(class_name.split()) != 1:
            raise ProfileError(
                f"[styles] key safelist[{index}] must be one non-empty class name"
            )
    return tuple(dict.fromkeys(class_names))


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


def _runtime_policy(value: Any) -> RuntimePolicyConfig:
    if value is None:
        return RuntimePolicyConfig()
    if not isinstance(value, dict):
        raise ProfileError("[runtime] key 'policy' must be a table")
    _reject_unknown(value, "[runtime.policy]", {"network", "subprocess"})
    return RuntimePolicyConfig(
        network=_runtime_policy_action(value, "network"),
        subprocess=_runtime_policy_action(value, "subprocess"),
    )


def _runtime_policy_action(
    data: dict[str, Any],
    key: str,
) -> RuntimePolicyAction:
    value = _optional_string(data, key, context="[runtime.policy]")
    if value is None:
        return "warn"
    if value not in RUNTIME_POLICY_ACTIONS:
        supported = ", ".join(repr(action) for action in sorted(RUNTIME_POLICY_ACTIONS))
        raise ProfileError(
            f"[runtime.policy] key {key!r} must be one of {supported}"
        )
    return cast(RuntimePolicyAction, value)


def _optional_backend_profile_path(
    backend: dict[str, Any],
    *,
    base: Path,
) -> Path | None:
    value = _optional_string(backend, "capability_profile", context="[backend]")
    if value is None:
        return None
    relative = Path(value)
    _validate_relative_file_path(relative, key="backend.capability_profile")
    return base / relative


def _optional_backend_coverage_requirements_path(
    backend: dict[str, Any],
    *,
    base: Path,
) -> Path | None:
    value = _optional_string(backend, "coverage_requirements", context="[backend]")
    if value is None:
        return None
    relative = Path(value)
    _validate_relative_file_path(relative, key="backend.coverage_requirements")
    return base / relative


def _optional_backend_package_manifest_path(
    backend_package: dict[str, Any],
    *,
    base: Path,
) -> Path | None:
    value = _optional_string(
        backend_package,
        "manifest",
        context="[backend.package]",
    )
    if value is None:
        return None
    relative = Path(value)
    _validate_relative_file_path(relative, key="backend.package.manifest")
    return base / relative


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
