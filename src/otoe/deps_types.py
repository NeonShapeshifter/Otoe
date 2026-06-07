from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

DependencyStatus = Literal["installed", "missing"]
ExtraStatus = Literal["known", "unknown"]
DiagnosticLevel = Literal["warning", "error"]


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
class DependencyAuditExternalImport:
    module: str
    source: str
    line: int
    packages: tuple[str, ...]
    declared: bool
    declared_by: str | None = None


@dataclass(frozen=True)
class DependencyAuditDynamicImport:
    module: str | None
    source: str
    line: int
    mechanism: str
    packages: tuple[str, ...]
    declared: bool
    declared_by: str | None = None


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
    external_imports: tuple[DependencyAuditExternalImport, ...]
    dynamic_imports: tuple[DependencyAuditDynamicImport, ...]
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
