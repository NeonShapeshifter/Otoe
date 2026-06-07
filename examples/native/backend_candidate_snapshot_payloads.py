from __future__ import annotations

from typing import Any

from .backend_candidate_renderer_types import (
    HeadlessCandidateFrameSummary,
    HeadlessCandidateRunReport,
    RendererCandidateCall,
    RendererContractBoxSnapshot,
    RendererContractPaintSnapshot,
)


def box_snapshot(box: Any) -> RendererContractBoxSnapshot:
    return RendererContractBoxSnapshot(
        path=box.path,
        name=box.name,
        bounds=(box.x, box.y, box.width, box.height),
        text=box.text,
        events=box.events,
        state=box.state,
    )


def paint_snapshot(command: Any) -> RendererContractPaintSnapshot:
    return RendererContractPaintSnapshot(
        kind=command.kind,
        path=command.path,
        bounds=(command.x, command.y, command.width, command.height),
        fill=command.fill,
        stroke=command.stroke,
        stroke_width=command.stroke_width,
        radius=command.radius,
        text=command.text,
        color=command.color,
        font_size=command.font_size,
        clip=command.clip,
    )


def renderer_call_to_dict(call: RendererCandidateCall) -> dict[str, Any]:
    payload = {
        "phase": call.phase,
        "subject": call.subject,
        "layoutBoxes": call.layout_boxes,
        "paintCommands": call.paint_commands,
    }
    if call.boundary is not None:
        payload["boundary"] = call.boundary
    return payload


def run_contract_snapshot_to_dict(
    report: HeadlessCandidateRunReport,
) -> dict[str, Any]:
    return {
        "backend": report.backend,
        "rendererBackend": report.renderer_backend,
        "title": report.title,
        "passed": report.passed,
        "replayPassed": bool(getattr(report.replay, "passed", False)),
        "before": frame_contract_snapshot_to_dict(report.before),
        "after": frame_contract_snapshot_to_dict(report.after),
    }


def frame_contract_snapshot_to_dict(
    frame: HeadlessCandidateFrameSummary,
) -> dict[str, Any]:
    return {
        "label": frame.label,
        "frame": frame.frame,
        "size": list(frame.size),
        "rootName": frame.root_name,
        "focused": list(frame.focused) if frame.focused is not None else None,
        "layoutBoxes": frame.layout_boxes,
        "paintCommands": frame.paint_commands,
        "visibleText": list(frame.visible_text),
        "paintKinds": list(frame.paint_kinds),
        "layout": [
            box_snapshot_to_dict(box)
            for box in frame.layout_snapshot
        ],
        "paint": [
            paint_snapshot_to_dict(command)
            for command in frame.paint_snapshot
        ],
    }


def box_snapshot_to_dict(box: RendererContractBoxSnapshot) -> dict[str, Any]:
    return {
        "path": list(box.path),
        "name": box.name,
        "bounds": list(box.bounds),
        "text": box.text,
        "events": list(box.events),
        "state": list(box.state),
    }


def paint_snapshot_to_dict(
    command: RendererContractPaintSnapshot,
) -> dict[str, Any]:
    return {
        "kind": command.kind,
        "path": list(command.path),
        "bounds": list(command.bounds),
        "fill": command.fill,
        "stroke": command.stroke,
        "strokeWidth": command.stroke_width,
        "radius": command.radius,
        "text": command.text,
        "color": command.color,
        "fontSize": command.font_size,
        "clip": list(command.clip) if command.clip is not None else None,
    }
