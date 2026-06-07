from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from otoe.backend_evidence_path0_semantics import path0_output_semantic_validation
from otoe.render_ir import RenderTree, render_tree_to_dict


EXTERNAL_PATH0_BACKEND = "path0-external-json-backend"


def run_external_path0_backend_evidence(
    render_tree: RenderTree,
    *,
    style_artifact: dict[str, Any] | None,
    source: str,
) -> dict[str, Any]:
    errors: list[str] = []
    contract: dict[str, Any] = {}
    process = {
        "mode": "subprocess",
        "entrypoint": "examples/native/path0_external_backend.py",
        "exitCode": None,
    }
    with tempfile.TemporaryDirectory(prefix="otoe-path0-external-") as temp_dir:
        temp = Path(temp_dir)
        render_tree_path = temp / "render-tree.json"
        styles_path = temp / "otoe-styles.json"
        layout_path = temp / "path0-layout-output.json"
        paint_path = temp / "path0-paint-output.json"
        contract_path = temp / "path0-external-report.json"
        render_tree_path.write_text(
            json.dumps(render_tree_to_dict(render_tree), sort_keys=True),
            encoding="utf-8",
        )
        args = [
            sys.executable,
            str(Path(__file__).with_name("path0_external_backend.py")),
            "--render-tree",
            str(render_tree_path),
            "--layout-out",
            str(layout_path),
            "--paint-out",
            str(paint_path),
            "--contract-out",
            str(contract_path),
            "--source",
            source,
        ]
        if style_artifact is not None:
            styles_path.write_text(
                json.dumps(style_artifact, sort_keys=True),
                encoding="utf-8",
            )
            args.extend(["--styles", str(styles_path)])
        result = subprocess.run(
            args,
            capture_output=True,
            cwd=temp,
            env={**os.environ, "PYTHONPATH": ""},
            text=True,
        )
        process["exitCode"] = result.returncode
        if result.returncode != 0:
            details = result.stderr.strip() or result.stdout.strip()
            errors.append(
                "external Path0 backend subprocess failed"
                + (f": {details}" if details else "")
            )
        else:
            try:
                contract = json.loads(contract_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                errors.append(f"external Path0 backend report could not be read: {exc}")
    output = contract.get("output") if isinstance(contract, dict) else None
    semantic_validation = path0_output_semantic_validation(output)
    if semantic_validation["errors"]:
        errors.extend(
            f"external Path0 backend output: {message}"
            for message in semantic_validation["errors"]
        )
    return {
        "schemaVersion": 1,
        "format": "path0-external-backend-evidence",
        "passed": not errors,
        "backend": (
            contract.get("backend")
            if isinstance(contract.get("backend"), str)
            else EXTERNAL_PATH0_BACKEND
        ),
        "source": source,
        "process": process,
        "input": contract.get("input", {}),
        "output": output if isinstance(output, dict) else {},
        "semanticValidation": semantic_validation,
        "errors": errors,
    }
