from cli_helpers import (
    hashlib,
    json,
    os,
    subprocess,
    sys,
    main,
    _refresh_manifest_artifact_hash,
    _png_contains_rgba,
)

def test_cli_build_writes_runner_that_loads_copied_runtime_target(
    tmp_path,
    monkeypatch,
    capsys,
):
    app = tmp_path / "bundled_runner_app.py"
    app.write_text(
        "from otoe import Text\n"
        "app = Text('Bundled app')\n",
        encoding="utf-8",
    )
    profile_file = tmp_path / "otoe.profile.toml"
    profile_file.write_text(
        'profile = "cage"\n'
        "\n"
        "[runtime]\n"
        'files = ["bundled_runner_app.py"]\n',
        encoding="utf-8",
    )
    output = tmp_path / "dist" / "runner-build"
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "build",
            "bundled_runner_app:app",
            "--profile-file",
            str(profile_file),
            "--out",
            str(output),
            "--validate",
        ]
    )

    captured = capsys.readouterr()
    env = {**os.environ, "PYTHONPATH": ""}
    verify = subprocess.run(
        [sys.executable, str(output / "otoe-run.py"), "--verify"],
        capture_output=True,
        cwd=output,
        env=env,
        text=True,
    )
    check = subprocess.run(
        [sys.executable, str(output / "otoe-run.py"), "--check"],
        capture_output=True,
        cwd=output,
        env=env,
        text=True,
    )
    layout_check = subprocess.run(
        [sys.executable, str(output / "otoe-run.py"), "--layout-check"],
        capture_output=True,
        cwd=output,
        env=env,
        text=True,
    )
    frame = output / "frame.png"
    png = subprocess.run(
        [sys.executable, str(output / "otoe-run.py"), "--png", str(frame)],
        capture_output=True,
        cwd=output,
        env=env,
        text=True,
    )

    assert result == 0
    assert "validation: ok" in captured.out
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["runtimeFiles"] == [
        {
            "source": "bundled_runner_app.py",
            "bundlePath": "app/bundled_runner_app.py",
            "size": app.stat().st_size,
            "sha256": hashlib.sha256(app.read_bytes()).hexdigest(),
        }
    ]
    assert verify.returncode == 0, verify.stderr
    assert "verified: manifest.json" in verify.stdout
    assert check.returncode == 0, check.stderr
    assert "loaded: bundled_runner_app:app" in check.stdout
    assert layout_check.returncode == 0, layout_check.stderr
    assert "layout checked: bundled_runner_app:app" in layout_check.stdout
    assert png.returncode == 0, png.stderr
    assert frame.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")

    copied_app = output / "app" / "bundled_runner_app.py"
    copied_app.write_text(
        copied_app.read_text(encoding="utf-8").replace("Bundled app", "Bundled bad"),
        encoding="utf-8",
    )
    tampered = subprocess.run(
        [sys.executable, str(output / "otoe-run.py"), "--verify"],
        capture_output=True,
        cwd=output,
        env=env,
        text=True,
    )
    copied_app.unlink()
    missing = subprocess.run(
        [sys.executable, str(output / "otoe-run.py"), "--verify"],
        capture_output=True,
        cwd=output,
        env=env,
        text=True,
    )

    assert tampered.returncode == 1
    assert "sha256 mismatch" in tampered.stderr
    assert missing.returncode == 1
    assert "bundle file 'app/bundled_runner_app.py' does not exist" in missing.stderr

def test_cli_build_runner_rejects_manifest_schema_version(
    tmp_path,
    monkeypatch,
):
    app = tmp_path / "manifest_schema_app.py"
    app.write_text(
        "from otoe import Text\n"
        "app = Text('Manifest schema')\n",
        encoding="utf-8",
    )
    output = tmp_path / "dist" / "manifest-schema"
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "build",
            "manifest_schema_app:app",
            "--out",
            str(output),
            "--validate",
        ]
    )
    manifest_path = output / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["schemaVersion"] = 0
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    verify = subprocess.run(
        [sys.executable, str(output / "otoe-run.py"), "--verify"],
        capture_output=True,
        cwd=output,
        env={**os.environ, "PYTHONPATH": ""},
        text=True,
    )
    layout_check = subprocess.run(
        [sys.executable, str(output / "otoe-run.py"), "--layout-check"],
        capture_output=True,
        cwd=output,
        env={**os.environ, "PYTHONPATH": ""},
        text=True,
    )

    assert result == 0
    assert verify.returncode == 1
    assert "manifest.json: unsupported schemaVersion 0; expected 1" in verify.stderr
    assert layout_check.returncode == 1
    assert "manifest.json: unsupported schemaVersion 0; expected 1" in layout_check.stderr

def test_cli_build_runner_reports_missing_and_malformed_manifest(
    tmp_path,
    monkeypatch,
):
    app = tmp_path / "manifest_load_app.py"
    app.write_text(
        "from otoe import Text\n"
        "app = Text('Manifest load')\n",
        encoding="utf-8",
    )
    output = tmp_path / "dist" / "manifest-load"
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "build",
            "manifest_load_app:app",
            "--out",
            str(output),
            "--validate",
        ]
    )
    manifest_path = output / "manifest.json"
    backup_path = output / "manifest.json.bak"
    manifest_path.rename(backup_path)

    missing = _run_generated_runner(output, "--verify")

    backup_path.rename(manifest_path)
    manifest_path.write_text("{", encoding="utf-8")
    malformed = _run_generated_runner(output, "--verify")

    assert result == 0
    assert missing.returncode == 1
    assert "manifest.json" in missing.stderr
    assert "No such file or directory" in missing.stderr
    assert malformed.returncode == 1
    assert "Expecting property name enclosed in double quotes" in malformed.stderr

def test_cli_build_runner_rejects_missing_style_artifact(
    tmp_path,
    monkeypatch,
):
    app = tmp_path / "missing_style_artifact_app.py"
    app.write_text(
        "from otoe import Text\n"
        "app = Text('Missing style artifact')\n",
        encoding="utf-8",
    )
    output = tmp_path / "dist" / "missing-style-artifact"
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "build",
            "missing_style_artifact_app:app",
            "--out",
            str(output),
            "--validate",
        ]
    )
    (output / "otoe-styles.json").unlink()

    verify = _run_generated_runner(output, "--verify")
    layout_check = _run_generated_runner(output, "--layout-check")

    assert result == 0
    assert verify.returncode == 1
    assert "bundle file 'otoe-styles.json' does not exist" in verify.stderr
    assert layout_check.returncode == 1
    assert "bundle file 'otoe-styles.json' does not exist" in layout_check.stderr

def test_cli_build_runner_rejects_invalid_render_tree_artifact(
    tmp_path,
    monkeypatch,
):
    app = tmp_path / "invalid_render_tree_artifact_app.py"
    app.write_text(
        "from otoe import Text\n"
        "app = Text('Invalid render tree artifact')\n",
        encoding="utf-8",
    )
    output = tmp_path / "dist" / "invalid-render-tree-artifact"
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "build",
            "invalid_render_tree_artifact_app:app",
            "--out",
            str(output),
            "--validate",
        ]
    )
    render_tree_path = output / "otoe-render-tree.json"
    render_tree_path.write_text(
        json.dumps({"schemaVersion": 1, "format": "wrong-render-tree"}),
        encoding="utf-8",
    )
    _refresh_manifest_artifact_hash(output, "otoe-render-tree.json")

    verify = _run_generated_runner(output, "--verify")
    check = _run_generated_runner(output, "--check")

    assert result == 0
    assert verify.returncode == 1
    assert (
        "otoe-render-tree.json: RenderTree missing required fields: "
        "'nodeCount', 'root'"
    ) in verify.stderr
    assert check.returncode == 1
    assert "RenderTree missing required fields" in check.stderr

def test_cli_build_runner_rejects_style_artifact_schema_version(
    tmp_path,
    monkeypatch,
    capsys,
):
    app = tmp_path / "styles_schema_app.py"
    app.write_text(
        "from otoe import Text\n"
        "app = Text('Styles schema')\n",
        encoding="utf-8",
    )
    output = tmp_path / "dist" / "styles-schema"
    archive = tmp_path / "dist" / "styles-schema.tar.gz"
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "build",
            "styles_schema_app:app",
            "--out",
            str(output),
            "--validate",
        ]
    )
    styles_path = output / "otoe-styles.json"
    styles = json.loads(styles_path.read_text(encoding="utf-8"))
    styles["schemaVersion"] = 2
    styles_path.write_text(json.dumps(styles), encoding="utf-8")

    verify = subprocess.run(
        [sys.executable, str(output / "otoe-run.py"), "--verify"],
        capture_output=True,
        cwd=output,
        env={**os.environ, "PYTHONPATH": ""},
        text=True,
    )
    pack_result = main(["pack", str(output), "--out", str(archive)])

    captured = capsys.readouterr()
    assert result == 0
    assert verify.returncode == 1
    assert (
        "otoe-styles.json: unsupported schemaVersion 2; expected 1"
        in verify.stderr
    )
    assert pack_result == 1
    assert not archive.exists()
    assert "pack: runner verification failed:" in captured.err
    assert (
        "otoe-styles.json: unsupported schemaVersion 2; expected 1"
        in captured.err
    )

def test_cli_build_runner_rejects_style_ops_schema_version(
    tmp_path,
    monkeypatch,
):
    app = tmp_path / "style_ops_schema_app.py"
    app.write_text(
        "from otoe import Text\n"
        "app = Text('Style ops schema', className='text-danger')\n",
        encoding="utf-8",
    )
    output = tmp_path / "dist" / "style-ops-schema"
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "build",
            "style_ops_schema_app:app",
            "--out",
            str(output),
            "--utilities",
            "--validate",
        ]
    )
    styles_path = output / "otoe-styles.json"
    styles = json.loads(styles_path.read_text(encoding="utf-8"))
    styles["styleOps"]["schemaVersion"] = 2
    styles_path.write_text(json.dumps(styles), encoding="utf-8")

    verify = subprocess.run(
        [sys.executable, str(output / "otoe-run.py"), "--verify"],
        capture_output=True,
        cwd=output,
        env={**os.environ, "PYTHONPATH": ""},
        text=True,
    )
    layout_check = subprocess.run(
        [sys.executable, str(output / "otoe-run.py"), "--layout-check"],
        capture_output=True,
        cwd=output,
        env={**os.environ, "PYTHONPATH": ""},
        text=True,
    )

    assert result == 0
    assert verify.returncode == 1
    assert (
        "otoe-styles.json styleOps: unsupported schemaVersion 2; expected 1"
        in verify.stderr
    )
    assert layout_check.returncode == 1
    assert (
        "otoe-styles.json styleOps: unsupported schemaVersion 2; expected 1"
        in layout_check.stderr
    )

def test_cli_build_runner_rejects_bad_direct_style_ops_shape(
    tmp_path,
    monkeypatch,
):
    app = tmp_path / "bad_direct_style_ops_app.py"
    app.write_text(
        "from otoe import Text, VStack\n"
        "app = VStack(Text('Direct styles'), padding=8)\n",
        encoding="utf-8",
    )
    profile_file = tmp_path / "otoe.profile.toml"
    profile_file.write_text(
        'profile = "cage"\n'
        "\n"
        "[runtime]\n"
        'files = ["bad_direct_style_ops_app.py"]\n',
        encoding="utf-8",
    )
    output = tmp_path / "dist" / "bad-direct-style-ops"
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "build",
            "bad_direct_style_ops_app:app",
            "--profile-file",
            str(profile_file),
            "--out",
            str(output),
            "--validate",
        ]
    )
    styles_path = output / "otoe-styles.json"
    styles = json.loads(styles_path.read_text(encoding="utf-8"))
    styles["styleOps"]["directStyles"] = {}
    styles_path.write_text(json.dumps(styles), encoding="utf-8")

    verify = subprocess.run(
        [sys.executable, str(output / "otoe-run.py"), "--verify"],
        capture_output=True,
        cwd=output,
        env={**os.environ, "PYTHONPATH": ""},
        text=True,
    )

    assert result == 0
    assert verify.returncode == 1
    assert "otoe-styles.json: styleOps directStyles must be a list" in verify.stderr

def test_cli_build_runner_rejects_missing_framework_manifest_entry(
    tmp_path,
    monkeypatch,
):
    app = tmp_path / "missing_framework_entry_app.py"
    app.write_text(
        "from otoe import Text\n"
        "app = Text('Missing framework entry')\n",
        encoding="utf-8",
    )
    output = tmp_path / "dist" / "missing-framework-entry"
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "build",
            "missing_framework_entry_app:app",
            "--out",
            str(output),
            "--validate",
        ]
    )
    manifest_path = output / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["frameworkFiles"] = [
        entry
        for entry in manifest["frameworkFiles"]
        if entry["bundlePath"] != "framework/otoe/native.py"
    ]
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    verify = subprocess.run(
        [sys.executable, str(output / "otoe-run.py"), "--verify"],
        capture_output=True,
        cwd=output,
        env={**os.environ, "PYTHONPATH": ""},
        text=True,
    )

    assert result == 0
    assert verify.returncode == 1
    assert (
        "manifest.json: frameworkFiles missing required file "
        "'framework/otoe/native.py' for backend 'native'"
    ) in verify.stderr

def test_cli_build_runner_rejects_missing_framework_file_on_disk(
    tmp_path,
    monkeypatch,
):
    app = tmp_path / "missing_framework_file_app.py"
    app.write_text(
        "from otoe import Text\n"
        "app = Text('Missing framework file')\n",
        encoding="utf-8",
    )
    output = tmp_path / "dist" / "missing-framework-file"
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "build",
            "missing_framework_file_app:app",
            "--out",
            str(output),
            "--validate",
        ]
    )
    (output / "framework" / "otoe" / "native.py").unlink()

    verify = subprocess.run(
        [sys.executable, str(output / "otoe-run.py"), "--verify"],
        capture_output=True,
        cwd=output,
        env={**os.environ, "PYTHONPATH": ""},
        text=True,
    )

    assert result == 0
    assert verify.returncode == 1
    assert "bundle file 'framework/otoe/native.py' does not exist" in verify.stderr

def test_cli_build_runner_rejects_unsupported_manifest_backend(
    tmp_path,
    monkeypatch,
):
    app = tmp_path / "unsupported_manifest_backend_app.py"
    app.write_text(
        "from otoe import Text\n"
        "app = Text('Unsupported backend')\n",
        encoding="utf-8",
    )
    output = tmp_path / "dist" / "unsupported-manifest-backend"
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "build",
            "unsupported_manifest_backend_app:app",
            "--out",
            str(output),
            "--validate",
        ]
    )
    manifest_path = output / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["backend"] = "skia"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    verify = subprocess.run(
        [sys.executable, str(output / "otoe-run.py"), "--verify"],
        capture_output=True,
        cwd=output,
        env={**os.environ, "PYTHONPATH": ""},
        text=True,
    )

    assert result == 0
    assert verify.returncode == 1
    assert "manifest.json: unsupported backend 'skia'; supported: native" in verify.stderr

def test_cli_build_runner_png_uses_compiled_styles(tmp_path, monkeypatch):
    app = tmp_path / "styled_bundle_app.py"
    app.write_text(
        "from otoe import Text\n"
        "app = Text('Styled', className='danger')\n",
        encoding="utf-8",
    )
    styles = tmp_path / "styles.css"
    styles.write_text(
        ".danger { color: #ff0000; font-size: 18px; }\n",
        encoding="utf-8",
    )
    profile_file = tmp_path / "otoe.profile.toml"
    profile_file.write_text(
        'profile = "cage"\n'
        'css = ["styles.css"]\n'
        "\n"
        "[runtime]\n"
        'files = ["styled_bundle_app.py"]\n',
        encoding="utf-8",
    )
    output = tmp_path / "dist" / "styled-runner"
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "build",
            "styled_bundle_app:app",
            "--profile-file",
            str(profile_file),
            "--out",
            str(output),
            "--validate",
        ]
    )

    styles_payload = json.loads((output / "otoe-styles.json").read_text("utf-8"))
    danger_rule = next(
        rule for rule in styles_payload["rules"] if rule["className"] == "danger"
    )
    frame = output / "styled.png"
    png = subprocess.run(
        [sys.executable, str(output / "otoe-run.py"), "--png", str(frame)],
        capture_output=True,
        cwd=output,
        env={**os.environ, "PYTHONPATH": ""},
        text=True,
    )

    assert result == 0
    assert danger_rule["declarations"]["color"] == {
        "type": "literal",
        "value": "#ff0000",
    }
    assert danger_rule["declarations"]["fontSize"] == {
        "type": "size",
        "value": 18,
        "unit": "px",
    }
    style_ops = {
        entry["className"]: entry
        for entry in styles_payload["styleOps"]["classes"]
    }
    assert styles_payload["styleOps"]["schemaVersion"] == 1
    assert styles_payload["styleOps"]["format"] == "otoe-style-ops"
    assert style_ops["danger"]["ops"] == [
        {
            "op": "setStyle",
            "property": "color",
            "support": "paint",
            "value": {"type": "literal", "value": "#ff0000"},
        },
        {
            "op": "setStyle",
            "property": "fontSize",
            "support": "layout+paint",
            "value": {"type": "size", "value": 18, "unit": "px"},
        },
    ]
    assert style_ops["danger"]["omittedOps"] == []
    assert png.returncode == 0, png.stderr
    assert _png_contains_rgba(frame.read_bytes(), (255, 0, 0, 255))

def test_cli_build_runner_png_accepts_html_only_missing_class(
    tmp_path,
    monkeypatch,
):
    app = tmp_path / "html_only_bundle_app.py"
    app.write_text(
        "from otoe import Text\n"
        "app = Text('Preview class', className='preview-only')\n",
        encoding="utf-8",
    )
    profile_file = tmp_path / "otoe.profile.toml"
    profile_file.write_text(
        'profile = "cage"\n'
        "\n"
        "[runtime]\n"
        'files = ["html_only_bundle_app.py"]\n',
        encoding="utf-8",
    )
    output = tmp_path / "dist" / "html-only-runner"
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "build",
            "html_only_bundle_app:app",
            "--profile-file",
            str(profile_file),
            "--out",
            str(output),
            "--no-strict-styles",
            "--validate",
        ]
    )

    styles_payload = json.loads((output / "otoe-styles.json").read_text("utf-8"))
    preview_rule = next(
        rule
        for rule in styles_payload["rules"]
        if rule["className"] == "preview-only"
    )
    frame = output / "html-only.png"
    png = subprocess.run(
        [sys.executable, str(output / "otoe-run.py"), "--png", str(frame)],
        capture_output=True,
        cwd=output,
        env={**os.environ, "PYTHONPATH": ""},
        text=True,
    )

    assert result == 0
    assert preview_rule["missing"] is True
    assert preview_rule["declarations"] == {}
    assert png.returncode == 0, png.stderr
    assert frame.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")

def test_cli_build_validate_rejects_bad_compiled_styles(
    tmp_path,
    monkeypatch,
    capsys,
):
    app = tmp_path / "bad_compiled_styles_app.py"
    app.write_text(
        "from otoe import Text\n"
        "app = Text('Bad style', className='text-sm')\n",
        encoding="utf-8",
    )
    profile_file = tmp_path / "otoe.profile.toml"
    profile_file.write_text(
        'profile = "cage"\n'
        "\n"
        "[runtime]\n"
        'files = ["bad_compiled_styles_app.py"]\n',
        encoding="utf-8",
    )
    output = tmp_path / "dist" / "bad-compiled-styles"
    monkeypatch.syspath_prepend(str(tmp_path))

    def bad_compiled_styles(plan, *, target, stylesheet):
        return {
            "schemaVersion": 1,
            "target": target,
            "profile": plan.profile,
            "status": "ok",
            "classes": {
                "used": ["text-sm"],
                "safelisted": [],
                "planned": ["text-sm"],
                "htmlOnly": [],
                "invalid": [],
            },
            "styleCounts": {
                "portable": 1,
                "html-only": 0,
                "deferred": 0,
                "invalid": 0,
            },
            "directStyleCounts": {
                "portable": 0,
                "html-only": 0,
                "deferred": 0,
                "invalid": 0,
            },
            "tokens": {},
            "rules": [
                {
                    "className": "text-sm",
                    "selector": ".text-sm",
                    "declarations": {
                        "fontSize": {"type": "literal", "value": "large"}
                    },
                    "omittedDeclarations": [],
                    "missing": False,
                }
            ],
            "directStyles": [],
            "styleOps": {
                "schemaVersion": 1,
                "format": "otoe-style-ops",
                "capabilities": {"styles": {"fontSize": "layout"}},
                "classes": [
                    {
                        "className": "text-sm",
                        "selector": ".text-sm",
                        "missing": False,
                        "ops": [
                            {
                                "op": "setStyle",
                                "property": "fontSize",
                                "support": "layout",
                                "value": {"type": "literal", "value": "large"},
                            }
                        ],
                        "omittedOps": [],
                    }
                ],
                "directStyles": [],
            },
            "diagnostics": [],
        }

    monkeypatch.setattr("otoe.cli.compiled_styles_to_dict", bad_compiled_styles)

    result = main(
        [
            "build",
            "bad_compiled_styles_app:app",
            "--profile-file",
            str(profile_file),
            "--out",
            str(output),
            "--utilities",
            "--validate",
        ]
    )

    captured = capsys.readouterr()
    assert result == 1
    assert (output / "manifest.json").is_file()
    assert "build: runner layout validation failed:" in captured.err
    assert "Native layout expected numeric fontSize" in captured.err

def test_cli_build_runner_requires_core_artifacts_in_manifest_artifacts(
    tmp_path,
    monkeypatch,
    capsys,
):
    app = tmp_path / "missing_core_artifact_entry_app.py"
    app.write_text(
        "from otoe import Text\n"
        "app = Text('Missing core artifact entry')\n",
        encoding="utf-8",
    )
    output = tmp_path / "dist" / "missing-core-artifact-entry"
    archive = tmp_path / "dist" / "missing-core-artifact-entry.tar.gz"
    monkeypatch.syspath_prepend(str(tmp_path))

    assert (
        main(
            [
                "build",
                "missing_core_artifact_entry_app:app",
                "--out",
                str(output),
            ]
        )
        == 0
    )
    manifest_path = output / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["artifacts"] = [
        artifact
        for artifact in manifest["artifacts"]
        if artifact["path"] != "otoe-plan.json"
    ]
    manifest_path.write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")

    verify = subprocess.run(
        [sys.executable, str(output / "otoe-run.py"), "--verify"],
        capture_output=True,
        cwd=output,
        env={**os.environ, "PYTHONPATH": ""},
        text=True,
    )
    check = subprocess.run(
        [sys.executable, str(output / "otoe-run.py"), "--check"],
        capture_output=True,
        cwd=output,
        env={**os.environ, "PYTHONPATH": ""},
        text=True,
    )
    result = main(["pack", str(output), "--out", str(archive)])

    captured = capsys.readouterr()
    assert verify.returncode == 1
    assert "manifest.json: artifacts missing 'otoe-plan.json'" in verify.stderr
    assert check.returncode == 1
    assert "manifest.json: artifacts missing 'otoe-plan.json'" in check.stderr
    assert result == 1
    assert "pack: runner verification failed:" in captured.err
    assert "artifacts missing 'otoe-plan.json'" in captured.err

def test_cli_build_runner_requires_manifest_file_entry_hashes(
    tmp_path,
    monkeypatch,
    capsys,
):
    app = tmp_path / "missing_manifest_hash_app.py"
    app.write_text(
        "from otoe import Text\n"
        "app = Text('Missing manifest hash')\n",
        encoding="utf-8",
    )
    output = tmp_path / "dist" / "missing-manifest-hash"
    archive = tmp_path / "dist" / "missing-manifest-hash.tar.gz"
    monkeypatch.syspath_prepend(str(tmp_path))

    assert (
        main(
            [
                "build",
                "missing_manifest_hash_app:app",
                "--out",
                str(output),
            ]
        )
        == 0
    )
    manifest_path = output / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    del manifest["runtimeFiles"][0]["sha256"]
    manifest_path.write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")

    verify = subprocess.run(
        [sys.executable, str(output / "otoe-run.py"), "--verify"],
        capture_output=True,
        cwd=output,
        env={**os.environ, "PYTHONPATH": ""},
        text=True,
    )
    result = main(["pack", str(output), "--out", str(archive)])

    captured = capsys.readouterr()
    assert verify.returncode == 1
    assert (
        "manifest.json: runtimeFiles[0].sha256 must be a lowercase sha256 hex digest"
        in verify.stderr
    )
    assert result == 1
    assert "pack: runner verification failed:" in captured.err
    assert "runtimeFiles[0].sha256 must be a lowercase sha256 hex digest" in (
        captured.err
    )
    assert not archive.exists()

def test_cli_build_runner_rejects_duplicate_manifest_bundle_paths(
    tmp_path,
    monkeypatch,
    capsys,
):
    app = tmp_path / "duplicate_manifest_path_app.py"
    app.write_text(
        "from otoe import Text\n"
        "app = Text('Duplicate manifest path')\n",
        encoding="utf-8",
    )
    output = tmp_path / "dist" / "duplicate-manifest-path"
    archive = tmp_path / "dist" / "duplicate-manifest-path.tar.gz"
    monkeypatch.syspath_prepend(str(tmp_path))

    assert (
        main(
            [
                "build",
                "duplicate_manifest_path_app:app",
                "--out",
                str(output),
            ]
        )
        == 0
    )
    manifest_path = output / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["runtimeFiles"].append(dict(manifest["runtimeFiles"][0]))
    manifest_path.write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")

    verify = subprocess.run(
        [sys.executable, str(output / "otoe-run.py"), "--verify"],
        capture_output=True,
        cwd=output,
        env={**os.environ, "PYTHONPATH": ""},
        text=True,
    )
    result = main(["pack", str(output), "--out", str(archive)])

    captured = capsys.readouterr()
    assert verify.returncode == 1
    assert (
        "manifest.json: duplicate bundle path "
        "'app/duplicate_manifest_path_app.py' in runtimeFiles[1].bundlePath; "
        "already declared by runtimeFiles[0].bundlePath"
    ) in verify.stderr
    assert result == 1
    assert "pack: runner verification failed:" in captured.err
    assert "duplicate bundle path 'app/duplicate_manifest_path_app.py'" in (
        captured.err
    )
    assert not archive.exists()

def test_cli_build_runner_rejects_runtime_installs_allowed_manifest(
    tmp_path,
    monkeypatch,
):
    app = tmp_path / "runtime_install_manifest_drift_app.py"
    app.write_text(
        "from otoe import Text\n"
        "app = Text('Runtime install drift')\n",
        encoding="utf-8",
    )
    output = tmp_path / "dist" / "runtime-install-manifest-drift"
    monkeypatch.syspath_prepend(str(tmp_path))

    assert (
        main(
            [
                "build",
                "runtime_install_manifest_drift_app:app",
                "--out",
                str(output),
            ]
        )
        == 0
    )
    manifest_path = output / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["runtimeInstallsAllowed"] = True
    manifest_path.write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")

    verify = subprocess.run(
        [sys.executable, str(output / "otoe-run.py"), "--verify"],
        capture_output=True,
        cwd=output,
        env={**os.environ, "PYTHONPATH": ""},
        text=True,
    )

    assert verify.returncode == 1
    assert "manifest.json: runtimeInstallsAllowed must be false" in verify.stderr

def test_cli_build_runner_rejects_unmanifested_bundle_file(
    tmp_path,
    monkeypatch,
):
    app = tmp_path / "unmanifested_bundle_file_app.py"
    app.write_text(
        "from otoe import Text\n"
        "app = Text('Unmanifested bundle file')\n",
        encoding="utf-8",
    )
    output = tmp_path / "dist" / "unmanifested-bundle-file"
    monkeypatch.syspath_prepend(str(tmp_path))

    assert (
        main(
            [
                "build",
                "unmanifested_bundle_file_app:app",
                "--out",
                str(output),
            ]
        )
        == 0
    )
    (output / "app" / "extra.py").write_text("value = 1\n", encoding="utf-8")

    verify = _run_generated_runner(output, "--verify")

    assert verify.returncode == 1
    assert "unmanifested bundle file 'app/extra.py'" in verify.stderr


def _run_generated_runner(output, *args):
    return subprocess.run(
        [sys.executable, str(output / "otoe-run.py"), *args],
        capture_output=True,
        cwd=output,
        env={**os.environ, "PYTHONPATH": ""},
        text=True,
    )
