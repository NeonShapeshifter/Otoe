from cli_helpers import (
    json,
    main,
)


def test_cli_style_ir_inspects_compiled_artifact(tmp_path, monkeypatch, capsys):
    app = tmp_path / "style_ir_inspect_app.py"
    app.write_text(
        "from otoe import Text, VStack\n"
        "app = VStack(Text('Inspect'), className='shell', gap=4, padding=8)\n",
        encoding="utf-8",
    )
    styles = tmp_path / "styles.css"
    styles.write_text(".shell { color: #111827; }\n", encoding="utf-8")
    profile_file = tmp_path / "otoe.profile.toml"
    profile_file.write_text(
        'profile = "cage"\n'
        'css = ["styles.css"]\n'
        "\n"
        "[runtime]\n"
        'files = ["style_ir_inspect_app.py"]\n',
        encoding="utf-8",
    )
    output = tmp_path / "dist" / "style-ir-inspect"
    monkeypatch.syspath_prepend(str(tmp_path))

    build_result = main(
        [
            "build",
            "style_ir_inspect_app:app",
            "--profile-file",
            str(profile_file),
            "--out",
            str(output),
        ]
    )
    capsys.readouterr()

    styles_path = output / "otoe-styles.json"
    summary_result = main(["style-ir", str(styles_path)])
    summary = capsys.readouterr()
    json_result = main(["style-ir", str(styles_path), "--json"])
    captured_json = capsys.readouterr()
    payload = json.loads(captured_json.out)

    assert build_result == 0
    assert summary_result == 0
    assert f"style-ir {styles_path}" in summary.out
    assert "styleOps: schema=1 format=otoe-style-ops passed" in summary.out
    assert "classes: 1 rules, 1 primitive entries" in summary.out
    assert "direct styles: 1 entries, 1 primitive entries" in summary.out
    assert "errors: none" in summary.out
    assert json_result == 0
    assert payload["passed"] is True
    assert payload["target"] == "style_ir_inspect_app:app"
    assert payload["counts"] == {
        "rules": 1,
        "classOps": 1,
        "directStyles": 1,
        "directStyleOps": 1,
        "errors": 0,
    }
    assert payload["classes"][0]["appliedDeclarations"]["color"] == {
        "type": "literal",
        "value": "#111827",
    }
    assert payload["directStyles"][0]["appliedDeclarations"] == {
        "gap": {"type": "size", "value": 4, "unit": "px"},
        "padding": {"type": "size", "value": 8, "unit": "px"},
    }

def test_cli_style_ir_strict_detects_style_ops_drift(tmp_path, monkeypatch, capsys):
    app = tmp_path / "style_ir_strict_app.py"
    app.write_text(
        "from otoe import Text\n"
        "app = Text('Strict', className='shell')\n",
        encoding="utf-8",
    )
    styles = tmp_path / "styles.css"
    styles.write_text(".shell { color: #111827; }\n", encoding="utf-8")
    profile_file = tmp_path / "otoe.profile.toml"
    profile_file.write_text(
        'profile = "cage"\n'
        'css = ["styles.css"]\n'
        "\n"
        "[runtime]\n"
        'files = ["style_ir_strict_app.py"]\n',
        encoding="utf-8",
    )
    output = tmp_path / "dist" / "style-ir-strict"
    monkeypatch.syspath_prepend(str(tmp_path))

    build_result = main(
        [
            "build",
            "style_ir_strict_app:app",
            "--profile-file",
            str(profile_file),
            "--out",
            str(output),
        ]
    )
    capsys.readouterr()

    styles_path = output / "otoe-styles.json"
    payload = json.loads(styles_path.read_text(encoding="utf-8"))
    payload["styleOps"]["classes"][0]["ops"][0]["value"] = {
        "type": "literal",
        "value": "#dc2626",
    }
    styles_path.write_text(json.dumps(payload), encoding="utf-8")

    loose_result = main(["style-ir", str(styles_path)])
    loose = capsys.readouterr()
    strict_result = main(["style-ir", str(styles_path), "--strict", "--json"])
    strict = capsys.readouterr()
    strict_payload = json.loads(strict.out)

    assert build_result == 0
    assert loose_result == 0
    assert "errors: none" in loose.out
    assert strict_result == 1
    assert strict_payload["passed"] is False
    assert strict_payload["strict"]["enabled"] is True
    assert strict_payload["strict"]["passed"] is False
    assert (
        "styleOps class 'shell' applied declarations do not match compiled rules"
        in strict_payload["strict"]["errors"]
    )

def test_cli_style_ir_rejects_invalid_artifact(tmp_path, capsys):
    artifact = tmp_path / "bad-otoe-styles.json"
    artifact.write_text('{"schemaVersion": 2}\n', encoding="utf-8")

    result = main(["style-ir", str(artifact)])

    captured = capsys.readouterr()
    assert result == 1
    assert (
        "style-ir: style artifact: unsupported schemaVersion 2; expected 1"
        in captured.err
    )

def test_cli_compare_contract_accepts_matching_json(tmp_path, capsys):
    expected = tmp_path / "expected.json"
    actual = tmp_path / "actual.json"
    payload = {
        "schemaVersion": 1,
        "format": "renderer-contract-compact",
        "runs": {
            "minimal": {
                "after": {
                    "hashes": {
                        "layout": "sha256:aaa",
                        "paint": "sha256:bbb",
                    }
                }
            }
        },
    }
    expected.write_text(json.dumps(payload), encoding="utf-8")
    actual.write_text(json.dumps(payload), encoding="utf-8")

    result = main(["compare-contract", str(expected), str(actual)])

    captured = capsys.readouterr()
    assert result == 0
    assert f"contracts match: {expected} == {actual}" in captured.out
    assert captured.err == ""

def test_cli_compare_contract_reports_human_differences(tmp_path, capsys):
    expected = tmp_path / "expected.json"
    actual = tmp_path / "actual.json"
    expected.write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "runs": {
                    "minimal": {
                        "after": {
                            "hashes": {"layout": "sha256:expected"},
                            "visibleText": ["One", "Two"],
                        }
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    actual.write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "runs": {
                    "minimal": {
                        "after": {
                            "hashes": {"layout": "sha256:actual"},
                            "visibleText": ["One"],
                        }
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    result = main(["compare-contract", str(expected), str(actual)])

    captured = capsys.readouterr()
    assert result == 1
    assert "contracts differ: 2 difference(s)" in captured.out
    assert "/runs/minimal/after/hashes/layout" in captured.out
    assert '"sha256:expected"' in captured.out
    assert '"sha256:actual"' in captured.out
    assert "/runs/minimal/after/visibleText: length 2 != 1" in captured.out

def test_cli_compare_contract_ignores_json_pointer_paths(tmp_path, capsys):
    expected = tmp_path / "expected.json"
    actual = tmp_path / "actual.json"
    expected.write_text(
        json.dumps(
            {
                "pngSmoke": {
                    "path": "expected.png",
                    "frame": {"hashes": {"layout": "sha256:same"}},
                },
                "calls": [{"subject": "expected"}, {"subject": "stable"}],
            }
        ),
        encoding="utf-8",
    )
    actual.write_text(
        json.dumps(
            {
                "pngSmoke": {
                    "path": "actual.png",
                    "frame": {"hashes": {"layout": "sha256:same"}},
                },
                "calls": [{"subject": "actual"}, {"subject": "stable"}],
            }
        ),
        encoding="utf-8",
    )

    result = main(
        [
            "compare-contract",
            str(expected),
            str(actual),
            "--ignore-path",
            "/pngSmoke/path",
            "--ignore-path",
            "/calls/0/subject",
            "--json",
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert result == 0
    assert payload["matched"] is True
    assert payload["differenceCount"] == 0
    assert payload["ignoredPaths"] == ["/pngSmoke/path", "/calls/0/subject"]

def test_cli_compare_contract_outputs_json_report(tmp_path, capsys):
    expected = tmp_path / "expected.json"
    actual = tmp_path / "actual.json"
    expected.write_text(json.dumps({"a": {"b": 1}}), encoding="utf-8")
    actual.write_text(json.dumps({"a": {"b": 2}, "extra": True}), encoding="utf-8")

    result = main(["compare-contract", str(expected), str(actual), "--json"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert result == 1
    assert payload["schemaVersion"] == 1
    assert payload["matched"] is False
    assert payload["differenceCount"] == 2
    assert payload["differences"] == [
        {
            "actual": True,
            "expected": None,
            "kind": "extra",
            "path": "/extra",
        },
        {
            "actual": 2,
            "expected": 1,
            "kind": "value",
            "path": "/a/b",
        },
    ]

def test_cli_compare_contract_limits_reported_differences(tmp_path, capsys):
    expected = tmp_path / "expected.json"
    actual = tmp_path / "actual.json"
    expected.write_text(json.dumps({"a": 1, "b": 2, "c": 3}), encoding="utf-8")
    actual.write_text(json.dumps({"a": 4, "b": 5, "c": 6}), encoding="utf-8")

    result = main(
        [
            "compare-contract",
            str(expected),
            str(actual),
            "--max-diffs",
            "1",
        ]
    )

    captured = capsys.readouterr()
    assert result == 1
    assert "contracts differ: 3 difference(s)" in captured.out
    assert "- /a:" in captured.out
    assert "- /b:" not in captured.out
    assert "... 2 more difference(s)" in captured.out

def test_cli_compare_contract_rejects_invalid_ignore_path(tmp_path, capsys):
    expected = tmp_path / "expected.json"
    actual = tmp_path / "actual.json"
    expected.write_text("{}", encoding="utf-8")
    actual.write_text("{}", encoding="utf-8")

    result = main(
        [
            "compare-contract",
            str(expected),
            str(actual),
            "--ignore-path",
            "pngSmoke/path",
        ]
    )

    captured = capsys.readouterr()
    assert result == 1
    assert "compare-contract: ignore path must be a JSON pointer" in captured.err

def test_cli_compare_contract_rejects_missing_or_invalid_json(tmp_path, capsys):
    invalid = tmp_path / "invalid.json"
    valid = tmp_path / "valid.json"
    invalid.write_text("{ nope", encoding="utf-8")
    valid.write_text("{}", encoding="utf-8")

    missing_result = main(
        ["compare-contract", str(tmp_path / "missing.json"), str(valid)]
    )
    invalid_result = main(["compare-contract", str(invalid), str(valid)])

    captured = capsys.readouterr()
    assert missing_result == 1
    assert invalid_result == 1
    assert "compare-contract: expected file" in captured.err
    assert "does not exist" in captured.err
    assert "compare-contract: expected file" in captured.err
    assert "is not valid JSON" in captured.err
