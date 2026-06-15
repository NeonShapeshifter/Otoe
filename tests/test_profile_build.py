from cli_helpers import (
    hashlib,
    json,
    main,
)

def test_cli_build_validate_auto_copies_simple_target_module(
    tmp_path,
    monkeypatch,
    capsys,
):
    module = tmp_path / "auto_runtime_app.py"
    module.write_text(
        "from otoe import Text\n"
        "app = Text('Auto runtime')\n",
        encoding="utf-8",
    )
    output = tmp_path / "dist" / "auto-runtime"
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "build",
            "auto_runtime_app:app",
            "--out",
            str(output),
            "--validate",
        ]
    )

    captured = capsys.readouterr()
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    data = module.read_bytes()
    assert result == 0
    assert "validation: ok" in captured.out
    assert (output / "app" / "auto_runtime_app.py").read_bytes() == data
    assert manifest["runtimeFiles"] == [
        {
            "source": "auto_runtime_app.py",
            "bundlePath": "app/auto_runtime_app.py",
            "size": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
        }
    ]

def test_cli_build_validate_auto_copies_simple_local_imports(
    tmp_path,
    monkeypatch,
):
    module = tmp_path / "auto_import_app.py"
    module.write_text(
        "from otoe import Text\n"
        "from helper_view import view_text\n"
        "app = Text(view_text())\n",
        encoding="utf-8",
    )
    helper = tmp_path / "helper_view.py"
    helper.write_text(
        "from palette import LABEL\n"
        "def view_text():\n"
        "    return LABEL\n",
        encoding="utf-8",
    )
    palette = tmp_path / "palette.py"
    palette.write_text('LABEL = "Auto import"\n', encoding="utf-8")
    output = tmp_path / "dist" / "auto-imports"
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "build",
            "auto_import_app:app",
            "--out",
            str(output),
            "--validate",
        ]
    )

    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    runtime_files = {entry["bundlePath"]: entry for entry in manifest["runtimeFiles"]}
    assert result == 0
    assert sorted(runtime_files) == [
        "app/auto_import_app.py",
        "app/helper_view.py",
        "app/palette.py",
    ]
    for source in (module, helper, palette):
        bundle_path = f"app/{source.name}"
        data = source.read_bytes()
        assert (output / bundle_path).read_bytes() == data
        assert runtime_files[bundle_path] == {
            "source": source.name,
            "bundlePath": bundle_path,
            "size": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
        }

def test_cli_build_validate_auto_copies_package_target_runtime_files(
    tmp_path,
    monkeypatch,
):
    package = tmp_path / "workspace_pkg"
    package.mkdir()
    (package / "__init__.py").write_text(
        "from .boot import APP_NAME\n",
        encoding="utf-8",
    )
    (package / "boot.py").write_text("APP_NAME = 'Package'\n", encoding="utf-8")
    (package / "app.py").write_text(
        "from otoe import Text\n"
        "from . import views\n"
        "app = Text(views.view_text(), className='package-shell')\n",
        encoding="utf-8",
    )
    (package / "views.py").write_text(
        "from .palette import LABEL\n"
        "from workspace_pkg.tokens import SUFFIX\n"
        "def view_text():\n"
        "    return f'{LABEL} {SUFFIX}'\n",
        encoding="utf-8",
    )
    (package / "palette.py").write_text(
        "LABEL = 'Package runtime'\n",
        encoding="utf-8",
    )
    (package / "tokens.py").write_text(
        "SUFFIX = 'ready'\n",
        encoding="utf-8",
    )
    styles = tmp_path / "styles.css"
    styles.write_text(".package-shell { color: #111827; }\n", encoding="utf-8")
    output = tmp_path / "dist" / "package-auto"
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "build",
            "workspace_pkg.app:app",
            "--css",
            str(styles),
            "--out",
            str(output),
            "--validate",
        ]
    )

    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    runtime_files = {entry["bundlePath"]: entry for entry in manifest["runtimeFiles"]}
    assert result == 0
    assert sorted(runtime_files) == [
        "app/workspace_pkg/__init__.py",
        "app/workspace_pkg/app.py",
        "app/workspace_pkg/boot.py",
        "app/workspace_pkg/palette.py",
        "app/workspace_pkg/tokens.py",
        "app/workspace_pkg/views.py",
    ]
    for source in (
        package / "__init__.py",
        package / "app.py",
        package / "boot.py",
        package / "views.py",
        package / "palette.py",
        package / "tokens.py",
    ):
        relative = source.relative_to(tmp_path)
        bundle_path = f"app/{relative.as_posix()}"
        data = source.read_bytes()
        assert (output / bundle_path).read_bytes() == data
        assert runtime_files[bundle_path] == {
            "source": relative.as_posix(),
            "bundlePath": bundle_path,
            "size": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
        }

def test_cli_build_validate_auto_copies_namespace_package_runtime_files(
    tmp_path,
    monkeypatch,
):
    package = tmp_path / "namespace_pkg"
    package.mkdir()
    (package / "app.py").write_text(
        "from otoe import Text\n"
        "from namespace_pkg.views import view_text\n"
        "app = Text(view_text())\n",
        encoding="utf-8",
    )
    (package / "views.py").write_text(
        "from namespace_pkg.tokens import LABEL\n"
        "def view_text():\n"
        "    return LABEL\n",
        encoding="utf-8",
    )
    (package / "tokens.py").write_text(
        "LABEL = 'Namespace package runtime'\n",
        encoding="utf-8",
    )
    output = tmp_path / "dist" / "namespace-package-auto"
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "build",
            "namespace_pkg.app:app",
            "--out",
            str(output),
            "--validate",
        ]
    )

    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    runtime_files = {entry["bundlePath"]: entry for entry in manifest["runtimeFiles"]}
    assert result == 0
    assert sorted(runtime_files) == [
        "app/namespace_pkg/app.py",
        "app/namespace_pkg/tokens.py",
        "app/namespace_pkg/views.py",
    ]
    for source in (
        package / "app.py",
        package / "views.py",
        package / "tokens.py",
    ):
        relative = source.relative_to(tmp_path)
        bundle_path = f"app/{relative.as_posix()}"
        data = source.read_bytes()
        assert (output / bundle_path).read_bytes() == data
        assert runtime_files[bundle_path] == {
            "source": relative.as_posix(),
            "bundlePath": bundle_path,
            "size": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
        }

def test_cli_build_copies_runtime_files_into_bundle(tmp_path, monkeypatch):
    module = tmp_path / "runtime_build_surface.py"
    module.write_text(
        "from otoe import Text\n"
        "app = Text('Runtime')\n",
        encoding="utf-8",
    )
    entry = tmp_path / "app.py"
    entry.write_text("from otoe import Text\napp = Text('bundle')\n", encoding="utf-8")
    profile_file = tmp_path / "otoe.profile.toml"
    profile_file.write_text(
        'profile = "cage"\n'
        "\n"
        "[runtime]\n"
        "allow_runtime_installs = false\n"
        'files = ["app.py"]\n',
        encoding="utf-8",
    )
    output = tmp_path / "dist" / "runtime-build"
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "build",
            "runtime_build_surface:app",
            "--profile-file",
            str(profile_file),
            "--out",
            str(output),
        ]
    )

    copied = output / "app" / "app.py"
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    data = entry.read_bytes()
    module_data = module.read_bytes()
    assert result == 0
    assert copied.read_bytes() == data
    assert manifest["runtimeFiles"] == [
        {
            "source": "runtime_build_surface.py",
            "bundlePath": "app/runtime_build_surface.py",
            "size": len(module_data),
            "sha256": hashlib.sha256(module_data).hexdigest(),
        },
        {
            "source": "app.py",
            "bundlePath": "app/app.py",
            "size": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
        }
    ]

def test_cli_build_rejects_missing_runtime_file_without_manifest(
    tmp_path,
    monkeypatch,
    capsys,
):
    module = tmp_path / "missing_runtime_build_surface.py"
    module.write_text(
        "from otoe import Text\n"
        "app = Text('Missing runtime')\n",
        encoding="utf-8",
    )
    profile_file = tmp_path / "otoe.profile.toml"
    profile_file.write_text(
        'profile = "cage"\n'
        "\n"
        "[runtime]\n"
        'files = ["missing_app.py"]\n',
        encoding="utf-8",
    )
    output = tmp_path / "dist" / "missing-runtime"
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "build",
            "missing_runtime_build_surface:app",
            "--profile-file",
            str(profile_file),
            "--out",
            str(output),
        ]
    )

    captured = capsys.readouterr()
    assert result == 1
    assert (output / "otoe-plan.json").is_file()
    assert not (output / "manifest.json").exists()
    assert "build: runtime file" in captured.err
    assert "missing_app.py" in captured.err

def test_cli_build_rejects_unsafe_runtime_file_path(
    tmp_path,
    monkeypatch,
    capsys,
):
    module = tmp_path / "unsafe_runtime_build_surface.py"
    module.write_text(
        "from otoe import Text\n"
        "app = Text('Unsafe runtime')\n",
        encoding="utf-8",
    )
    profile_file = tmp_path / "otoe.profile.toml"
    profile_file.write_text(
        'profile = "cage"\n'
        "\n"
        "[runtime]\n"
        'files = ["../app.py"]\n',
        encoding="utf-8",
    )
    output = tmp_path / "dist" / "unsafe-runtime"
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "build",
            "unsafe_runtime_build_surface:app",
            "--profile-file",
            str(profile_file),
            "--out",
            str(output),
        ]
    )

    captured = capsys.readouterr()
    assert result == 1
    assert "build: profile file key 'runtime.files[0]' must not contain" in captured.err
    assert not output.exists()

def test_cli_build_copies_profile_assets_into_bundle(tmp_path, monkeypatch):
    module = tmp_path / "asset_build_surface.py"
    module.write_text(
        "from otoe import Text\n"
        "app = Text('Assets')\n",
        encoding="utf-8",
    )
    asset = tmp_path / "static" / "logo.txt"
    asset.parent.mkdir()
    asset.write_text("otoe asset\n", encoding="utf-8")
    profile_file = tmp_path / "otoe.profile.toml"
    profile_file.write_text(
        'profile = "cage"\n'
        'assets = ["static/logo.txt"]\n',
        encoding="utf-8",
    )
    output = tmp_path / "dist" / "asset-build"
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "build",
            "asset_build_surface:app",
            "--profile-file",
            str(profile_file),
            "--out",
            str(output),
        ]
    )

    copied = output / "assets" / "static" / "logo.txt"
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    data = asset.read_bytes()
    assert result == 0
    assert copied.read_bytes() == data
    assert manifest["assets"] == [
        {
            "source": "static/logo.txt",
            "bundlePath": "assets/static/logo.txt",
            "size": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
        }
    ]

def test_cli_build_rejects_missing_asset_without_manifest(
    tmp_path,
    monkeypatch,
    capsys,
):
    module = tmp_path / "missing_asset_build_surface.py"
    module.write_text(
        "from otoe import Text\n"
        "app = Text('Missing asset')\n",
        encoding="utf-8",
    )
    profile_file = tmp_path / "otoe.profile.toml"
    profile_file.write_text(
        'profile = "cage"\n'
        'assets = ["static/missing.txt"]\n',
        encoding="utf-8",
    )
    output = tmp_path / "dist" / "missing-asset"
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "build",
            "missing_asset_build_surface:app",
            "--profile-file",
            str(profile_file),
            "--out",
            str(output),
        ]
    )

    captured = capsys.readouterr()
    assert result == 1
    assert (output / "otoe-plan.json").is_file()
    assert not (output / "manifest.json").exists()
    assert "build: asset file" in captured.err
    assert "static/missing.txt" in captured.err

def test_cli_build_rejects_unsafe_asset_path(tmp_path, monkeypatch, capsys):
    module = tmp_path / "unsafe_asset_build_surface.py"
    module.write_text(
        "from otoe import Text\n"
        "app = Text('Unsafe asset')\n",
        encoding="utf-8",
    )
    profile_file = tmp_path / "otoe.profile.toml"
    profile_file.write_text(
        'profile = "cage"\n'
        'assets = ["../secret.txt"]\n',
        encoding="utf-8",
    )
    output = tmp_path / "dist" / "unsafe-asset"
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "build",
            "unsafe_asset_build_surface:app",
            "--profile-file",
            str(profile_file),
            "--out",
            str(output),
        ]
    )

    captured = capsys.readouterr()
    assert result == 1
    assert "build: profile file key 'assets[0]' must not contain" in captured.err
    assert not output.exists()

def test_cli_build_allows_warning_plan_status(tmp_path, monkeypatch):
    module = tmp_path / "warning_build_surface.py"
    module.write_text(
        "from otoe import Text\n"
        "app = Text('Warning', className='font-semibold')\n",
        encoding="utf-8",
    )
    output = tmp_path / "dist" / "warning"
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "build",
            "warning_build_surface:app",
            "--utilities",
            "--out",
            str(output),
        ]
    )

    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    plan = json.loads((output / "otoe-plan.json").read_text(encoding="utf-8"))
    assert result == 0
    assert plan["status"] == "warnings"
    assert manifest["status"] == "warnings"

def test_cli_build_fails_for_invalid_plan_without_manifest(
    tmp_path,
    monkeypatch,
    capsys,
):
    module = tmp_path / "invalid_build_surface.py"
    module.write_text(
        "from otoe import Text\n"
        "app = Text('Invalid', className='missing')\n",
        encoding="utf-8",
    )
    output = tmp_path / "dist" / "invalid"
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(["build", "invalid_build_surface:app", "--out", str(output)])

    captured = capsys.readouterr()
    plan = json.loads((output / "otoe-plan.json").read_text(encoding="utf-8"))
    assert result == 1
    assert plan["status"] == "invalid"
    assert not (output / "manifest.json").exists()
    assert "build: plan invalid; refusing to write build manifest" in captured.err

def test_cli_build_fails_for_invalid_dependency_audit_without_manifest(
    tmp_path,
    monkeypatch,
    capsys,
):
    module = tmp_path / "invalid_deps_build_surface.py"
    module.write_text(
        "from otoe import Text\n"
        "app = Text('Invalid deps')\n",
        encoding="utf-8",
    )
    profile_file = tmp_path / "otoe.profile.toml"
    profile_file.write_text(
        'profile = "cage"\n'
        "\n"
        "[deps]\n"
        'packages = ["otoe-missing-package-xyz"]\n',
        encoding="utf-8",
    )
    output = tmp_path / "dist" / "invalid-deps"
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "build",
            "invalid_deps_build_surface:app",
            "--profile-file",
            str(profile_file),
            "--out",
            str(output),
        ]
    )

    captured = capsys.readouterr()
    plan = json.loads((output / "otoe-plan.json").read_text(encoding="utf-8"))
    deps = json.loads((output / "otoe-deps.json").read_text(encoding="utf-8"))
    assert result == 1
    assert plan["status"] == "ok"
    assert deps["status"] == "invalid"
    assert deps["packages"][0] == {
        "name": "otoe-missing-package-xyz",
        "status": "missing",
    }
    assert not (output / "manifest.json").exists()
    assert (
        "build: dependency audit invalid; refusing to write build manifest"
        in captured.err
    )

def test_cli_build_rejects_undeclared_external_runtime_import(
    tmp_path,
    monkeypatch,
    capsys,
):
    module = tmp_path / "undeclared_external_import_app.py"
    module.write_text(
        "import pytest\n"
        "from otoe import Text\n"
        "app = Text(pytest.__name__)\n",
        encoding="utf-8",
    )
    output = tmp_path / "dist" / "undeclared-external-import"
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "build",
            "undeclared_external_import_app:app",
            "--out",
            str(output),
        ]
    )

    captured = capsys.readouterr()
    deps = json.loads((output / "otoe-deps.json").read_text(encoding="utf-8"))
    assert result == 1
    assert deps["status"] == "invalid"
    assert deps["externalImports"] == [
        {
            "module": "pytest",
            "source": "undeclared_external_import_app.py",
            "line": 1,
            "packages": ["pytest"],
            "declared": False,
            "declaredBy": None,
        }
    ]
    assert deps["diagnostics"] == [
        {
            "level": "error",
            "message": (
                "external import 'pytest' from "
                "undeclared_external_import_app.py:1 is not declared in "
                "[deps] packages (candidate packages: pytest)"
            ),
        }
    ]
    assert not (output / "manifest.json").exists()
    assert (
        "build: dependency audit invalid; refusing to write build manifest"
        in captured.err
    )

def test_cli_build_rejects_unknown_backend_without_manifest(
    tmp_path,
    monkeypatch,
    capsys,
):
    module = tmp_path / "unknown_backend_build_surface.py"
    module.write_text(
        "from otoe import Text\n"
        "app = Text('Unknown backend')\n",
        encoding="utf-8",
    )
    profile_file = tmp_path / "otoe.profile.toml"
    profile_file.write_text(
        'profile = "cage"\n'
        "\n"
        "[backend]\n"
        'name = "skia"\n',
        encoding="utf-8",
    )
    output = tmp_path / "dist" / "unknown-backend"
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "build",
            "unknown_backend_build_surface:app",
            "--profile-file",
            str(profile_file),
            "--out",
            str(output),
        ]
    )

    captured = capsys.readouterr()
    assert result == 1
    assert (output / "otoe-plan.json").is_file()
    assert (output / "otoe-deps.json").is_file()
    assert not (output / "manifest.json").exists()
    assert "build: unsupported build backend 'skia'; supported: native" in captured.err

def test_cli_build_rejects_runtime_policy_error(
    tmp_path,
    monkeypatch,
    capsys,
):
    module = tmp_path / "runtime_policy_build_error_app.py"
    module.write_text(
        "from subprocess import run\n"
        "from otoe import Text\n"
        "app = Text('Runtime policy build error')\n",
        encoding="utf-8",
    )
    profile_file = tmp_path / "otoe.profile.toml"
    profile_file.write_text(
        'profile = "cage"\n'
        "\n"
        "[runtime.policy]\n"
        'subprocess = "error"\n',
        encoding="utf-8",
    )
    output = tmp_path / "dist" / "runtime-policy-build-error"
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "build",
            "runtime_policy_build_error_app:app",
            "--profile-file",
            str(profile_file),
            "--out",
            str(output),
        ]
    )

    captured = capsys.readouterr()
    deps = json.loads((output / "otoe-deps.json").read_text(encoding="utf-8"))
    assert result == 1
    assert deps["status"] == "invalid"
    assert not (output / "manifest.json").exists()
    assert "build: dependency audit invalid" in captured.err

