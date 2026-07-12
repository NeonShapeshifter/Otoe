from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path
from typing import Any

from .profile import DEFAULT_PROFILE_FILENAME, ProfileError, load_plan_profile
from .profile_types import PlanProfileConfig


class CliError(ValueError):
    pass


def emit_json_payload(
    payload: dict[str, Any],
    *,
    print_json: bool,
    output_path: str | None,
    artifact_label: str,
) -> None:
    encoded = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if output_path is not None:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(encoded, encoding="utf-8")
        if not print_json:
            print(f"{artifact_label}: {path}")
    if print_json:
        print(encoded, end="")


def write_json_artifact(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def load_json_artifact(path: Path, *, label: str) -> Any:
    if not path.exists():
        raise CliError(f"{label} file {str(path)!r} does not exist")
    if not path.is_file():
        raise CliError(f"{label} path {str(path)!r} is not a file")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise CliError(f"{label} file {str(path)!r} is not valid JSON: {exc}") from exc


def parse_target_spec(spec: str) -> tuple[str, str]:
    module_name, separator, object_path = spec.partition(":")
    if not separator or not module_name or not object_path:
        raise CliError(
            f"target {spec!r} must use MODULE:OBJECT syntax, for example app:app"
        )
    return module_name, object_path


def load_plan_profile_config(path: str | None) -> PlanProfileConfig:
    profile_path = Path(path) if path is not None else Path(DEFAULT_PROFILE_FILENAME)
    if not profile_path.exists():
        if path is not None:
            raise CliError(f"profile file {path!r} does not exist")
        return PlanProfileConfig()
    try:
        return load_plan_profile(profile_path)
    except ProfileError as exc:
        raise CliError(str(exc)) from exc


def load_target(spec: str) -> Any:
    module_name, object_path = parse_target_spec(spec)
    _ensure_cwd_on_syspath()
    try:
        value = importlib.import_module(module_name)
    except Exception as exc:
        raise CliError(
            f"could not import module {module_name!r} from target {spec!r}; "
            "run the command from the app directory or use MODULE:OBJECT syntax"
        ) from exc
    for part in object_path.split("."):
        try:
            value = getattr(value, part)
        except AttributeError as exc:
            raise CliError(
                f"target {spec!r} could not resolve attribute {part!r}; "
                f"available object path starts at module {module_name!r}"
            ) from exc
    return value


def _ensure_cwd_on_syspath() -> None:
    cwd = str(Path.cwd())
    if "" in sys.path or cwd in sys.path:
        return
    sys.path.insert(0, cwd)
