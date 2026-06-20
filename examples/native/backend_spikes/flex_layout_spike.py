from __future__ import annotations

import argparse
import importlib.metadata
import importlib.util
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from math import floor


SUPPORTED_EXTERNAL_BINDINGS = (
    "yoga_layout",
    "yogalayout",
    "taffy_layout",
    "taffy_py",
)
KNOWN_WRONG_PACKAGES = {
    "yoga": "PyPI `yoga` is an image optimizer, not Facebook/React Yoga layout.",
    "taffy": "PyPI `taffy` is a comparative genomics package, not Taffy UI layout.",
}


@dataclass(frozen=True)
class Style:
    direction: str = "column"
    width: int | None = None
    height: int | None = None
    min_width: int = 0
    min_height: int = 0
    max_width: int | None = None
    max_height: int | None = None
    padding: int = 0
    gap: int = 0
    flex_grow: int = 0
    flex_shrink: int = 1
    flex_basis: int | None = None
    align_items: str = "stretch"


@dataclass(frozen=True)
class Node:
    id: str
    kind: str
    style: Style = field(default_factory=Style)
    text: str = ""
    children: tuple["Node", ...] = ()


@dataclass(frozen=True)
class Box:
    path: tuple[int, ...]
    id: str
    kind: str
    x: int
    y: int
    width: int
    height: int


@dataclass(frozen=True)
class BindingProbe:
    status: str
    detail: str


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m examples.native.backend_spikes.flex_layout_spike",
        description=(
            "Run an isolated Yoga/Taffy-style layout spike without importing "
            "or modifying Otoe core."
        ),
    )
    parser.add_argument(
        "--engine",
        choices=("auto", "toy", "external"),
        default="auto",
        help=(
            "auto probes external bindings and falls back to the local toy-flex "
            "engine; external only probes and skips if no supported binding is "
            "available"
        ),
    )
    parser.add_argument(
        "--width",
        type=int,
        default=1280,
        help="root surface width in logical pixels",
    )
    parser.add_argument(
        "--height",
        type=int,
        default=800,
        help="root surface height in logical pixels",
    )
    args = parser.parse_args(argv)

    if args.width <= 0 or args.height <= 0:
        parser.error("--width and --height must be positive")

    probe = probe_external_binding()
    if args.engine == "external":
        print(f"external-binding={probe.status}: {probe.detail}")
        if probe.status != "available":
            print("result=skipped")
            return 0
        print("result=skipped: external binding was found, but this spike has no adapter yet")
        return 0

    engine = "toy-flex"
    if args.engine == "auto":
        print(f"external-binding={probe.status}: {probe.detail}")
    print(f"engine={engine}")
    print(f"surface={args.width}x{args.height}")
    boxes = layout_tree(mission_exec_like_tree(args.width, args.height))
    for line in format_boxes(boxes):
        print(line)
    return 0


def probe_external_binding() -> BindingProbe:
    found_wrong = []
    for name, reason in KNOWN_WRONG_PACKAGES.items():
        if importlib.util.find_spec(name) is not None:
            version = _package_version(name)
            found_wrong.append(f"{name} {version}: {reason}")

    found_supported = []
    for name in SUPPORTED_EXTERNAL_BINDINGS:
        if importlib.util.find_spec(name) is not None:
            found_supported.append(f"{name} {_package_version(name)}")

    if found_supported:
        return BindingProbe(
            status="available",
            detail=(
                "found "
                + ", ".join(found_supported)
                + "; adapter intentionally not implemented in this isolated spike"
            ),
        )
    if found_wrong:
        return BindingProbe(
            status="skipped",
            detail=(
                "no supported Yoga/Taffy Python binding found; ignored "
                + "; ".join(found_wrong)
            ),
        )
    return BindingProbe(
        status="skipped",
        detail=(
            "no supported Yoga/Taffy Python binding found. Tried "
            + ", ".join(SUPPORTED_EXTERNAL_BINDINGS)
        ),
    )


def mission_exec_like_tree(width: int, height: int) -> Node:
    return Node(
        id="mission-exec",
        kind="AppFrame",
        style=Style(width=width, height=height, padding=16, gap=12),
        children=(
            Node(
                id="topbar",
                kind="Topbar",
                style=Style(direction="row", height=56, gap=12, align_items="center"),
                children=(
                    leaf("mission-title", "MISSION EXEC"),
                    leaf("timer", "T+00:14:32"),
                    leaf("mode", "LIVE"),
                ),
            ),
            Node(
                id="body",
                kind="MainSplit",
                style=Style(
                    direction="row",
                    flex_grow=1,
                    min_height=0,
                    gap=12,
                    align_items="stretch",
                ),
                children=(
                    Node(
                        id="status-column",
                        kind="StatusColumn",
                        style=Style(width=360, flex_shrink=0, gap=10),
                        children=(
                            panel(
                                "state-panel",
                                "StatePanel",
                                "ACTIVE / OPERATOR CONFIRMED",
                                height=110,
                            ),
                            panel(
                                "preflight-panel",
                                "PreflightPanel",
                                "7 checks passing",
                                height=156,
                            ),
                            panel(
                                "control-panel",
                                "ControlPanel",
                                "Pause / Abort / Export",
                                flex_grow=1,
                                min_height=160,
                            ),
                        ),
                    ),
                    Node(
                        id="live-column",
                        kind="LiveColumn",
                        style=Style(flex_grow=1, min_width=0, gap=12),
                        children=(
                            Node(
                                id="probe-strip",
                                kind="ProbeStrip",
                                style=Style(direction="row", height=84, gap=10),
                                children=(
                                    panel("probe-1", "ProbeCard", "latency 31ms", flex_grow=1),
                                    panel("probe-2", "ProbeCard", "queue 04", flex_grow=1),
                                    panel("probe-3", "ProbeCard", "risk low", flex_grow=1),
                                ),
                            ),
                            Node(
                                id="feed-split",
                                kind="FeedSplit",
                                style=Style(
                                    direction="row",
                                    flex_grow=1,
                                    min_height=0,
                                    gap=12,
                                ),
                                children=(
                                    Node(
                                        id="terminal",
                                        kind="TerminalPanel",
                                        style=Style(flex_grow=1, min_width=0, gap=6),
                                        children=(
                                            leaf("terminal-title", "Runtime Log"),
                                            leaf("log-1", "00:14:02 INFO probe handshake ok"),
                                            leaf("log-2", "00:14:09 WARN waiting for approval"),
                                            leaf("log-3", "00:14:22 INFO payload staged"),
                                        ),
                                    ),
                                    Node(
                                        id="events",
                                        kind="EventTimeline",
                                        style=Style(width=300, flex_shrink=0, gap=6),
                                        children=(
                                            leaf("events-title", "Events"),
                                            leaf("event-1", "operator armed"),
                                            leaf("event-2", "network stable"),
                                            leaf("event-3", "approval pending"),
                                        ),
                                    ),
                                ),
                            ),
                        ),
                    ),
                ),
            ),
        ),
    )


def leaf(id: str, text: str) -> Node:
    return Node(id=id, kind="Text", text=text, style=Style(height=22))


def panel(
    id: str,
    kind: str,
    text: str,
    *,
    height: int | None = None,
    flex_grow: int = 0,
    min_height: int = 0,
) -> Node:
    return Node(
        id=id,
        kind=kind,
        style=Style(height=height, flex_grow=flex_grow, min_height=min_height, padding=10),
        children=(leaf(f"{id}-label", text),),
    )


def layout_tree(root: Node) -> tuple[Box, ...]:
    boxes: list[Box] = []
    _layout_node(root, x=0, y=0, width=root.style.width, height=root.style.height, path=(), out=boxes)
    return tuple(boxes)


def _layout_node(
    node: Node,
    *,
    x: int,
    y: int,
    width: int | None,
    height: int | None,
    path: tuple[int, ...],
    out: list[Box],
) -> Box:
    style = node.style
    resolved_width = _constrain(
        style.width if style.width is not None else width,
        minimum=style.min_width,
        maximum=style.max_width,
    )
    resolved_height = _constrain(
        style.height if style.height is not None else height,
        minimum=style.min_height,
        maximum=style.max_height,
    )

    if not node.children:
        natural_width, natural_height = _measure_leaf(node)
        resolved_width = _constrain(
            resolved_width if resolved_width is not None else natural_width,
            minimum=style.min_width,
            maximum=style.max_width,
        )
        resolved_height = _constrain(
            resolved_height if resolved_height is not None else natural_height,
            minimum=style.min_height,
            maximum=style.max_height,
        )
        box = Box(
            path=path,
            id=node.id,
            kind=node.kind,
            x=x,
            y=y,
            width=resolved_width or 0,
            height=resolved_height or 0,
        )
        out.append(box)
        return box

    if resolved_width is None or resolved_height is None:
        natural_width, natural_height = _measure_container(node)
        resolved_width = _constrain(
            resolved_width if resolved_width is not None else natural_width,
            minimum=style.min_width,
            maximum=style.max_width,
        )
        resolved_height = _constrain(
            resolved_height if resolved_height is not None else natural_height,
            minimum=style.min_height,
            maximum=style.max_height,
        )

    box = Box(
        path=path,
        id=node.id,
        kind=node.kind,
        x=x,
        y=y,
        width=resolved_width or 0,
        height=resolved_height or 0,
    )
    out.append(box)

    inner_x = x + style.padding
    inner_y = y + style.padding
    inner_width = max(0, box.width - style.padding * 2)
    inner_height = max(0, box.height - style.padding * 2)
    _layout_children(
        node,
        x=inner_x,
        y=inner_y,
        width=inner_width,
        height=inner_height,
        path=path,
        out=out,
    )
    return box


def _layout_children(
    node: Node,
    *,
    x: int,
    y: int,
    width: int,
    height: int,
    path: tuple[int, ...],
    out: list[Box],
) -> None:
    style = node.style
    main_available = width if style.direction == "row" else height
    cross_available = height if style.direction == "row" else width
    bases = [_child_basis(child, style.direction) for child in node.children]
    total_gap = max(0, len(node.children) - 1) * style.gap
    allocated = _allocate_main_sizes(
        node.children,
        bases=bases,
        available=max(0, main_available - total_gap),
        direction=style.direction,
    )

    cursor = 0
    for index, (child, main_size) in enumerate(zip(node.children, allocated, strict=True)):
        if index:
            cursor += style.gap
        natural_width, natural_height = _measure_node(child)
        if style.direction == "row":
            child_width = main_size
            child_height = _resolve_cross_size(
                child,
                natural=natural_height,
                available=cross_available,
                parent_align=style.align_items,
                dimension="height",
            )
            child_x = x + cursor
            child_y = y + _cross_offset(cross_available, child_height, style.align_items)
        else:
            child_width = _resolve_cross_size(
                child,
                natural=natural_width,
                available=cross_available,
                parent_align=style.align_items,
                dimension="width",
            )
            child_height = main_size
            child_x = x + _cross_offset(cross_available, child_width, style.align_items)
            child_y = y + cursor
        _layout_node(
            child,
            x=child_x,
            y=child_y,
            width=child_width,
            height=child_height,
            path=(*path, index),
            out=out,
        )
        cursor += main_size


def _allocate_main_sizes(
    children: tuple[Node, ...],
    *,
    bases: list[int],
    available: int,
    direction: str,
) -> list[int]:
    total_base = sum(bases)
    delta = available - total_base
    sizes = list(bases)
    if delta > 0:
        grow_total = sum(child.style.flex_grow for child in children)
        if grow_total:
            remaining = delta
            for index, child in enumerate(children):
                share = 0
                if child.style.flex_grow:
                    share = floor(delta * child.style.flex_grow / grow_total)
                sizes[index] += share
                remaining -= share
            sizes[-1] += remaining
    elif delta < 0:
        shrink_total = sum(child.style.flex_shrink for child in children)
        if shrink_total:
            debt = -delta
            for index, child in enumerate(children):
                share = floor(debt * child.style.flex_shrink / shrink_total)
                sizes[index] = max(_min_main(child, direction), sizes[index] - share)
            overflow = sum(sizes) - available
            index = len(sizes) - 1
            while overflow > 0 and index >= 0:
                floor_size = _min_main(children[index], direction)
                reducible = max(0, sizes[index] - floor_size)
                take = min(reducible, overflow)
                sizes[index] -= take
                overflow -= take
                index -= 1
    return sizes


def _child_basis(child: Node, direction: str) -> int:
    if child.style.flex_basis is not None:
        return child.style.flex_basis
    if direction == "row" and child.style.width is not None:
        return child.style.width
    if direction == "column" and child.style.height is not None:
        return child.style.height
    width, height = _measure_node(child)
    return width if direction == "row" else height


def _measure_node(node: Node) -> tuple[int, int]:
    if not node.children:
        return _measure_leaf(node)
    return _measure_container(node)


def _measure_leaf(node: Node) -> tuple[int, int]:
    text_width = max(24, len(node.text) * 8)
    width = node.style.width if node.style.width is not None else text_width
    height = node.style.height if node.style.height is not None else 22
    return (
        _constrain(width, minimum=node.style.min_width, maximum=node.style.max_width) or 0,
        _constrain(height, minimum=node.style.min_height, maximum=node.style.max_height) or 0,
    )


def _measure_container(node: Node) -> tuple[int, int]:
    child_sizes = [_measure_node(child) for child in node.children]
    if not child_sizes:
        content_width = 0
        content_height = 0
    elif node.style.direction == "row":
        content_width = sum(width for width, _height in child_sizes)
        content_width += max(0, len(child_sizes) - 1) * node.style.gap
        content_height = max(height for _width, height in child_sizes)
    else:
        content_width = max(width for width, _height in child_sizes)
        content_height = sum(height for _width, height in child_sizes)
        content_height += max(0, len(child_sizes) - 1) * node.style.gap
    width = node.style.width if node.style.width is not None else content_width + node.style.padding * 2
    height = (
        node.style.height
        if node.style.height is not None
        else content_height + node.style.padding * 2
    )
    return (
        _constrain(width, minimum=node.style.min_width, maximum=node.style.max_width) or 0,
        _constrain(height, minimum=node.style.min_height, maximum=node.style.max_height) or 0,
    )


def _resolve_cross_size(
    node: Node,
    *,
    natural: int,
    available: int,
    parent_align: str,
    dimension: str,
) -> int:
    explicit = node.style.height if dimension == "height" else node.style.width
    if explicit is not None:
        return explicit
    if parent_align == "stretch":
        return max(0, available)
    return min(natural, max(0, available))


def _cross_offset(available: int, size: int, align_items: str) -> int:
    if align_items in {"center", "middle"}:
        return max(0, (available - size) // 2)
    if align_items in {"end", "flex-end"}:
        return max(0, available - size)
    return 0


def _min_main(node: Node, direction: str) -> int:
    return node.style.min_width if direction == "row" else node.style.min_height


def _constrain(
    value: int | None,
    *,
    minimum: int = 0,
    maximum: int | None = None,
) -> int | None:
    if value is None:
        return None
    constrained = max(minimum, value)
    if maximum is not None:
        constrained = min(maximum, constrained)
    return constrained


def format_boxes(boxes: Iterable[Box]) -> tuple[str, ...]:
    return tuple(
        "box path={path:<9} id={id:<18} kind={kind:<14} x={x:<4} y={y:<4} w={w:<4} h={h:<4}".format(
            path=_format_path(box.path),
            id=box.id,
            kind=box.kind,
            x=box.x,
            y=box.y,
            w=box.width,
            h=box.height,
        )
        for box in boxes
    )


def _format_path(path: tuple[int, ...]) -> str:
    return "root" if not path else ".".join(str(part) for part in path)


def _package_version(module_name: str) -> str:
    candidates = (module_name, module_name.replace("_", "-"))
    for candidate in candidates:
        try:
            return importlib.metadata.version(candidate)
        except importlib.metadata.PackageNotFoundError:
            continue
    return "unknown-version"


if __name__ == "__main__":
    raise SystemExit(main())
