# Otoe Preview Gallery

`preview/` is the checked-in static gallery for Otoe's current product-facing
examples. It should lead with neutral Otoe surfaces for local operational UI:
hardware panels, portable UI primitives, utility consoles, dashboards, and
case studies.

Open `index.html` directly in a browser to browse the gallery.

The HTML files are convenience artifacts. Regenerate them from the source
checkout with `PYTHONPATH=src:.` so the local package is used.

## Gallery Entries

| Preview | Type | Maturity | HTML | Regenerate |
| --- | --- | --- | --- | --- |
| Hardware Control Panel | Reference app | Product-preview surface; static HTML is usable for review, native/offline paths remain pre-alpha evidence | `hardware.html`, `hardware_cli.html` | `python -m examples.hardware.preview > preview/hardware.html`; `python -m otoe render examples.hardware.control_panel:app --out /tmp/hardware_cli.fragment.html --css preview/hardware_portable.css --pretty`, then copy the fragment into the checked-in wrapper |
| Local Admin Console | Reference app | Product-preview surface for local settings, access controls, validation feedback, route chrome, and provider-backed updates | `admin.html` | `python -m examples.admin.preview > preview/admin.html` |
| Data Workflow Console | Reference app | Product-preview surface for table workflow, search/filter state, batch selection, guarded actions, and fake provider boundaries | `data_workflow.html` | `python -m examples.data_workflow.preview > preview/data_workflow.html` |
| Portable Core UI | Reference gallery | Public pre-alpha support matrix for portable widgets and product-preview UI primitives | `portable_core_ui.html` | `python -m otoe render examples.portable_core_ui:app --out preview/portable_core_ui.html --css preview/portable_core_ui.css --pretty` |
| UI Kit | Reference app | Product-preview kitchen sink for shared UI primitives and live interaction patterns | `ui.html` | `python -m examples.ui.preview > preview/ui.html` |
| SaaS Case Study | Case study | Browser/static product-shape example; not Otoe's primary appliance niche | `saas.html` | `python -m examples.saas.preview > preview/saas.html` |
| Utility Ops | Reference app | Utility-first operational console using Otoe helpers and generated utility CSS | `utility_ops.html` | `python -m examples.utility.preview > preview/utility_ops.html` |
| Wraith Case Study | Case study | Legacy Wraith-inspired static surface; useful context, not the product identity | `wraith.html` | `python -m examples.wraith.preview > preview/wraith.html` |
| Wraith Mission Exec Case Study | Case study | Pre-alpha operator-console showcase with fake local data and portable style evidence | `wraith_mission_exec.html` | `python -m otoe render examples.wraith.mission_exec_showcase:app --out preview/wraith_mission_exec.html --css preview/wraith_mission_exec.css --pretty` |

## Supporting Previews

These are checked in for coverage and comparison, but they are not front-door
gallery cards yet.

| Asset | HTML status | Regenerate |
| --- | --- | --- |
| `wraith_input_console.css` | `wraith_input_console.html` is checked in as a Wraith case-study support surface | `python -m otoe render examples.wraith_input_console:app --out preview/wraith_input_console.html --css preview/wraith_input_console.css --pretty` |

## CSS Inventory

Every CSS file currently checked into `preview/` is listed below. Some
`otoe render --css` outputs inline resolved styles instead of linking the CSS
file directly; in those cases the CSS remains the source artifact used by the
command.

| CSS | Checked-in HTML | Notes |
| --- | --- | --- |
| `admin.css` | `admin.html` | Front-door local-admin reference preview. |
| `data_workflow.css` | `data_workflow.html` | Front-door data workflow reference preview. |
| `hardware.css` | `hardware.html` | Rich static hardware reference preview from `examples.hardware.preview`. |
| `hardware_portable.css` | `hardware_cli.html` | Strict portable CSS path for CLI render, native PNG, plan, and build evidence. |
| `portable_core_ui.css` | `portable_core_ui.html` | Portable Core UI support matrix/gallery source CSS. |
| `reference_theme.css` | `hardware.html`, `admin.html`, `data_workflow.html`, `utility_ops.html` | Shared browser-preview theme for neutral reference apps. `utility_ops.html` also inlines generated utility CSS. |
| `saas.css` | `saas.html` | SaaS case-study browser stylesheet. |
| `ui.css` | `ui.html` | UI Kit browser stylesheet. |
| `wraith.css` | `wraith.html` | Legacy Wraith case-study stylesheet. Mission Exec now uses `wraith_mission_exec.css`. |
| `wraith_input_console.css` | `wraith_input_console.html` | Wraith case-study support surface. |
| `wraith_mission_exec.css` | `wraith_mission_exec.html` | Mission Exec showcase CSS. The checked-in HTML is regenerated from `examples.wraith.mission_exec_showcase:app`; the older `wraith.css` link was legacy, not the current showcase path. |

## Live Preview Commands

Live previews are local-development tools only. Keep them bound to localhost;
they are not public servers or sandboxes.

```bash
PYTHONPATH=src:. python -m examples.hardware.live_preview
PYTHONPATH=src:. python -m examples.admin.live_preview
PYTHONPATH=src:. python -m examples.data_workflow.live_preview
PYTHONPATH=src:. python -m examples.saas.live_preview
PYTHONPATH=src:. python -m examples.ui.live_preview
PYTHONPATH=src:. python -m examples.wraith.live_preview
PYTHONPATH=src:. python -m examples.wraith.mission_exec_live_preview
```

## Authoring Notes

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

`hardware_cli.html` is wrapped for the static gallery so it has a document
title. `otoe render ...` emits the inner fragment; preserve the checked-in
wrapper when refreshing it.
