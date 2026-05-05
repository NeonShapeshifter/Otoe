from __future__ import annotations

from examples.wraith.arsenal import ArsenalView
from examples.wraith.runtime_status import RuntimeStatusCluster
from examples.wraith.topbar import TopBar
from otoe import mount, render_html, signal


def build_preview_html() -> str:
    topbar = mount(
        TopBar(
            campaign=signal("Primary Campaign"),
            wifi_state=signal("UP"),
            stealth_active=signal(True),
        )
    )
    status = mount(
        RuntimeStatusCluster(
            probe=lambda: {
                "wifi": "UP",
                "bluetooth": "READY",
                "cpu": "42C",
                "storage": "18GB",
            }
        )
    )
    arsenal = mount(
        ArsenalView(
            query=signal(""),
            active_tag=signal("ALL"),
            missions=signal(
                [
                    {
                        "id": "wifi",
                        "name": "WiFi Scan",
                        "description": "Discover nearby networks.",
                        "vector": "WiFi",
                        "opsec": "LOW",
                    },
                    {
                        "id": "rf",
                        "name": "RF Survey",
                        "description": "Inspect spectrum activity.",
                        "vector": "RF",
                        "opsec": "MED",
                    },
                    {
                        "id": "lab",
                        "name": "Lab Flow",
                        "description": "Restricted validation path.",
                        "vector": "USB",
                        "opsec": "HIGH",
                    },
                ]
            ),
            page_label=signal("PAGE 1/1"),
            on_search=lambda value: None,
            on_next=lambda: None,
        )
    )

    body = "\n".join(
        [
            render_html(topbar, pretty=True, indent=4),
            '    <main class="preview-main">',
            '      <section class="preview-column preview-column--left">',
            '        <div class="preview-section-title">Runtime</div>',
            render_html(status, pretty=True, indent=8),
            "      </section>",
            '      <section class="preview-column preview-column--main">',
            '        <div class="preview-section-title">Arsenal</div>',
            render_html(arsenal, pretty=True, indent=8),
            "      </section>",
            "    </main>",
        ]
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Otoe Wraith Preview</title>
  <link rel="stylesheet" href="wraith.css">
</head>
<body>
  <div class="app-shell">
{body}
  </div>
</body>
</html>
"""


if __name__ == "__main__":
    print(build_preview_html())
