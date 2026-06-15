from cli_helpers import (
    hashlib,
    json,
    main,
    _write_backend_capability_profile,
)

def test_cli_build_writes_minimal_bundle_manifest(tmp_path, monkeypatch, capsys):
    module = tmp_path / "build_surface.py"
    module.write_text(
        "from otoe import Text, VStack\n"
        "app = VStack(Text('Build'), className='p-4 bg-panel')\n",
        encoding="utf-8",
    )
    profile_file = tmp_path / "otoe.profile.toml"
    profile_file.write_text(
        'profile = "cage"\n'
        "utilities = true\n"
        "\n"
        "[runtime]\n"
        "allow_runtime_installs = false\n"
        "\n"
        "[backend]\n"
        'name = "native"\n',
        encoding="utf-8",
    )
    output = tmp_path / "dist" / "cage"
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "build",
            "build_surface:app",
            "--profile-file",
            str(profile_file),
            "--out",
            str(output),
        ]
    )

    captured = capsys.readouterr()
    plan = json.loads((output / "otoe-plan.json").read_text(encoding="utf-8"))
    deps = json.loads((output / "otoe-deps.json").read_text(encoding="utf-8"))
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    runtime_data = module.read_bytes()
    assert result == 0
    assert f"build build_surface:app: {output}" in captured.out
    assert f"deps artifact: {output / 'otoe-deps.json'}" in captured.out
    assert f"styles artifact: {output / 'otoe-styles.json'}" in captured.out
    assert f"render tree artifact: {output / 'otoe-render-tree.json'}" in captured.out
    assert plan["status"] == "ok"
    assert deps["status"] == "ok"
    artifacts = manifest.pop("artifacts")
    framework_files = manifest.pop("frameworkFiles")
    runner = manifest.pop("runner")
    assert artifacts == [
        {
            "path": "otoe-plan.json",
            "size": (output / "otoe-plan.json").stat().st_size,
            "sha256": hashlib.sha256(
                (output / "otoe-plan.json").read_bytes()
            ).hexdigest(),
        },
        {
            "path": "otoe-deps.json",
            "size": (output / "otoe-deps.json").stat().st_size,
            "sha256": hashlib.sha256(
                (output / "otoe-deps.json").read_bytes()
            ).hexdigest(),
        },
        {
            "path": "otoe-styles.json",
            "size": (output / "otoe-styles.json").stat().st_size,
            "sha256": hashlib.sha256(
                (output / "otoe-styles.json").read_bytes()
            ).hexdigest(),
        },
        {
            "path": "otoe-render-tree.json",
            "size": (output / "otoe-render-tree.json").stat().st_size,
            "sha256": hashlib.sha256(
                (output / "otoe-render-tree.json").read_bytes()
            ).hexdigest(),
        },
    ]
    assert {
        "source": "otoe/native.py",
        "bundlePath": "framework/otoe/native.py",
        "size": (output / "framework" / "otoe" / "native.py").stat().st_size,
        "sha256": hashlib.sha256(
            (output / "framework" / "otoe" / "native.py").read_bytes()
        ).hexdigest(),
    } in framework_files
    assert {
        "source": "otoe/_native_backend.py",
        "bundlePath": "framework/otoe/_native_backend.py",
        "size": (output / "framework" / "otoe" / "_native_backend.py").stat().st_size,
        "sha256": hashlib.sha256(
            (output / "framework" / "otoe" / "_native_backend.py").read_bytes()
        ).hexdigest(),
    } in framework_files
    assert {
        "source": "otoe/__init__.py",
        "bundlePath": "framework/otoe/__init__.py",
        "size": (output / "framework" / "otoe" / "__init__.py").stat().st_size,
        "sha256": hashlib.sha256(
            (output / "framework" / "otoe" / "__init__.py").read_bytes()
        ).hexdigest(),
    } in framework_files
    assert {
        "source": "otoe/style_ops.py",
        "bundlePath": "framework/otoe/style_ops.py",
        "size": (output / "framework" / "otoe" / "style_ops.py").stat().st_size,
        "sha256": hashlib.sha256(
            (output / "framework" / "otoe" / "style_ops.py").read_bytes()
        ).hexdigest(),
    } in framework_files
    assert {
        "source": "otoe/bundle_backend_coverage.py",
        "bundlePath": "framework/otoe/bundle_backend_coverage.py",
        "size": (
            output / "framework" / "otoe" / "bundle_backend_coverage.py"
        ).stat().st_size,
        "sha256": hashlib.sha256(
            (output / "framework" / "otoe" / "bundle_backend_coverage.py").read_bytes()
        ).hexdigest(),
    } in framework_files
    assert {
        "source": "otoe/bundle_backend_package.py",
        "bundlePath": "framework/otoe/bundle_backend_package.py",
        "size": (
            output / "framework" / "otoe" / "bundle_backend_package.py"
        ).stat().st_size,
        "sha256": hashlib.sha256(
            (output / "framework" / "otoe" / "bundle_backend_package.py").read_bytes()
        ).hexdigest(),
    } in framework_files
    assert {
        "source": "otoe/bundle_deps.py",
        "bundlePath": "framework/otoe/bundle_deps.py",
        "size": (output / "framework" / "otoe" / "bundle_deps.py").stat().st_size,
        "sha256": hashlib.sha256(
            (output / "framework" / "otoe" / "bundle_deps.py").read_bytes()
        ).hexdigest(),
    } in framework_files
    assert {
        "source": "otoe/_render_identity.py",
        "bundlePath": "framework/otoe/_render_identity.py",
        "size": (
            output / "framework" / "otoe" / "_render_identity.py"
        ).stat().st_size,
        "sha256": hashlib.sha256(
            (output / "framework" / "otoe" / "_render_identity.py").read_bytes()
        ).hexdigest(),
    } in framework_files
    assert not (output / "framework" / "otoe" / "build.py").exists()
    assert runner == {
        "path": "otoe-run.py",
        "pythonPath": ["app", "framework"],
        "modes": [
            "backend-package-check",
            "check",
            "external-backend-check",
            "layout-check",
            "png",
            "verify",
        ],
        "size": (output / "otoe-run.py").stat().st_size,
        "sha256": hashlib.sha256((output / "otoe-run.py").read_bytes()).hexdigest(),
    }
    assert manifest == {
        "schemaVersion": 1,
        "target": "build_surface:app",
        "profile": "cage",
        "backend": "native",
        "backendCapability": "native-python",
        "runtimeInstallsAllowed": False,
        "plan": "otoe-plan.json",
        "deps": "otoe-deps.json",
        "styles": "otoe-styles.json",
        "renderTree": "otoe-render-tree.json",
        "assets": [],
        "runtimeFiles": [
            {
                "source": "build_surface.py",
                "bundlePath": "app/build_surface.py",
                "size": len(runtime_data),
                "sha256": hashlib.sha256(runtime_data).hexdigest(),
            }
        ],
        "status": "ok",
    }

def test_cli_build_uses_backend_capability_profile_json(
    tmp_path,
    monkeypatch,
    capsys,
):
    module = tmp_path / "build_backend_profile_surface.py"
    module.write_text(
        "from otoe import Text, VStack\n"
        "app = VStack(Text('Build profile'), className='shell')\n",
        encoding="utf-8",
    )
    styles = tmp_path / "styles.css"
    styles.write_text(
        ".shell { padding: 8; background: #ffffff; }\n",
        encoding="utf-8",
    )
    backend_profile = tmp_path / "candidate-profile.json"
    _write_backend_capability_profile(
        backend_profile,
        name="candidate-build",
        styles={"background": "paint", "padding": "layout"},
        widgets={"Text": "text", "VStack": "container"},
    )
    output = tmp_path / "dist" / "candidate-build"
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "build",
            "build_backend_profile_surface:app",
            "--css",
            str(styles),
            "--backend-capability-profile",
            str(backend_profile),
            "--out",
            str(output),
        ]
    )

    capsys.readouterr()
    plan = json.loads((output / "otoe-plan.json").read_text(encoding="utf-8"))
    styles_payload = json.loads(
        (output / "otoe-styles.json").read_text(encoding="utf-8")
    )
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    assert result == 0
    assert plan["backend"] == "candidate-build"
    assert plan["backendCapabilities"]["styles"] == {
        "background": "paint",
        "padding": "layout",
    }
    assert styles_payload["backend"] == "candidate-build"
    assert styles_payload["styleOps"]["backend"] == "candidate-build"
    assert styles_payload["styleOps"]["capabilities"]["styles"] == {
        "background": "paint",
        "padding": "layout",
    }
    assert manifest["backendCapability"] == "candidate-build"

def test_cli_build_validate_accepts_relative_output_path(
    tmp_path,
    monkeypatch,
    capsys,
):
    app = tmp_path / "relative_build_app.py"
    app.write_text(
        "from otoe import Text\n"
        "app = Text('Relative build')\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "build",
            "relative_build_app:app",
            "--out",
            "dist/cage",
            "--validate",
        ]
    )

    captured = capsys.readouterr()
    assert result == 0
    assert "validation: ok" in captured.out
    assert (tmp_path / "dist" / "cage" / "otoe-run.py").exists()
    assert (tmp_path / "dist" / "cage" / "manifest.json").exists()

def test_cli_build_compiles_low_level_style_ops_for_omitted_declarations(
    tmp_path,
    monkeypatch,
):
    app = tmp_path / "style_ops_bundle_app.py"
    app.write_text(
        "from otoe import Text, VStack\n"
        "app = VStack(Text('Ops'), className='shell')\n",
        encoding="utf-8",
    )
    styles = tmp_path / "styles.css"
    styles.write_text(
        ".shell { padding: 8px; width: 50%; border-style: solid; color: #111827; }\n",
        encoding="utf-8",
    )
    profile_file = tmp_path / "otoe.profile.toml"
    profile_file.write_text(
        'profile = "cage"\n'
        'css = ["styles.css"]\n'
        "\n"
        "[runtime]\n"
        'files = ["style_ops_bundle_app.py"]\n',
        encoding="utf-8",
    )
    output = tmp_path / "dist" / "style-ops"
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "build",
            "style_ops_bundle_app:app",
            "--profile-file",
            str(profile_file),
            "--out",
            str(output),
            "--validate",
        ]
    )

    styles_payload = json.loads((output / "otoe-styles.json").read_text("utf-8"))
    shell_ops = styles_payload["styleOps"]["classes"][0]
    assert result == 0
    assert styles_payload["status"] == "warnings"
    assert styles_payload["backend"] == "native-python"
    assert styles_payload["backendCapabilities"]["styles"]["width"] == "layout"
    assert styles_payload["styleOps"]["backend"] == "native-python"
    assert styles_payload["styleOps"]["capabilities"]["styles"]["width"] == "layout"
    assert shell_ops["className"] == "shell"
    assert shell_ops["ops"] == [
        {
            "op": "setStyle",
            "property": "padding",
            "support": "layout",
            "value": {"type": "size", "value": 8, "unit": "px"},
        },
        {
            "op": "setStyle",
            "property": "color",
            "support": "paint",
            "value": {"type": "literal", "value": "#111827"},
        },
    ]
    assert shell_ops["omittedOps"] == [
        {
            "op": "omitStyle",
            "property": "width",
            "support": "layout",
            "status": "deferred",
            "value": {"type": "size", "value": 50, "unit": "%"},
            "message": "property 'width' uses non-px dimension '%'",
        },
        {
            "op": "omitStyle",
            "property": "borderStyle",
            "support": "ignored",
            "status": "html-only",
            "value": {"type": "literal", "value": "solid"},
            "message": "property 'borderStyle' is accepted but ignored by native",
        },
    ]

def test_cli_build_compiles_profile_style_safelist(tmp_path, monkeypatch):
    app = tmp_path / "safelist_bundle_app.py"
    app.write_text(
        "from otoe import Text\n"
        "app = Text('Stateful', className='is-idle')\n",
        encoding="utf-8",
    )
    styles = tmp_path / "styles.css"
    styles.write_text(
        ".is-idle { color: #111827; }\n"
        ".is-danger { color: #dc2626; }\n",
        encoding="utf-8",
    )
    profile_file = tmp_path / "otoe.profile.toml"
    profile_file.write_text(
        'profile = "cage"\n'
        'css = ["styles.css"]\n'
        "\n"
        "[styles]\n"
        'safelist = ["is-danger"]\n'
        "\n"
        "[runtime]\n"
        'files = ["safelist_bundle_app.py"]\n',
        encoding="utf-8",
    )
    output = tmp_path / "dist" / "safelist-runner"
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "build",
            "safelist_bundle_app:app",
            "--profile-file",
            str(profile_file),
            "--out",
            str(output),
            "--validate",
        ]
    )

    styles_payload = json.loads((output / "otoe-styles.json").read_text("utf-8"))
    rules = {rule["className"]: rule for rule in styles_payload["rules"]}
    assert result == 0
    assert styles_payload["classes"]["used"] == ["is-idle"]
    assert styles_payload["classes"]["safelisted"] == ["is-danger"]
    assert styles_payload["classes"]["planned"] == ["is-idle", "is-danger"]
    assert rules["is-danger"]["declarations"]["color"] == {
        "type": "literal",
        "value": "#dc2626",
    }

def test_cli_build_safelists_reactive_ui_variant_classes(tmp_path, monkeypatch):
    app = tmp_path / "ui_variant_safelist_bundle_app.py"
    app.write_text(
        "from otoe import Badge, signal\n"
        "tone = signal('neutral')\n"
        "app = Badge('Health', tone=tone)\n",
        encoding="utf-8",
    )
    styles = tmp_path / "styles.css"
    styles.write_text(
        ".ui-badge { color: #111827; }\n"
        ".is-neutral { background: #f8fafc; }\n"
        ".is-success { background: #dcfce7; }\n",
        encoding="utf-8",
    )
    profile_file = tmp_path / "otoe.profile.toml"
    profile_file.write_text(
        'profile = "cage"\n'
        'css = ["styles.css"]\n'
        "\n"
        "[styles]\n"
        'safelist = ["is-success"]\n'
        "\n"
        "[runtime]\n"
        'files = ["ui_variant_safelist_bundle_app.py"]\n',
        encoding="utf-8",
    )
    output = tmp_path / "dist" / "ui-variant-safelist"
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "build",
            "ui_variant_safelist_bundle_app:app",
            "--profile-file",
            str(profile_file),
            "--out",
            str(output),
            "--validate",
        ]
    )

    styles_payload = json.loads((output / "otoe-styles.json").read_text("utf-8"))
    rules = {rule["className"]: rule for rule in styles_payload["rules"]}
    assert result == 0
    assert styles_payload["classes"]["used"] == ["ui-badge", "is-neutral"]
    assert styles_payload["classes"]["static"] == []
    assert styles_payload["classes"]["safelisted"] == ["is-success"]
    assert styles_payload["classes"]["planned"] == [
        "ui-badge",
        "is-neutral",
        "is-success",
    ]
    assert rules["is-success"]["declarations"]["background"] == {
        "type": "literal",
        "value": "#dcfce7",
    }

def test_cli_build_compiles_static_class_names_from_local_target(
    tmp_path,
    monkeypatch,
):
    app = tmp_path / "static_class_bundle_app.py"
    app.write_text(
        "from otoe import Text, VStack, class_names, computed, signal\n"
        "ready = signal(False)\n"
        "def app():\n"
        "    state_class = computed(\n"
        "        lambda: class_names(\n"
        "            'status',\n"
        "            'is-ready' if ready.value else 'is-idle',\n"
        "        )\n"
        "    )\n"
        "    return VStack(Text('State', className=state_class), className='shell')\n",
        encoding="utf-8",
    )
    styles = tmp_path / "styles.css"
    styles.write_text(
        ".shell { padding: 8; }\n"
        ".status { color: #111827; }\n"
        ".is-idle { background: #ffffff; }\n"
        ".is-ready { background: #dcfce7; }\n",
        encoding="utf-8",
    )
    profile_file = tmp_path / "otoe.profile.toml"
    profile_file.write_text(
        'profile = "cage"\n'
        'css = ["styles.css"]\n'
        "\n"
        "[runtime]\n"
        'files = ["static_class_bundle_app.py"]\n',
        encoding="utf-8",
    )
    output = tmp_path / "dist" / "static-class-runner"
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "build",
            "static_class_bundle_app:app",
            "--profile-file",
            str(profile_file),
            "--out",
            str(output),
            "--validate",
        ]
    )

    styles_payload = json.loads((output / "otoe-styles.json").read_text("utf-8"))
    rules = {rule["className"]: rule for rule in styles_payload["rules"]}
    style_ops = {
        entry["className"]: entry
        for entry in styles_payload["styleOps"]["classes"]
    }
    assert result == 0
    assert styles_payload["classes"]["used"] == ["shell", "status", "is-idle"]
    assert styles_payload["classes"]["static"] == ["is-ready"]
    assert styles_payload["classes"]["safelisted"] == []
    assert styles_payload["classes"]["planned"] == [
        "shell",
        "status",
        "is-idle",
        "is-ready",
    ]
    assert rules["is-ready"]["declarations"]["background"] == {
        "type": "literal",
        "value": "#dcfce7",
    }
    assert style_ops["is-ready"]["ops"] == [
        {
            "op": "setStyle",
            "property": "background",
            "support": "paint",
            "value": {"type": "literal", "value": "#dcfce7"},
        }
    ]

