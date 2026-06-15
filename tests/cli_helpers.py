import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tarfile
import tomllib
import zlib
from pathlib import Path

import pytest

import otoe.deps as deps_module
from otoe.capabilities import backend_capability_profile
from otoe.cli import main

__all__ = [
    "hashlib",
    "importlib",
    "json",
    "os",
    "subprocess",
    "sys",
    "tarfile",
    "tomllib",
    "zlib",
    "Path",
    "pytest",
    "deps_module",
    "backend_capability_profile",
    "main",
    "_write_backend_capability_profile",
    "_write_backend_coverage_requirements",
    "_system_test_font",
    "_backend_coverage_path0_output",
    "_backend_coverage_output_hash",
    "_backend_coverage_test_hash",
    "_refresh_manifest_artifact_hash",
    "_png_contains_rgba",
    "_png_size",
]

def _write_backend_capability_profile(
    path,
    *,
    name: str,
    styles: dict[str, str] | None = None,
    widgets: dict[str, str] | None = None,
    inputs: dict[str, str] | None = None,
) -> None:
    path.write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "format": "backend-capability-profile",
                "name": name,
                "label": f"{name} profile",
                "styles": styles or {},
                "widgets": widgets or {},
                "inputs": inputs or {},
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

def _write_backend_coverage_requirements(
    path,
    *,
    widgets: tuple[str, ...] = ("Text",),
    inputs: tuple[str, ...] = ("click",),
    styles: tuple[str, ...] = ("padding",),
    omitted: tuple[str, ...] = ("borderStyle",),
) -> None:
    declared = backend_capability_profile("native-python").coverage_declaration()[
        "covers"
    ]
    evidenced_widgets = tuple(declared["widgets"])
    evidenced_inputs = tuple(declared["inputs"])
    evidenced_styles = tuple(declared["styles"])
    evidenced_omissions = tuple(declared["declaredStyleOmissions"])
    evidenced_boundaries = tuple(declared["rendererBoundaries"])
    path0_output = _backend_coverage_path0_output()
    path0_render_tree_hash = _backend_coverage_test_hash("test-render-tree")
    path0_runtime = {
        "source": "test:requirements",
        "rendererBackend": "test-renderer",
        "styleOpsPresent": True,
        "styleOpsMatchesRenderTree": True,
        "styledNodes": 1,
        "layoutBoxes": 1,
        "paintCommands": 1,
        "layoutEvidence": {
            "observationCount": 1,
            "observationHash": _backend_coverage_test_hash("test-layout"),
            "styleProperties": list(evidenced_styles),
            "observedProperties": list(evidenced_styles),
        },
        "paintEvidence": {
            "observationCount": 1,
            "observationHash": _backend_coverage_test_hash("test-paint"),
            "styleProperties": list(evidenced_styles),
            "observedProperties": list(evidenced_styles),
        },
    }
    path.write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "format": "backend-readiness-report",
                "passed": True,
                "blockers": [],
                "candidateScope": {
                    "level": "path0-render-tree-ir-v0",
                },
                "candidate": {
                    "backend": "native-python",
                },
                "gates": {
                    "rendererReplay": True,
                    "styleOpsReplay": True,
                    "path0RenderTreeEvidence": True,
                },
                "path0": {
                    "input": {
                        "renderTreeHash": path0_render_tree_hash,
                    },
                    "output": path0_output,
                    "semanticValidation": {
                        "passed": True,
                        "errors": [],
                    },
                },
                "requirements": {
                    "rendererBoundaries": [
                        {
                            "kind": "rendererBoundary",
                            "boundaries": [
                                {"boundary": boundary}
                                for boundary in evidenced_boundaries
                            ],
                        }
                    ],
                    "widgets": [
                        {
                            "widgets": [{"name": name} for name in widgets],
                        }
                    ],
                    "inputs": [
                        {
                            "capabilities": [
                                {"capability": capability} for capability in inputs
                            ],
                        }
                    ],
                    "styles": [
                        {
                            "properties": [{"property": prop} for prop in styles],
                        }
                    ],
                    "declaredStyleOmissions": [
                        {
                            "properties": [{"property": prop} for prop in omitted],
                        }
                    ],
                },
                "evidence": {
                    "rendererBoundaries": [
                        {
                            "kind": "rendererBoundary",
                            "source": "test:requirements",
                            "gate": "path0RenderTreeEvidence",
                            "boundaries": [
                                {
                                    "boundary": "paint",
                                    "count": 1,
                                    "proof": {
                                        "phase": "paint",
                                        "source": "test:requirements",
                                        "paintCommands": 1,
                                        "outputHash": path0_output["paint"][
                                            "outputHash"
                                        ],
                                    },
                                },
                                {
                                    "boundary": "renderTreeLayout",
                                    "count": 1,
                                    "proof": {
                                        "phase": "layout",
                                        "boundary": "renderTree",
                                        "source": "test:requirements",
                                        "renderTreeHash": path0_render_tree_hash,
                                        "layoutBoxes": 1,
                                        "outputHash": path0_output["layout"][
                                            "outputHash"
                                        ],
                                    },
                                },
                            ],
                        }
                    ],
                    "path0": {
                        "source": "test:requirements",
                        "gate": "path0RenderTreeEvidence",
                        "rendererBackend": "test-renderer",
                        "styleOpsPresent": True,
                        "styleOpsMatchesRenderTree": True,
                        "renderTreeHash": path0_render_tree_hash,
                        "renderTreeBoundary": {
                            "phase": "layout",
                            "boundary": "renderTree",
                            "source": "test:requirements",
                            "renderTreeHash": path0_render_tree_hash,
                            "layoutBoxes": 1,
                            "outputHash": path0_output["layout"]["outputHash"],
                        },
                        "styledNodes": 1,
                        "layoutBoxes": 1,
                        "paintCommands": 1,
                        "phases": ["layout", "paint"],
                        "layoutOutputHash": path0_output["layout"]["outputHash"],
                        "paintOutputHash": path0_output["paint"]["outputHash"],
                        "layoutEvidence": path0_runtime["layoutEvidence"],
                        "paintEvidence": path0_runtime["paintEvidence"],
                    },
                    "widgets": [
                        {
                            "source": "test:requirements",
                            "gate": "rendererReplay",
                            "proof": {
                                "source": "test:requirements",
                                "auditHash": _backend_coverage_test_hash(
                                    "test-widgets"
                                ),
                                "itemCount": len(evidenced_widgets),
                                "observedWidgets": list(evidenced_widgets),
                            },
                            "widgets": [
                                {"name": name} for name in evidenced_widgets
                            ],
                        }
                    ],
                    "inputs": [
                        {
                            "source": "test:requirements",
                            "gate": "rendererReplay",
                            "proof": {
                                "source": "test:requirements",
                                "auditHash": _backend_coverage_test_hash(
                                    "test-inputs"
                                ),
                                "itemCount": len(evidenced_inputs),
                                "observedCapabilities": list(evidenced_inputs),
                            },
                            "capabilities": [
                                {"capability": capability}
                                for capability in evidenced_inputs
                            ],
                        }
                    ],
                    "styles": [
                        {
                            "kind": "apply",
                            "source": "test:requirements",
                            "gate": "styleOpsReplay+path0RenderTreeEvidence",
                            "support": "layout+paint",
                            "properties": [
                                {"property": prop} for prop in evidenced_styles
                            ],
                            "runtime": path0_runtime,
                        }
                    ],
                    "declaredStyleOmissions": [
                        {
                            "kind": "omit",
                            "source": "test:requirements",
                            "gate": "styleOpsReplay+path0RenderTreeEvidence",
                            "status": "test-omitted",
                            "properties": [
                                {"property": prop} for prop in evidenced_omissions
                            ],
                            "runtime": path0_runtime,
                        }
                    ],
                },
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

def _system_test_font() -> Path:
    for candidate in (
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf"),
        Path("/Library/Fonts/Arial.ttf"),
        Path("/System/Library/Fonts/Supplemental/Arial.ttf"),
    ):
        if candidate.is_file():
            return candidate
    pytest.skip("no TrueType system font available for Pillow native text smoke")

def _backend_coverage_path0_output() -> dict:
    layout = {
        "schemaVersion": 1,
        "format": "path0-layout-output",
        "boxCount": 1,
        "rootPath": [],
        "boxes": [
            {
                "path": [],
                "name": "Text",
                "bounds": [0, 0, 10, 10],
                "id": None,
                "context": "Text",
                "text": "Backend coverage",
                "events": [],
                "state": [],
                "style": {},
                "children": [],
            }
        ],
    }
    paint = {
        "schemaVersion": 1,
        "format": "path0-paint-output",
        "width": 10,
        "height": 10,
        "commandCount": 1,
        "commands": [
            {
                "kind": "rect",
                "path": [],
                "bounds": [0, 0, 10, 10],
                "fill": "#ffffff",
                "stroke": None,
                "strokeWidth": 0,
                "radius": 0,
                "text": None,
                "color": None,
                "fontSize": 14,
                "clip": None,
                "context": "test",
            }
        ],
    }
    return {
        "layout": {**layout, "outputHash": _backend_coverage_output_hash(layout)},
        "paint": {**paint, "outputHash": _backend_coverage_output_hash(paint)},
    }

def _backend_coverage_output_hash(payload: dict) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"

def _backend_coverage_test_hash(label: str) -> str:
    return f"sha256:{hashlib.sha256(label.encode('utf-8')).hexdigest()}"

def _refresh_manifest_artifact_hash(output, artifact_name: str) -> None:
    artifact_path = output / artifact_name
    manifest_path = output / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for artifact in manifest["artifacts"]:
        if artifact["path"] == artifact_name:
            data = artifact_path.read_bytes()
            artifact["size"] = len(data)
            artifact["sha256"] = hashlib.sha256(data).hexdigest()
            manifest_path.write_text(
                json.dumps(manifest, sort_keys=True),
                encoding="utf-8",
            )
            return
    raise AssertionError(f"manifest artifact {artifact_name!r} not found")

def _png_contains_rgba(data: bytes, rgba: tuple[int, int, int, int]) -> bool:
    idat = []
    offset = 8
    while offset < len(data):
        length = int.from_bytes(data[offset : offset + 4], "big")
        kind = data[offset + 4 : offset + 8]
        payload = data[offset + 8 : offset + 8 + length]
        if kind == b"IDAT":
            idat.append(payload)
        offset += length + 12
    return bytes(rgba) in zlib.decompress(b"".join(idat))

def _png_size(data: bytes) -> tuple[int, int]:
    assert data.startswith(b"\x89PNG\r\n\x1a\n")
    return (
        int.from_bytes(data[16:20], "big"),
        int.from_bytes(data[20:24], "big"),
    )
