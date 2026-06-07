from __future__ import annotations

import argparse
import json
import sys
from dataclasses import replace

from .cli_common import CliError, load_plan_profile_config, parse_target_spec
from .deps import audit_deps, deps_to_dict, format_deps
from .runtime_files import RuntimeFileError


def run_deps(args: argparse.Namespace) -> int:
    try:
        parse_target_spec(args.target)
        profile_config = load_plan_profile_config(args.profile_file)
        if args.profile is not None:
            profile_config = replace(profile_config, profile=args.profile)
        audit = audit_deps(target=args.target, profile_config=profile_config)
    except (CliError, RuntimeFileError) as exc:
        print(f"deps: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(deps_to_dict(audit), indent=2, sort_keys=True))
    else:
        print(format_deps(audit))
    return 1 if audit.has_errors else 0
