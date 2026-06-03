from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


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
    style_safelist: tuple[str, ...] = ()
    assets: tuple[ProfileAsset, ...] = ()
    runtime_files: tuple[ProfileRuntimeFile, ...] = ()
    allow_runtime_installs: bool = False
    backend_name: str | None = None
    backend_capability: str | None = None
    backend_capability_profile: Path | None = None
    backend_coverage_requirements: Path | None = None
    dependency_packages: tuple[str, ...] = ()
    dependency_extras: tuple[str, ...] = ()
