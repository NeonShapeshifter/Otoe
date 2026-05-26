from examples.data_workflow.workbench import (
    DataWorkflowWorkbench,
    MemoryDataWorkflowProvider,
    WorkflowSnapshot,
)
from otoe import mount, render_html, signal


def build_preview_html(snapshot: WorkflowSnapshot | None = None, route: str = "queue") -> str:
    provider = MemoryDataWorkflowProvider(snapshot)
    app = mount(
        DataWorkflowWorkbench(
            snapshot=signal(provider.snapshot()),
            active_route=signal(route),
            on_navigate=lambda route_id: None,
            on_query=lambda value: None,
            on_stage_filter=lambda value: None,
            on_toggle_record=lambda record_id: None,
            on_action=lambda action_id: None,
        )
    )
    body = render_html(app, pretty=True, indent=4)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Otoe Data Workflow Console</title>
  <link rel="stylesheet" href="reference_theme.css">
  <link rel="stylesheet" href="data_workflow.css">
</head>
<body>
{body}
</body>
</html>
"""


if __name__ == "__main__":
    print(build_preview_html())
