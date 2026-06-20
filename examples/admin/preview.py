from examples.admin.settings_console import (
    AdminSettingsProvider,
    AdminSnapshot,
    MemoryAdminSettingsProvider,
    app,
)
from otoe import mount, render_html


def build_preview_html(
    snapshot: AdminSnapshot | None = None,
    route: str = "overview",
    *,
    provider: AdminSettingsProvider | None = None,
) -> str:
    provider = provider or MemoryAdminSettingsProvider(snapshot)
    mounted = mount(app(route=route, provider=provider))
    body = render_html(mounted, pretty=True, indent=4)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Otoe Local Admin Console</title>
  <link rel="stylesheet" href="reference_theme.css">
  <link rel="stylesheet" href="admin.css">
</head>
<body>
{body}
</body>
</html>
"""


if __name__ == "__main__":
    print(build_preview_html())
