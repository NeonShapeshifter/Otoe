# ADR-005: Portable Style System

**Status:** Prototype accepted  
**Date:** May 5, 2026

## Context

The HTML backend is a validation tool, not Otoe's final renderer. If previews
depend only on browser CSS, the styling work does not transfer cleanly to a
future Skia/Taffy/Kivy/Qt backend.

Otoe needs a style representation that is:

- Python-importable.
- CSS-like enough to feel normal.
- Strict enough to catch unsupported properties.
- Renderer-independent.

## Decision

Add `css(...)`, `StyleSheet`, `StyleRule`, `Token`, and `Size`.

```python
from otoe import css

styles = css(
    """
    .card {
      padding: 16px;
      border-radius: 8px;
      background: panel;
    }
    .primary {
      background: accent;
      color: white;
    }
    """,
    tokens={"panel": "#ffffff", "accent": "#5b6ee1"},
)
```

The parser accepts a small subset:

- Single class selectors.
- Known style properties only.
- Numbers and `px` / `%` sizes.
- Boolean values.
- Tokens for color-like properties.
- Class merging through `className="card primary"`.

The HTML renderer can consume a `StyleSheet` and emit inline styles as a proof
backend:

```python
render_html(view, stylesheet=styles)
```

## Consequences

This keeps styling portable. Browser CSS files can still exist for visual
preview work, but Otoe now has a framework-owned style IR that a low-level
renderer can consume later.

Unknown style properties fail during parsing. Unknown classes fail during
strict resolution. This avoids silent styling failure.
