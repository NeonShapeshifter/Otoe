# Wraith Preview

Open `wraith.html` directly in a browser for the current static visual preview.
Open `wraith_mission_exec.html` for the extracted Mission Exec surface.
Open `saas.html` for a softer SaaS-style case study using the same Otoe runtime.
Open `ui.html` for the shared UI kit kitchen-sink preview.

The checked-in HTML is a convenience artifact generated from the current Otoe
fake tree with the pretty HTML renderer:

```bash
PYTHONPATH=src:. python -m examples.wraith.preview
```

For the interactive preview, run:

```bash
PYTHONPATH=src:. python -m examples.wraith.live_preview
```

Then open <http://127.0.0.1:8765>.

The Wraith Mission Exec preview can be regenerated with:

```bash
PYTHONPATH=src:. python -m examples.wraith.mission_exec_preview
```

For the interactive Mission Exec preview, run:

```bash
PYTHONPATH=src:. python -m examples.wraith.mission_exec_live_preview
```

Then open <http://127.0.0.1:8767>.
Use `SIMULATE FRAME` to verify the live runtime path: frame, elapsed time,
telemetry, and timeline state update through Otoe events and signals.

The SaaS preview can be regenerated with:

```bash
PYTHONPATH=src:. python -m examples.saas.preview
```

For the interactive SaaS preview, run:

```bash
PYTHONPATH=src:. python -m examples.saas.live_preview
```

Then open <http://127.0.0.1:8766>.

The UI kit preview can be regenerated with:

```bash
PYTHONPATH=src:. python -m examples.ui.preview
```

For the interactive UI kit preview, run:

```bash
PYTHONPATH=src:. python -m examples.ui.live_preview
```

Then open <http://127.0.0.1:8768>.
Use the sidebar and command palette to verify live route switching between UI
Kit, SaaS, and Wraith-shaped surfaces.

Otoe also has an optional JSX-like `template(...)` authoring path. It returns
the same `Node` tree as Python components, so it is syntax sugar rather than a
separate runtime.

Otoe also has an experimental portable style path:

```python
from otoe import css, render_html

styles = css(".card { padding: 16px; background: panel; }")
html = render_html(view, stylesheet=styles)
```

The HTML renderer emits inline styles only as a proof backend; `StyleSheet` is
intended to be renderer-independent.
