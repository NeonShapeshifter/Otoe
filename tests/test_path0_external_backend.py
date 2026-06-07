from __future__ import annotations

import ast
import json
import os
import re
import subprocess
import sys
from pathlib import Path

from examples.native.backend_candidate_skeleton import (
    backend_candidate_style_artifact,
    run_render_tree_candidate_acceptance,
)
from examples.native.path0_external_backend import (
    ExternalPath0BackendError,
    run_external_path0_backend,
)
from otoe import render_tree_to_dict
from otoe.backend_evidence_path0_semantics import path0_output_semantic_errors


STRICT_SHA256 = re.compile(r"^sha256:[0-9a-f]{64}$")
REPO_ROOT = Path(__file__).resolve().parents[1]
EXTERNAL_BACKEND = REPO_ROOT / "examples/native/path0_external_backend.py"


def test_path0_external_backend_cli_consumes_render_tree_json_out_of_process(tmp_path):
    artifact = backend_candidate_style_artifact()
    render_tree = run_render_tree_candidate_acceptance(artifact).minimal
    render_tree_path = tmp_path / "render-tree.json"
    styles_path = tmp_path / "otoe-styles.json"
    layout_path = tmp_path / "path0-layout-output.json"
    paint_path = tmp_path / "path0-paint-output.json"
    contract_path = tmp_path / "path0-external-report.json"

    render_tree_path.write_text(
        json.dumps(render_tree_to_dict(render_tree), sort_keys=True),
        encoding="utf-8",
    )
    styles_path.write_text(json.dumps(artifact, sort_keys=True), encoding="utf-8")

    env = {
        **os.environ,
        "PYTHONPATH": f"{REPO_ROOT / 'src'}:{REPO_ROOT}",
    }
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "examples.native.path0_external_backend",
            "--render-tree",
            str(render_tree_path),
            "--styles",
            str(styles_path),
            "--layout-out",
            str(layout_path),
            "--paint-out",
            str(paint_path),
            "--contract-out",
            str(contract_path),
            "--source",
            "pytest:render-tree-artifact",
        ],
        cwd=REPO_ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    layout = json.loads(layout_path.read_text(encoding="utf-8"))
    paint = json.loads(paint_path.read_text(encoding="utf-8"))
    contract = json.loads(contract_path.read_text(encoding="utf-8"))

    assert contract["format"] == "path0-external-backend-report"
    assert contract["backend"] == "path0-external-json-backend"
    assert contract["source"] == "pytest:render-tree-artifact"
    assert contract["input"]["nodeCount"] == render_tree.node_count
    assert STRICT_SHA256.fullmatch(contract["input"]["renderTreeHash"])
    assert contract["input"]["styleOps"]["present"] is True
    assert contract["input"]["styleOps"]["schemaVersion"] == 1
    assert contract["input"]["styleOps"]["format"] == "otoe-style-ops"
    assert STRICT_SHA256.fullmatch(contract["input"]["styleOps"]["artifactHash"])
    assert layout["format"] == "path0-layout-output"
    assert layout["boxCount"] == render_tree.node_count
    assert STRICT_SHA256.fullmatch(layout["outputHash"])
    assert paint["format"] == "path0-paint-output"
    assert paint["commandCount"] > 0
    assert STRICT_SHA256.fullmatch(paint["outputHash"])
    assert contract["output"]["layout"] == layout
    assert contract["output"]["paint"] == paint
    assert path0_output_semantic_errors({"layout": layout, "paint": paint}) == []
    assert {box["name"] for box in layout["boxes"]} >= {"Button", "Input", "Text"}
    assert {command["kind"] for command in paint["commands"]} <= {"rect", "text"}


def test_path0_external_backend_has_no_internal_renderer_imports():
    tree = ast.parse(EXTERNAL_BACKEND.read_text(encoding="utf-8"))
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)

    assert not [name for name in imports if name == "otoe" or name.startswith("otoe.")]
    assert not [
        name
        for name in imports
        if name == "examples.native" or name.startswith("examples.native.")
    ]


def test_path0_external_backend_rejects_unknown_widget_instead_of_fallback():
    payload = {
        "schemaVersion": 1,
        "format": "otoe-render-tree",
        "nodeCount": 1,
        "root": {
            "id": "root:Widget",
            "path": [],
            "name": "TotallyUnknownWidget",
            "widgetId": None,
            "key": None,
            "className": None,
            "props": {},
            "events": [],
            "state": [],
            "context": "TotallyUnknownWidget",
            "style": {},
            "children": [],
        },
    }

    try:
        run_external_path0_backend(payload)
    except ExternalPath0BackendError as exc:
        assert "is not supported by path0-external-json-backend" in str(exc)
    else:  # pragma: no cover - assertion branch
        raise AssertionError("external Path0 backend must reject unknown widgets")
