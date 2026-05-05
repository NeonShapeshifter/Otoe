# ADR-002: Control Flow Primitives (`Show`, `For`) and Disposal Semantics

**Project:** Otoe  
**Status:** Accepted for Prototype  
**Date:** May 4, 2026  
**Related:** ADR-001, ROADMAP.md

---

## Context

ADR-001 establishes that component functions run once. That means ordinary Python conditionals and list comprehensions inside the component body also run once. Wraith-shaped screens need dynamic UI:

- empty/loading states
- mission lists
- dashboard rows
- service/finding/loot collections
- conditional panels and overlays

Therefore dynamic children must be represented as explicit runtime nodes.

---

## Decision

Otoe provides two control-flow primitives:

- `Show(when=..., children=..., fallback=...)`
- `For(each=..., key=..., children=..., fallback=...)`

They are not visual widgets. They mount to a placeholder fake widget in the prototype and control their rendered child widgets underneath that placeholder. A future renderer can map the placeholder to a fragment-like internal node.

### `Show`

`Show` renders its children when `when` is truthy. If `when` is false and `fallback` is provided, it renders the fallback. `when` may be a static value, `Signal`, or `Computed`.

When the condition changes, the previously mounted branch is unmounted before the new branch mounts. This guarantees owner cleanup for components inside hidden branches.

### `For`

`For` renders a collection. `each` may be a static iterable, `Signal`, or `Computed`. `children` is a render function:

```python
For(
    each=missions,
    key=lambda mission: mission["id"],
    children=lambda mission: MissionCard(mission=mission),
)
```

`key` is required for Phase 1. Keyed identity is the default because Wraith screens render operational lists where stable identity matters. When the collection changes:

1. items with existing keys keep their mounted owner/widget identity;
2. removed keys are unmounted and disposed;
3. new keys are mounted;
4. visual order follows the current iterable order.

If the list is empty and `fallback` is provided, the fallback is mounted.

---

## Consequences

- Dynamic children do not require virtual DOM reconciliation.
- Components inside `Show` and `For` participate in owner cleanup.
- List rendering is explicit enough for tests and future renderer backends.
- Phase 1 avoids unkeyed list semantics; they can be added later only if a real use case appears.

