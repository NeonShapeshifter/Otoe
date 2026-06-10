from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal


RuntimePolicyAction = Literal["allow", "warn", "error"]
NativeTextRenderer = Literal["marker", "pillow"]


@dataclass(frozen=True)
class ProfileAsset:
    source: Path
    relative_path: Path


@dataclass(frozen=True)
class ProfileRuntimeFile:
    source: Path
    relative_path: Path


@dataclass(frozen=True)
class RuntimePolicyConfig:
    network: RuntimePolicyAction = "warn"
    subprocess: RuntimePolicyAction = "warn"


@dataclass(frozen=True)
class NativeTextConfig:
    renderer: NativeTextRenderer = "marker"
    font: Path | None = None
    font_relative_path: Path | None = None


@dataclass(frozen=True)
class PlanProfileConfig:
    profile: str = "cage"
    utilities: bool = False
    css_paths: tuple[Path, ...] = ()
    style_safelist: tuple[str, ...] = ()
    assets: tuple[ProfileAsset, ...] = ()
    runtime_files: tuple[ProfileRuntimeFile, ...] = ()
    allow_runtime_installs: bool = False
    runtime_policy: RuntimePolicyConfig = RuntimePolicyConfig()
    native_text: NativeTextConfig = NativeTextConfig()
    backend_name: str | None = None
    backend_capability: str | None = None
    backend_capability_profile: Path | None = None
    backend_coverage_requirements: Path | None = None
    backend_package_manifest: Path | None = None
    dependency_packages: tuple[str, ...] = ()
    dependency_extras: tuple[str, ...] = ()
