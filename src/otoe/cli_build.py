from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

from .build import (
    BACKEND_COVERAGE_ARTIFACT_FILENAME,
    BUILD_MANIFEST_FILENAME,
    DEPS_ARTIFACT_FILENAME,
    PATH0_EXTERNAL_BACKEND_ARTIFACT_FILENAME,
    PLAN_ARTIFACT_FILENAME,
    RENDER_TREE_ARTIFACT_FILENAME,
    RUNNER_FILENAME,
    STYLE_ARTIFACT_FILENAME,
    BuildError,
    build_manifest,
    bundle_artifact,
    copy_assets,
    copy_backend_package_artifacts,
    copy_framework_files,
    copy_native_text_font,
    copy_runtime_files,
    write_runner,
)
from .bundle_backend_package import run_backend_package_render_tree_report
from .cli_common import CliError, write_json_artifact
from .cli_plan import resolve_plan_request_details
from .deps import audit_deps, deps_to_dict
from .plan import PlanError
from .plan_artifacts import compiled_styles_to_dict
from .render_ir import render_tree_from_target, render_tree_to_dict
from .runtime_files import RuntimeFileError, build_runtime_files
from .style import resolved_style_map_from_style_ops_artifact


def run_build(args: argparse.Namespace) -> int:
    try:
        resolved = resolve_plan_request_details(args)
        profile_config = resolved.profile_config
        plan = resolved.plan
        plan_dict = resolved.plan_dict
        stylesheet = resolved.stylesheet
        backend_coverage = resolved.backend_coverage
        output = Path(args.out)
        output.mkdir(parents=True, exist_ok=True)
        plan_path = output / PLAN_ARTIFACT_FILENAME
        write_json_artifact(plan_path, plan_dict)
        if plan.has_errors:
            raise BuildError("plan invalid; refusing to write build manifest")
        backend_coverage_path = None
        if backend_coverage is not None:
            backend_coverage_path = output / BACKEND_COVERAGE_ARTIFACT_FILENAME
            write_json_artifact(backend_coverage_path, backend_coverage)
            if backend_coverage.get("passed") is not True:
                raise BuildError(
                    "backend coverage invalid; refusing to write build manifest"
                )
        deps_audit = audit_deps(target=args.target, profile_config=profile_config)
        deps_dict = deps_to_dict(deps_audit)
        deps_path = output / DEPS_ARTIFACT_FILENAME
        write_json_artifact(deps_path, deps_dict)
        if deps_audit.has_errors:
            raise BuildError(
                "dependency audit invalid; refusing to write build manifest"
            )
        style_path = output / STYLE_ARTIFACT_FILENAME
        style_artifact = compiled_styles_to_dict(
            plan,
            target=args.target,
            stylesheet=stylesheet,
        )
        write_json_artifact(style_path, style_artifact)
        render_tree_path = output / RENDER_TREE_ARTIFACT_FILENAME
        render_tree_artifact = render_tree_to_dict(
            render_tree_from_target(
                resolved.mounted,
                style_map=resolved_style_map_from_style_ops_artifact(style_artifact),
            )
        )
        write_json_artifact(render_tree_path, render_tree_artifact)
        artifact_manifest = [
            bundle_artifact(plan_path, output_dir=output),
            bundle_artifact(deps_path, output_dir=output),
            bundle_artifact(style_path, output_dir=output),
            bundle_artifact(render_tree_path, output_dir=output),
        ]
        if backend_coverage_path is not None:
            artifact_manifest.append(
                bundle_artifact(backend_coverage_path, output_dir=output)
            )
        backend_package_artifacts = copy_backend_package_artifacts(
            profile_config,
            output_dir=output,
        )
        backend_package_manifest = None
        if backend_package_artifacts is not None:
            backend_package_manifest = backend_package_artifacts.summary
            artifact_manifest.extend(backend_package_artifacts.artifacts)
        external_backend_report = None
        external_backend_report_path = None
        if backend_package_manifest is not None:
            external_backend_report = run_backend_package_render_tree_report(
                {
                    "backendPackage": backend_package_manifest,
                    "renderTree": RENDER_TREE_ARTIFACT_FILENAME,
                    "styles": STYLE_ARTIFACT_FILENAME,
                    "artifacts": artifact_manifest,
                },
                root=output,
                executable=sys.executable,
            )
            assert external_backend_report is not None
            external_backend_report_path = (
                output / PATH0_EXTERNAL_BACKEND_ARTIFACT_FILENAME
            )
            write_json_artifact(external_backend_report_path, external_backend_report)
            artifact_manifest.append(
                bundle_artifact(external_backend_report_path, output_dir=output)
            )
        framework_file_manifest = copy_framework_files(
            profile_config,
            output_dir=output,
        )
        native_text_manifest = copy_native_text_font(
            profile_config,
            output_dir=output,
        )
        asset_manifest = copy_assets(profile_config.assets, output_dir=output)
        runtime_file_manifest = copy_runtime_files(
            build_runtime_files(args.target, profile_config.runtime_files),
            output_dir=output,
        )
        runner_manifest = write_runner(output_dir=output)
        manifest = build_manifest(
            target=args.target,
            plan=plan_dict,
            deps=deps_dict,
            profile_config=profile_config,
            assets=asset_manifest,
            artifacts=artifact_manifest,
            backend_coverage=backend_coverage,
            backend_package=backend_package_manifest,
            external_backend_report=external_backend_report,
            framework_files=framework_file_manifest,
            native_text=native_text_manifest,
            runner=runner_manifest,
            runtime_files=runtime_file_manifest,
        )
        manifest_path = output / BUILD_MANIFEST_FILENAME
        write_json_artifact(manifest_path, manifest)
        if args.validate:
            validate_build_runner(output)
    except (BuildError, CliError, PlanError, RuntimeFileError) as exc:
        print(f"build: {exc}", file=sys.stderr)
        return 1

    print(f"build {args.target}: {output}")
    print(f"plan artifact: {plan_path}")
    if backend_coverage_path is not None:
        print(f"backend coverage artifact: {backend_coverage_path}")
    if backend_package_manifest is not None:
        print(f"backend package: {backend_package_manifest['path']}")
    if external_backend_report_path is not None:
        print(f"external backend artifact: {external_backend_report_path}")
    print(f"deps artifact: {deps_path}")
    print(f"styles artifact: {style_path}")
    print(f"render tree artifact: {render_tree_path}")
    print(f"manifest: {manifest_path}")
    if args.validate:
        print("validation: ok")
    return 0


def validate_build_runner(output: Path) -> None:
    run_build_runner(output, "--verify", label="verification")
    run_build_runner(output, "--check", label="validation")
    run_build_runner(output, "--layout-check", label="layout validation")


def run_build_runner(output: Path, mode: str, *, label: str) -> None:
    command = [sys.executable, str((output / RUNNER_FILENAME).resolve()), mode]
    result = subprocess.run(
        command,
        capture_output=True,
        cwd=output,
        env={**os.environ, "PYTHONPATH": ""},
        text=True,
    )
    if result.returncode == 0:
        return
    details = result.stderr.strip() or result.stdout.strip()
    if not details:
        details = f"runner exited with status {result.returncode}"
    raise BuildError(f"runner {label} failed: {details}")
