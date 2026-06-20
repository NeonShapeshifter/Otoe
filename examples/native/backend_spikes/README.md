# Native Backend Spikes

These files are isolated experiments for future native backend work. They are
not imported by Otoe core, not wired into the `otoe` CLI, and not required by
normal tests.

## Flex Layout Spike

Run the no-dependency baseline:

```bash
PYTHONPATH=src:. python -m examples.native.backend_spikes.flex_layout_spike
```

This builds a small MissionExec-like tree, runs a local `toy-flex` layout
engine, and prints deterministic boxes. The goal is to validate the Otoe-facing
layout shape before choosing or binding Yoga/Taffy.

Probe external bindings only:

```bash
PYTHONPATH=src:. python -m examples.native.backend_spikes.flex_layout_spike --engine external
```

If no supported binding is installed, the command exits successfully and prints
`result=skipped` with a clear reason.

## Optional Installation Notes

There is intentionally no dependency added to `pyproject.toml`.

As of the matrix in `docs/native-backend-stack-matrix.md`, there is no vetted
Python wheel for Facebook/React Yoga layout or the Rust Taffy UI layout engine.
Do not install PyPI `yoga` or PyPI `taffy` for this spike:

- `yoga` on PyPI is an image optimization package.
- `taffy` on PyPI is a comparative genomics package.

If a real Yoga or Taffy Python binding is introduced later, install it in a
separate virtual environment and add a small adapter inside this spike first.
Only after the adapter proves deterministic boxes, text measurement callbacks,
ARM64 viability, and offline packaging should it be considered for an optional
backend package.
