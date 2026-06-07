from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from typing import Any

from .backend_candidate_renderer_types import (
    HeadlessCandidateFrameSummary,
    HeadlessCandidateRunReport,
    RendererCandidateCall,
    RendererContractBoxSnapshot,
    RendererContractPaintSnapshot,
)
from .backend_candidate_snapshot_payloads import (
    frame_contract_snapshot_to_dict,
    renderer_call_to_dict,
)


def compact_run_contract_snapshot_to_dict(
    report: HeadlessCandidateRunReport,
) -> dict[str, Any]:
    return {
        "backend": report.backend,
        "rendererBackend": report.renderer_backend,
        "title": report.title,
        "passed": report.passed,
        "replayPassed": bool(getattr(report.replay, "passed", False)),
        "before": compact_frame_contract_snapshot_to_dict(report.before),
        "after": compact_frame_contract_snapshot_to_dict(report.after),
    }


def compact_frame_contract_snapshot_to_dict(
    frame: HeadlessCandidateFrameSummary,
) -> dict[str, Any]:
    full = frame_contract_snapshot_to_dict(frame)
    layout_signature = [
        compact_box_signature(box)
        for box in frame.layout_snapshot
    ]
    paint_signature = [
        compact_paint_signature(command)
        for command in frame.paint_snapshot
    ]
    text_paths = [
        {
            "path": list(box.path),
            "text": box.text,
        }
        for box in frame.layout_snapshot
        if box.text is not None
    ]
    clip_rects = sorted(
        {
            command.clip
            for command in frame.paint_snapshot
            if command.clip is not None
        }
    )
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
        "layoutSignature": contract_hash(layout_signature),
        "paintSignature": contract_hash(paint_signature),
        "anchors": {
            "layoutNames": [box.name for box in frame.layout_snapshot],
            "textPaths": text_paths,
            "clipRects": [list(rect) for rect in clip_rects],
        },
        "hashes": {
            "layout": contract_hash(full["layout"]),
            "paint": contract_hash(full["paint"]),
            "visibleText": contract_hash(full["visibleText"]),
            "frame": contract_hash(full),
        },
    }


def compact_call_stream(
    calls: Sequence[RendererCandidateCall],
) -> dict[str, Any]:
    signature = [renderer_call_to_dict(call) for call in calls]
    return {
        "count": len(calls),
        "signature": signature,
        "hash": contract_hash(signature),
    }


def compact_box_signature(box: RendererContractBoxSnapshot) -> dict[str, Any]:
    return {
        "path": list(box.path),
        "name": box.name,
        "bounds": list(box.bounds),
        "text": box.text,
        "events": list(box.events),
    }


def compact_paint_signature(
    command: RendererContractPaintSnapshot,
) -> dict[str, Any]:
    return {
        "kind": command.kind,
        "path": list(command.path),
        "bounds": list(command.bounds),
        "text": command.text,
        "clip": list(command.clip) if command.clip is not None else None,
    }


def contract_hash(payload: Any) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"
