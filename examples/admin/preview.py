from examples.admin.settings_console import (
    AdminSettingsConsole,
    AdminSnapshot,
    MemoryAdminSettingsProvider,
)
from otoe import mount, render_html, signal


def build_preview_html(snapshot: AdminSnapshot | None = None, route: str = "overview") -> str:
    provider = MemoryAdminSettingsProvider(snapshot)
    app = mount(
        AdminSettingsConsole(
            snapshot=signal(provider.snapshot()),
            active_route=signal(route),
            on_navigate=lambda route_id: None,
            on_setting_change=lambda setting_id, value: None,
            on_action=lambda action_id: None,
            on_rule_toggle=lambda rule_id: None,
        )
    )
    body = render_html(app, pretty=True, indent=4)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Otoe Local Admin Console</title>
  <link rel="stylesheet" href="admin.css">
</head>
<body>
{body}
</body>
</html>
"""


if __name__ == "__main__":
    print(build_preview_html())
