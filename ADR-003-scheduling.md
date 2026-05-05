# ADR-003: Batching, Scheduling, Timers, and Async UI Ownership

**Project:** Otoe  
**Status:** Accepted for Prototype  
**Date:** May 4, 2026  
**Related:** ADR-001, ADR-002, ROADMAP.md

---

## Context

Wraith-shaped screens update several pieces of state from one operator action or one runtime tick:

- search changes query, visible missions, pagination, and notices
- top bar polling updates WiFi, Bluetooth, CPU, storage, battery, and hardware summary
- mission execution updates status, output tail, progress, findings, and action availability

If every `signal.set()` immediately runs every dependent effect and reactive prop update, Otoe will work but do unnecessary repeated work. The runtime needs a minimal scheduler before visible rendering.

---

## Decision

Otoe provides `batch(fn)` and `with batch():` semantics.

Within a batch:

1. signal writes update signal values immediately;
2. subscribers are queued instead of called immediately;
3. each subscriber runs at most once when the outermost batch exits;
4. nested batches flush only at the outermost exit.

Outside a batch, updates keep the current immediate behavior.

The prototype scheduler is synchronous. It does not introduce a render loop yet. A future renderer may map the flush boundary to a UI frame/tick.

---

## Timers

Otoe provides an owner-scoped `interval(seconds, callback, immediate=False)` helper for recurring work.

In the prototype, the interval is a controllable runtime object with `.tick()` for deterministic tests and examples. It registers with the current component owner, so unmounting the component cancels the interval automatically.

A future backend can connect the same API to the UI/event loop timer.

---

## Async UI Ownership

Event handlers may still be sync or async as defined in ADR-001. ADR-003 does not change handler classification. Async handler scheduling remains the event dispatcher's job.

Timer callbacks are normal callbacks. If a callback needs async work, it should either schedule that work explicitly or return a coroutine once the runtime has a backend event loop policy.

---

## Consequences

- Multi-signal updates can be grouped without duplicating effect runs.
- Wraith-style polling can be represented without leaking timers after unmount.
- The scheduler remains backend-neutral.
- The first batching implementation is intentionally small: no priorities, no animation frames, no async scheduler lanes.

