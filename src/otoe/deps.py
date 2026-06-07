from __future__ import annotations

import sys
from importlib import metadata
from pathlib import Path

from .deps_imports import (
    runtime_file_dynamic_imports,
    runtime_file_imports,
    runtime_file_policy_refs,
)
from .deps_report import deps_to_dict, format_deps
from .deps_types import (
    DependencyAudit,
    DependencyAuditDiagnostic,
    DependencyAuditDynamicImport,
    DependencyAuditExternalImport,
    DependencyAuditExtra,
    DependencyAuditPackage,
    DependencyAuditRuntimePolicyFinding,
)
from .profile_types import PlanProfileConfig
from .runtime_files import build_runtime_files


KNOWN_EXTRAS: dict[str, tuple[str, ...]] = {
    "dev": ("pytest", "mypy"),
    "release": ("build", "twine"),
}


def audit_deps(*, target: str, profile_config: PlanProfileConfig) -> DependencyAudit:
    packages = tuple(
        _audit_package(package) for package in profile_config.dependency_packages
    )
    extras = tuple(_audit_extra(extra) for extra in profile_config.dependency_extras)
    external_imports = _external_imports_for_target(
        target,
        profile_config=profile_config,
    )
    dynamic_imports = _dynamic_imports_for_target(
        target,
        profile_config=profile_config,
    )
    runtime_policy_findings = _runtime_policy_findings_for_target(
        target,
        profile_config=profile_config,
    )
    diagnostics = list(_diagnostics_for_packages(packages))
    diagnostics.extend(_diagnostics_for_extras(extras))
    diagnostics.extend(_diagnostics_for_external_imports(external_imports))
    diagnostics.extend(_diagnostics_for_dynamic_imports(dynamic_imports))
    diagnostics.extend(_diagnostics_for_runtime_policy(runtime_policy_findings))
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
        external_imports=external_imports,
        dynamic_imports=dynamic_imports,
        runtime_policy=profile_config.runtime_policy,
        runtime_policy_findings=runtime_policy_findings,
        diagnostics=tuple(diagnostics),
    )


def _external_imports_for_target(
    target: str,
    *,
    profile_config: PlanProfileConfig,
) -> tuple[DependencyAuditExternalImport, ...]:
    runtime_files = build_runtime_files(target, profile_config.runtime_files)
    local_modules = _local_module_roots(runtime_files)
    declared_packages = _declared_dependency_packages(profile_config)
    package_map = metadata.packages_distributions()
    external_imports: list[DependencyAuditExternalImport] = []
    seen = set()

    for runtime_file in runtime_files:
        if not runtime_file.source.is_file():
            continue
        for import_ref in runtime_file_imports(runtime_file.source):
            if _is_internal_import(import_ref.module, local_modules=local_modules):
                continue
            packages = tuple(sorted(package_map.get(import_ref.module, ())))
            declared_by = _external_import_declared_by(
                import_ref.module,
                packages=packages,
                declared_packages=declared_packages,
            )
            key = (
                import_ref.module,
                runtime_file.relative_path.as_posix(),
                import_ref.line,
            )
            if key in seen:
                continue
            seen.add(key)
            external_imports.append(
                DependencyAuditExternalImport(
                    module=import_ref.module,
                    source=runtime_file.relative_path.as_posix(),
                    line=import_ref.line,
                    packages=packages,
                    declared=declared_by is not None,
                    declared_by=declared_by,
                )
            )
    return tuple(external_imports)


def _dynamic_imports_for_target(
    target: str,
    *,
    profile_config: PlanProfileConfig,
) -> tuple[DependencyAuditDynamicImport, ...]:
    runtime_files = build_runtime_files(target, profile_config.runtime_files)
    declared_packages = _declared_dependency_packages(profile_config)
    package_map = metadata.packages_distributions()
    dynamic_imports: list[DependencyAuditDynamicImport] = []
    seen = set()

    for runtime_file in runtime_files:
        if not runtime_file.source.is_file():
            continue
        for import_ref in runtime_file_dynamic_imports(runtime_file.source):
            packages = (
                tuple(sorted(package_map.get(import_ref.module, ())))
                if import_ref.module is not None
                else ()
            )
            declared_by = (
                _external_import_declared_by(
                    import_ref.module,
                    packages=packages,
                    declared_packages=declared_packages,
                )
                if import_ref.module is not None
                else None
            )
            key = (
                import_ref.module,
                import_ref.mechanism,
                runtime_file.relative_path.as_posix(),
                import_ref.line,
            )
            if key in seen:
                continue
            seen.add(key)
            dynamic_imports.append(
                DependencyAuditDynamicImport(
                    module=import_ref.module,
                    source=runtime_file.relative_path.as_posix(),
                    line=import_ref.line,
                    mechanism=import_ref.mechanism,
                    packages=packages,
                    declared=declared_by is not None,
                    declared_by=declared_by,
                )
            )
    return tuple(dynamic_imports)


def _runtime_policy_findings_for_target(
    target: str,
    *,
    profile_config: PlanProfileConfig,
) -> tuple[DependencyAuditRuntimePolicyFinding, ...]:
    runtime_files = build_runtime_files(target, profile_config.runtime_files)
    findings: list[DependencyAuditRuntimePolicyFinding] = []
    seen = set()

    for runtime_file in runtime_files:
        if not runtime_file.source.is_file():
            continue
        for policy_ref in runtime_file_policy_refs(runtime_file.source):
            action = getattr(profile_config.runtime_policy, policy_ref.category)
            if action == "allow":
                continue
            key = (
                policy_ref.category,
                policy_ref.module,
                policy_ref.mechanism,
                runtime_file.relative_path.as_posix(),
                policy_ref.line,
            )
            if key in seen:
                continue
            seen.add(key)
            findings.append(
                DependencyAuditRuntimePolicyFinding(
                    category=policy_ref.category,
                    module=policy_ref.module,
                    source=runtime_file.relative_path.as_posix(),
                    line=policy_ref.line,
                    mechanism=policy_ref.mechanism,
                    action="warning" if action == "warn" else "error",
                )
            )
    return tuple(findings)


def _local_module_roots(runtime_files) -> set[str]:
    roots = set()
    for runtime_file in runtime_files:
        parts = runtime_file.relative_path.parts
        if not parts:
            continue
        first = parts[0]
        if first == "__init__.py":
            continue
        if first.endswith(".py"):
            roots.add(Path(first).stem)
        else:
            roots.add(first)
    return roots


def _is_internal_import(module: str, *, local_modules: set[str]) -> bool:
    if module in local_modules:
        return True
    if module == "otoe":
        return True
    if module in sys.builtin_module_names:
        return True
    stdlib_modules = getattr(sys, "stdlib_module_names", frozenset())
    return module in stdlib_modules


def _declared_dependency_packages(profile_config: PlanProfileConfig) -> dict[str, str]:
    packages = {
        _normalize_package_name(name): name
        for name in profile_config.dependency_packages
    }
    for extra_name in profile_config.dependency_extras:
        for package in KNOWN_EXTRAS.get(extra_name, ()):
            packages.setdefault(_normalize_package_name(package), package)
    return packages


def _external_import_declared_by(
    module: str,
    *,
    packages: tuple[str, ...],
    declared_packages: dict[str, str],
) -> str | None:
    normalized_module = _normalize_package_name(module)
    if normalized_module in declared_packages:
        return declared_packages[normalized_module]
    for package in packages:
        normalized_package = _normalize_package_name(package)
        if normalized_package in declared_packages:
            return declared_packages[normalized_package]
    return None

def _normalize_package_name(name: str) -> str:
    return name.replace("_", "-").lower()


def _external_import_candidate_text(packages: tuple[str, ...]) -> str:
    return ", ".join(packages)


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


def _diagnostics_for_external_imports(
    external_imports: tuple[DependencyAuditExternalImport, ...],
) -> tuple[DependencyAuditDiagnostic, ...]:
    return tuple(
        DependencyAuditDiagnostic(
            level="error",
            message=_external_import_diagnostic_message(external_import),
        )
        for external_import in external_imports
        if not external_import.declared
    )


def _diagnostics_for_dynamic_imports(
    dynamic_imports: tuple[DependencyAuditDynamicImport, ...],
) -> tuple[DependencyAuditDiagnostic, ...]:
    return tuple(
        DependencyAuditDiagnostic(
            level="warning",
            message=_dynamic_import_diagnostic_message(dynamic_import),
        )
        for dynamic_import in dynamic_imports
    )


def _diagnostics_for_runtime_policy(
    findings: tuple[DependencyAuditRuntimePolicyFinding, ...],
) -> tuple[DependencyAuditDiagnostic, ...]:
    return tuple(
        DependencyAuditDiagnostic(
            level=finding.action,
            message=_runtime_policy_diagnostic_message(finding),
        )
        for finding in findings
    )


def _external_import_diagnostic_message(
    external_import: DependencyAuditExternalImport,
) -> str:
    message = (
        f"external import {external_import.module!r} from "
        f"{external_import.source}:{external_import.line} is not declared "
        "in [deps] packages"
    )
    candidates = _external_import_candidate_text(external_import.packages)
    if candidates:
        return f"{message} (candidate packages: {candidates})"
    return f"{message} (no installed package metadata found)"


def _dynamic_import_diagnostic_message(
    dynamic_import: DependencyAuditDynamicImport,
) -> str:
    location = f"{dynamic_import.source}:{dynamic_import.line}"
    manual = "declare required [runtime] files and [deps] packages manually"
    if dynamic_import.module is None:
        return (
            f"dynamic import expression from {location} via "
            f"{dynamic_import.mechanism} cannot be resolved statically; {manual}"
        )
    if dynamic_import.declared_by is not None:
        return (
            f"dynamic import {dynamic_import.module!r} from {location} via "
            f"{dynamic_import.mechanism} is declared by package "
            f"{dynamic_import.declared_by!r}; {manual}"
        )
    candidates = _external_import_candidate_text(dynamic_import.packages)
    if candidates:
        return (
            f"dynamic import {dynamic_import.module!r} from {location} via "
            f"{dynamic_import.mechanism} is not statically copied; {manual} "
            f"(candidate packages: {candidates})"
        )
    return (
        f"dynamic import {dynamic_import.module!r} from {location} via "
        f"{dynamic_import.mechanism} is not statically copied; {manual} "
        "(no installed package metadata found)"
    )


def _runtime_policy_diagnostic_message(
    finding: DependencyAuditRuntimePolicyFinding,
) -> str:
    return (
        f"runtime policy {finding.category} use from "
        f"{finding.source}:{finding.line} via {finding.mechanism}"
    )
