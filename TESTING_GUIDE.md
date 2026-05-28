# Testing Guide

This guide explains how to choose the right test surface for Otoe. The main
principle is to test at the smallest layer that proves the behavior you care
about. Use renderer tests when behavior crosses a renderer boundary; use
snapshot or HTML tests when it does not.

## Test Surface Ladder

| Need | Prefer | What It Proves |
| --- | --- | --- |
| Component structure and resolved props | `mount(...)` plus `snapshot(...)` | Components, signals, control flow, props, events, and child ordering. |
| Human-readable tree diffs | `snapshot_text(...)` | Same as snapshot, with deterministic JSON text for focused assertions. |
| HTML adapter output | `render_html(...)` | HTML escaping, class/style output, focus attributes, and static preview shape. |
| Native layout or paint contracts | `layout_native(...)`, `paint_native(...)`, or `NativeSurface` | Native boxes, paint commands, style support, clipping, and diagnostics. |
| Native input and rerender behavior | `NativeSurface` | Headless click, focus, key, input text, scroll, and frame refresh. |
| Window-shaped native input | `NativeWindowDriver` | Backend-facing click, wheel, key-down, and key-input dispatch without an OS window. |
| Generated image artifact | `render_png(...)` or demo frame helpers | PNG creation, non-empty output, and distinct frame changes. |
| Backend candidate parity | backend-replay acceptance test | Whether a future layout, paint, raster, or window backend preserves the current contract. |

Avoid starting with PNG or OS-window tests. Most behavior should be proven by
snapshots, HTML output, `NativeSurface`, or `NativeWindowDriver`.

## Snapshot Tests

Use snapshots when the behavior is about component output rather than renderer
details. Snapshot tests should assert specific props, events, text, and child
positions instead of treating the whole tree as an opaque golden file.

```python
from otoe import Button, HStack, Text, mount, snapshot, signal


def test_toolbar_snapshot_tracks_events_and_state():
    label = signal("Ready")
    mounted = mount(
        HStack(
            Text(label),
            Button("Run", onClick=lambda: label.set("Running")),
            gap=8,
        )
    )

    tree = snapshot(mounted)

    assert tree["name"] == "HStack"
    assert tree["props"] == {"gap": 8}
    assert tree["children"][0]["props"]["content"] == "Ready"
    assert tree["children"][1]["events"] == ["onClick"]
```

Use `snapshot_text(...)` when a readable string assertion is enough:

```python
from otoe import snapshot_text

before = snapshot_text(mounted)
label.set("Running")
after = snapshot_text(mounted)

assert '"content": "Ready"' in before
assert '"content": "Running"' in after
```

Snapshot tests are the right home for `Show`, `For`, reactive props, lifecycle
effects that mutate visible state, and app-level case-study surfaces.

## HTML Render Tests

Use `render_html(...)` when the HTML adapter itself matters. Good HTML tests
check escaping, classes, inline style output, autofocus markers, focus-scope
metadata, and static page builders.

```python
from otoe import Button, HStack, Text, mount, render_html


def test_html_render_escapes_text_and_attrs():
    mounted = mount(
        HStack(
            Text("<Otoe>", className="brand"),
            Button("Run", className='x"y', onClick=lambda: None),
            gap=8,
        )
    )

    html = render_html(mounted)

    assert "&lt;Otoe&gt;" in html
    assert 'class="otoe-button x&quot;y"' in html
    assert 'style="--otoe-gap:8px"' in html
```

Do not use HTML tests to prove native behavior. If the assertion depends on
native layout, paint, clipping, hit testing, focus, or scroll, use the native
test surfaces instead.

## NativeSurface Tests

Use `NativeSurface` when a test needs the headless native frame loop. It owns
one mounted tree and exposes layout, paint, hit testing, focus, input dispatch,
scroll dispatch, PNG output, and frame refresh.

```python
from otoe import Button, NativeSurface, Text, VStack, signal


def test_native_surface_click_refreshes_layout():
    label = signal("OFF")
    surface = NativeSurface(
        VStack(
            Text(label),
            Button("Toggle", onClick=lambda: label.set("ON")),
            padding=8,
            gap=4,
        )
    )
    button = surface.box((1,))

    surface.click(button.x + 2, button.y + 2)

    assert label.value == "ON"
    assert surface.box((0,)).text == "ON"
```

Use `surface.box(path)` for stable layout assertions, `surface.paint.commands`
for paint-order assertions, and `surface.frame` when a test must prove a native
event refreshed the frame. Keep path assertions targeted; do not lock an entire
layout tree unless the test is specifically about tree shape.

## NativeWindowDriver Tests

Use `NativeWindowDriver` when behavior should look like window input rather than
direct surface calls. It is still headless, so tests stay fast and do not need a
display server.

```python
from otoe import Input, NativeWindowDriver, NativeWindowEvent, signal


def test_window_driver_input_text_edits_focused_input():
    value = signal("")
    driver = NativeWindowDriver.from_target(
        Input(
            value=value,
            autoFocus=True,
            onChange=lambda next_value: value.set(next_value),
        )
    )

    driver.dispatch(NativeWindowEvent("input_text", text="search"))

    assert value.value == "search"
    assert driver.surface.input_value() == "search"
```

Prefer `NativeWindowDriver` for tests involving key-input translation,
Backspace/Delete behavior, shortcut fallbacks, wheel dispatch, backend adapter
handoff, or anything a future real window backend must reproduce.

## PNG Frame Tests

Use PNG tests to prove that a renderer path writes files and that meaningful
state changes produce distinct output. Keep PNG assertions coarse:

- file exists
- file starts with the PNG signature
- expected sequence count is produced
- before/after bytes differ when state changes

```python
def test_demo_writes_distinct_frames(tmp_path):
    before, after = render_demo_frames(tmp_path)

    assert before.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    assert after.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    assert before.read_bytes() != after.read_bytes()
```

Do not make pixel-perfect assertions against the current PNG marker text path.
The headless PNG renderer is deterministic, but real font shaping and
rasterization are deferred backend work.

## Backend Acceptance Tests

The backend-replay acceptance test is the contract future backend candidates
must satisfy before claiming parity with the current native path. It should stay
small and framework-neutral.

The current acceptance harness lives in `tests/test_native_backend_contract.py`.
It names the required layout paths through `BackendContractPaths`, builds one
driver/surface pair through `backend_contract_harness()`, and replays the
contract through focused assertion helpers. Reuse that harness shape before
adding a second broad acceptance surface.

That file also keeps one app-shaped replay over the native task board demo. The
task board replay is the Phase 5 pressure surface for backend candidates: it
proves a realistic search, filtered-list, modal, shortcut-reset, scroll, focus,
and frame-refresh flow without pulling a full reference app into the native
contract.

It also includes a fake backend adapter replay through `run_native(...)`. That
test proves custom adapters receive a `NativeWindowDriver` and can drive the
same acceptance contract without bypassing the driver/surface boundary.

A good backend acceptance surface proves:

- the tree mounts through `NativeWindowDriver.from_target(...)`
- native layout exposes expected paths
- paint commands appear in deterministic painter order
- focused input accepts controlled text
- modified key input reaches shortcut handlers without mutating text
- hit-tested clicks choose the same topmost path as paint order
- wheel dispatch updates controlled `ScrollView(scrollY=...)`
- frame count advances after state-changing native events
- custom backend adapters enter through `run_native(...)` and receive a
  replayable `NativeWindowDriver`

Do not expand the acceptance test to cover every widget. Specific layout, paint,
input, and diagnostic behavior belongs in focused unit tests. The acceptance
test is the cross-layer smoke contract for backend replacement.

## Diagnostic Tests

Diagnostics are part of the developer experience. When adding new errors, test
the smallest boundary that owns the failure:

- widget prop and event errors: mount/component tests
- style parsing errors: style tests
- unsupported native style or dimension errors: native layout tests
- invalid paint colors or commands: native paint/PNG tests
- invalid input or focus targets: `NativeSurface` tests
- backend names and adapter failures: native window tests

Assert the useful part of the message, especially component/widget context and
target paths. Avoid asserting full exception strings unless the whole message is
the contract.

## What Not To Test Yet

- Tk OS-window behavior in automated tests.
- Pixel-perfect native PNG text output.
- Production accessibility trees.
- Skia, Taffy, Qt, SDL, or other backend-specific behavior before an adapter
  exists.
- App-specific service behavior inside Otoe renderer tests.

Keep renderer tests framework-neutral unless a case study is intentionally
acting as regression pressure.
