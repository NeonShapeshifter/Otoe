# ADR-004: Optional Template Syntax

**Status:** Prototype accepted  
**Date:** May 5, 2026

## Context

Otoe needs to support two authoring styles:

- Python-native components for maximum clarity, tooling, and control.
- JSX-like templates for people who prefer markup-shaped UI composition.

The framework should not choose one at the expense of the other. Both styles
must compile to the same `Node` tree so the runtime, renderer, lifecycle,
signals, events, and styling system remain shared.

## Decision

Add an optional `template(...)` API:

```python
from otoe import template

view = template(
    """
    <VStack className="screen" gap="12">
      <Text className="title">{title}</Text>
      <Button className="primary" onClick="{save}">Save</Button>
    </VStack>
    """,
    scope={"title": title, "save": save},
)
```

This is syntactic sugar over the same Python component tree:

```python
VStack(
    Text(title, className="title"),
    Button("Save", className="primary", onClick=save),
    className="screen",
    gap=12,
)
```

## Rules

- Python components remain the base API.
- Templates are optional.
- Templates return `Node`, not a separate renderable type.
- Expressions use explicit `scope`; no implicit global/local capture.
- Tags are resolved through a tag registry.
- Unknown tags and unknown expressions are errors.
- The first implementation supports widget tags, string props, bool props,
  numeric props, primary text content, custom tag mappings, and scoped
  expressions.

## Consequences

This keeps Otoe flexible without recreating Kivy's KV split as the foundation.
The runtime remains Python-first, while teams can opt into a JSX-like authoring
surface where it improves readability.
