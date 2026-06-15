from cli_helpers import (
    json,
    deps_module,
    main,
)


def test_cli_deps_reports_ok_without_declared_deps(capsys):
    result = main(["deps", "missing_module:app"])

    captured = capsys.readouterr()
    assert result == 0
    assert "deps missing_module:app: profile cage" in captured.out
    assert "runtime installs: forbidden" in captured.out
    assert "resolution: audit-only; no lockfile; no wheel closure" in captured.out
    assert "packages: 0 declared, 0 installed, 0 missing" in captured.out
    assert "status: ok" in captured.out

def test_cli_deps_reports_missing_profile_package(tmp_path, capsys):
    profile_file = tmp_path / "otoe.profile.toml"
    profile_file.write_text(
        'profile = "cage"\n'
        "\n"
        "[deps]\n"
        'packages = ["otoe-missing-package-xyz"]\n',
        encoding="utf-8",
    )

    result = main(
        [
            "deps",
            "app:app",
            "--profile-file",
            str(profile_file),
        ]
    )

    captured = capsys.readouterr()
    assert result == 1
    assert "package otoe-missing-package-xyz: missing" in captured.out
    assert "status: invalid" in captured.out
    assert "error: package 'otoe-missing-package-xyz' is not installed" in captured.out

def test_cli_deps_can_emit_json_report(tmp_path, capsys):
    profile_file = tmp_path / "otoe.profile.toml"
    profile_file.write_text(
        'profile = "cage"\n'
        "\n"
        "[deps]\n"
        'packages = ["pytest"]\n',
        encoding="utf-8",
    )

    result = main(
        [
            "deps",
            "app:app",
            "--profile-file",
            str(profile_file),
            "--json",
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert result == 0
    assert payload["schemaVersion"] == 1
    assert payload["target"] == "app:app"
    assert payload["profile"] == "cage"
    assert payload["status"] == "ok"
    assert payload["hasErrors"] is False
    assert payload["runtimeInstallsAllowed"] is False
    assert payload["resolution"] == {
        "mode": "audit-only",
        "lockfile": False,
        "wheelClosure": False,
        "runtimeInstallsAllowed": False,
    }
    assert payload["packages"][0]["name"] == "pytest"
    assert payload["packages"][0]["status"] == "installed"
    assert "version" in payload["packages"][0]
    assert payload["extras"] == []
    assert payload["externalImports"] == []
    assert payload["runtimePolicy"] == {
        "mode": "audit-only",
        "network": "warn",
        "subprocess": "warn",
        "findings": [],
    }

def test_cli_deps_reports_declared_external_runtime_import(
    tmp_path,
    monkeypatch,
    capsys,
):
    module = tmp_path / "declared_external_import_app.py"
    module.write_text(
        "import pytest\n"
        "from otoe import Text\n"
        "app = Text('Declared external')\n",
        encoding="utf-8",
    )
    profile_file = tmp_path / "otoe.profile.toml"
    profile_file.write_text(
        'profile = "cage"\n'
        "\n"
        "[deps]\n"
        'packages = ["pytest"]\n',
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "deps",
            "declared_external_import_app:app",
            "--profile-file",
            str(profile_file),
            "--json",
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert result == 0
    assert payload["status"] == "ok"
    assert payload["externalImports"] == [
        {
            "module": "pytest",
            "source": "declared_external_import_app.py",
            "line": 1,
            "packages": ["pytest"],
            "declared": True,
            "declaredBy": "pytest",
        }
    ]

def test_cli_deps_accepts_external_import_declared_by_distribution_name(
    tmp_path,
    monkeypatch,
    capsys,
):
    module = tmp_path / "pillow_alias_import_app.py"
    module.write_text(
        "import PIL\n"
        "from otoe import Text\n"
        "app = Text('Pillow alias')\n",
        encoding="utf-8",
    )
    profile_file = tmp_path / "otoe.profile.toml"
    profile_file.write_text(
        'profile = "cage"\n'
        "\n"
        "[deps]\n"
        'packages = ["Pillow"]\n',
        encoding="utf-8",
    )
    original_version = deps_module.metadata.version

    def fake_version(name):
        if name == "Pillow":
            return "10.0.0"
        return original_version(name)

    monkeypatch.syspath_prepend(str(tmp_path))
    monkeypatch.setattr(
        deps_module.metadata,
        "packages_distributions",
        lambda: {"PIL": ["Pillow"]},
    )
    monkeypatch.setattr(deps_module.metadata, "version", fake_version)

    result = main(
        [
            "deps",
            "pillow_alias_import_app:app",
            "--profile-file",
            str(profile_file),
            "--json",
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert result == 0
    assert payload["packages"] == [
        {
            "name": "Pillow",
            "status": "installed",
            "version": "10.0.0",
        }
    ]
    assert payload["externalImports"] == [
        {
            "module": "PIL",
            "source": "pillow_alias_import_app.py",
            "line": 1,
            "packages": ["Pillow"],
            "declared": True,
            "declaredBy": "Pillow",
        }
    ]

def test_cli_deps_reports_unknown_external_import_metadata(
    tmp_path,
    monkeypatch,
    capsys,
):
    module = tmp_path / "unknown_external_import_app.py"
    module.write_text(
        "import vendorlib\n"
        "from otoe import Text\n"
        "app = Text('Unknown external')\n",
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    monkeypatch.setattr(
        deps_module.metadata,
        "packages_distributions",
        lambda: {},
    )

    result = main(["deps", "unknown_external_import_app:app"])

    captured = capsys.readouterr()
    assert result == 1
    assert (
        "external import vendorlib: undeclared; no installed package metadata "
        "found at unknown_external_import_app.py:1"
    ) in captured.out
    assert (
        "error: external import 'vendorlib' from unknown_external_import_app.py:1 "
        "is not declared in [deps] packages (no installed package metadata found)"
    ) in captured.out

def test_cli_deps_ignores_type_checking_only_external_import(
    tmp_path,
    monkeypatch,
    capsys,
):
    module = tmp_path / "type_checking_import_app.py"
    module.write_text(
        "from typing import TYPE_CHECKING\n"
        "from otoe import Text\n"
        "if TYPE_CHECKING:\n"
        "    import pytest\n"
        "app = Text('Type checking only')\n",
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(["deps", "type_checking_import_app:app", "--json"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert result == 0
    assert payload["externalImports"] == []

def test_cli_deps_reports_dynamic_literal_import_warning(
    tmp_path,
    monkeypatch,
    capsys,
):
    module = tmp_path / "dynamic_literal_import_app.py"
    module.write_text(
        "import importlib as imports\n"
        "from otoe import Text\n"
        "imports.import_module('pytest')\n"
        "app = Text('Dynamic literal import')\n",
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(["deps", "dynamic_literal_import_app:app", "--json"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert result == 0
    assert payload["status"] == "warnings"
    assert payload["externalImports"] == []
    assert payload["dynamicImports"] == [
        {
            "module": "pytest",
            "source": "dynamic_literal_import_app.py",
            "line": 3,
            "mechanism": "importlib.import_module",
            "packages": ["pytest"],
            "declared": False,
            "declaredBy": None,
        }
    ]
    assert payload["diagnostics"] == [
        {
            "level": "warning",
            "message": (
                "dynamic import 'pytest' from dynamic_literal_import_app.py:3 "
                "via importlib.import_module is not statically copied; declare "
                "required [runtime] files and [deps] packages manually "
                "(candidate packages: pytest)"
            ),
        }
    ]

def test_cli_deps_reports_unresolved_dynamic_import_expression(
    tmp_path,
    monkeypatch,
    capsys,
):
    module = tmp_path / "dynamic_expression_import_app.py"
    module.write_text(
        "def load_dynamic(module_name):\n"
        "    load_module(module_name)\n"
        "from importlib import import_module as load_module\n"
        "from otoe import Text\n"
        "module_name = 'pytest'\n"
        "__import__(module_name)\n"
        "app = Text('Dynamic expression import')\n",
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(["deps", "dynamic_expression_import_app:app", "--json"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert result == 0
    assert payload["status"] == "warnings"
    assert payload["dynamicImports"] == [
        {
            "module": None,
            "source": "dynamic_expression_import_app.py",
            "line": 2,
            "mechanism": "importlib.import_module",
            "packages": [],
            "declared": False,
            "declaredBy": None,
        },
        {
            "module": None,
            "source": "dynamic_expression_import_app.py",
            "line": 6,
            "mechanism": "__import__",
            "packages": [],
            "declared": False,
            "declaredBy": None,
        },
    ]
    assert payload["diagnostics"] == [
        {
            "level": "warning",
            "message": (
                "dynamic import expression from dynamic_expression_import_app.py:2 "
                "via importlib.import_module cannot be resolved statically; declare "
                "required [runtime] files and [deps] packages manually"
            ),
        },
        {
            "level": "warning",
            "message": (
                "dynamic import expression from dynamic_expression_import_app.py:6 "
                "via __import__ cannot be resolved statically; declare required "
                "[runtime] files and [deps] packages manually"
            ),
        },
    ]

def test_cli_deps_reports_runtime_policy_warnings(
    tmp_path,
    monkeypatch,
    capsys,
):
    module = tmp_path / "runtime_policy_warning_app.py"
    module.write_text(
        "import os\n"
        "import socket\n"
        "from otoe import Text\n"
        "os.system('echo runtime policy')\n"
        "app = Text('Runtime policy')\n",
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(["deps", "runtime_policy_warning_app:app", "--json"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert result == 0
    assert payload["status"] == "warnings"
    assert payload["runtimePolicy"] == {
        "mode": "audit-only",
        "network": "warn",
        "subprocess": "warn",
        "findings": [
            {
                "category": "network",
                "module": "socket",
                "source": "runtime_policy_warning_app.py",
                "line": 2,
                "mechanism": "import socket",
                "action": "warning",
            },
            {
                "category": "subprocess",
                "module": "os",
                "source": "runtime_policy_warning_app.py",
                "line": 4,
                "mechanism": "os.system",
                "action": "warning",
            },
        ],
    }
    assert payload["diagnostics"] == [
        {
            "level": "warning",
            "message": (
                "runtime policy network use from "
                "runtime_policy_warning_app.py:2 via import socket"
            ),
        },
        {
            "level": "warning",
            "message": (
                "runtime policy subprocess use from "
                "runtime_policy_warning_app.py:4 via os.system"
            ),
        },
    ]

def test_cli_deps_runtime_policy_error_can_block_hardware_profile(
    tmp_path,
    monkeypatch,
    capsys,
):
    module = tmp_path / "runtime_policy_error_app.py"
    module.write_text(
        "import subprocess\n"
        "from otoe import Text\n"
        "app = Text('Runtime policy error')\n",
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
    monkeypatch.syspath_prepend(str(tmp_path))

    result = main(
        [
            "deps",
            "runtime_policy_error_app:app",
            "--profile-file",
            str(profile_file),
            "--json",
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert result == 1
    assert payload["status"] == "invalid"
    assert payload["runtimePolicy"]["subprocess"] == "error"
    assert payload["runtimePolicy"]["findings"] == [
        {
            "category": "subprocess",
            "module": "subprocess",
            "source": "runtime_policy_error_app.py",
            "line": 1,
            "mechanism": "import subprocess",
            "action": "error",
        }
    ]
    assert payload["diagnostics"] == [
        {
            "level": "error",
            "message": (
                "runtime policy subprocess use from "
                "runtime_policy_error_app.py:1 via import subprocess"
            ),
        }
    ]

def test_cli_deps_rejects_invalid_runtime_policy_action(tmp_path, capsys):
    profile_file = tmp_path / "otoe.profile.toml"
    profile_file.write_text(
        'profile = "cage"\n'
        "\n"
        "[runtime.policy]\n"
        'network = "forbidden"\n',
        encoding="utf-8",
    )

    result = main(
        [
            "deps",
            "app:app",
            "--profile-file",
            str(profile_file),
        ]
    )

    captured = capsys.readouterr()
    assert result == 1
    assert (
        "deps: [runtime.policy] key 'network' must be one of "
        "'allow', 'error', 'warn'"
    ) in captured.err

def test_cli_deps_rejects_unknown_profile_extra(tmp_path, capsys):
    profile_file = tmp_path / "otoe.profile.toml"
    profile_file.write_text(
        'profile = "cage"\n'
        "\n"
        "[deps]\n"
        'extras = ["hardware-magic"]\n',
        encoding="utf-8",
    )

    result = main(
        [
            "deps",
            "app:app",
            "--profile-file",
            str(profile_file),
        ]
    )

    captured = capsys.readouterr()
    assert result == 1
    assert "extra hardware-magic: unknown" in captured.out
    assert "error: extra 'hardware-magic' is not declared by Otoe" in captured.out

def test_cli_deps_accepts_native_text_profile_extra(tmp_path, monkeypatch, capsys):
    profile_file = tmp_path / "otoe.profile.toml"
    profile_file.write_text(
        'profile = "cage"\n'
        "\n"
        "[deps]\n"
        'extras = ["native-text"]\n',
        encoding="utf-8",
    )
    original_version = deps_module.metadata.version

    def fake_version(name):
        if name == "Pillow":
            return "10.0.0"
        return original_version(name)

    monkeypatch.setattr(deps_module.metadata, "version", fake_version)

    result = main(
        [
            "deps",
            "app:app",
            "--profile-file",
            str(profile_file),
            "--json",
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert result == 0
    assert payload["status"] == "ok"
    assert payload["extras"] == [
        {
            "name": "native-text",
            "status": "known",
            "packages": [
                {
                    "name": "Pillow",
                    "status": "installed",
                    "version": "10.0.0",
                }
            ],
        }
    ]

def test_cli_deps_rejects_runtime_installs_in_cage_profile(tmp_path, capsys):
    profile_file = tmp_path / "otoe.profile.toml"
    profile_file.write_text(
        'profile = "cage"\n'
        "\n"
        "[runtime]\n"
        "allow_runtime_installs = true\n",
        encoding="utf-8",
    )

    result = main(
        [
            "deps",
            "app:app",
            "--profile-file",
            str(profile_file),
        ]
    )

    captured = capsys.readouterr()
    assert result == 1
    assert "deps: profile 'cage' forbids runtime installs" in captured.err
