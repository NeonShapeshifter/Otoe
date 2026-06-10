from examples.hardware.control_panel import DeviceSnapshot, app
from otoe import mount, render_html


def build_preview_html(snapshot: DeviceSnapshot | None = None, route: str = "overview") -> str:
    mounted = mount(app(snapshot=snapshot, route=route))
    body = render_html(mounted, pretty=True, indent=4)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Otoe Hardware Control Panel</title>
  <link rel="stylesheet" href="reference_theme.css">
  <link rel="stylesheet" href="hardware.css">
</head>
<body>
{body}
</body>
</html>
"""


if __name__ == "__main__":
    print(build_preview_html())
