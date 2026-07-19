import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tarfile

import pytest


ROOT = Path(__file__).resolve().parents[1]
RELEASE_CHECK = ROOT / "scripts" / "release_check.sh"


@pytest.mark.parametrize("dirty_state", ["unstaged", "staged", "untracked"])
def test_release_check_rejects_dirty_source_before_cleanup(
    tmp_path: Path,
    dirty_state: str,
) -> None:
    repo = tmp_path / "repo"
    scripts = repo / "scripts"
    scripts.mkdir(parents=True)
    script = scripts / "release_check.sh"
    shutil.copy2(RELEASE_CHECK, script)
    tracked = repo / "tracked.txt"
    tracked.write_text("committed\n", encoding="utf-8")
    cleanup_sentinel = repo / "build" / "keep.txt"
    cleanup_sentinel.parent.mkdir()
    cleanup_sentinel.write_text("keep\n", encoding="utf-8")

    _git(repo, "init", "-q")
    _git(repo, "config", "user.name", "Otoe Test")
    _git(repo, "config", "user.email", "otoe-test@example.invalid")
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "fixture")

    if dirty_state == "untracked":
        dirty_path = repo / "untracked.txt"
        dirty_path.write_text("dirty\n", encoding="utf-8")
    else:
        dirty_path = tracked
        dirty_path.write_text("dirty\n", encoding="utf-8")
        if dirty_state == "staged":
            _git(repo, "add", str(dirty_path))

    completed = subprocess.run(
        ["bash", str(script)],
        cwd=repo,
        env={**os.environ, "PYTHON": sys.executable},
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )

    assert completed.returncode == 1
    assert "source working tree and index must be clean" in completed.stderr
    assert dirty_path.name in completed.stderr
    assert cleanup_sentinel.read_text(encoding="utf-8") == "keep\n"


def test_sdist_manifest_prunes_ignored_native_preview(tmp_path: Path) -> None:
    project = tmp_path / "manifest-fixture"
    preview = project / "preview"
    native_preview = preview / "native"
    native_preview.mkdir(parents=True)
    shutil.copy2(ROOT / "MANIFEST.in", project / "MANIFEST.in")
    (project / "setup.py").write_text(
        "from setuptools import setup\nsetup(name='manifest-fixture', version='1.0')\n",
        encoding="utf-8",
    )
    (preview / "published.html").write_text("published\n", encoding="utf-8")
    (native_preview / "ignored.html").write_text("ignored\n", encoding="utf-8")
    dist = project / "dist"

    completed = subprocess.run(
        [sys.executable, "setup.py", "--quiet", "sdist", "--dist-dir", str(dist)],
        cwd=project,
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert completed.returncode == 0, completed.stderr
    archive = next(dist.glob("*.tar.gz"))
    with tarfile.open(archive, "r:gz") as source_distribution:
        members = source_distribution.getnames()
    assert any(name.endswith("/preview/published.html") for name in members)
    assert not any("/preview/native/" in name for name in members)


def test_release_check_uses_commit_timestamp_not_inherited_epoch(tmp_path: Path) -> None:
    repo = _release_fixture(tmp_path)
    epoch_output = tmp_path / "observed-epoch.txt"
    python_wrapper = tmp_path / "python-wrapper"
    python_wrapper.write_text(
        "#!/usr/bin/env bash\n"
        "if [[ \"${1:-}\" == -m && \"${2:-}\" == pip ]]; then\n"
        "  printf '%s\\n' \"$SOURCE_DATE_EPOCH\" > \"$EPOCH_OUTPUT\"\n"
        "  exit 91\n"
        "fi\n"
        f"exec {shlex.quote(sys.executable)} \"$@\"\n",
        encoding="utf-8",
    )
    python_wrapper.chmod(0o755)

    completed = subprocess.run(
        ["bash", "scripts/release_check.sh"],
        cwd=repo,
        env={
            **os.environ,
            "EPOCH_OUTPUT": str(epoch_output),
            "PYTHON": str(python_wrapper),
            "SOURCE_DATE_EPOCH": "1",
        },
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )

    expected_epoch = _git(repo, "show", "-s", "--format=%ct", "HEAD").strip()
    assert completed.returncode == 91
    assert epoch_output.read_text(encoding="utf-8").strip() == expected_epoch
    assert expected_epoch != "1"


def test_release_check_rejects_source_mutation_before_build(tmp_path: Path) -> None:
    repo = _release_fixture(tmp_path)
    tracked = repo / "tracked.txt"
    build_started = tmp_path / "build-started"
    python_wrapper = tmp_path / "python-wrapper"
    python_wrapper.write_text(
        "#!/usr/bin/env bash\n"
        "if [[ \"${1:-}\" == - ]]; then\n"
        f"  exec {shlex.quote(sys.executable)} \"$@\"\n"
        "fi\n"
        "if [[ \" $* \" == *' -m pytest '* ]]; then\n"
        "  printf 'mutated\\n' >> \"$MUTATE_PATH\"\n"
        "  exit 0\n"
        "fi\n"
        "if [[ \" $* \" == *' -m build '* ]]; then\n"
        "  : > \"$BUILD_STARTED\"\n"
        "fi\n"
        "exit 0\n",
        encoding="utf-8",
    )
    python_wrapper.chmod(0o755)

    completed = subprocess.run(
        ["bash", "scripts/release_check.sh"],
        cwd=repo,
        env={
            **os.environ,
            "BUILD_STARTED": str(build_started),
            "MUTATE_PATH": str(tracked),
            "PYTHON": str(python_wrapper),
        },
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )

    assert completed.returncode == 1
    assert "source working tree and index must be clean" in completed.stderr
    assert "tracked.txt" in completed.stderr
    assert not build_started.exists()


def _release_fixture(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    scripts = repo / "scripts"
    scripts.mkdir(parents=True)
    shutil.copy2(RELEASE_CHECK, scripts / "release_check.sh")
    (repo / "tracked.txt").write_text("committed\n", encoding="utf-8")
    _git(repo, "init", "-q")
    _git(repo, "config", "user.name", "Otoe Test")
    _git(repo, "config", "user.email", "otoe-test@example.invalid")
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "fixture")
    return repo


def _git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout
