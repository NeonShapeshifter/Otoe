import json
from pathlib import Path

import pytest

from otoe.pack import PackError, _run_style_ir_strict_verify, _safe_bundle_path


def test_safe_bundle_path_rejects_empty_and_current_directory():
    bundle_dir = Path("/bundle")

    with pytest.raises(PackError, match="bundle path '' is not safe"):
        _safe_bundle_path(bundle_dir, "")
    with pytest.raises(PackError, match="bundle path '\\.' is not safe"):
        _safe_bundle_path(bundle_dir, ".")


def test_safe_bundle_path_rejects_absolute_and_parent_paths():
    bundle_dir = Path("/bundle")

    with pytest.raises(PackError, match="bundle path '/tmp/styles.json' is not safe"):
        _safe_bundle_path(bundle_dir, "/tmp/styles.json")
    with pytest.raises(PackError, match="bundle path '../styles.json' is not safe"):
        _safe_bundle_path(bundle_dir, "../styles.json")


def test_safe_bundle_path_accepts_relative_bundle_file():
    bundle_dir = Path("/bundle")

    assert _safe_bundle_path(bundle_dir, "styles/otoe-styles.json") == (
        bundle_dir / "styles" / "otoe-styles.json"
    )


def test_run_style_ir_strict_verify_rejects_style_ops_drift(tmp_path):
    (tmp_path / "manifest.json").write_text(
        json.dumps({"styles": "otoe-styles.json"}),
        encoding="utf-8",
    )
    (tmp_path / "otoe-styles.json").write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "rules": [
                    {
                        "className": "shell",
                        "selector": ".shell",
                        "declarations": {
                            "color": {"type": "literal", "value": "#111827"}
                        },
                        "omittedDeclarations": [],
                        "missing": False,
                    }
                ],
                "directStyles": [],
                "styleOps": {
                    "schemaVersion": 1,
                    "format": "otoe-style-ops",
                    "capabilities": {"styles": {"color": "paint"}},
                    "classes": [
                        {
                            "className": "shell",
                            "selector": ".shell",
                            "missing": False,
                            "ops": [
                                {
                                    "op": "setStyle",
                                    "property": "color",
                                    "support": "paint",
                                    "value": {
                                        "type": "literal",
                                        "value": "#dc2626",
                                    },
                                }
                            ],
                            "omittedOps": [],
                        }
                    ],
                    "directStyles": [],
                },
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(
        PackError,
        match="styleOps class 'shell' applied declarations do not match compiled rules",
    ):
        _run_style_ir_strict_verify(tmp_path)
