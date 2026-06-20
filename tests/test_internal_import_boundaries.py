from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_style_ir_does_not_import_private_helpers_from_plan():
    source = ROOT / "src" / "otoe" / "style_ir.py"
    tree = ast.parse(source.read_text(encoding="utf-8"))

    private_plan_imports = [
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        and node.level == 1
        and node.module == "plan"
        for alias in node.names
        if alias.name.startswith("_")
    ]

    assert private_plan_imports == []
