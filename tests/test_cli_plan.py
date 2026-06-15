from cli_helpers import (
    json,
    sys,
    main,
    _write_backend_capability_profile,
    _write_backend_coverage_requirements,
)

def test_cli_plan_reports_cage_summary_for_portable_css(
    tmp_path,
    monkeypatch,
    capsys,
):
    module = tmp_path / "planned_surface.py"
    module.write_text(
        "from otoe import Text, VStack\n"
        "app = VStack(Text('Ready', className='title'), className='shell', gap=8)\n",
        encoding="utf-8",
    )
    styles = tmp_path / "styles.css"
    styles.write_text(
        ".shell { padding: 8; background: #f8fafc; }\n"
        ".title { color: #172033; font-size: 16; }\n",
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "plan",
            "planned_surface:app",
            "--profile",
            "cage",
            "--css",
            str(styles),
        ]
    )

    captured = capsys.readouterr()
    assert result == 0
    assert "plan planned_surface:app: profile cage" in captured.out
    assert "widgets: 2" in captured.out
    assert "classes: 2 used, 2 planned, 0 html-only, 0 invalid" in captured.out
    assert "style declarations: portable=4, html-only=0, deferred=0, invalid=0" in captured.out
    assert "direct style props: portable=1, html-only=0, deferred=0, invalid=0" in captured.out
    assert "status: ok" in captured.out

def test_cli_plan_can_emit_json_report(tmp_path, monkeypatch, capsys):
    module = tmp_path / "json_plan_surface.py"
    module.write_text(
        "from otoe import Text, VStack\n"
        "app = VStack(Text('Ready', className='title'), className='shell')\n",
        encoding="utf-8",
    )
    styles = tmp_path / "styles.css"
    styles.write_text(
        ".shell { padding: 8; background: #f8fafc; }\n"
        ".title { color: #172033; }\n",
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "plan",
            "json_plan_surface:app",
            "--css",
            str(styles),
            "--json",
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert result == 0
    assert payload["schemaVersion"] == 1
    assert payload["target"] == "json_plan_surface:app"
    assert payload["profile"] == "cage"
    assert payload["backend"] == "native-python"
    assert payload["backendCapabilities"]["name"] == "native-python"
    assert payload["backendCapabilities"]["styles"]["padding"] == "layout"
    assert payload["widgetSupportCounts"] == {"container": 1, "text": 1}
    assert payload["status"] == "ok"
    assert payload["hasErrors"] is False
    assert payload["classes"] == {
        "used": ["shell", "title"],
        "static": [],
        "safelisted": [],
        "planned": ["shell", "title"],
        "htmlOnly": [],
        "invalid": [],
    }
    assert payload["styleCounts"]["portable"] == 3
    assert payload["diagnostics"] == []

def test_cli_plan_imports_target_from_current_directory_without_sys_path(
    tmp_path,
    monkeypatch,
    capsys,
):
    module = tmp_path / "cwd_plan_surface.py"
    module.write_text(
        "from otoe import Text\n"
        "app = Text('Ready')\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        sys,
        "path",
        [entry for entry in sys.path if entry not in {"", str(tmp_path)}],
    )

    result = main(["plan", "cwd_plan_surface:app", "--json"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert result == 0
    assert payload["target"] == "cwd_plan_surface:app"
    assert payload["widgetCount"] == 1

def test_cli_plan_accepts_backend_capability_override(
    tmp_path,
    monkeypatch,
    capsys,
):
    module = tmp_path / "backend_capability_surface.py"
    module.write_text(
        "from otoe import Text\n"
        "app = Text('Backend', className='title')\n",
        encoding="utf-8",
    )
    styles = tmp_path / "styles.css"
    styles.write_text(".title { color: #172033; }\n", encoding="utf-8")
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "plan",
            "backend_capability_surface:app",
            "--css",
            str(styles),
            "--backend",
            "native",
            "--json",
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert result == 0
    assert payload["backend"] == "native-python"
    assert payload["backendCapabilities"]["label"] == "Python native renderer"

def test_cli_plan_accepts_backend_capability_profile_json(
    tmp_path,
    monkeypatch,
    capsys,
):
    module = tmp_path / "backend_capability_profile_surface.py"
    module.write_text(
        "from otoe import Text, VStack\n"
        "app = VStack(Text('Backend profile'), className='shell')\n",
        encoding="utf-8",
    )
    styles = tmp_path / "styles.css"
    styles.write_text(
        ".shell { padding: 8; background: #ffffff; }\n",
        encoding="utf-8",
    )
    profile = tmp_path / "candidate-profile.json"
    _write_backend_capability_profile(
        profile,
        name="candidate-cli",
        styles={"background": "paint", "padding": "layout"},
        widgets={"Text": "text", "VStack": "container"},
    )
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "plan",
            "backend_capability_profile_surface:app",
            "--css",
            str(styles),
            "--backend-capability-profile",
            str(profile),
            "--json",
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert result == 0
    assert payload["backend"] == "candidate-cli"
    assert payload["backendCapabilities"]["label"] == "candidate-cli profile"
    assert payload["backendCapabilities"]["styles"] == {
        "background": "paint",
        "padding": "layout",
    }
    assert payload["widgetSupportCounts"] == {"container": 1, "text": 1}
    assert payload["styleCounts"]["portable"] == 2

def test_cli_plan_rejects_unknown_backend_capability(
    tmp_path,
    monkeypatch,
    capsys,
):
    module = tmp_path / "unknown_backend_capability_surface.py"
    module.write_text(
        "from otoe import Text\n"
        "app = Text('Backend')\n",
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "plan",
            "unknown_backend_capability_surface:app",
            "--backend",
            "gpu-magic",
        ]
    )

    captured = capsys.readouterr()
    assert result == 1
    assert "unsupported backend capability profile 'gpu-magic'" in captured.err

def test_cli_plan_rejects_backend_capability_and_profile_together(
    tmp_path,
    monkeypatch,
    capsys,
):
    module = tmp_path / "backend_capability_conflict_surface.py"
    module.write_text(
        "from otoe import Text\n"
        "app = Text('Backend')\n",
        encoding="utf-8",
    )
    profile = tmp_path / "candidate-profile.json"
    _write_backend_capability_profile(profile, name="candidate-conflict")
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "plan",
            "backend_capability_conflict_surface:app",
            "--backend",
            "native",
            "--backend-capability-profile",
            str(profile),
        ]
    )

    captured = capsys.readouterr()
    assert result == 1
    assert (
        "--backend and --backend-capability-profile are mutually exclusive"
        in captured.err
    )

def test_cli_plan_writes_json_artifact(tmp_path, monkeypatch, capsys):
    module = tmp_path / "plan_artifact_surface.py"
    module.write_text(
        "from otoe import Text, VStack\n"
        "app = VStack(Text('Utility'), className='p-4 bg-panel')\n",
        encoding="utf-8",
    )
    output = tmp_path / "dist" / "otoe-plan.json"
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "plan",
            "plan_artifact_surface:app",
            "--utilities",
            "--out",
            str(output),
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert result == 0
    assert output.is_file()
    assert f"plan artifact: {output}" in captured.out
    assert payload["target"] == "plan_artifact_surface:app"
    assert payload["status"] == "ok"
    assert payload["classes"]["planned"] == ["p-4", "bg-panel"]

def test_cli_plan_compiles_profile_style_safelist(
    tmp_path,
    monkeypatch,
    capsys,
):
    module = tmp_path / "safelist_plan_surface.py"
    module.write_text(
        "from otoe import Text\n"
        "app = Text('Dynamic classes', className='base')\n",
        encoding="utf-8",
    )
    styles = tmp_path / "styles.css"
    styles.write_text(
        ".base { color: #111827; }\n"
        ".is-danger { color: #dc2626; }\n",
        encoding="utf-8",
    )
    profile_file = tmp_path / "otoe.profile.toml"
    profile_file.write_text(
        'profile = "cage"\n'
        'css = ["styles.css"]\n'
        "\n"
        "[styles]\n"
        'safelist = ["is-danger"]\n',
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "plan",
            "safelist_plan_surface:app",
            "--profile-file",
            str(profile_file),
            "--json",
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert result == 0
    assert payload["classes"]["used"] == ["base"]
    assert payload["classes"]["safelisted"] == ["is-danger"]
    assert payload["classes"]["planned"] == ["base", "is-danger"]
    assert payload["styleCounts"]["portable"] == 2

def test_cli_plan_extracts_static_class_names_from_class_name_expressions(
    tmp_path,
    monkeypatch,
    capsys,
):
    module = tmp_path / "static_class_plan_surface.py"
    module.write_text(
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
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "plan",
            "static_class_plan_surface:app",
            "--css",
            str(styles),
            "--json",
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert result == 0
    assert payload["classes"]["used"] == ["shell", "status", "is-idle"]
    assert payload["classes"]["static"] == ["is-ready"]
    assert payload["classes"]["safelisted"] == []
    assert payload["classes"]["planned"] == [
        "shell",
        "status",
        "is-idle",
        "is-ready",
    ]
    assert payload["styleCounts"]["portable"] == 4

def test_cli_plan_static_class_scan_ignores_condition_literals(
    tmp_path,
    monkeypatch,
    capsys,
):
    module = tmp_path / "conditional_class_plan_surface.py"
    module.write_text(
        "from otoe import Text, class_names, computed, signal\n"
        "theme = signal('light')\n"
        "def app():\n"
        "    state_class = computed(\n"
        "        lambda: class_names(\n"
        "            'status',\n"
        "            'is-dark' if theme.value == 'dark' else 'is-light',\n"
        "        )\n"
        "    )\n"
        "    return Text('State', className=state_class)\n",
        encoding="utf-8",
    )
    styles = tmp_path / "styles.css"
    styles.write_text(
        ".status { color: #111827; }\n"
        ".is-light { background: #ffffff; }\n"
        ".is-dark { background: #000000; }\n",
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "plan",
            "conditional_class_plan_surface:app",
            "--css",
            str(styles),
            "--json",
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert result == 0
    assert payload["classes"]["used"] == ["status", "is-light"]
    assert payload["classes"]["static"] == ["is-dark"]
    assert payload["classes"]["planned"] == ["status", "is-light", "is-dark"]
    assert payload["diagnostics"] == []

def test_cli_plan_safelists_matching_ui_dynamic_classes(
    tmp_path,
    monkeypatch,
    capsys,
):
    module = tmp_path / "ui_dynamic_class_plan_surface.py"
    module.write_text(
        "from otoe import Badge, signal\n"
        "tone = signal('neutral')\n"
        "def app():\n"
        "    return Badge('State', tone=tone)\n",
        encoding="utf-8",
    )
    styles = tmp_path / "styles.css"
    styles.write_text(
        ".ui-badge { padding: 4; }\n"
        ".is-neutral { background: #ffffff; }\n"
        ".is-success { background: #dcfce7; }\n",
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "plan",
            "ui_dynamic_class_plan_surface:app",
            "--css",
            str(styles),
            "--json",
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert result == 0
    assert payload["classes"]["used"] == ["ui-badge", "is-neutral"]
    assert payload["classes"]["static"] == ["is-success"]
    assert payload["classes"]["safelisted"] == []
    assert payload["classes"]["planned"] == [
        "ui-badge",
        "is-neutral",
        "is-success",
    ]
    assert payload["diagnostics"] == []

def test_cli_plan_does_not_safelist_missing_ui_dynamic_rules(
    tmp_path,
    monkeypatch,
    capsys,
):
    module = tmp_path / "ui_dynamic_missing_rule_plan_surface.py"
    module.write_text(
        "from otoe import Badge, signal\n"
        "tone = signal('neutral')\n"
        "def app():\n"
        "    return Badge('State', tone=tone)\n",
        encoding="utf-8",
    )
    styles = tmp_path / "styles.css"
    styles.write_text(
        ".ui-badge { padding: 4; }\n"
        ".is-neutral { background: #ffffff; }\n",
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "plan",
            "ui_dynamic_missing_rule_plan_surface:app",
            "--css",
            str(styles),
            "--json",
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert result == 0
    assert payload["classes"]["used"] == ["ui-badge", "is-neutral"]
    assert payload["classes"]["static"] == []
    assert payload["classes"]["planned"] == ["ui-badge", "is-neutral"]
    assert payload["diagnostics"] == []

def test_cli_plan_does_not_extract_dynamic_f_string_class_fragments(
    tmp_path,
    monkeypatch,
    capsys,
):
    module = tmp_path / "dynamic_fstring_plan_surface.py"
    module.write_text(
        "from otoe import Text, computed, signal\n"
        "tone = signal('idle')\n"
        "app = Text(\n"
        "    'State',\n"
        "    className=computed(lambda: f'status is-{tone.value}'),\n"
        ")\n",
        encoding="utf-8",
    )
    styles = tmp_path / "styles.css"
    styles.write_text(
        ".status { color: #111827; }\n"
        ".is-idle { background: #ffffff; }\n",
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "plan",
            "dynamic_fstring_plan_surface:app",
            "--css",
            str(styles),
            "--json",
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert result == 0
    assert payload["status"] == "warnings"
    assert payload["classes"]["used"] == ["status", "is-idle"]
    assert payload["classes"]["static"] == []
    assert payload["classes"]["planned"] == ["status", "is-idle"]
    assert payload["diagnostics"] == [
        {
            "level": "warning",
            "message": (
                "dynamic className expression in "
                "dynamic_fstring_plan_surface.py:5 uses f-string interpolation; "
                "safelist possible output classes for hardware/cage builds"
            ),
        }
    ]

def test_cli_plan_rejects_invalid_profile_style_safelist_item(
    tmp_path,
    monkeypatch,
    capsys,
):
    module = tmp_path / "bad_safelist_surface.py"
    module.write_text(
        "from otoe import Text\n"
        "app = Text('Bad safelist')\n",
        encoding="utf-8",
    )
    profile_file = tmp_path / "otoe.profile.toml"
    profile_file.write_text(
        'profile = "cage"\n'
        "\n"
        "[styles]\n"
        'safelist = ["bad class"]\n',
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "plan",
            "bad_safelist_surface:app",
            "--profile-file",
            str(profile_file),
        ]
    )

    captured = capsys.readouterr()
    assert result == 1
    assert "[styles] key safelist[0] must be one non-empty class name" in captured.err

def test_cli_plan_writes_invalid_json_artifact(tmp_path, monkeypatch, capsys):
    module = tmp_path / "invalid_plan_artifact_surface.py"
    module.write_text(
        "from otoe import Text\n"
        "app = Text('Missing', className='missing')\n",
        encoding="utf-8",
    )
    output = tmp_path / "dist" / "bad-plan.json"
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "plan",
            "invalid_plan_artifact_surface:app",
            "--out",
            str(output),
            "--json",
        ]
    )

    captured = capsys.readouterr()
    stdout_payload = json.loads(captured.out)
    file_payload = json.loads(output.read_text(encoding="utf-8"))
    assert result == 1
    assert stdout_payload == file_payload
    assert stdout_payload["status"] == "invalid"
    assert stdout_payload["hasErrors"] is True
    assert stdout_payload["classes"]["invalid"] == ["missing"]

def test_cli_plan_loads_default_profile_file(tmp_path, monkeypatch, capsys):
    module = tmp_path / "profile_surface.py"
    module.write_text(
        "from otoe import Text, VStack\n"
        "app = VStack(Text('Profile'), className='p-4 custom')\n",
        encoding="utf-8",
    )
    (tmp_path / "styles.css").write_text(
        ".custom { color: #172033; }\n",
        encoding="utf-8",
    )
    (tmp_path / "otoe.profile.toml").write_text(
        'profile = "cage"\n'
        "utilities = true\n"
        'css = ["styles.css"]\n'
        "\n"
        "[runtime]\n"
        "allow_runtime_installs = false\n"
        "\n"
        "[backend]\n"
        'name = "native"\n',
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(["plan", "profile_surface:app"])

    captured = capsys.readouterr()
    assert result == 0
    assert "classes: 2 used, 2 planned, 0 html-only, 0 invalid" in captured.out
    assert "used classes: p-4, custom" in captured.out

def test_cli_plan_loads_backend_capability_from_profile(
    tmp_path,
    monkeypatch,
    capsys,
):
    module = tmp_path / "profile_backend_capability_surface.py"
    module.write_text(
        "from otoe import Text\n"
        "app = Text('Profile', className='custom')\n",
        encoding="utf-8",
    )
    styles = tmp_path / "styles.css"
    styles.write_text(".custom { color: #172033; }\n", encoding="utf-8")
    profile_file = tmp_path / "otoe.profile.toml"
    profile_file.write_text(
        'profile = "cage"\n'
        'css = ["styles.css"]\n'
        "\n"
        "[backend]\n"
        'name = "native"\n'
        'capability = "native"\n',
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "plan",
            "profile_backend_capability_surface:app",
            "--profile-file",
            str(profile_file),
            "--json",
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert result == 0
    assert payload["backend"] == "native-python"

def test_cli_plan_loads_backend_capability_profile_from_profile_file(
    tmp_path,
    monkeypatch,
    capsys,
):
    module = tmp_path / "profile_backend_capability_json_surface.py"
    module.write_text(
        "from otoe import Text, VStack\n"
        "app = VStack(Text('Profile JSON'), className='shell')\n",
        encoding="utf-8",
    )
    styles = tmp_path / "styles.css"
    styles.write_text(".shell { padding: 8; }\n", encoding="utf-8")
    profile_json = tmp_path / "candidate-profile.json"
    _write_backend_capability_profile(
        profile_json,
        name="candidate-profile-file",
        styles={"padding": "layout"},
        widgets={"Text": "text", "VStack": "container"},
    )
    profile_file = tmp_path / "otoe.profile.toml"
    profile_file.write_text(
        'profile = "cage"\n'
        'css = ["styles.css"]\n'
        "\n"
        "[backend]\n"
        'name = "native"\n'
        'capability_profile = "candidate-profile.json"\n',
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "plan",
            "profile_backend_capability_json_surface:app",
            "--profile-file",
            str(profile_file),
            "--json",
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert result == 0
    assert payload["backend"] == "candidate-profile-file"
    assert payload["backendCapabilities"]["styles"] == {"padding": "layout"}

def test_cli_plan_reports_backend_coverage_from_profile_file(
    tmp_path,
    monkeypatch,
    capsys,
):
    module = tmp_path / "profile_backend_coverage_surface.py"
    module.write_text(
        "from otoe import Text\n"
        "app = Text('Coverage profile')\n",
        encoding="utf-8",
    )
    requirements = tmp_path / "backend-requirements.json"
    _write_backend_coverage_requirements(requirements)
    profile_file = tmp_path / "otoe.profile.toml"
    profile_file.write_text(
        'profile = "cage"\n'
        "\n"
        "[backend]\n"
        'name = "native"\n'
        'coverage_requirements = "backend-requirements.json"\n',
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "plan",
            "profile_backend_coverage_surface:app",
            "--profile-file",
            str(profile_file),
            "--json",
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert result == 0
    assert payload["backendCoverage"]["backend"] == "native-python"
    assert payload["backendCoverage"]["passed"] is True
    assert payload["backendCoverage"]["blockers"] == []

def test_cli_plan_fails_when_backend_coverage_is_incomplete(
    tmp_path,
    monkeypatch,
    capsys,
):
    module = tmp_path / "profile_backend_coverage_failure_surface.py"
    module.write_text(
        "from otoe import Text\n"
        "app = Text('Coverage failure')\n",
        encoding="utf-8",
    )
    requirements = tmp_path / "backend-requirements.json"
    _write_backend_coverage_requirements(requirements, widgets=("Text", "Button"))
    profile_json = tmp_path / "candidate-profile.json"
    _write_backend_capability_profile(
        profile_json,
        name="candidate-coverage-failure",
        widgets={"Text": "text"},
    )
    profile_file = tmp_path / "otoe.profile.toml"
    profile_file.write_text(
        'profile = "cage"\n'
        "\n"
        "[backend]\n"
        'name = "native"\n'
        'capability_profile = "candidate-profile.json"\n'
        'coverage_requirements = "backend-requirements.json"\n',
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "plan",
            "profile_backend_coverage_failure_surface:app",
            "--profile-file",
            str(profile_file),
            "--json",
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert result == 1
    assert payload["status"] == "ok"
    assert payload["backendCoverage"]["passed"] is False
    assert "widgetsCoverage" in payload["backendCoverage"]["blockers"]
    assert payload["backendCoverage"]["coverage"]["widgets"]["missing"] == ["Button"]

def test_cli_plan_profile_file_resolves_css_relative_to_profile(
    tmp_path,
    monkeypatch,
    capsys,
):
    module = tmp_path / "relative_profile_surface.py"
    module.write_text(
        "from otoe import Text\n"
        "app = Text('Relative', className='custom')\n",
        encoding="utf-8",
    )
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "styles.css").write_text(
        ".custom { color: #172033; }\n",
        encoding="utf-8",
    )
    profile_file = config_dir / "otoe.profile.toml"
    profile_file.write_text(
        'profile = "cage"\n'
        'css = ["styles.css"]\n',
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "plan",
            "relative_profile_surface:app",
            "--profile-file",
            str(profile_file),
        ]
    )

    captured = capsys.readouterr()
    assert result == 0
    assert "classes: 1 used, 1 planned, 0 html-only, 0 invalid" in captured.out

def test_cli_plan_rejects_runtime_installs_in_cage_profile(
    tmp_path,
    monkeypatch,
    capsys,
):
    module = tmp_path / "runtime_install_surface.py"
    module.write_text(
        "from otoe import Text\n"
        "app = Text('No installs')\n",
        encoding="utf-8",
    )
    profile_file = tmp_path / "otoe.profile.toml"
    profile_file.write_text(
        'profile = "cage"\n'
        "\n"
        "[runtime]\n"
        "allow_runtime_installs = true\n",
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "plan",
            "runtime_install_surface:app",
            "--profile-file",
            str(profile_file),
        ]
    )

    captured = capsys.readouterr()
    assert result == 1
    assert "plan: profile 'cage' forbids runtime installs" in captured.err

def test_cli_plan_cli_css_overrides_profile_css(tmp_path, monkeypatch, capsys):
    module = tmp_path / "override_css_surface.py"
    module.write_text(
        "from otoe import Text\n"
        "app = Text('Override', className='cli')\n",
        encoding="utf-8",
    )
    profile_file = tmp_path / "otoe.profile.toml"
    profile_file.write_text(
        'profile = "cage"\n'
        'css = ["missing.css"]\n',
        encoding="utf-8",
    )
    cli_css = tmp_path / "cli.css"
    cli_css.write_text(".cli { color: #172033; }\n", encoding="utf-8")
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "plan",
            "override_css_surface:app",
            "--profile-file",
            str(profile_file),
            "--css",
            str(cli_css),
        ]
    )

    captured = capsys.readouterr()
    assert result == 0
    assert "classes: 1 used, 1 planned, 0 html-only, 0 invalid" in captured.out

def test_cli_plan_no_utilities_overrides_profile_utilities(
    tmp_path,
    monkeypatch,
    capsys,
):
    module = tmp_path / "override_utilities_surface.py"
    module.write_text(
        "from otoe import Text\n"
        "app = Text('Utility', className='p-4')\n",
        encoding="utf-8",
    )
    profile_file = tmp_path / "otoe.profile.toml"
    profile_file.write_text(
        'profile = "cage"\n'
        "utilities = true\n",
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "plan",
            "override_utilities_surface:app",
            "--profile-file",
            str(profile_file),
            "--no-utilities",
        ]
    )

    captured = capsys.readouterr()
    assert result == 1
    assert "classes: 1 used, 0 planned, 0 html-only, 1 invalid" in captured.out

def test_cli_plan_reports_missing_profile_css(tmp_path, monkeypatch, capsys):
    module = tmp_path / "missing_profile_css_surface.py"
    module.write_text(
        "from otoe import Text\n"
        "app = Text('Missing CSS')\n",
        encoding="utf-8",
    )
    profile_file = tmp_path / "otoe.profile.toml"
    profile_file.write_text(
        'profile = "cage"\n'
        'css = ["missing.css"]\n',
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "plan",
            "missing_profile_css_surface:app",
            "--profile-file",
            str(profile_file),
        ]
    )

    captured = capsys.readouterr()
    assert result == 1
    assert "plan: css file" in captured.err
    assert "missing.css" in captured.err

def test_cli_plan_can_include_builtin_utilities(tmp_path, monkeypatch, capsys):
    module = tmp_path / "utility_surface.py"
    module.write_text(
        "from otoe import Text, VStack\n"
        "app = VStack(Text('Utility'), className='p-4 bg-panel font-semibold')\n",
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(["plan", "utility_surface:app", "--utilities"])

    captured = capsys.readouterr()
    assert result == 0
    assert "classes: 3 used, 3 planned, 0 html-only, 0 invalid" in captured.out
    assert "style declarations: portable=2, html-only=1, deferred=0, invalid=0" in captured.out
    assert "status: warnings" in captured.out
    assert "property 'fontWeight' is accepted but ignored by native" in captured.out

def test_cli_plan_rejects_unknown_style_class_by_default(
    tmp_path,
    monkeypatch,
    capsys,
):
    module = tmp_path / "missing_style_surface.py"
    module.write_text(
        "from otoe import Text\n"
        "app = Text('Missing', className='missing')\n",
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(["plan", "missing_style_surface:app"])

    captured = capsys.readouterr()
    assert result == 1
    assert "classes: 1 used, 0 planned, 0 html-only, 1 invalid" in captured.out
    assert "status: invalid" in captured.out
    assert "error: class 'missing' has no portable rule" in captured.out

def test_cli_plan_can_downgrade_unknown_classes_to_html_only(
    tmp_path,
    monkeypatch,
    capsys,
):
    module = tmp_path / "html_only_surface.py"
    module.write_text(
        "from otoe import Text\n"
        "app = Text('HTML', className='marketing-only')\n",
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(["plan", "html_only_surface:app", "--no-strict-styles"])

    captured = capsys.readouterr()
    assert result == 0
    assert "classes: 1 used, 0 planned, 1 html-only, 0 invalid" in captured.out
    assert "status: warnings" in captured.out
    assert "warning: class 'marketing-only' has no portable rule" in captured.out

def test_cli_plan_reports_css_errors(tmp_path, monkeypatch, capsys):
    module = tmp_path / "bad_plan_surface.py"
    module.write_text("from otoe import Text\napp = Text('Bad plan')\n", encoding="utf-8")
    styles = tmp_path / "styles.css"
    styles.write_text(".bad { nope: 1; }\n", encoding="utf-8")
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(["plan", "bad_plan_surface:app", "--css", str(styles)])

    captured = capsys.readouterr()
    assert result == 1
    assert "plan: css file" in captured.err
    assert "Unknown style property 'nope'" in captured.err

