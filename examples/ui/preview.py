from __future__ import annotations

from examples.ui.kitchen_sink import UIKitKitchenSink
from otoe import mount, render_html, signal


def build_preview_html() -> str:
    app = mount(
        UIKitKitchenSink(
            query=signal(""),
            selected=signal("mission"),
            dialog_open=signal(True),
            active_route=signal("ui"),
            on_query=lambda value: None,
            on_select=lambda command_id: None,
            on_toggle_dialog=lambda: None,
            on_navigate=lambda route_id: None,
            on_shortcut=lambda payload: None,
        )
    )
    body = render_html(app, pretty=True, indent=4)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Otoe UI Kit Preview</title>
  <link rel="stylesheet" href="ui.css">
</head>
<body>
{body}
</body>
</html>
"""


if __name__ == "__main__":
    print(build_preview_html())
