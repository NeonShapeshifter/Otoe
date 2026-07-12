from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .cli_common import CliError


def run_new(args: argparse.Namespace) -> int:
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
        "Run these commands from this directory:\n"
        "\n"
        "```bash\n"
        "otoe check\n"
        f"otoe check --target app:app{css_arg}\n"
        f"otoe render app:app --out preview.html{css_arg} --pretty\n"
        f"otoe render app:app --out preview.png --native{css_arg}\n"
        f"otoe dev app:app{css_arg}\n"
        f"otoe build app:app --out dist/cage{css_arg} --validate\n"
        "```\n"
        "\n"
        "Notes:\n"
        "\n"
        "- `otoe check --target app:app` validates that the generated target imports.\n"
        "- `otoe dev` is a localhost development preview, not a public server.\n"
        "- `--native` writes deterministic native evidence, not a production native renderer.\n"
        "- `otoe build --validate` is offline bundle tooling in technical preview, not a sandbox.\n"
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
