from examples.hardware.control_panel import FakeHardwareProvider, HardwareControlPanel
from otoe import mount, render_html, signal


def build_preview_html() -> str:
    provider = FakeHardwareProvider()
    app = mount(
        HardwareControlPanel(
            snapshot=signal(provider.snapshot()),
            active_route=signal("overview"),
            on_navigate=lambda route_id: None,
            on_command=lambda command_id: None,
        )
    )
    body = render_html(app, pretty=True, indent=4)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Otoe Hardware Control Panel</title>
  <link rel="stylesheet" href="hardware.css">
</head>
<body>
{body}
</body>
</html>
"""


if __name__ == "__main__":
    print(build_preview_html())
