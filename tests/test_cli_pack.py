from cli_helpers import (
    hashlib,
    json,
    os,
    subprocess,
    sys,
    tarfile,
    main,
    _write_backend_coverage_requirements,
    _refresh_manifest_artifact_hash,
)


def test_cli_pack_writes_verified_tarball(tmp_path, monkeypatch, capsys):
    app = tmp_path / "packed_app.py"
    app.write_text(
        "from otoe import Text\n"
        "app = Text('Packed app')\n",
        encoding="utf-8",
    )
    profile_file = tmp_path / "otoe.profile.toml"
    profile_file.write_text(
        'profile = "cage"\n'
        "\n"
        "[runtime]\n"
        'files = ["packed_app.py"]\n',
        encoding="utf-8",
    )
    output = tmp_path / "dist" / "pack-build"
    archive = tmp_path / "dist" / "pack-build.tar.gz"
    monkeypatch.syspath_prepend(str(tmp_path))

    assert (
        main(
            [
                "build",
                "packed_app:app",
                "--profile-file",
                str(profile_file),
                "--out",
                str(output),
                "--validate",
            ]
        )
        == 0
    )
    (output / "app" / "__pycache__").mkdir(exist_ok=True)
    (output / "app" / "__pycache__" / "ignored.pyc").write_bytes(b"ignored")
    (output / ".pytest_cache").mkdir()
    (output / ".pytest_cache" / "ignored").write_text("ignored", encoding="utf-8")
    (output / "frame.png").write_bytes(b"not part of the deploy bundle")

    result = main(["pack", str(output), "--out", str(archive)])

    captured = capsys.readouterr()
    assert result == 0
    assert f"pack {output}: {archive}" in captured.out
    assert "sha256:" in captured.out
    with tarfile.open(archive, "r:gz") as tar:
        names = tar.getnames()
        for member in tar.getmembers():
            target = tmp_path / "extracted" / member.name
            target.parent.mkdir(parents=True, exist_ok=True)
            source = tar.extractfile(member)
            assert source is not None
            target.write_bytes(source.read())
    assert "manifest.json" in names
    assert "otoe-plan.json" in names
    assert "otoe-deps.json" in names
    assert "otoe-styles.json" in names
    assert "otoe-run.py" in names
    assert "app/packed_app.py" in names
    assert "framework/otoe/native.py" in names
    assert "frame.png" not in names
    assert all("__pycache__" not in name for name in names)
    assert all(".pytest_cache" not in name for name in names)

    extracted = tmp_path / "extracted"
    verify = subprocess.run(
        [sys.executable, str(extracted / "otoe-run.py"), "--verify"],
        capture_output=True,
        cwd=extracted,
        env={**os.environ, "PYTHONPATH": ""},
        text=True,
    )
    assert verify.returncode == 0, verify.stderr
    assert "verified: manifest.json" in verify.stdout

def test_cli_pack_rejects_unmanifested_packable_files(
    tmp_path,
    monkeypatch,
    capsys,
):
    app = tmp_path / "hermetic_pack_app.py"
    app.write_text(
        "from otoe import Text\n"
        "app = Text('Hermetic pack')\n",
        encoding="utf-8",
    )
    profile_file = tmp_path / "otoe.profile.toml"
    profile_file.write_text(
        'profile = "cage"\n'
        "\n"
        "[runtime]\n"
        'files = ["hermetic_pack_app.py"]\n'
        "\n",
        encoding="utf-8",
    )
    output = tmp_path / "dist" / "hermetic-pack"
    archive = tmp_path / "dist" / "hermetic-pack.tar.gz"
    monkeypatch.syspath_prepend(str(tmp_path))

    assert (
        main(
            [
                "build",
                "hermetic_pack_app:app",
                "--profile-file",
                str(profile_file),
                "--out",
                str(output),
                "--validate",
            ]
        )
        == 0
    )
    capsys.readouterr()

    extras = (
        output / "app" / "debug.py",
        output / "assets" / "secret.txt",
        output / "framework" / "otoe" / "old_runtime.py",
    )
    for extra in extras:
        extra.parent.mkdir(parents=True, exist_ok=True)
        extra.write_text("extra\n", encoding="utf-8")

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
        assert f"unmanifested bundle file '{extra.relative_to(output)}'" in (
            verify.stderr
        )
        assert result == 1
        assert f"pack: unmanifested bundle file '{extra.relative_to(output)}'" in (
            captured.err
        )
        assert not archive.exists()
        extra.unlink()

def test_cli_pack_includes_backend_coverage_artifact(
    tmp_path,
    monkeypatch,
    capsys,
):
    app = tmp_path / "packed_backend_coverage_app.py"
    app.write_text(
        "from otoe import Text\n"
        "app = Text('Packed coverage app')\n",
        encoding="utf-8",
    )
    requirements = tmp_path / "backend-requirements.json"
    _write_backend_coverage_requirements(requirements)
    profile_file = tmp_path / "otoe.profile.toml"
    profile_file.write_text(
        'profile = "cage"\n'
        "\n"
        "[runtime]\n"
        'files = ["packed_backend_coverage_app.py"]\n'
        "\n"
        "[backend]\n"
        'coverage_requirements = "backend-requirements.json"\n',
        encoding="utf-8",
    )
    output = tmp_path / "dist" / "pack-backend-coverage"
    archive = tmp_path / "dist" / "pack-backend-coverage.tar.gz"
    extracted = tmp_path / "extracted-backend-coverage"
    monkeypatch.syspath_prepend(str(tmp_path))

    assert (
        main(
            [
                "build",
                "packed_backend_coverage_app:app",
                "--profile-file",
                str(profile_file),
                "--out",
                str(output),
                "--validate",
            ]
        )
        == 0
    )

    result = main(["pack", str(output), "--out", str(archive)])

    capsys.readouterr()
    assert result == 0
    with tarfile.open(archive, "r:gz") as tar:
        names = tar.getnames()
        for member in tar.getmembers():
            target = extracted / member.name
            target.parent.mkdir(parents=True, exist_ok=True)
            source = tar.extractfile(member)
            assert source is not None
            target.write_bytes(source.read())

    assert "otoe-backend-coverage.json" in names
    verify = subprocess.run(
        [sys.executable, str(extracted / "otoe-run.py"), "--verify"],
        capture_output=True,
        cwd=extracted,
        env={**os.environ, "PYTHONPATH": ""},
        text=True,
    )
    assert verify.returncode == 0, verify.stderr
    assert "verified: manifest.json" in verify.stdout

def test_cli_pack_rejects_tampered_bundle(tmp_path, monkeypatch, capsys):
    app = tmp_path / "tampered_pack_app.py"
    app.write_text(
        "from otoe import Text\n"
        "app = Text('Packed app')\n",
        encoding="utf-8",
    )
    profile_file = tmp_path / "otoe.profile.toml"
    profile_file.write_text(
        'profile = "cage"\n'
        "\n"
        "[runtime]\n"
        'files = ["tampered_pack_app.py"]\n',
        encoding="utf-8",
    )
    output = tmp_path / "dist" / "tampered-pack"
    archive = tmp_path / "dist" / "tampered-pack.tar.gz"
    monkeypatch.syspath_prepend(str(tmp_path))

    assert (
        main(
            [
                "build",
                "tampered_pack_app:app",
                "--profile-file",
                str(profile_file),
                "--out",
                str(output),
            ]
        )
        == 0
    )
    copied_app = output / "app" / "tampered_pack_app.py"
    copied_app.write_text(
        copied_app.read_text(encoding="utf-8").replace("Packed app", "Tampered!!"),
        encoding="utf-8",
    )

    result = main(["pack", str(output), "--out", str(archive)])

    captured = capsys.readouterr()
    assert result == 1
    assert not archive.exists()
    assert "pack: runner verification failed:" in captured.err
    assert "sha256 mismatch" in captured.err

def test_cli_pack_rejects_invalid_plan_after_hash_update(
    tmp_path,
    monkeypatch,
    capsys,
):
    app = tmp_path / "invalid_plan_drift_pack_app.py"
    app.write_text(
        "from otoe import Text\n"
        "app = Text('Invalid plan drift')\n",
        encoding="utf-8",
    )
    output = tmp_path / "dist" / "invalid-plan-drift-pack"
    archive = tmp_path / "dist" / "invalid-plan-drift-pack.tar.gz"
    monkeypatch.syspath_prepend(str(tmp_path))

    assert (
        main(
            [
                "build",
                "invalid_plan_drift_pack_app:app",
                "--out",
                str(output),
            ]
        )
        == 0
    )
    capsys.readouterr()

    plan_path = output / "otoe-plan.json"
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    plan["hasErrors"] = True
    plan["status"] = "invalid"
    plan_path.write_text(json.dumps(plan, sort_keys=True), encoding="utf-8")
    _refresh_manifest_artifact_hash(output, "otoe-plan.json")

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
    assert "otoe-plan.json: plan has errors" in verify.stderr
    assert result == 1
    assert not archive.exists()
    assert "pack: runner verification failed:" in captured.err
    assert "otoe-plan.json: plan has errors" in captured.err

def test_cli_pack_rejects_invalid_deps_after_hash_update(
    tmp_path,
    monkeypatch,
    capsys,
):
    app = tmp_path / "invalid_deps_drift_pack_app.py"
    app.write_text(
        "from otoe import Text\n"
        "app = Text('Invalid deps drift')\n",
        encoding="utf-8",
    )
    output = tmp_path / "dist" / "invalid-deps-drift-pack"
    archive = tmp_path / "dist" / "invalid-deps-drift-pack.tar.gz"
    monkeypatch.syspath_prepend(str(tmp_path))

    assert (
        main(
            [
                "build",
                "invalid_deps_drift_pack_app:app",
                "--out",
                str(output),
            ]
        )
        == 0
    )
    capsys.readouterr()

    deps_path = output / "otoe-deps.json"
    deps = json.loads(deps_path.read_text(encoding="utf-8"))
    deps["hasErrors"] = True
    deps["status"] = "invalid"
    deps_path.write_text(json.dumps(deps, sort_keys=True), encoding="utf-8")
    _refresh_manifest_artifact_hash(output, "otoe-deps.json")

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
    assert "otoe-deps.json: dependency audit has errors" in verify.stderr
    assert result == 1
    assert not archive.exists()
    assert "pack: runner verification failed:" in captured.err
    assert "otoe-deps.json: dependency audit has errors" in captured.err

def test_cli_pack_rejects_dependency_audit_resolution_drift_after_hash_update(
    tmp_path,
    monkeypatch,
    capsys,
):
    app = tmp_path / "deps_resolution_drift_pack_app.py"
    app.write_text(
        "from otoe import Text\n"
        "app = Text('Dependency resolution drift')\n",
        encoding="utf-8",
    )
    output = tmp_path / "dist" / "deps-resolution-drift-pack"
    archive = tmp_path / "dist" / "deps-resolution-drift-pack.tar.gz"
    monkeypatch.syspath_prepend(str(tmp_path))

    assert (
        main(
            [
                "build",
                "deps_resolution_drift_pack_app:app",
                "--out",
                str(output),
            ]
        )
        == 0
    )
    capsys.readouterr()

    deps_path = output / "otoe-deps.json"
    deps = json.loads(deps_path.read_text(encoding="utf-8"))
    deps["resolution"]["lockfile"] = True
    deps_path.write_text(json.dumps(deps, sort_keys=True), encoding="utf-8")
    _refresh_manifest_artifact_hash(output, "otoe-deps.json")

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
    assert "otoe-deps.json: resolution.lockfile must be false" in verify.stderr
    assert result == 1
    assert not archive.exists()
    assert "pack: runner verification failed:" in captured.err
    assert "otoe-deps.json: resolution.lockfile must be false" in captured.err

def test_cli_pack_rejects_dependency_runtime_policy_drift_after_hash_update(
    tmp_path,
    monkeypatch,
    capsys,
):
    app = tmp_path / "deps_runtime_policy_drift_pack_app.py"
    app.write_text(
        "from otoe import Text\n"
        "app = Text('Dependency runtime policy drift')\n",
        encoding="utf-8",
    )
    output = tmp_path / "dist" / "deps-runtime-policy-drift-pack"
    archive = tmp_path / "dist" / "deps-runtime-policy-drift-pack.tar.gz"
    monkeypatch.syspath_prepend(str(tmp_path))

    assert (
        main(
            [
                "build",
                "deps_runtime_policy_drift_pack_app:app",
                "--out",
                str(output),
            ]
        )
        == 0
    )
    capsys.readouterr()

    deps_path = output / "otoe-deps.json"
    deps = json.loads(deps_path.read_text(encoding="utf-8"))
    deps["runtimePolicy"]["mode"] = "enforced"
    deps_path.write_text(json.dumps(deps, sort_keys=True), encoding="utf-8")
    _refresh_manifest_artifact_hash(output, "otoe-deps.json")

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
    assert "otoe-deps.json: runtimePolicy.mode must be 'audit-only'" in verify.stderr
    assert result == 1
    assert not archive.exists()
    assert "pack: runner verification failed:" in captured.err
    assert "otoe-deps.json: runtimePolicy.mode must be 'audit-only'" in captured.err

def test_cli_pack_rejects_invalid_styles_after_hash_update(
    tmp_path,
    monkeypatch,
    capsys,
):
    app = tmp_path / "invalid_styles_drift_pack_app.py"
    app.write_text(
        "from otoe import Text\n"
        "app = Text('Invalid styles drift')\n",
        encoding="utf-8",
    )
    output = tmp_path / "dist" / "invalid-styles-drift-pack"
    archive = tmp_path / "dist" / "invalid-styles-drift-pack.tar.gz"
    monkeypatch.syspath_prepend(str(tmp_path))

    assert (
        main(
            [
                "build",
                "invalid_styles_drift_pack_app:app",
                "--out",
                str(output),
            ]
        )
        == 0
    )
    capsys.readouterr()

    styles_path = output / "otoe-styles.json"
    styles = json.loads(styles_path.read_text(encoding="utf-8"))
    styles["status"] = "invalid"
    styles_path.write_text(json.dumps(styles, sort_keys=True), encoding="utf-8")
    _refresh_manifest_artifact_hash(output, "otoe-styles.json")

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
    assert "otoe-styles.json: style artifact is invalid" in verify.stderr
    assert result == 1
    assert not archive.exists()
    assert "pack: runner verification failed:" in captured.err
    assert "otoe-styles.json: style artifact is invalid" in captured.err

def test_cli_pack_rejects_failing_backend_coverage_after_hash_update(
    tmp_path,
    monkeypatch,
    capsys,
):
    app = tmp_path / "backend_coverage_drift_pack_app.py"
    app.write_text(
        "from otoe import Text\n"
        "app = Text('Backend coverage drift')\n",
        encoding="utf-8",
    )
    requirements = tmp_path / "backend-requirements.json"
    _write_backend_coverage_requirements(requirements)
    profile_file = tmp_path / "otoe.profile.toml"
    profile_file.write_text(
        'profile = "cage"\n'
        "\n"
        "[runtime]\n"
        'files = ["backend_coverage_drift_pack_app.py"]\n'
        "\n"
        "[backend]\n"
        'coverage_requirements = "backend-requirements.json"\n',
        encoding="utf-8",
    )
    output = tmp_path / "dist" / "backend-coverage-drift-pack"
    archive = tmp_path / "dist" / "backend-coverage-drift-pack.tar.gz"
    monkeypatch.syspath_prepend(str(tmp_path))

    assert (
        main(
            [
                "build",
                "backend_coverage_drift_pack_app:app",
                "--profile-file",
                str(profile_file),
                "--out",
                str(output),
                "--validate",
            ]
        )
        == 0
    )
    capsys.readouterr()

    coverage_path = output / "otoe-backend-coverage.json"
    coverage = json.loads(coverage_path.read_text(encoding="utf-8"))
    coverage["passed"] = False
    coverage["blockers"] = ["widgetsCoverage"]
    coverage_path.write_text(json.dumps(coverage, sort_keys=True), encoding="utf-8")

    manifest_path = output / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for artifact in manifest["artifacts"]:
        if artifact["path"] == "otoe-backend-coverage.json":
            data = coverage_path.read_bytes()
            artifact["size"] = len(data)
            artifact["sha256"] = hashlib.sha256(data).hexdigest()
            break
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
        "otoe-backend-coverage.json: backend coverage failed: widgetsCoverage"
        in verify.stderr
    )
    assert result == 1
    assert not archive.exists()
    assert "pack: runner verification failed:" in captured.err
    assert "backend coverage failed: widgetsCoverage" in captured.err

def test_cli_pack_rejects_backend_coverage_without_traceable_evidence_map(
    tmp_path,
    monkeypatch,
    capsys,
):
    app = tmp_path / "backend_coverage_trace_pack_app.py"
    app.write_text(
        "from otoe import Text\n"
        "app = Text('Backend coverage traceability')\n",
        encoding="utf-8",
    )
    requirements = tmp_path / "backend-requirements.json"
    _write_backend_coverage_requirements(requirements)
    profile_file = tmp_path / "otoe.profile.toml"
    profile_file.write_text(
        'profile = "cage"\n'
        "\n"
        "[runtime]\n"
        'files = ["backend_coverage_trace_pack_app.py"]\n'
        "\n"
        "[backend]\n"
        'coverage_requirements = "backend-requirements.json"\n',
        encoding="utf-8",
    )
    output = tmp_path / "dist" / "backend-coverage-trace-pack"
    archive = tmp_path / "dist" / "backend-coverage-trace-pack.tar.gz"
    monkeypatch.syspath_prepend(str(tmp_path))

    assert (
        main(
            [
                "build",
                "backend_coverage_trace_pack_app:app",
                "--profile-file",
                str(profile_file),
                "--out",
                str(output),
                "--validate",
            ]
        )
        == 0
    )
    capsys.readouterr()

    coverage_path = output / "otoe-backend-coverage.json"
    coverage = json.loads(coverage_path.read_text(encoding="utf-8"))
    coverage["coverage"]["widgets"]["evidenceMap"]["Text"]["sources"] = []
    coverage_path.write_text(json.dumps(coverage, sort_keys=True), encoding="utf-8")
    _refresh_manifest_artifact_hash(output, "otoe-backend-coverage.json")

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
        "otoe-backend-coverage.json: coverage.widgets.evidenceMap.Text.sources "
        "must not be empty for exercised coverage"
    ) in verify.stderr
    assert result == 1
    assert not archive.exists()
    assert "pack: runner verification failed:" in captured.err
    assert "coverage.widgets.evidenceMap.Text.sources" in captured.err

def test_cli_pack_rejects_backend_coverage_without_capability_proof_observation(
    tmp_path,
    monkeypatch,
    capsys,
):
    app = tmp_path / "backend_coverage_capability_trace_pack_app.py"
    app.write_text(
        "from otoe import Text\n"
        "app = Text('Backend coverage capability traceability')\n",
        encoding="utf-8",
    )
    requirements = tmp_path / "backend-requirements.json"
    _write_backend_coverage_requirements(requirements)
    profile_file = tmp_path / "otoe.profile.toml"
    profile_file.write_text(
        'profile = "cage"\n'
        "\n"
        "[runtime]\n"
        'files = ["backend_coverage_capability_trace_pack_app.py"]\n'
        "\n"
        "[backend]\n"
        'coverage_requirements = "backend-requirements.json"\n',
        encoding="utf-8",
    )
    output = tmp_path / "dist" / "backend-coverage-capability-trace-pack"
    archive = tmp_path / "dist" / "backend-coverage-capability-trace-pack.tar.gz"
    monkeypatch.syspath_prepend(str(tmp_path))

    assert (
        main(
            [
                "build",
                "backend_coverage_capability_trace_pack_app:app",
                "--profile-file",
                str(profile_file),
                "--out",
                str(output),
                "--validate",
            ]
        )
        == 0
    )
    capsys.readouterr()

    coverage_path = output / "otoe-backend-coverage.json"
    coverage = json.loads(coverage_path.read_text(encoding="utf-8"))
    text_source = coverage["coverage"]["widgets"]["evidenceMap"]["Text"][
        "sources"
    ][0]
    text_source["capabilityProof"]["observedWidgets"].remove("Text")
    coverage_path.write_text(json.dumps(coverage, sort_keys=True), encoding="utf-8")
    _refresh_manifest_artifact_hash(output, "otoe-backend-coverage.json")

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
        "otoe-backend-coverage.json: coverage.widgets.evidenceMap.Text.sources[0]"
        ".capabilityProof.observedWidgets must include 'Text'"
    ) in verify.stderr
    assert result == 1
    assert not archive.exists()
    assert "pack: runner verification failed:" in captured.err
    assert "capabilityProof.observedWidgets must include 'Text'" in captured.err

def test_cli_pack_rejects_style_ir_drift_after_hash_update(
    tmp_path,
    monkeypatch,
    capsys,
):
    app = tmp_path / "drift_pack_app.py"
    app.write_text(
        "from otoe import Text\n"
        "app = Text('Style drift', className='shell')\n",
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
        'files = ["drift_pack_app.py"]\n',
        encoding="utf-8",
    )
    output = tmp_path / "dist" / "style-ir-drift-pack"
    archive = tmp_path / "dist" / "style-ir-drift-pack.tar.gz"
    monkeypatch.syspath_prepend(str(tmp_path))

    assert (
        main(
            [
                "build",
                "drift_pack_app:app",
                "--profile-file",
                str(profile_file),
                "--out",
                str(output),
                "--validate",
            ]
        )
        == 0
    )
    capsys.readouterr()

    styles_path = output / "otoe-styles.json"
    styles_payload = json.loads(styles_path.read_text(encoding="utf-8"))
    styles_payload["styleOps"]["classes"][0]["ops"][0]["value"] = {
        "type": "literal",
        "value": "#dc2626",
    }
    styles_path.write_text(json.dumps(styles_payload, sort_keys=True), encoding="utf-8")

    manifest_path = output / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for artifact in manifest["artifacts"]:
        if artifact["path"] == "otoe-styles.json":
            data = styles_path.read_bytes()
            artifact["size"] = len(data)
            artifact["sha256"] = hashlib.sha256(data).hexdigest()
            break
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
        "otoe-styles.json: styleOps validation failed: "
        "styleOps class 'shell' applied declarations do not match compiled rules"
        in verify.stderr
    )
    assert result == 1
    assert not archive.exists()
    assert "pack: runner verification failed:" in captured.err
    assert (
        "styleOps class 'shell' applied declarations do not match compiled rules"
        in captured.err
    )

def test_cli_pack_rejects_missing_manifest(tmp_path, capsys):
    bundle = tmp_path / "empty-bundle"
    bundle.mkdir()

    result = main(["pack", str(bundle), "--out", str(tmp_path / "bundle.tar.gz")])

    captured = capsys.readouterr()
    assert result == 1
    assert "pack: bundle is missing manifest.json" in captured.err
