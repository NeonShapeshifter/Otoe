from __future__ import annotations

import sys
import types
from pathlib import Path

from otoe.runtime_files import auto_target_runtime_files


def test_auto_target_runtime_files_follow_dotted_package_imports(
    tmp_path,
    monkeypatch,
):
    (tmp_path / "app.py").write_text(
        "from otoe import Text\n"
        "import workspace_pkg.widgets.card as card\n"
        "app = Text(card.label())\n",
        encoding="utf-8",
    )
    package = tmp_path / "workspace_pkg"
    widgets = package / "widgets"
    widgets.mkdir(parents=True)
    (package / "__init__.py").write_text(
        "from .settings import PREFIX\n",
        encoding="utf-8",
    )
    (package / "settings.py").write_text(
        "PREFIX = 'Nested'\n",
        encoding="utf-8",
    )
    (widgets / "__init__.py").write_text(
        "from .card import label\n",
        encoding="utf-8",
    )
    (widgets / "card.py").write_text(
        "from workspace_pkg import PREFIX\n"
        "from .theme import SUFFIX\n"
        "def label():\n"
        "    return f'{PREFIX} {SUFFIX}'\n",
        encoding="utf-8",
    )
    (widgets / "theme.py").write_text(
        "SUFFIX = 'ready'\n",
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(tmp_path))

    files = auto_target_runtime_files("app:app")

    assert _relative_paths(files) == [
        "app.py",
        "workspace_pkg/__init__.py",
        "workspace_pkg/settings.py",
        "workspace_pkg/widgets/__init__.py",
        "workspace_pkg/widgets/card.py",
        "workspace_pkg/widgets/theme.py",
    ]


def test_auto_target_runtime_files_follow_package_target_imports(
    tmp_path,
    monkeypatch,
):
    package = tmp_path / "package_target"
    panels = package / "panels"
    panels.mkdir(parents=True)
    (package / "__init__.py").write_text(
        "from .boot import TITLE\n",
        encoding="utf-8",
    )
    (package / "boot.py").write_text(
        "TITLE = 'Package target'\n",
        encoding="utf-8",
    )
    (package / "app.py").write_text(
        "from otoe import Text\n"
        "from package_target.panels import summary\n"
        "app = Text(summary.text())\n",
        encoding="utf-8",
    )
    (panels / "__init__.py").write_text(
        "from .summary import text\n",
        encoding="utf-8",
    )
    (panels / "summary.py").write_text(
        "from package_target import TITLE\n"
        "def text():\n"
        "    return TITLE\n",
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(tmp_path))

    files = auto_target_runtime_files("package_target.app:app")

    assert _relative_paths(files) == [
        "package_target/__init__.py",
        "package_target/boot.py",
        "package_target/app.py",
        "package_target/panels/__init__.py",
        "package_target/panels/summary.py",
    ]


def test_auto_target_runtime_files_follow_namespace_package_target_imports(
    tmp_path,
    monkeypatch,
):
    package = tmp_path / "namespace_target"
    package.mkdir()
    (package / "app.py").write_text(
        "from otoe import Text\n"
        "from namespace_target.views import text\n"
        "app = Text(text())\n",
        encoding="utf-8",
    )
    (package / "views.py").write_text(
        "from namespace_target.tokens import TITLE\n"
        "def text():\n"
        "    return TITLE\n",
        encoding="utf-8",
    )
    (package / "tokens.py").write_text(
        "TITLE = 'Namespace package target'\n",
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(tmp_path))

    files = auto_target_runtime_files("namespace_target.app:app")

    assert _relative_paths(files) == [
        "namespace_target/app.py",
        "namespace_target/views.py",
        "namespace_target/tokens.py",
    ]


def test_auto_target_runtime_files_prefers_current_sys_path_over_stale_module(
    tmp_path,
    monkeypatch,
):
    old_root = tmp_path / "old"
    new_root = tmp_path / "new"
    old_root.mkdir()
    new_root.mkdir()
    old_source = old_root / "shadowed_runtime_app.py"
    new_source = new_root / "shadowed_runtime_app.py"
    old_source.write_text(
        "from otoe import Text\n"
        "app = Text('old')\n",
        encoding="utf-8",
    )
    new_source.write_text(
        "from otoe import Text\n"
        "from shadowed_helper import label\n"
        "app = Text(label())\n",
        encoding="utf-8",
    )
    (new_root / "shadowed_helper.py").write_text(
        "def label():\n"
        "    return 'new'\n",
        encoding="utf-8",
    )
    stale_module = types.ModuleType("shadowed_runtime_app")
    stale_module.__file__ = str(old_source)
    monkeypatch.setitem(sys.modules, "shadowed_runtime_app", stale_module)
    monkeypatch.syspath_prepend(str(new_root))

    files = auto_target_runtime_files("shadowed_runtime_app:app")

    assert _relative_paths(files) == [
        "shadowed_runtime_app.py",
        "shadowed_helper.py",
    ]
    assert files[0].source == new_source.resolve()


def _relative_paths(files) -> list[str]:
    return [Path(file.relative_path).as_posix() for file in files]
