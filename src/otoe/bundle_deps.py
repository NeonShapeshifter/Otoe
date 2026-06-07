from __future__ import annotations

from typing import Any


def verify_dependency_audit_contract(payload: dict[str, Any], label: str) -> None:
    if payload.get("hasErrors") is not False or payload.get("status") == "invalid":
        raise ValueError(f"{label}: dependency audit has errors")
    if payload.get("runtimeInstallsAllowed") is not False:
        raise ValueError(f"{label}: runtimeInstallsAllowed must be false")
    resolution = payload.get("resolution")
    if not isinstance(resolution, dict):
        raise ValueError(f"{label}: resolution must be an object")
    if resolution.get("mode") != "audit-only":
        raise ValueError(f"{label}: resolution.mode must be 'audit-only'")
    if resolution.get("lockfile") is not False:
        raise ValueError(f"{label}: resolution.lockfile must be false")
    if resolution.get("wheelClosure") is not False:
        raise ValueError(f"{label}: resolution.wheelClosure must be false")
    if resolution.get("runtimeInstallsAllowed") is not False:
        raise ValueError(f"{label}: resolution.runtimeInstallsAllowed must be false")
    runtime_policy = payload.get("runtimePolicy")
    if runtime_policy is not None:
        _verify_dependency_runtime_policy_contract(runtime_policy, label)


def _verify_dependency_runtime_policy_contract(
    runtime_policy: Any,
    label: str,
) -> None:
    if not isinstance(runtime_policy, dict):
        raise ValueError(f"{label}: runtimePolicy must be an object")
    if runtime_policy.get("mode") != "audit-only":
        raise ValueError(f"{label}: runtimePolicy.mode must be 'audit-only'")
    for key in ("network", "subprocess"):
        if runtime_policy.get(key) not in {"allow", "warn", "error"}:
            raise ValueError(
                f"{label}: runtimePolicy.{key} must be allow, warn, or error"
            )
    findings = runtime_policy.get("findings")
    if not isinstance(findings, list):
        raise ValueError(f"{label}: runtimePolicy.findings must be a list")
    for index, finding in enumerate(findings):
        finding_label = f"{label}: runtimePolicy.findings[{index}]"
        if not isinstance(finding, dict):
            raise ValueError(f"{finding_label} must be an object")
        if finding.get("category") not in {"network", "subprocess"}:
            raise ValueError(f"{finding_label}.category must be network or subprocess")
        if finding.get("action") not in {"warning", "error"}:
            raise ValueError(f"{finding_label}.action must be warning or error")
        for key in ("module", "source", "mechanism"):
            if not isinstance(finding.get(key), str) or not finding.get(key):
                raise ValueError(f"{finding_label}.{key} must be a non-empty string")
        line = finding.get("line")
        if type(line) is not int or line <= 0:
            raise ValueError(f"{finding_label}.line must be a positive integer")
