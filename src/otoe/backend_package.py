from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping


BACKEND_PACKAGE_SCHEMA_VERSION = 1
BACKEND_PACKAGE_MANIFEST_FORMAT = "backend-package-manifest"
BACKEND_PACKAGE_FORMAT = "backend-package"
BACKEND_PACKAGE_DESCRIPTOR = "backend-package.json"
BACKEND_PACKAGE_FILE_ROLES = frozenset({"runner", "support"})
BACKEND_PACKAGE_MANIFEST_KEYS = frozenset(
    {
        "schemaVersion",
        "format",
        "name",
        "label",
        "kind",
        "entrypoint",
        "files",
        "contracts",
        "runtime",
    }
)
BACKEND_PACKAGE_FILE_KEYS = frozenset({"path", "role"})


class BackendPackageError(ValueError):
    pass


@dataclass(frozen=True)
class BackendPackageFile:
    path: Path
    role: str

    @property
    def bundle_path(self) -> Path:
        return self.path


@dataclass(frozen=True)
class BackendPackageManifest:
    name: str
    label: str
    kind: str
    entrypoint: Path
    files: tuple[BackendPackageFile, ...]
    contracts: dict[str, Any]
    runtime: dict[str, Any]
    source_dir: Path

    @property
    def entrypoint_source(self) -> Path:
        return self.source_dir / self.entrypoint


def load_backend_package_manifest(path: str | Path) -> BackendPackageManifest:
    manifest_path = Path(path)
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise BackendPackageError(
            f"backend package manifest {str(manifest_path)!r} is not valid JSON: {exc}"
        ) from exc
    if not isinstance(payload, Mapping):
        raise BackendPackageError(
            f"backend package manifest {str(manifest_path)!r} must be a JSON object"
        )
    return backend_package_manifest_from_dict(
        payload,
        source_dir=manifest_path.parent,
        source=str(manifest_path),
    )


def backend_package_manifest_from_dict(
    payload: Mapping[str, Any],
    *,
    source_dir: str | Path,
    source: str = "backend package manifest",
) -> BackendPackageManifest:
    _reject_unexpected_keys(payload, BACKEND_PACKAGE_MANIFEST_KEYS, context=source)
    if payload.get("schemaVersion") != BACKEND_PACKAGE_SCHEMA_VERSION:
        raise BackendPackageError(f"{source}: schemaVersion must be 1")
    if payload.get("format") != BACKEND_PACKAGE_MANIFEST_FORMAT:
        raise BackendPackageError(
            f"{source}: format must be {BACKEND_PACKAGE_MANIFEST_FORMAT!r}"
        )
    name = _required_string(payload, "name", source=source)
    label = _required_string(payload, "label", source=source)
    kind = _required_string(payload, "kind", source=source)
    root = Path(source_dir)
    entrypoint = _relative_path(
        _required_string(payload, "entrypoint", source=source),
        context=f"{source}: entrypoint",
    )
    files = _backend_package_files(payload.get("files"), source=source)
    file_paths = {file.path for file in files}
    if entrypoint not in file_paths:
        raise BackendPackageError(f"{source}: entrypoint must be listed in files")
    if not (root / entrypoint).is_file():
        raise BackendPackageError(
            f"{source}: entrypoint file {entrypoint.as_posix()!r} does not exist"
        )
    contracts = _json_object(payload.get("contracts"), context=f"{source}: contracts")
    _validate_string_list(contracts, "inputs", context=f"{source}: contracts")
    _validate_string_list(
        contracts,
        "optionalInputs",
        context=f"{source}: contracts",
        required=False,
    )
    _validate_string_list(contracts, "outputs", context=f"{source}: contracts")
    runtime = _json_object(payload.get("runtime"), context=f"{source}: runtime")
    if runtime.get("runtimeInstallsAllowed") is not False:
        raise BackendPackageError(
            f"{source}: runtime.runtimeInstallsAllowed must be false"
        )
    language = runtime.get("language")
    if not isinstance(language, str) or not language:
        raise BackendPackageError(f"{source}: runtime.language must be non-empty")
    for file in files:
        if not (root / file.path).is_file():
            raise BackendPackageError(
                f"{source}: file {file.path.as_posix()!r} does not exist"
            )
    return BackendPackageManifest(
        name=name,
        label=label,
        kind=kind,
        entrypoint=entrypoint,
        files=files,
        contracts=dict(contracts),
        runtime=dict(runtime),
        source_dir=root,
    )


def backend_package_to_dict(manifest: BackendPackageManifest) -> dict[str, Any]:
    payload = {
        "schemaVersion": BACKEND_PACKAGE_SCHEMA_VERSION,
        "format": BACKEND_PACKAGE_FORMAT,
        "name": manifest.name,
        "label": manifest.label,
        "kind": manifest.kind,
        "entrypoint": manifest.entrypoint.as_posix(),
        "contracts": _jsonable(manifest.contracts),
        "runtime": _jsonable(manifest.runtime),
        "files": [
            _backend_package_file_to_dict(manifest, file)
            for file in manifest.files
        ],
    }
    return {**payload, "packageHash": package_hash(payload)}


def copy_backend_package(
    manifest: BackendPackageManifest,
    *,
    output_dir: str | Path,
) -> dict[str, Any]:
    package_dir = Path(output_dir)
    package_dir.mkdir(parents=True, exist_ok=True)
    descriptor = backend_package_to_dict(manifest)
    for file in manifest.files:
        destination = package_dir / file.bundle_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(manifest.source_dir / file.path, destination)
    (package_dir / BACKEND_PACKAGE_DESCRIPTOR).write_text(
        json.dumps(descriptor, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return descriptor


def backend_package_payload_errors(payload: Any) -> list[str]:
    if not isinstance(payload, Mapping):
        return ["backend package must be a JSON object"]
    errors: list[str] = []
    if payload.get("schemaVersion") != BACKEND_PACKAGE_SCHEMA_VERSION:
        errors.append("backend package schemaVersion must be 1")
    if payload.get("format") != BACKEND_PACKAGE_FORMAT:
        errors.append(f"backend package format must be {BACKEND_PACKAGE_FORMAT!r}")
    for key in ("name", "label", "kind", "entrypoint"):
        value = payload.get(key)
        if not isinstance(value, str) or not value:
            errors.append(f"backend package {key} must be a non-empty string")
    files = payload.get("files")
    file_paths: set[str] = set()
    if not isinstance(files, list) or not files:
        errors.append("backend package files must be a non-empty list")
    else:
        for index, file_payload in enumerate(files):
            prefix = f"backend package files[{index}]"
            if not isinstance(file_payload, Mapping):
                errors.append(f"{prefix} must be a JSON object")
                continue
            path = file_payload.get("path")
            role = file_payload.get("role")
            size = file_payload.get("size")
            sha256 = file_payload.get("sha256")
            if not isinstance(path, str) or not path:
                errors.append(f"{prefix}.path must be a non-empty string")
            else:
                file_paths.add(path)
            if role not in BACKEND_PACKAGE_FILE_ROLES:
                errors.append(
                    f"{prefix}.role must be one of "
                    f"{', '.join(sorted(BACKEND_PACKAGE_FILE_ROLES))}"
                )
            if type(size) is not int or size <= 0:
                errors.append(f"{prefix}.size must be a positive integer")
            if not _is_sha256_hex(sha256):
                errors.append(f"{prefix}.sha256 must be 64 lowercase hex chars")
    entrypoint = payload.get("entrypoint")
    if isinstance(entrypoint, str) and entrypoint and entrypoint not in file_paths:
        errors.append("backend package entrypoint must be listed in files")
    runtime = payload.get("runtime")
    if not isinstance(runtime, Mapping):
        errors.append("backend package runtime must be a JSON object")
    elif runtime.get("runtimeInstallsAllowed") is not False:
        errors.append("backend package runtime.runtimeInstallsAllowed must be false")
    package_hash_value = payload.get("packageHash")
    if not _is_sha256_uri(package_hash_value):
        errors.append("backend package packageHash must be a sha256 string")
    elif package_hash_value != package_hash(payload):
        errors.append("backend package packageHash must match payload")
    return errors


def package_hash(payload: Mapping[str, Any]) -> str:
    payload_without_hash = {
        key: value for key, value in payload.items() if key != "packageHash"
    }
    encoded = json.dumps(
        payload_without_hash,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


def _backend_package_files(value: Any, *, source: str) -> tuple[BackendPackageFile, ...]:
    if not isinstance(value, list) or not value:
        raise BackendPackageError(f"{source}: files must be a non-empty list")
    result: list[BackendPackageFile] = []
    seen: set[Path] = set()
    for index, item in enumerate(value):
        context = f"{source}: files[{index}]"
        if not isinstance(item, Mapping):
            raise BackendPackageError(f"{context} must be a JSON object")
        _reject_unexpected_keys(item, BACKEND_PACKAGE_FILE_KEYS, context=context)
        path = _relative_path(_required_string(item, "path", source=context), context=context)
        if path in seen:
            raise BackendPackageError(f"{context}.path {path.as_posix()!r} is duplicated")
        seen.add(path)
        role = _required_string(item, "role", source=context)
        if role not in BACKEND_PACKAGE_FILE_ROLES:
            supported = ", ".join(sorted(BACKEND_PACKAGE_FILE_ROLES))
            raise BackendPackageError(f"{context}.role must be one of {supported}")
        result.append(BackendPackageFile(path=path, role=role))
    return tuple(result)


def _backend_package_file_to_dict(
    manifest: BackendPackageManifest,
    file: BackendPackageFile,
) -> dict[str, Any]:
    data = (manifest.source_dir / file.path).read_bytes()
    return {
        "path": file.bundle_path.as_posix(),
        "role": file.role,
        "size": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def _relative_path(value: str, *, context: str) -> Path:
    path = Path(value)
    if path.is_absolute() or value in {"", "."}:
        raise BackendPackageError(f"{context} must be a safe relative file path")
    if any(part in {"", ".", ".."} for part in path.parts):
        raise BackendPackageError(f"{context} must be a safe relative file path")
    return path


def _json_object(value: Any, *, context: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise BackendPackageError(f"{context} must be a JSON object")
    if not all(isinstance(key, str) and key for key in value):
        raise BackendPackageError(f"{context} keys must be non-empty strings")
    return dict(value)


def _validate_string_list(
    payload: Mapping[str, Any],
    key: str,
    *,
    context: str,
    required: bool = True,
) -> None:
    value = payload.get(key)
    if value is None and not required:
        return
    if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
        raise BackendPackageError(f"{context}.{key} must be a list of strings")


def _required_string(payload: Mapping[str, Any], key: str, *, source: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise BackendPackageError(f"{source}: {key} must be a non-empty string")
    return value


def _reject_unexpected_keys(
    payload: Mapping[str, Any],
    expected: frozenset[str],
    *,
    context: str,
) -> None:
    extra = sorted(repr(key) for key in set(payload) - expected)
    if extra:
        raise BackendPackageError(
            f"{context} has unexpected fields: {', '.join(extra)}"
        )


def _jsonable(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=True, sort_keys=True))


def _is_sha256_uri(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    prefix = "sha256:"
    if len(value) != len(prefix) + 64 or not value.startswith(prefix):
        return False
    return _is_sha256_hex(value[len(prefix) :])


def _is_sha256_hex(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(char in "0123456789abcdef" for char in value)
    )
