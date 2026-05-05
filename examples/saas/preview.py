from examples.saas.overview import SaaSOverview
from otoe import mount, render_html, signal


def build_preview_html() -> str:
    app = mount(
        SaaSOverview(
            query=signal(""),
            workspace=signal("Growth workspace"),
            active_section=signal("Overview"),
            deals=signal(DEALS),
            customers=signal(CUSTOMERS),
            on_search=lambda value: None,
            on_invite=lambda: None,
            on_nav=lambda section: None,
        )
    )
    body = render_html(app, pretty=True, indent=4)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Otoe SaaS Preview</title>
  <link rel="stylesheet" href="saas.css">
</head>
<body>
{body}
</body>
</html>
"""


DEALS = [
    {
        "id": "northstar",
        "stage": "Expansion",
        "confidence": "82%",
        "name": "Northstar Analytics",
        "owner": "Maya Chen",
        "amount": "$42,000",
        "value": 42000,
    },
    {
        "id": "arcadia",
        "stage": "Pilot",
        "confidence": "64%",
        "name": "Arcadia Finance",
        "owner": "Jon Bell",
        "amount": "$18,500",
        "value": 18500,
    },
    {
        "id": "helio",
        "stage": "Renewal",
        "confidence": "91%",
        "name": "Helio Studio",
        "owner": "Nora Patel",
        "amount": "$27,800",
        "value": 27800,
    },
]

CUSTOMERS = [
    {"id": "a", "name": "Mercury Labs", "plan": "Scale", "health": "Healthy", "tone": "good"},
    {"id": "b", "name": "Fable Cloud", "plan": "Pro", "health": "Watch", "tone": "warn"},
    {"id": "c", "name": "Atlas HR", "plan": "Scale", "health": "Healthy", "tone": "good"},
    {"id": "d", "name": "SignalDesk", "plan": "Starter", "health": "Needs touch", "tone": "danger"},
]


if __name__ == "__main__":
    print(build_preview_html())
