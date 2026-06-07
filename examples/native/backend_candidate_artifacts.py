from __future__ import annotations

import argparse
import importlib
import json
import os
import subprocess
import sys
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from otoe.capabilities import (
    backend_capability_profile,
    load_backend_capability_profile,
)
from otoe.render_ir import (
    RenderTree,
    load_render_tree_artifact as _load_render_tree_artifact,
)


@dataclass(frozen=True)
class RenderTreeSource:
    style_artifact: dict[str, Any] | None
    target: Any | None
    render_tree: RenderTree | None
    source: str | None


def warn_backend_coverage_compat(flag: str) -> None:
    print(
        "backend-candidate-skeleton: "
        f"{flag} is compatibility-only; prefer python -m otoe "
        "backend-profile/backend-coverage for coverage workflows.",
        file=sys.stderr,
    )


def emit_contract_payload(
    payload: dict[str, Any],
    *,
    output_path: str | None,
) -> None:
    encoded = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if output_path is None:
        print(encoded, end="")
        return
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(encoded, encoding="utf-8")
    print(f"contract artifact: {path}")


def load_style_artifact(path: str) -> dict[str, Any]:
    return load_json_object(path, label="style artifact")


def load_render_tree_artifact(path: str) -> RenderTree:
    return _load_render_tree_artifact(path)


def load_json_object(path: str, *, label: str) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected {label} {path!r} to contain a JSON object.")
    return payload


def style_artifact_from_args(args: argparse.Namespace) -> dict[str, Any] | None:
    if args.bundle is not None:
        return load_style_artifact_from_bundle(args.bundle)
    if args.style_artifact is not None:
        return load_style_artifact(args.style_artifact)
    return None


def render_tree_source_from_args(
    args: argparse.Namespace,
    *,
    loaded_style_artifact: dict[str, Any] | None = None,
) -> RenderTreeSource:
    if args.render_tree_artifact is not None:
        style_artifact = (
            loaded_style_artifact
            if loaded_style_artifact is not None
            else style_artifact_from_args(args)
        )
        artifact_path = Path(args.render_tree_artifact)
        return RenderTreeSource(
            style_artifact=style_artifact,
            target=None,
            render_tree=load_render_tree_artifact(args.render_tree_artifact),
            source=f"render-tree-artifact:{artifact_path.name}",
        )
    if args.bundle is not None:
        bundle_dir = Path(args.bundle).resolve()
        style_artifact = (
            loaded_style_artifact
            if loaded_style_artifact is not None
            else load_style_artifact_from_bundle(str(bundle_dir))
        )
        return RenderTreeSource(
            style_artifact=style_artifact,
            target=load_target_from_bundle(bundle_dir),
            render_tree=None,
            source=f"bundle:{bundle_dir.name}",
        )
    if args.style_artifact is not None:
        style_artifact = (
            loaded_style_artifact
            if loaded_style_artifact is not None
            else load_style_artifact(args.style_artifact)
        )
        return RenderTreeSource(
            style_artifact=style_artifact,
            target=None,
            render_tree=None,
            source=f"style-artifact:{Path(args.style_artifact).name}",
        )
    return RenderTreeSource(
        style_artifact=None,
        target=None,
        render_tree=None,
        source=None,
    )


def coverage_declaration_from_args(args: argparse.Namespace) -> dict[str, Any]:
    if args.coverage_declaration is not None:
        return load_json_object(
            args.coverage_declaration,
            label="coverage declaration",
        )
    return coverage_declaration_from_backend_args(args)


def coverage_declaration_from_backend_args(
    args: argparse.Namespace,
) -> dict[str, Any]:
    if args.backend_capability_profile is not None:
        profile = load_backend_capability_profile(args.backend_capability_profile)
    else:
        profile = backend_capability_profile(args.backend_capability)
    return profile.coverage_declaration()


def load_style_artifact_from_bundle(bundle: str) -> dict[str, Any]:
    bundle_dir = Path(bundle).resolve()
    if not bundle_dir.is_dir():
        raise ValueError(f"Bundle {str(bundle_dir)!r} is not a directory.")
    manifest_path = bundle_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise ValueError(f"Expected {str(manifest_path)!r} to contain a JSON object.")

    verify_bundle_runner(bundle_dir)
    styles_relative = manifest.get("styles", "otoe-styles.json")
    if not isinstance(styles_relative, str):
        raise ValueError("Bundle manifest field 'styles' must be a string.")
    styles_path = bundle_relative_path(bundle_dir, styles_relative)
    return load_style_artifact(str(styles_path))


def load_target_from_bundle(bundle_dir: Path) -> Any:
    manifest = load_json_object(str(bundle_dir / "manifest.json"), label="bundle manifest")
    target = manifest.get("target")
    if not isinstance(target, str) or ":" not in target:
        raise ValueError("bundle manifest target must use MODULE:OBJECT syntax")
    module_name, object_path = target.split(":", 1)
    if not module_name or not object_path:
        raise ValueError("bundle manifest target must use MODULE:OBJECT syntax")
    with bundle_pythonpath(bundle_dir):
        previous_module = sys.modules.pop(module_name, None)
        try:
            value = importlib.import_module(module_name)
            for part in object_path.split("."):
                value = getattr(value, part)
            return value
        except Exception as exc:
            raise ValueError(f"could not load bundle target {target!r}") from exc
        finally:
            if previous_module is not None:
                sys.modules[module_name] = previous_module


@contextmanager
def bundle_pythonpath(bundle_dir: Path):
    entries = [str(bundle_dir / "app"), str(bundle_dir / "framework")]
    for entry in reversed(entries):
        sys.path.insert(0, entry)
    try:
        yield
    finally:
        for entry in entries:
            try:
                sys.path.remove(entry)
            except ValueError:
                pass


def verify_bundle_runner(bundle_dir: Path) -> None:
    runner = bundle_dir / "otoe-run.py"
    if not runner.is_file():
        raise ValueError(f"Bundle is missing {runner.name}.")
    result = subprocess.run(
        [sys.executable, str(runner), "--verify"],
        capture_output=True,
        cwd=bundle_dir,
        env={**os.environ, "PYTHONPATH": ""},
        text=True,
    )
    if result.returncode == 0:
        return
    details = result.stderr.strip() or result.stdout.strip()
    if not details:
        details = f"runner exited with status {result.returncode}"
    raise ValueError(f"Bundle verification failed: {details}")


def bundle_relative_path(bundle_dir: Path, relative: str) -> Path:
    if relative in {"", "."}:
        raise ValueError(f"Bundle path {relative!r} is not safe.")
    path = Path(relative)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError(f"Bundle path {relative!r} is not safe.")
    return bundle_dir / path
