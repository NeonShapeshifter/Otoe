import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest


pytest.importorskip("mypy")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"


def _run_mypy(path: Path, cache_dir: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["MYPYPATH"] = _prepend_path(env.get("MYPYPATH"), SRC_ROOT)
    env["PYTHONPATH"] = _prepend_path(env.get("PYTHONPATH"), SRC_ROOT)

    return subprocess.run(
        [
            sys.executable,
            "-m",
            "mypy",
            "--strict",
            "--show-error-codes",
            "--hide-error-context",
            "--no-error-summary",
            "--cache-dir",
            str(cache_dir),
            str(path),
        ],
        check=False,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def _prepend_path(current: str | None, path: Path) -> str:
    value = str(path)
    if not current:
        return value
    return os.pathsep.join((value, current))


def _write_sample(path: Path, source: str) -> Path:
    path.write_text(textwrap.dedent(source).strip() + "\n", encoding="utf-8")
    return path


def test_public_typing_accepts_valid_widget_and_ui_usage(tmp_path):
    sample = _write_sample(
        tmp_path / "valid_otoe_app.py",
        """
        from typing import Any

        from otoe import (
            ActionButton,
            Button,
            DataTable,
            HStack,
            NavRoute,
            Node,
            RouteView,
            SidebarNav,
            TableColumn,
            Text,
            VStack,
        )


        rows: list[dict[str, str]] = [{"id": "arcadia", "name": "Arcadia"}]
        columns: list[TableColumn] = [TableColumn("name", "Name")]
        routes: list[NavRoute] = [NavRoute("overview", "Overview")]


        def row_key(row: Any) -> str:
            return str(row["id"])


        def render_cell(row: Any, column: TableColumn) -> Node:
            return Text(row[column.key])


        def navigate(route_id: str) -> None:
            assert route_id


        def render_route(route: NavRoute) -> Node:
            return Text(route.label)


        app: Node = VStack(
            HStack(Text("Otoe"), Button("Run", onClick=lambda: None)),
            ActionButton("Save", onClick=lambda: None),
            DataTable(columns=columns, rows=rows, key=row_key, render_cell=render_cell),
            SidebarNav(routes=routes, active="overview", on_navigate=navigate),
            RouteView(route="overview", routes=routes, render=render_route),
        )
        """,
    )

    result = _run_mypy(sample, tmp_path / ".mypy_cache")

    assert result.returncode == 0, result.stdout + result.stderr


def test_public_typing_reports_common_widget_mistakes(tmp_path):
    sample = _write_sample(
        tmp_path / "invalid_otoe_app.py",
        """
        from typing import Any

        from otoe import ActionButton, Button, DataTable, Node, TableColumn, Text


        def bad_cell(row: Any, column: TableColumn) -> str:
            return str(row[column.key])


        def ok_key(row: Any) -> str:
            return str(row)


        bad_button_event: Node = Button("Run", onPressed=lambda: None)
        bad_button_handler: Node = ActionButton("Save", onClick=lambda value: None)
        bad_cell_renderer: Node = DataTable(
            columns=[TableColumn("name", "Name")],
            rows=[],
            key=ok_key,
            render_cell=bad_cell,
        )
        bad_text_event: Node = Text("No events", onClick=lambda: None)
        """,
    )

    result = _run_mypy(sample, tmp_path / ".mypy_cache")
    output = result.stdout + result.stderr

    assert result.returncode != 0
    assert 'Unexpected keyword argument "onPressed"' in output
    assert 'Unexpected keyword argument "onClick" for "Text"' in output
    assert "Argument \"onClick\" to \"ActionButton\" has incompatible type" in output
    assert "Argument \"render_cell\" to \"DataTable\" has incompatible type" in output
