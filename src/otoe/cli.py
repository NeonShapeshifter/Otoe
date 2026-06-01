from __future__ import annotations

import argparse
import ast
import compileall
import importlib
import json
import os
import subprocess
import sys
from collections.abc import Callable, Sequence
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from typing import Any

from .build import (
    BUILD_MANIFEST_FILENAME,
    DEPS_ARTIFACT_FILENAME,
    PLAN_ARTIFACT_FILENAME,
    RUNNER_FILENAME,
    STYLE_ARTIFACT_FILENAME,
    BuildError,
    build_manifest,
    bundle_artifact,
    copy_assets,
    copy_framework_files,
    copy_runtime_files,
    write_runner,
)
from .deps import audit_deps, deps_to_dict, format_deps
from .html import render_html
from .live_server import LivePreviewApp, LivePreviewConfig, run_live_preview
from .mount import MountedNode, mount
from .native import render_native_png
from .node import Node
from .pack import PackError, pack_bundle
from .plan import (
    PlanError,
    compiled_styles_to_dict,
    format_plan,
    plan_mounted,
    plan_to_dict,
)
from .profile import (
    DEFAULT_PROFILE_FILENAME,
    PlanProfileConfig,
    ProfileError,
    ProfileRuntimeFile,
    load_plan_profile,
)
from .style import StyleError, StyleSheet, css
from .utilities import utility_stylesheet

DEFAULT_CHECK_PATHS = ("src", "examples", "tests")


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="otoe")
    subcommands = parser.add_subparsers(dest="command", required=True)

    check = subcommands.add_parser("check", help="run local Otoe health checks")
    check.add_argument(
        "--path",
        action="append",
        dest="paths",
        help="path to compile; may be passed more than once",
    )
    check.add_argument(
        "--tests",
        action="store_true",
        help="also run pytest after compile checks",
    )
    check.add_argument(
        "--pytest-arg",
        action="append",
        default=[],
        help="extra argument passed to pytest; may be passed more than once",
    )
    check.add_argument(
        "pytest_args",
        nargs=argparse.REMAINDER,
        help="pytest arguments after --",
    )
    check.set_defaults(func=_check)

    render = subcommands.add_parser("render", help="render an Otoe target")
    render.add_argument("target", help="import target in MODULE:OBJECT form")
    render.add_argument("--out", required=True, help="output HTML path")
    render.add_argument("--pretty", action="store_true", help="pretty-print HTML")
    render.add_argument("--indent", type=int, default=0, help="base HTML indent")
    render.add_argument(
        "--css",
        help="optional Otoe CSS file to apply inline during render",
    )
    render.add_argument(
        "--no-strict-styles",
        action="store_false",
        default=True,
        dest="strict_styles",
        help="ignore class names missing from --css",
    )
    render.add_argument(
        "--native",
        action="store_true",
        help="render a native PNG frame",
    )
    render.add_argument(
        "--background",
        default="#ffffff",
        help="native PNG background",
    )
    render.set_defaults(func=_render)

    plan = subcommands.add_parser(
        "plan",
        help="diagnose an Otoe target for an offline deployment profile",
    )
    plan.add_argument("target", help="import target in MODULE:OBJECT form")
    plan.add_argument(
        "--profile",
        default=None,
        choices=["cage"],
        help="offline target profile to diagnose",
    )
    plan.add_argument(
        "--profile-file",
        help="optional TOML profile file; defaults to otoe.profile.toml when present",
    )
    plan.add_argument(
        "--css",
        action="append",
        help="optional Otoe CSS file to include in the style plan",
    )
    utilities = plan.add_mutually_exclusive_group()
    utilities.add_argument(
        "--utilities",
        action="store_true",
        default=None,
        help="include Otoe's built-in utility stylesheet",
    )
    utilities.add_argument(
        "--no-utilities",
        action="store_false",
        dest="utilities",
        help="disable built-in utilities even when a profile file enables them",
    )
    plan.add_argument(
        "--no-strict-styles",
        action="store_false",
        default=True,
        dest="strict_styles",
        help="treat missing class rules as html-only warnings",
    )
    plan.add_argument(
        "--json",
        action="store_true",
        help="write the plan report as JSON to stdout",
    )
    plan.add_argument(
        "--out",
        help="optional path to write the JSON plan artifact",
    )
    plan.set_defaults(func=_plan)

    build = subcommands.add_parser(
        "build",
        help="write a minimal offline bundle manifest for an Otoe target",
    )
    build.add_argument("target", help="import target in MODULE:OBJECT form")
    build.add_argument(
        "--out",
        required=True,
        help="output bundle directory",
    )
    build.add_argument(
        "--profile",
        default=None,
        choices=["cage"],
        help="offline target profile to build",
    )
    build.add_argument(
        "--profile-file",
        help="optional TOML profile file; defaults to otoe.profile.toml when present",
    )
    build.add_argument(
        "--css",
        action="append",
        help="optional Otoe CSS file to include in the style plan",
    )
    build_utilities = build.add_mutually_exclusive_group()
    build_utilities.add_argument(
        "--utilities",
        action="store_true",
        default=None,
        help="include Otoe's built-in utility stylesheet",
    )
    build_utilities.add_argument(
        "--no-utilities",
        action="store_false",
        dest="utilities",
        help="disable built-in utilities even when a profile file enables them",
    )
    build.add_argument(
        "--no-strict-styles",
        action="store_false",
        default=True,
        dest="strict_styles",
        help="treat missing class rules as html-only warnings",
    )
    build.add_argument(
        "--validate",
        action="store_true",
        help="run the generated bundle runner after writing artifacts",
    )
    build.set_defaults(func=_build)

    pack = subcommands.add_parser(
        "pack",
        help="verify and package an offline Otoe bundle",
    )
    pack.add_argument("bundle", help="bundle directory written by otoe build")
    pack.add_argument(
        "--out",
        required=True,
        help="output .tar.gz path",
    )
    pack.set_defaults(func=_pack)

    compare_contract = subcommands.add_parser(
        "compare-contract",
        help="compare two JSON contract artifacts",
    )
    compare_contract.add_argument("expected", help="expected JSON contract path")
    compare_contract.add_argument("actual", help="actual JSON contract path")
    compare_contract.add_argument(
        "--json",
        action="store_true",
        help="write the comparison report as JSON to stdout",
    )
    compare_contract.add_argument(
        "--max-diffs",
        type=int,
        default=20,
        help="maximum differences to print or include in the report",
    )
    compare_contract.add_argument(
        "--ignore-path",
        action="append",
        default=[],
        help="JSON pointer path to ignore; may be passed more than once",
    )
    compare_contract.set_defaults(func=_compare_contract)

    deps = subcommands.add_parser(
        "deps",
        help="audit profile dependencies without installing anything",
    )
    deps.add_argument("target", help="import target label in MODULE:OBJECT form")
    deps.add_argument(
        "--profile",
        default=None,
        choices=["cage"],
        help="offline target profile to audit",
    )
    deps.add_argument(
        "--profile-file",
        help="optional TOML profile file; defaults to otoe.profile.toml when present",
    )
    deps.add_argument(
        "--json",
        action="store_true",
        help="write the dependency audit as JSON to stdout",
    )
    deps.set_defaults(func=_deps)

    dev = subcommands.add_parser("dev", help="run a local live preview app")
    dev.add_argument("target", help="app target in MODULE:APP form")
    dev.add_argument("--host", default="127.0.0.1")
    dev.add_argument("--port", default=8767, type=int)
    dev.add_argument("--title", default="Otoe Dev")
    dev.add_argument("--css", help="optional CSS file to serve")
    dev.add_argument("--css-route", default="/otoe.css")
    dev.add_argument("--root-class", default="", help="class added to the live root")
    dev.set_defaults(func=_dev)

    new = subcommands.add_parser("new", help="scaffold a small Otoe app")
    new.add_argument("path", help="directory to create or populate")
    new.add_argument(
        "--name",
        help="display name for the generated app; defaults to the directory name",
    )
    new.add_argument(
        "--force",
        action="store_true",
        help="overwrite existing scaffold files",
    )
    new.add_argument(
        "--no-css",
        action="store_true",
        help="skip writing styles.css",
    )
    new.set_defaults(func=_new)

    return parser


def _check(args: argparse.Namespace) -> int:
    paths = tuple(args.paths or DEFAULT_CHECK_PATHS)
    ok = True
    for path in paths:
        ok = _compile_path(path) and ok
    if not ok:
        return 1
    if args.tests:
        command = [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            *args.pytest_arg,
            *_pytest_args(args.pytest_args),
        ]
        print(f"pytest: {' '.join(command)}")
        return subprocess.run(command).returncode
    return 0


def _compile_path(path: str) -> bool:
    target = Path(path)
    if not target.exists():
        print(f"compile {path}: missing", file=sys.stderr)
        return False
    if target.is_dir():
        ok = compileall.compile_dir(str(target), quiet=1)
    else:
        ok = compileall.compile_file(str(target), quiet=1)
    print(f"compile {path}: {'ok' if ok else 'failed'}")
    return bool(ok)


def _pytest_args(args: list[str]) -> list[str]:
    if args and args[0] == "--":
        return args[1:]
    return args


def _render(args: argparse.Namespace) -> int:
    try:
        target = _load_target(args.target)
        mounted = _coerce_render_target(target)
        stylesheet = _load_stylesheet(args.css)
    except CliError as exc:
        print(f"render: {exc}", file=sys.stderr)
        return 1

    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        if args.native:
            render_native_png(
                mounted,
                output,
                stylesheet=stylesheet,
                strict_styles=args.strict_styles,
                background=args.background,
            )
            print(f"render native {args.target}: {output}")
            return 0

        output.write_text(
            render_html(
                mounted,
                pretty=args.pretty,
                indent=args.indent,
                stylesheet=stylesheet,
                strict_styles=args.strict_styles,
            ),
            encoding="utf-8",
        )
    except (StyleError, ValueError) as exc:
        print(f"render: {exc}", file=sys.stderr)
        return 1
    print(f"render {args.target}: {output}")
    return 0


def _plan(args: argparse.Namespace) -> int:
    try:
        _, plan, plan_dict, _ = _resolve_plan_request(args)
        if args.out:
            _write_json_artifact(Path(args.out), plan_dict)
    except (CliError, PlanError) as exc:
        print(f"plan: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(plan_dict, indent=2, sort_keys=True))
    else:
        print(format_plan(plan, target=args.target))
        if args.out:
            print(f"plan artifact: {Path(args.out)}")
    return 1 if plan.has_errors else 0


def _build(args: argparse.Namespace) -> int:
    try:
        profile_config, plan, plan_dict, stylesheet = _resolve_plan_request(args)
        output = Path(args.out)
        output.mkdir(parents=True, exist_ok=True)
        plan_path = output / PLAN_ARTIFACT_FILENAME
        _write_json_artifact(plan_path, plan_dict)
        if plan.has_errors:
            raise BuildError("plan invalid; refusing to write build manifest")
        deps_audit = audit_deps(target=args.target, profile_config=profile_config)
        deps_dict = deps_to_dict(deps_audit)
        deps_path = output / DEPS_ARTIFACT_FILENAME
        _write_json_artifact(deps_path, deps_dict)
        if deps_audit.has_errors:
            raise BuildError(
                "dependency audit invalid; refusing to write build manifest"
            )
        style_path = output / STYLE_ARTIFACT_FILENAME
        _write_json_artifact(
            style_path,
            compiled_styles_to_dict(
                plan,
                target=args.target,
                stylesheet=stylesheet,
            ),
        )
        artifact_manifest = [
            bundle_artifact(plan_path, output_dir=output),
            bundle_artifact(deps_path, output_dir=output),
            bundle_artifact(style_path, output_dir=output),
        ]
        framework_file_manifest = copy_framework_files(
            profile_config,
            output_dir=output,
        )
        asset_manifest = copy_assets(profile_config.assets, output_dir=output)
        runtime_file_manifest = copy_runtime_files(
            _build_runtime_files(args.target, profile_config),
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
            framework_files=framework_file_manifest,
            runner=runner_manifest,
            runtime_files=runtime_file_manifest,
        )
        manifest_path = output / BUILD_MANIFEST_FILENAME
        _write_json_artifact(manifest_path, manifest)
        if args.validate:
            _validate_build_runner(output)
    except (BuildError, CliError, PlanError) as exc:
        print(f"build: {exc}", file=sys.stderr)
        return 1

    print(f"build {args.target}: {output}")
    print(f"plan artifact: {plan_path}")
    print(f"deps artifact: {deps_path}")
    print(f"styles artifact: {style_path}")
    print(f"manifest: {manifest_path}")
    if args.validate:
        print("validation: ok")
    return 0


def _pack(args: argparse.Namespace) -> int:
    try:
        result = pack_bundle(Path(args.bundle), Path(args.out))
    except PackError as exc:
        print(f"pack: {exc}", file=sys.stderr)
        return 1

    print(f"pack {Path(args.bundle)}: {Path(args.out)}")
    print(f"files: {result.files}")
    print(f"size: {result.size}")
    print(f"sha256: {result.sha256}")
    return 0


def _compare_contract(args: argparse.Namespace) -> int:
    try:
        expected = _load_json_artifact(Path(args.expected), label="expected")
        actual = _load_json_artifact(Path(args.actual), label="actual")
        ignored_paths = tuple(args.ignore_path or ())
        if ignored_paths:
            expected = deepcopy(expected)
            actual = deepcopy(actual)
            for pointer in ignored_paths:
                _delete_json_pointer(expected, pointer)
                _delete_json_pointer(actual, pointer)
    except CliError as exc:
        print(f"compare-contract: {exc}", file=sys.stderr)
        return 1

    differences = _compare_json_contracts(expected, actual)
    max_diffs = max(args.max_diffs, 0)
    shown_differences = differences[:max_diffs]
    report = {
        "schemaVersion": 1,
        "expected": str(Path(args.expected)),
        "actual": str(Path(args.actual)),
        "matched": not differences,
        "differenceCount": len(differences),
        "differences": shown_differences,
        "ignoredPaths": list(ignored_paths),
        "truncated": len(shown_differences) < len(differences),
    }

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    elif not differences:
        print(f"contracts match: {Path(args.expected)} == {Path(args.actual)}")
    else:
        print(
            f"contracts differ: {len(differences)} difference(s) between "
            f"{Path(args.expected)} and {Path(args.actual)}"
        )
        for difference in shown_differences:
            print(_format_contract_difference(difference))
        if report["truncated"]:
            print(f"... {len(differences) - len(shown_differences)} more difference(s)")

    return 0 if not differences else 1


def _validate_build_runner(output: Path) -> None:
    _run_build_runner(output, "--verify", label="verification")
    _run_build_runner(output, "--check", label="validation")
    _run_build_runner(output, "--layout-check", label="layout validation")


def _run_build_runner(output: Path, mode: str, *, label: str) -> None:
    command = [sys.executable, str(output / RUNNER_FILENAME), mode]
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


def _build_runtime_files(
    target: str,
    profile_config: PlanProfileConfig,
) -> tuple[ProfileRuntimeFile, ...]:
    files = [*_auto_target_runtime_files(target), *profile_config.runtime_files]
    deduped: list[ProfileRuntimeFile] = []
    seen = set()
    for file in files:
        key = file.relative_path.as_posix()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(file)
    return tuple(deduped)


def _auto_target_runtime_files(target: str) -> tuple[ProfileRuntimeFile, ...]:
    module_name, _ = _parse_target_spec(target)
    if "." in module_name:
        return ()
    module = sys.modules.get(module_name)
    source = getattr(module, "__file__", None)
    if source is None:
        return ()
    path = Path(source)
    if path.suffix != ".py" or path.name != f"{module_name}.py":
        return ()
    if not path.is_file():
        return ()
    return tuple(_local_runtime_files(path, seen=set()))


def _local_runtime_files(
    path: Path,
    *,
    seen: set[Path],
) -> list[ProfileRuntimeFile]:
    resolved = path.resolve()
    if resolved in seen:
        return []
    seen.add(resolved)

    files = [ProfileRuntimeFile(source=path, relative_path=Path(path.name))]
    for candidate in _local_import_files(path):
        files.extend(_local_runtime_files(candidate, seen=seen))
    return files


def _local_import_files(path: Path) -> list[Path]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError as exc:
        raise BuildError(f"could not parse runtime module {str(path)!r}: {exc}") from exc

    imports: list[Path] = []
    for name in _local_import_module_names(tree):
        candidate = path.parent / f"{name}.py"
        if candidate.is_file():
            imports.append(candidate)
    return imports


def _local_import_module_names(tree: ast.AST) -> tuple[str, ...]:
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if "." not in alias.name:
                    names.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0 and node.module and "." not in node.module:
                names.append(node.module)
    return tuple(dict.fromkeys(names))


def _deps(args: argparse.Namespace) -> int:
    try:
        _parse_target_spec(args.target)
        profile_config = _load_plan_profile_config(args.profile_file)
        if args.profile is not None:
            profile_config = replace(profile_config, profile=args.profile)
        audit = audit_deps(target=args.target, profile_config=profile_config)
    except CliError as exc:
        print(f"deps: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(deps_to_dict(audit), indent=2, sort_keys=True))
    else:
        print(format_deps(audit))
    return 1 if audit.has_errors else 0


def _dev(args: argparse.Namespace) -> int:
    try:
        target = _load_target(args.target)
        app_factory = _coerce_dev_app_factory(target)
        css_path = _dev_css_path(args.css)
    except CliError as exc:
        print(f"dev: {exc}", file=sys.stderr)
        return 1

    config = LivePreviewConfig(
        title=args.title,
        css_route=args.css_route,
        css_path=css_path,
        root_class=args.root_class,
    )
    try:
        run_live_preview(
            app_factory=app_factory,
            config=config,
            host=args.host,
            port=args.port,
            label="Otoe dev",
        )
    except CliError as exc:
        print(f"dev: {exc}", file=sys.stderr)
        return 1
    return 0


def _new(args: argparse.Namespace) -> int:
    target = Path(args.path)
    app_name = args.name or _display_name_from_path(target)
    try:
        target.mkdir(parents=True, exist_ok=True)
        _write_scaffold_file(
            target / "app.py",
            _app_template(app_name),
            force=args.force,
        )
        _write_scaffold_file(
            target / "README.md",
            _readme_template(app_name, include_css=not args.no_css),
            force=args.force,
        )
        if not args.no_css:
            _write_scaffold_file(
                target / "styles.css",
                _css_template(),
                force=args.force,
            )
    except CliError as exc:
        print(f"new: {exc}", file=sys.stderr)
        return 1
    print(f"new {app_name}: {target}")
    return 0


def _load_target(spec: str) -> Any:
    module_name, object_path = _parse_target_spec(spec)
    try:
        value = importlib.import_module(module_name)
    except Exception as exc:
        raise CliError(f"could not import module {module_name!r}") from exc
    for part in object_path.split("."):
        try:
            value = getattr(value, part)
        except AttributeError as exc:
            raise CliError(f"{spec!r} could not resolve attribute {part!r}") from exc
    return value


def _parse_target_spec(spec: str) -> tuple[str, str]:
    module_name, separator, object_path = spec.partition(":")
    if not separator or not module_name or not object_path:
        raise CliError("target must use MODULE:OBJECT syntax")
    return module_name, object_path


def _load_stylesheet(path: str | Path | None) -> StyleSheet | None:
    if path is None:
        return None
    source = Path(path)
    if not source.exists():
        raise CliError(f"css file {path!r} does not exist")
    try:
        return css(source.read_text(encoding="utf-8"))
    except StyleError as exc:
        raise CliError(f"css file {path!r}: {exc}") from exc


def _load_plan_profile_config(path: str | None) -> PlanProfileConfig:
    profile_path = Path(path) if path is not None else Path(DEFAULT_PROFILE_FILENAME)
    if not profile_path.exists():
        if path is not None:
            raise CliError(f"profile file {path!r} does not exist")
        return PlanProfileConfig()
    try:
        return load_plan_profile(profile_path)
    except ProfileError as exc:
        raise CliError(str(exc)) from exc


def _resolve_plan_request(
    args: argparse.Namespace,
) -> tuple[PlanProfileConfig, Any, dict[str, Any], StyleSheet | None]:
    target = _load_target(args.target)
    mounted = _coerce_render_target(target)
    profile_config = _load_plan_profile_config(args.profile_file)
    if args.profile is not None:
        profile_config = replace(profile_config, profile=args.profile)
    include_utilities = profile_config.utilities if args.utilities is None else args.utilities
    css_paths = tuple(args.css or profile_config.css_paths)
    stylesheet = _load_plan_stylesheet(
        css_paths,
        include_utilities=include_utilities,
    )
    plan = plan_mounted(
        mounted,
        profile=profile_config.profile,
        stylesheet=stylesheet,
        safelist=profile_config.style_safelist,
        strict_styles=args.strict_styles,
    )
    return profile_config, plan, plan_to_dict(plan, target=args.target), stylesheet


def _load_plan_stylesheet(
    paths: Sequence[str | Path],
    *,
    include_utilities: bool,
) -> StyleSheet | None:
    stylesheets: list[StyleSheet] = []
    if include_utilities:
        stylesheets.append(utility_stylesheet())
    for path in paths:
        stylesheet = _load_stylesheet(path)
        if stylesheet is not None:
            stylesheets.append(stylesheet)
    if not stylesheets:
        return None
    return _merge_stylesheets(stylesheets)


def _merge_stylesheets(stylesheets: list[StyleSheet]) -> StyleSheet:
    rules = {}
    tokens = {}
    for stylesheet in stylesheets:
        rules.update(stylesheet.rules)
        tokens.update(stylesheet.tokens)
    return StyleSheet(rules=rules, tokens=tokens)


def _write_json_artifact(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _load_json_artifact(path: Path, *, label: str) -> Any:
    if not path.exists():
        raise CliError(f"{label} file {str(path)!r} does not exist")
    if not path.is_file():
        raise CliError(f"{label} path {str(path)!r} is not a file")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise CliError(f"{label} file {str(path)!r} is not valid JSON: {exc}") from exc


def _compare_json_contracts(expected: Any, actual: Any) -> list[dict[str, Any]]:
    differences: list[dict[str, Any]] = []
    _collect_json_contract_differences(
        expected,
        actual,
        pointer="",
        differences=differences,
    )
    return differences


def _collect_json_contract_differences(
    expected: Any,
    actual: Any,
    *,
    pointer: str,
    differences: list[dict[str, Any]],
) -> None:
    expected_type = _json_type_name(expected)
    actual_type = _json_type_name(actual)
    if expected_type != actual_type:
        differences.append(
            {
                "path": pointer,
                "kind": "type",
                "expectedType": expected_type,
                "actualType": actual_type,
                "expected": _summarize_contract_value(expected),
                "actual": _summarize_contract_value(actual),
            }
        )
        return

    if isinstance(expected, dict):
        expected_keys = set(expected)
        actual_keys = set(actual)
        for key in sorted(expected_keys - actual_keys):
            differences.append(
                {
                    "path": _json_pointer_child(pointer, key),
                    "kind": "missing",
                    "expected": _summarize_contract_value(expected[key]),
                    "actual": None,
                }
            )
        for key in sorted(actual_keys - expected_keys):
            differences.append(
                {
                    "path": _json_pointer_child(pointer, key),
                    "kind": "extra",
                    "expected": None,
                    "actual": _summarize_contract_value(actual[key]),
                }
            )
        for key in sorted(expected_keys & actual_keys):
            _collect_json_contract_differences(
                expected[key],
                actual[key],
                pointer=_json_pointer_child(pointer, key),
                differences=differences,
            )
        return

    if isinstance(expected, list):
        if len(expected) != len(actual):
            differences.append(
                {
                    "path": pointer,
                    "kind": "length",
                    "expected": len(expected),
                    "actual": len(actual),
                }
            )
        for index, (expected_item, actual_item) in enumerate(zip(expected, actual)):
            _collect_json_contract_differences(
                expected_item,
                actual_item,
                pointer=_json_pointer_child(pointer, str(index)),
                differences=differences,
            )
        return

    if expected != actual:
        differences.append(
            {
                "path": pointer,
                "kind": "value",
                "expected": expected,
                "actual": actual,
            }
        )


def _json_type_name(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, dict):
        return "object"
    if isinstance(value, list):
        return "array"
    if isinstance(value, int | float):
        return "number"
    if isinstance(value, str):
        return "string"
    return type(value).__name__


def _json_pointer_child(pointer: str, key: str) -> str:
    escaped = key.replace("~", "~0").replace("/", "~1")
    return f"{pointer}/{escaped}"


def _delete_json_pointer(payload: Any, pointer: str) -> None:
    parts = _parse_json_pointer(pointer)
    current = payload
    for part in parts[:-1]:
        if isinstance(current, dict):
            if part not in current:
                return
            current = current[part]
        elif isinstance(current, list):
            index = _json_pointer_list_index(part)
            if index is None or index >= len(current):
                return
            current = current[index]
        else:
            return

    key = parts[-1]
    if isinstance(current, dict):
        current.pop(key, None)
    elif isinstance(current, list):
        index = _json_pointer_list_index(key)
        if index is not None and index < len(current):
            del current[index]


def _parse_json_pointer(pointer: str) -> tuple[str, ...]:
    if not pointer.startswith("/"):
        raise CliError(f"ignore path must be a JSON pointer starting with '/': {pointer!r}")
    return tuple(_unescape_json_pointer_part(part) for part in pointer.split("/")[1:])


def _unescape_json_pointer_part(part: str) -> str:
    chars: list[str] = []
    index = 0
    while index < len(part):
        char = part[index]
        if char != "~":
            chars.append(char)
            index += 1
            continue
        if index + 1 >= len(part) or part[index + 1] not in {"0", "1"}:
            raise CliError(f"invalid JSON pointer escape in ignore path: {part!r}")
        chars.append("~" if part[index + 1] == "0" else "/")
        index += 2
    return "".join(chars)


def _json_pointer_list_index(part: str) -> int | None:
    if not part.isdigit():
        return None
    return int(part)


def _display_json_pointer(pointer: str) -> str:
    return "$" if not pointer else pointer


def _summarize_contract_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            "type": "object",
            "keys": sorted(str(key) for key in value),
        }
    if isinstance(value, list):
        return {
            "type": "array",
            "length": len(value),
        }
    return value


def _format_contract_difference(difference: dict[str, Any]) -> str:
    path = _display_json_pointer(str(difference["path"]))
    kind = difference["kind"]
    if kind == "missing":
        return f"- {path}: missing in actual; expected {_format_contract_value(difference['expected'])}"
    if kind == "extra":
        return f"- {path}: extra in actual; actual {_format_contract_value(difference['actual'])}"
    if kind == "type":
        return (
            f"- {path}: type {difference['expectedType']} != "
            f"{difference['actualType']}"
        )
    if kind == "length":
        return f"- {path}: length {difference['expected']} != {difference['actual']}"
    return (
        f"- {path}: expected {_format_contract_value(difference['expected'])}, "
        f"actual {_format_contract_value(difference['actual'])}"
    )


def _format_contract_value(value: Any) -> str:
    return json.dumps(value, sort_keys=True)


def _coerce_render_target(target: Any) -> MountedNode:
    if isinstance(target, MountedNode):
        return target
    if isinstance(target, Node):
        return mount(target)
    if callable(target):
        return _coerce_render_target(target())
    raise CliError(
        "render target must be a Node, MountedNode, or zero-argument callable "
        f"returning one; got {type(target).__name__}"
    )


def _coerce_dev_app_factory(target: Any) -> Callable[[], LivePreviewApp]:
    if _is_live_preview_app(target):
        return lambda: target
    if callable(target):
        return lambda: _coerce_dev_app(target())
    return _coerce_dev_app(target)


def _coerce_dev_app(target: Any) -> LivePreviewApp:
    if _is_live_preview_app(target):
        return target
    raise CliError(
        "dev target must expose render_fragment() and dispatch_event(event_id, *args)"
    )


def _is_live_preview_app(target: Any) -> bool:
    if callable(getattr(target, "render_fragment", None)) and callable(
        getattr(target, "dispatch_event", None)
    ):
        return True
    return False


def _dev_css_path(path: str | None) -> Path | None:
    if path is None:
        return None
    css_path = Path(path)
    if not css_path.exists():
        raise CliError(f"css file {path!r} does not exist")
    return css_path


def _write_scaffold_file(path: Path, content: str, *, force: bool) -> None:
    if path.exists() and not force:
        raise CliError(f"{path} already exists; pass --force to overwrite")
    path.write_text(content, encoding="utf-8")


def _display_name_from_path(path: Path) -> str:
    name = path.name.strip().replace("_", " ").replace("-", " ")
    return name.title() if name else "Otoe App"


def _app_template(app_name: str) -> str:
    return (
        "from otoe import Button, Text, VStack, computed, signal\n"
        "\n"
        "\n"
        "count = signal(0)\n"
        "\n"
        "\n"
        "def app():\n"
        f"    title = {app_name!r}\n"
        "    label = computed(lambda: f\"Count: {count.value}\")\n"
        "    return VStack(\n"
        "        Text(title, className=\"title\"),\n"
        "        Text(label),\n"
        "        Button(\"Increment\", onClick=lambda: count.set(count.value + 1)),\n"
        "        className=\"app\",\n"
        "        gap=8,\n"
        "        padding=12,\n"
        "    )\n"
    )


def _readme_template(app_name: str, *, include_css: bool) -> str:
    css_arg = " --css styles.css" if include_css else ""
    return (
        f"# {app_name}\n"
        "\n"
        "Render the app from this directory:\n"
        "\n"
        "```bash\n"
        f"otoe render app:app --out preview.html{css_arg} --pretty\n"
        f"otoe render app:app --out preview.png --native{css_arg}\n"
        "```\n"
    )


def _css_template() -> str:
    return (
        ".app {\n"
        "  padding: 16;\n"
        "  gap: 8;\n"
        "  background: #f8fafc;\n"
        "}\n"
        "\n"
        ".title {\n"
        "  color: #111827;\n"
        "  font-size: 20;\n"
        "}\n"
    )


class CliError(ValueError):
    pass
