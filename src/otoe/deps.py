from __future__ import annotations

from dataclasses import dataclass
from importlib import metadata
from typing import Any, Literal

from .profile import PlanProfileConfig


DependencyStatus = Literal["installed", "missing"]
ExtraStatus = Literal["known", "unknown"]
DiagnosticLevel = Literal["warning", "error"]


KNOWN_EXTRAS: dict[str, tuple[str, ...]] = {
    "dev": ("pytest", "mypy"),
    "release": ("build", "twine"),
}


@dataclass(frozen=True)
class DependencyAuditPackage:
    name: str
    status: DependencyStatus
    version: str | None = None


@dataclass(frozen=True)
class DependencyAuditExtra:
    name: str
    status: ExtraStatus
    packages: tuple[DependencyAuditPackage, ...] = ()


@dataclass(frozen=True)
class DependencyAuditDiagnostic:
    level: DiagnosticLevel
    message: str


@dataclass(frozen=True)
class DependencyAudit:
    target: str
    profile: str
    runtime_installs_allowed: bool
    packages: tuple[DependencyAuditPackage, ...]
    extras: tuple[DependencyAuditExtra, ...]
    diagnostics: tuple[DependencyAuditDiagnostic, ...]

    @property
    def has_errors(self) -> bool:
        return any(diagnostic.level == "error" for diagnostic in self.diagnostics)

    @property
    def status(self) -> str:
        if self.has_errors:
            return "invalid"
        if self.diagnostics:
            return "warnings"
        return "ok"


def audit_deps(*, target: str, profile_config: PlanProfileConfig) -> DependencyAudit:
    packages = tuple(
        _audit_package(package) for package in profile_config.dependency_packages
    )
    extras = tuple(_audit_extra(extra) for extra in profile_config.dependency_extras)
    diagnostics = list(_diagnostics_for_packages(packages))
    diagnostics.extend(_diagnostics_for_extras(extras))
    if profile_config.allow_runtime_installs:
        diagnostics.append(
            DependencyAuditDiagnostic(
                level="error",
                message="runtime dependency installs are enabled",
            )
        )

    return DependencyAudit(
        target=target,
        profile=profile_config.profile,
        runtime_installs_allowed=profile_config.allow_runtime_installs,
        packages=packages,
        extras=extras,
        diagnostics=tuple(diagnostics),
    )


def deps_to_dict(audit: DependencyAudit) -> dict[str, Any]:
    return {
        "schemaVersion": 1,
        "target": audit.target,
        "profile": audit.profile,
        "status": audit.status,
        "hasErrors": audit.has_errors,
        "runtimeInstallsAllowed": audit.runtime_installs_allowed,
        "packages": [_package_to_dict(package) for package in audit.packages],
        "extras": [_extra_to_dict(extra) for extra in audit.extras],
        "diagnostics": [
            {"level": diagnostic.level, "message": diagnostic.message}
            for diagnostic in audit.diagnostics
        ],
    }


def format_deps(audit: DependencyAudit) -> str:
    installed_packages = _count_packages(audit.packages, "installed")
    missing_packages = _count_packages(audit.packages, "missing")
    known_extras = _count_extras(audit.extras, "known")
    unknown_extras = _count_extras(audit.extras, "unknown")
    lines = [
        f"deps {audit.target}: profile {audit.profile}",
        f"runtime installs: {'allowed' if audit.runtime_installs_allowed else 'forbidden'}",
        (
            f"packages: {len(audit.packages)} declared, "
            f"{installed_packages} installed, {missing_packages} missing"
        ),
        (
            f"extras: {len(audit.extras)} declared, "
            f"{known_extras} known, {unknown_extras} unknown"
        ),
    ]
    for package in audit.packages:
        version = f" ({package.version})" if package.version else ""
        lines.append(f"package {package.name}: {package.status}{version}")
    for extra in audit.extras:
        lines.append(f"extra {extra.name}: {extra.status}")
        for package in extra.packages:
            version = f" ({package.version})" if package.version else ""
            lines.append(
                f"extra {extra.name} package {package.name}: "
                f"{package.status}{version}"
            )
    lines.append(f"status: {audit.status}")
    for diagnostic in audit.diagnostics:
        lines.append(f"{diagnostic.level}: {diagnostic.message}")
    return "\n".join(lines)


def _audit_extra(name: str) -> DependencyAuditExtra:
    packages = KNOWN_EXTRAS.get(name)
    if packages is None:
        return DependencyAuditExtra(name=name, status="unknown")
    return DependencyAuditExtra(
        name=name,
        status="known",
        packages=tuple(_audit_package(package) for package in packages),
    )


def _audit_package(name: str) -> DependencyAuditPackage:
    try:
        package_version = metadata.version(name)
    except metadata.PackageNotFoundError:
        return DependencyAuditPackage(name=name, status="missing")
    return DependencyAuditPackage(
        name=name,
        status="installed",
        version=package_version,
    )


def _diagnostics_for_packages(
    packages: tuple[DependencyAuditPackage, ...],
) -> tuple[DependencyAuditDiagnostic, ...]:
    return tuple(
        DependencyAuditDiagnostic(
            level="error",
            message=f"package {package.name!r} is not installed in this environment",
        )
        for package in packages
        if package.status == "missing"
    )


def _diagnostics_for_extras(
    extras: tuple[DependencyAuditExtra, ...],
) -> tuple[DependencyAuditDiagnostic, ...]:
    diagnostics = []
    for extra in extras:
        if extra.status == "unknown":
            diagnostics.append(
                DependencyAuditDiagnostic(
                    level="error",
                    message=f"extra {extra.name!r} is not declared by Otoe",
                )
            )
            continue
        diagnostics.extend(_diagnostics_for_packages(extra.packages))
    return tuple(diagnostics)


def _package_to_dict(package: DependencyAuditPackage) -> dict[str, Any]:
    payload: dict[str, Any] = {"name": package.name, "status": package.status}
    if package.version is not None:
        payload["version"] = package.version
    return payload


def _extra_to_dict(extra: DependencyAuditExtra) -> dict[str, Any]:
    return {
        "name": extra.name,
        "status": extra.status,
        "packages": [_package_to_dict(package) for package in extra.packages],
    }


def _count_packages(
    packages: tuple[DependencyAuditPackage, ...],
    status: DependencyStatus,
) -> int:
    return sum(1 for package in packages if package.status == status)


def _count_extras(
    extras: tuple[DependencyAuditExtra, ...],
    status: ExtraStatus,
) -> int:
    return sum(1 for extra in extras if extra.status == status)
