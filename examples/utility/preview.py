from __future__ import annotations

from examples.utility.ops_console import (
    MemoryUtilityOpsProvider,
    UtilityOpsConsole,
    UtilitySnapshot,
)
from otoe import mount, render_html, signal, utility_css


def build_preview_html(snapshot: UtilitySnapshot | None = None) -> str:
    provider = MemoryUtilityOpsProvider(snapshot)
    app = mount(
        UtilityOpsConsole(
            snapshot=signal(provider.snapshot()),
            on_action=lambda action_id: None,
        )
    )
    body = render_html(app, pretty=True, indent=4)
    utilities = utility_css()
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Otoe Utility Ops Preview</title>
  <link rel="stylesheet" href="reference_theme.css">
  <style>
{utilities}  </style>
</head>
<body>
{body}
</body>
</html>
"""


if __name__ == "__main__":
    print(build_preview_html())
