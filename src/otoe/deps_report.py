from __future__ import annotations

from typing import Any

from .deps_types import (
    DependencyAudit,
    DependencyAuditDynamicImport,
    DependencyAuditExternalImport,
    DependencyAuditExtra,
    DependencyAuditPackage,
    DependencyAuditRuntimePolicyFinding,
    DependencyStatus,
    ExtraStatus,
)


DEPENDENCY_RESOLUTION_CONTRACT = {
    "mode": "audit-only",
    "lockfile": False,
    "wheelClosure": False,
}


def deps_to_dict(audit: DependencyAudit) -> dict[str, Any]:
    return {
        "schemaVersion": 1,
        "target": audit.target,
        "profile": audit.profile,
        "status": audit.status,
        "hasErrors": audit.has_errors,
        "runtimeInstallsAllowed": audit.runtime_installs_allowed,
        "resolution": {
            **DEPENDENCY_RESOLUTION_CONTRACT,
            "runtimeInstallsAllowed": audit.runtime_installs_allowed,
        },
        "packages": [_package_to_dict(package) for package in audit.packages],
        "extras": [_extra_to_dict(extra) for extra in audit.extras],
        "externalImports": [
            _external_import_to_dict(external_import)
            for external_import in audit.external_imports
        ],
        "dynamicImports": [
            _dynamic_import_to_dict(dynamic_import)
            for dynamic_import in audit.dynamic_imports
        ],
        "runtimePolicy": {
            "mode": "audit-only",
            "network": audit.runtime_policy.network,
            "subprocess": audit.runtime_policy.subprocess,
            "findings": [
                _runtime_policy_finding_to_dict(finding)
                for finding in audit.runtime_policy_findings
            ],
        },
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
        "resolution: audit-only; no lockfile; no wheel closure",
        (
            f"packages: {len(audit.packages)} declared, "
            f"{installed_packages} installed, {missing_packages} missing"
        ),
        (
            f"extras: {len(audit.extras)} declared, "
            f"{known_extras} known, {unknown_extras} unknown"
        ),
        f"external imports: {len(audit.external_imports)} detected",
        f"dynamic imports: {len(audit.dynamic_imports)} detected",
        (
            "runtime policy: "
            f"network {audit.runtime_policy.network}, "
            f"subprocess {audit.runtime_policy.subprocess}; "
            f"{len(audit.runtime_policy_findings)} findings"
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
    for external_import in audit.external_imports:
        lines.append(_format_external_import(external_import))
    for dynamic_import in audit.dynamic_imports:
        lines.append(_format_dynamic_import(dynamic_import))
    for finding in audit.runtime_policy_findings:
        lines.append(_format_runtime_policy_finding(finding))
    lines.append(f"status: {audit.status}")
    for diagnostic in audit.diagnostics:
        lines.append(f"{diagnostic.level}: {diagnostic.message}")
    return "\n".join(lines)


def _format_external_import(external_import: DependencyAuditExternalImport) -> str:
    location = f"{external_import.source}:{external_import.line}"
    if external_import.declared_by is not None:
        candidates = _external_import_candidate_text(external_import.packages)
        suffix = f"; candidates: {candidates}" if candidates else ""
        return (
            f"external import {external_import.module}: declared via package "
            f"{external_import.declared_by}{suffix} at {location}"
        )
    candidates = _external_import_candidate_text(external_import.packages)
    if candidates:
        return (
            f"external import {external_import.module}: undeclared; "
            f"package candidates: {candidates} at {location}"
        )
    return (
        f"external import {external_import.module}: undeclared; "
        f"no installed package metadata found at {location}"
    )


def _format_dynamic_import(dynamic_import: DependencyAuditDynamicImport) -> str:
    location = f"{dynamic_import.source}:{dynamic_import.line}"
    if dynamic_import.module is None:
        return (
            f"dynamic import expression via {dynamic_import.mechanism}: "
            f"unresolved at {location}"
        )
    if dynamic_import.declared_by is not None:
        candidates = _external_import_candidate_text(dynamic_import.packages)
        suffix = f"; candidates: {candidates}" if candidates else ""
        return (
            f"dynamic import {dynamic_import.module} via {dynamic_import.mechanism}: "
            f"declared via package {dynamic_import.declared_by}{suffix} at {location}"
        )
    candidates = _external_import_candidate_text(dynamic_import.packages)
    if candidates:
        return (
            f"dynamic import {dynamic_import.module} via {dynamic_import.mechanism}: "
            f"not statically copied; package candidates: {candidates} at {location}"
        )
    return (
        f"dynamic import {dynamic_import.module} via {dynamic_import.mechanism}: "
        f"not statically copied; no installed package metadata found at {location}"
    )


def _format_runtime_policy_finding(
    finding: DependencyAuditRuntimePolicyFinding,
) -> str:
    location = f"{finding.source}:{finding.line}"
    return (
        f"runtime policy {finding.category}: {finding.action} via "
        f"{finding.mechanism} at {location}"
    )


def _external_import_candidate_text(packages: tuple[str, ...]) -> str:
    return ", ".join(packages)


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


def _external_import_to_dict(
    external_import: DependencyAuditExternalImport,
) -> dict[str, Any]:
    return {
        "module": external_import.module,
        "source": external_import.source,
        "line": external_import.line,
        "packages": list(external_import.packages),
        "declared": external_import.declared,
        "declaredBy": external_import.declared_by,
    }


def _dynamic_import_to_dict(
    dynamic_import: DependencyAuditDynamicImport,
) -> dict[str, Any]:
    return {
        "module": dynamic_import.module,
        "source": dynamic_import.source,
        "line": dynamic_import.line,
        "mechanism": dynamic_import.mechanism,
        "packages": list(dynamic_import.packages),
        "declared": dynamic_import.declared,
        "declaredBy": dynamic_import.declared_by,
    }


def _runtime_policy_finding_to_dict(
    finding: DependencyAuditRuntimePolicyFinding,
) -> dict[str, Any]:
    return {
        "category": finding.category,
        "module": finding.module,
        "source": finding.source,
        "line": finding.line,
        "mechanism": finding.mechanism,
        "action": finding.action,
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
